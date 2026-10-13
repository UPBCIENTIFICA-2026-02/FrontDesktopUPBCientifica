# -*- coding: utf-8 -*-
"""Vista de Cómputo HPC (Contrato_HPC). Igual que HpcScreen.kt del móvil:
tarjeta del clúster (procesos en uso, nodos de la malla, cola), filtros
Todos / Activos / Finalizados, buscador, tarjetas de trabajo y formulario
"Nuevo trabajo". Mientras la vista está en pantalla se consulta cada 3 s, sin
parpadeo: las tarjetas se actualizan en su sitio.

El trabajo es código fuente + dataset del Home y se ejecuta con MPI en el
clúster; el resultado queda en "Resultados HPC/" del Home. ANTES el formulario
pedía un "comando" que el gestor ejecutaba con bash en su propia máquina."""

import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from ..theme import (
    PRIMARY, PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER, TERTIARY, EXITO, ERROR, SURFACE,
    SURFACE_CONTAINER_LOW, SURFACE_CONTAINER_HIGHEST,
    ON_SURFACE_VARIANT, INVERSE_SURFACE, INVERSE_ON_SURFACE, RADIUS_L, RADIUS_M, RADIUS_S,
    font, icon_font, glifo, mono, tint,
)
from ..widgets import (primary_button, tonal_button, filter_chip, chip, pill, circle,
                       SearchBar, Skeleton, empty_state, bind_click, Dialog, DetailsDialog,
                       TipoArchivo, formatear_hace, formatear_minutos)
from ..utils import run_async, describir
from ..data.hpc import (SolicitudTrabajo, PENDIENTE, EN_COLA, EJECUTANDO, COMPLETADO, GUARDANDO,
                        FALLIDO, TIMEOUT, CANCELADO, PRIORIDADES)

# Botón deshabilitado de Material 3 (igual que en el login).
DISABLED_BG = ("#E1E2E9", "#32353A")
DISABLED_FG = ("#9A9CA5", "#6B6E76")

INTERVALO_CONSULTA_MS = 3000
FILTROS = ["Todos", "Activos", "Finalizados"]

# Etiqueta, icono y color de cada estado del contrato; un solo sitio para lista y detalle.
ASPECTO = {
    PENDIENTE: ("Pendiente", "⌛", TERTIARY),
    EN_COLA: ("En cola", "⌛", TERTIARY),
    EJECUTANDO: ("Ejecutando", "↻", PRIMARY),
    GUARDANDO: ("Guardando resultado", "↻", PRIMARY),
    COMPLETADO: ("Completado", "✓", EXITO),
    FALLIDO: ("Fallido", "✕", ERROR),
    TIMEOUT: ("Tiempo agotado", "✕", ERROR),
    CANCELADO: ("Cancelado", "⊘", ON_SURFACE_VARIANT),
}


def _aspecto(t):
    return ASPECTO.get(t.estado, ASPECTO[FALLIDO])


def _texto_estado(t):
    etiqueta = _aspecto(t)[0]
    if t.estado == EN_COLA and t.posicion_cola:
        return f"{etiqueta} · posición {t.posicion_cola}"
    return etiqueta


def _pasa_filtro(t, filtro):
    return filtro == "Todos" or (filtro == "Activos") == t.activo


class HpcView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.filtro = "Todos"
        self.trabajos = []
        self.tarjetas = {}
        self._job = None
        self._cargado = False
        self._dialogo_detalle = None
        self._detalle_id = None

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(0, 6))
        primary_button(top, "＋  Nuevo trabajo", self._nuevo, width=170, height=48).pack(side="right", padx=(12, 0))
        self.busqueda = SearchBar(top, "Buscar trabajos", lambda _q: self._ordenar_tarjetas())
        self.busqueda.pack(side="left", fill="x", expand=True)

        self.cuerpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cuerpo.pack(fill="both", expand=True)
        self.esqueleto = Skeleton(self.cuerpo)
        self.esqueleto.pack(fill="x")

        self.toast = ctk.CTkLabel(self, text="", fg_color=INVERSE_SURFACE, text_color=INVERSE_ON_SURFACE,
                                  corner_radius=8, height=44, font=font("body"))

    @property
    def repo(self):
        # Se lee en cada uso: ApiClient.reconfigurar() puede cambiar el repositorio.
        return self.app.api.hpc

    # --- Consulta periódica mientras la vista está visible -------------------
    def on_show(self):
        self.actualizar()

    def on_hide(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None

    def actualizar(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(INTERVALO_CONSULTA_MS, self.actualizar)
        run_async(self, self.repo.consultar_todo, self._recibido, self._fallo)

    def _fallo(self, e):
        # Solo se muestra el error la primera vez; después se conserva lo último.
        if not self._cargado:
            self.on_hide()
            for w in self.cuerpo.winfo_children():
                w.destroy()
            empty_state(self.cuerpo, "☁", "No se pudo cargar", describir(e),
                        ("Reintentar", self._reintentar)).pack(pady=50)

    def _reintentar(self):
        for w in self.cuerpo.winfo_children():
            w.destroy()
        Skeleton(self.cuerpo).pack(fill="x")
        self.actualizar()

    def _recibido(self, datos):
        cluster, trabajos = datos
        if not self._cargado:
            self._construir()
            self._cargado = True
        self.trabajos = trabajos
        self._pintar_cluster(cluster)
        for t in trabajos:
            if t.id not in self.tarjetas:
                self.tarjetas[t.id] = TarjetaTrabajo(self.lista, t, self._detalles)
            else:
                self.tarjetas[t.id].actualizar(t)
        self._pintar_filtros()
        self._ordenar_tarjetas()
        if self._dialogo_detalle:
            self._refrescar_detalle()

    # --- Estructura (se construye una vez) -----------------------------------
    def _construir(self):
        for w in self.cuerpo.winfo_children():
            w.destroy()

        c = ctk.CTkFrame(self.cuerpo, fg_color=SURFACE_CONTAINER_LOW, corner_radius=RADIUS_L)
        c.pack(fill="x", padx=4, pady=(4, 12))
        head = ctk.CTkFrame(c, fg_color="transparent")
        head.pack(fill="x", padx=22, pady=(20, 0))
        circle(head, "▣", 40, PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER, size=17).pack(side="left")
        t = ctk.CTkFrame(head, fg_color="transparent")
        t.pack(side="left", padx=12)
        ctk.CTkLabel(t, text="Clúster UPB · malla Grid", font=font("title_medium"), anchor="w").pack(anchor="w")
        self.c_uso = ctk.CTkLabel(t, text="", font=font("body_small"), text_color=ON_SURFACE_VARIANT, anchor="w")
        self.c_uso.pack(anchor="w")
        self.c_estado = ctk.CTkFrame(head, fg_color="transparent")
        self.c_estado.pack(side="right")

        m = ctk.CTkFrame(c, fg_color="transparent")
        m.pack(fill="x", padx=22, pady=(16, 0))
        r = ctk.CTkFrame(m, fg_color="transparent")
        r.pack(fill="x")
        ctk.CTkLabel(r, text="Procesos MPI en uso", font=font("label_large")).pack(side="left")
        self.pct = ctk.CTkLabel(r, text="", font=font("label_large"), text_color=ON_SURFACE_VARIANT)
        self.pct.pack(side="right")
        self.barra = ctk.CTkProgressBar(m, height=8, fg_color=SURFACE_CONTAINER_HIGHEST)
        self.barra.pack(fill="x", pady=(6, 0))

        cifras = ctk.CTkFrame(c, fg_color="transparent")
        cifras.pack(fill="x", padx=22, pady=(18, 4))
        self.cifras = {}
        for i, nombre in enumerate(["Nodos disponibles", "En cola", "Ejecutando"]):
            cifras.grid_columnconfigure(i, weight=1, uniform="c")
            col = ctk.CTkFrame(cifras, fg_color="transparent")
            col.grid(row=0, column=i, sticky="w")
            v = ctk.CTkLabel(col, text="", font=font("title_large"), anchor="w")
            v.pack(anchor="w")
            ctk.CTkLabel(col, text=nombre, font=font("body_small"), text_color=ON_SURFACE_VARIANT).pack(anchor="w")
            self.cifras[nombre] = v
        self.c_nodos = ctk.CTkLabel(c, text="", font=font("body_small"), text_color=ON_SURFACE_VARIANT,
                                    anchor="w", justify="left", wraplength=900)
        self.c_nodos.pack(anchor="w", padx=22, pady=(8, 18))

        self.filtros = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        self.filtros.pack(fill="x", padx=4, pady=(0, 6))
        self.lista = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        self.lista.pack(fill="x", padx=4)
        self.vacio = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        self._conectado_pintado = None

    def _pintar_cluster(self, cl):
        self.c_uso.configure(text=f"{cl.procesos_en_uso} de {cl.procesos_totales} procesos en uso · "
                                  f"{cl.nodos_totales} nodos" + (f" ({cl.nodos_en_falla} en falla)" if cl.nodos_en_falla else ""))
        self.pct.configure(text=f"{round(cl.uso * 100)} %")
        self.barra.set(cl.uso)
        self.cifras["Nodos disponibles"].configure(text=f"{cl.nodos_disponibles}/{cl.nodos_totales}")
        self.cifras["En cola"].configure(text=str(cl.trabajos_en_cola))
        self.cifras["Ejecutando"].configure(text=str(cl.trabajos_ejecutando))
        self.c_nodos.configure(text="   ".join(
            f"{n[0]}: {n[3]}/{n[2]}{' · externo' if n[4] == 'EXTERNO' else ''}{' · EN FALLA' if n[1] == 'EN_FALLA' else ''}"
            for n in cl.nodos))
        clave = (self.repo.simulado, cl.ejecutor_conectado)
        if self._conectado_pintado != clave:
            self._conectado_pintado = clave
            for w in self.c_estado.winfo_children():
                w.destroy()
            if self.repo.simulado:
                chip(self.c_estado, "Simulado", "warn").pack(side="right")
            elif cl.ejecutor_conectado:
                ctk.CTkLabel(self.c_estado, text="●  job-runner en línea", text_color=EXITO,
                             font=font("label_medium")).pack(side="right")
            else:
                ctk.CTkLabel(self.c_estado, text="●  job-runner sin conexión: los trabajos esperan en cola",
                             text_color=ERROR, font=font("label_medium")).pack(side="right")

    def _pintar_filtros(self):
        for w in self.filtros.winfo_children():
            w.destroy()
        for f in FILTROS:
            n = sum(1 for t in self.trabajos if _pasa_filtro(t, f))
            filter_chip(self.filtros, f"{f} · {n}", f == self.filtro,
                        lambda f=f: self._cambiar_filtro(f)).pack(side="left", padx=(0, 8))

    def _cambiar_filtro(self, f):
        self.filtro = f
        self._pintar_filtros()
        self._ordenar_tarjetas()

    def _ordenar_tarjetas(self):
        if not self._cargado:
            return
        q = self.busqueda.value.strip().lower()
        visibles = [t for t in self.trabajos
                    if _pasa_filtro(t, self.filtro)
                    and (q in t.nombre.lower() or q in t.id.lower() or q in t.ruta_codigo.lower())]
        for tarjeta in self.tarjetas.values():
            tarjeta.pack_forget()
        for w in self.vacio.winfo_children():
            w.destroy()
        self.vacio.pack_forget()
        if not visibles:
            if q:
                empty_state(self.vacio, "🔍", "Sin resultados", f"Ningún trabajo coincide con \"{q}\".").pack()
            else:
                empty_state(self.vacio, "▣", "No hay trabajos aquí",
                            "Envía código y datos al clúster con \"Nuevo trabajo\".").pack()
            self.vacio.pack(pady=40)
            return
        for t in visibles:
            self.tarjetas[t.id].pack(fill="x", pady=(0, 12))

    # --- Detalles -----------------------------------------------------------
    def _detalles(self, trabajo):
        self._detalle_id = trabajo.id
        etiqueta, icono, color = _aspecto(trabajo)
        t = trabajo
        filas = [("Estado", _texto_estado(t)), ("Código", t.ruta_codigo),
                 ("Dataset", t.ruta_dataset or "—"),
                 ("Recursos", f"{t.procesos} procesos MPI · máximo {formatear_minutos(max(1, t.tiempo_maximo_s // 60))}"
                              f" · prioridad {t.prioridad.lower()}"),
                 ("Nodos", ", ".join(t.nodos) or "—"),
                 ("Resultado", (t.ruta_resultado or "—") + ("  (incompleto)" if t.incompleto else "")),
                 ("Detalle", t.mensaje_error or "—"),
                 ("Enviado", formatear_hace(t.enviado_en)), ("Identificador", t.id)]
        acciones = []
        if t.con_logs:
            acciones.append(("Ver registros", lambda: self._ver_logs(t), PRIMARY))
        if t.activo:
            acciones.append(("Cancelar trabajo", lambda: self._cancelar(t), ERROR))
        if t.reintentable:
            acciones.append(("Reintentar", lambda: self._reintentar_trabajo(t), PRIMARY))
        self._dialogo_detalle = DetailsDialog(self, t.nombre, TipoArchivo(etiqueta, icono, color[0]), filas, acciones)

    def _refrescar_detalle(self):
        """La hoja sigue mostrando el estado más reciente mientras está abierta."""
        d = self._dialogo_detalle
        try:
            if not d.winfo_exists():
                self._dialogo_detalle = None
                return
        except Exception:
            self._dialogo_detalle = None
            return
        t = next((x for x in self.trabajos if x.id == self._detalle_id), None)
        if t is None:
            return
        d.valores["Estado"].configure(text=_texto_estado(t))
        d.valores["Nodos"].configure(text=", ".join(t.nodos) or "—")
        d.valores["Resultado"].configure(text=(t.ruta_resultado or "—") + ("  (incompleto)" if t.incompleto else ""))
        d.valores["Detalle"].configure(text=t.mensaje_error or "—")
        d.valores["Enviado"].configure(text=formatear_hace(t.enviado_en))

    def _ver_logs(self, t):
        dlg = Dialog(self, f"Registros · {t.nombre}", 760, 520)
        caja = ctk.CTkTextbox(dlg, font=mono(12), wrap="none")
        caja.pack(fill="both", expand=True, padx=16, pady=16)
        caja.insert("1.0", "Cargando…")
        caja.configure(state="disabled")

        def mostrar(texto):
            if caja.winfo_exists():
                caja.configure(state="normal")
                caja.delete("1.0", "end")
                caja.insert("1.0", texto or "(sin salida)")
                caja.configure(state="disabled")

        run_async(self, lambda: self.repo.logs(t.id), mostrar, lambda e: mostrar(f"No se pudieron leer: {describir(e)}"))

    def _cancelar(self, t):
        def ok(_r):
            self._mostrar_toast(f"Trabajo #{t.id_corto} cancelado")
            self.actualizar()
        run_async(self, lambda: self.repo.cancelar(t.id), ok,
                  lambda e: self._mostrar_toast(f"No se pudo cancelar: {describir(e)}"))

    def _reintentar_trabajo(self, t):
        def ok(r):
            nuevo, aviso = r
            self._mostrar_toast(f"Reintento enviado (#{(nuevo or '')[:8]}). {aviso or ''}")
            self.actualizar()
        run_async(self, lambda: self.repo.reintentar(t.id), ok,
                  lambda e: self._mostrar_toast(f"No se pudo reintentar: {describir(e)}"))

    # --- Nuevo trabajo -------------------------------------------------------
    def _nuevo(self):
        NuevoTrabajoDialog(self, self.repo, self._enviar)

    def _enviar(self, solicitud, dialogo):
        def ok(trabajo):
            dialogo.destroy()
            self._mostrar_toast(f"Trabajo #{trabajo.id_corto} enviado al clúster")
            self.actualizar()

        def err(e):
            dialogo.fallo(describir(e))

        run_async(self, lambda: self.repo.enviar_trabajo(solicitud), ok, err)

    def _mostrar_toast(self, texto):
        """Snackbar: aviso breve abajo a la izquierda."""
        self.toast.configure(text=f"   {texto}   ")
        self.toast.place(relx=0.0, rely=1.0, x=8, y=-8, anchor="sw")
        self.toast.lift()
        self.after(4500, self.toast.place_forget)


class TarjetaTrabajo(ctk.CTkFrame):
    """OutlinedCard de un trabajo; se actualiza en su sitio en cada consulta."""

    def __init__(self, master, trabajo, on_click):
        super().__init__(master, fg_color=SURFACE, border_width=1, corner_radius=RADIUS_M,
                         border_color=("#C4C6D0", "#44474F"))
        self.t = trabajo
        self.on_click = on_click
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=16, pady=(16, 0))
        self.icono = ctk.CTkLabel(fila, text="", width=40, height=40, corner_radius=RADIUS_S, font=icon_font(17))
        self.icono.pack(side="left")
        txt = ctk.CTkFrame(fila, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True, padx=12)
        ctk.CTkLabel(txt, text=trabajo.nombre, font=font("title_small"), anchor="w").pack(anchor="w")
        self.sub = ctk.CTkLabel(txt, text="", font=font("body_small"), text_color=ON_SURFACE_VARIANT, anchor="w")
        self.sub.pack(anchor="w")
        self.estado_holder = ctk.CTkFrame(fila, fg_color="transparent")
        self.estado_holder.pack(side="right")

        self.prog_box = ctk.CTkFrame(self, fg_color="transparent")
        self.barra = ctk.CTkProgressBar(self.prog_box, height=6, fg_color=SURFACE_CONTAINER_HIGHEST,
                                        mode="indeterminate")
        self.barra.pack(side="left", fill="x", expand=True)

        self.pie = ctk.CTkFrame(self, fg_color="transparent")
        self.pie.pack(fill="x", padx=16, pady=(12, 16))
        codigo = trabajo.ruta_codigo + (f"  ·  {trabajo.ruta_dataset}" if trabajo.ruta_dataset else "")
        ctk.CTkLabel(self.pie, text=codigo, font=mono(12), text_color=ON_SURFACE_VARIANT, anchor="w").pack(anchor="w")
        self.linea = ctk.CTkLabel(self.pie, text="", font=font("body_small"), text_color=ON_SURFACE_VARIANT,
                                  anchor="w", justify="left", wraplength=820)
        self.linea.pack(anchor="w")
        self._estado_pintado = None
        self.actualizar(trabajo)
        bind_click(self, lambda: self.on_click(self.t), hover=SURFACE_CONTAINER_LOW)

    def actualizar(self, t):
        self.t = t
        etiqueta, icono, color = _aspecto(t)
        self.sub.configure(text=f"#{t.id_corto} · {formatear_hace(t.enviado_en)}")
        partes = [f"{t.procesos} procesos", f"prioridad {t.prioridad.lower()}"]
        if t.nodos and t.estado == EJECUTANDO:
            partes.append("en " + ", ".join(t.nodos))
        if t.ruta_resultado:
            partes.append("resultado: " + t.ruta_resultado)
        if t.mensaje_error and t.estado != COMPLETADO:
            partes.append(t.mensaje_error)
        self.linea.configure(text=" · ".join(partes))
        if self._estado_pintado != t.estado:
            self._estado_pintado = t.estado
            self.icono.configure(text=glifo(icono), text_color=color, fg_color=tint(color, 0.14, SURFACE))
            for w in self.estado_holder.winfo_children():
                w.destroy()
            p = pill(self.estado_holder, etiqueta, color)
            p.pack()
            for w in [p] + list(p.winfo_children()):
                w.bind("<Button-1>", lambda _e: self.on_click(self.t))
            self.barra.stop()
            if t.activo:
                # OpenMPI no informa el porcentaje de avance: barra indeterminada.
                self.barra.configure(progress_color=color)
                self.prog_box.pack(fill="x", padx=16, pady=(14, 0), before=self.pie)
                self.barra.start()
            else:
                self.prog_box.pack_forget()


class NuevoTrabajoDialog(Dialog):
    """HojaNuevoTrabajo: código fuente y dataset del Home + recursos (Contrato_HPC §3.1).

    "Elegir…" sube el archivo del PC a "Trabajos HPC/" del Home y rellena la ruta;
    también se puede escribir la ruta de algo que ya esté en el Home."""

    def __init__(self, master, repo, on_enviar):
        super().__init__(master, "Nuevo trabajo", 600, 690)
        self.repo = repo
        self.on_enviar = on_enviar
        self.prioridad = "NORMAL"
        self.ocupado = False

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=26, pady=(22, 0))
        ctk.CTkLabel(body, text="Nuevo trabajo", font=font("title_large")).pack(anchor="w")
        ctk.CTkLabel(body, text="Tu código se compila y se ejecuta con MPI en el clúster; el resultado "
                                "queda en \"Resultados HPC\" de tu Home.",
                     font=font("body"), text_color=ON_SURFACE_VARIANT, wraplength=540, justify="left").pack(anchor="w", pady=(2, 14))

        self.e_nombre = self._campo(body, "Nombre del trabajo", "Simulación de fluidos")
        self.e_codigo = self._campo_archivo(body, "Código fuente (.c, .cpp o .py con mpi4py)", "/Proyectos/simulacion.c")
        self.e_dataset = self._campo_archivo(body, "Dataset (opcional)", "/Proyectos/datos.csv")

        fila = ctk.CTkFrame(body, fg_color="transparent")
        fila.pack(fill="x", pady=(2, 10))
        izq = ctk.CTkFrame(fila, fg_color="transparent")
        izq.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(izq, text="Procesos MPI", font=font("label_medium"), text_color=ON_SURFACE_VARIANT).pack(anchor="w")
        self.e_procesos = ctk.CTkEntry(izq, height=40, width=120, font=font("body_large"))
        self.e_procesos.insert(0, "4")
        self.e_procesos.pack(anchor="w", pady=(4, 0))
        der = ctk.CTkFrame(fila, fg_color="transparent")
        der.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(der, text="Tiempo máximo (minutos)", font=font("label_medium"), text_color=ON_SURFACE_VARIANT).pack(anchor="w")
        self.e_tiempo = ctk.CTkEntry(der, height=40, width=120, font=font("body_large"))
        self.e_tiempo.insert(0, "10")
        self.e_tiempo.pack(anchor="w", pady=(4, 0))

        ctk.CTkLabel(body, text="Prioridad", font=font("label_medium"), text_color=ON_SURFACE_VARIANT).pack(anchor="w")
        self.seg = ctk.CTkSegmentedButton(body, values=[p.capitalize() for p in PRIORIDADES],
                                          command=lambda v: setattr(self, "prioridad", v.upper()))
        self.seg.set("Normal")
        self.seg.pack(anchor="w", pady=(4, 10))
        self.e_param = self._campo(body, "Parámetros (opcional): clave=valor separados por comas", "iteraciones=1000, tolerancia=0.01")

        self.aviso = ctk.CTkLabel(body, text="", font=font("body_small"), text_color=ERROR, wraplength=540, justify="left")
        self.aviso.pack(anchor="w")
        for e in (self.e_nombre, self.e_codigo, self.e_procesos, self.e_tiempo):
            e.bind("<KeyRelease>", lambda _e: self._validar(), add="+")

        self.btn = primary_button(self, "Enviar al clúster", self._enviar, width=540, height=52)
        self.btn.pack(fill="x", padx=26, pady=20, side="bottom")
        self._validar()
        self.after(150, self.e_nombre.focus_set)

    def _campo(self, padre, etiqueta, ejemplo):
        ctk.CTkLabel(padre, text=etiqueta, font=font("label_medium"), text_color=ON_SURFACE_VARIANT).pack(anchor="w")
        e = ctk.CTkEntry(padre, height=40, placeholder_text=ejemplo, font=font("body_large"))
        e.pack(fill="x", pady=(4, 10))
        return e

    def _campo_archivo(self, padre, etiqueta, ejemplo):
        ctk.CTkLabel(padre, text=etiqueta, font=font("label_medium"), text_color=ON_SURFACE_VARIANT).pack(anchor="w")
        f = ctk.CTkFrame(padre, fg_color="transparent")
        f.pack(fill="x", pady=(4, 10))
        e = ctk.CTkEntry(f, height=40, placeholder_text=f"Ruta en tu Home, p. ej. {ejemplo}", font=mono(13))
        e.pack(side="left", fill="x", expand=True)
        tonal_button(f, "Elegir…", lambda: self._elegir(e), width=96, height=40).pack(side="left", padx=(8, 0))
        return e

    def _elegir(self, entrada):
        ruta = filedialog.askopenfilename(parent=self, title="Elegir archivo para el trabajo")
        if not ruta:
            return
        self._ocupado(True, "Subiendo a tu Home…")

        def ok(ruta_home):
            entrada.delete(0, "end")
            entrada.insert(0, ruta_home)
            self._ocupado(False)

        run_async(self, lambda: self.repo.subir_al_home(ruta), ok,
                  lambda e: self._ocupado(False, f"No se pudo subir: {describir(e)}"))

    def _ocupado(self, valor, aviso=""):
        self.ocupado = valor
        self.aviso.configure(text=aviso, text_color=ON_SURFACE_VARIANT if valor else ERROR)
        self._validar()

    @staticmethod
    def _entero(e, minimo):
        try:
            v = int(e.get().strip())
            return v if v >= minimo else None
        except ValueError:
            return None

    def _parametros(self):
        params = {}
        for parte in self.e_param.get().split(","):
            if parte.strip():
                k, _, v = parte.partition("=")
                params[k.strip()] = v.strip()
        return params

    def _validar(self):
        valido = (bool(self.e_nombre.get().strip()) and bool(self.e_codigo.get().strip())
                  and self._entero(self.e_procesos, 1) is not None and self._entero(self.e_tiempo, 1) is not None)
        listo = valido and not self.ocupado
        self.btn.configure(state="normal" if listo else "disabled",
                           fg_color=PRIMARY if listo else DISABLED_BG, text_color_disabled=DISABLED_FG,
                           text="Enviando…" if self.ocupado and self.aviso.cget("text") == "" else "Enviar al clúster")

    def fallo(self, mensaje):
        """El servidor rechazó el trabajo: se queda abierto para corregirlo."""
        self._ocupado(False, f"No se pudo enviar: {mensaje}")

    def _enviar(self):
        if self.ocupado:
            return
        self.ocupado = True
        self.aviso.configure(text="")
        self._validar()
        self.on_enviar(SolicitudTrabajo(
            nombre=self.e_nombre.get().strip(), ruta_codigo=self.e_codigo.get().strip(),
            ruta_dataset=self.e_dataset.get().strip(), procesos=self._entero(self.e_procesos, 1),
            tiempo_maximo_s=self._entero(self.e_tiempo, 1) * 60, prioridad=self.prioridad,
            parametros=self._parametros()), self)
