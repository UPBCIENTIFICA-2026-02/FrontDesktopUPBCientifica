# -*- coding: utf-8 -*-
"""Vista de Cómputo HPC. Igual que HpcScreen.kt del móvil: tarjeta del clúster
(nodos, CPU, GPU, cola), filtros Todos / Activos / Finalizados, buscador,
tarjetas de trabajo con su estado y progreso, hoja de detalles y formulario
"Nuevo trabajo". Mientras la vista está en pantalla se consulta el estado cada
3 s, sin parpadeo: las tarjetas se actualizan en su sitio.

Con el servicio real (job-api) el formulario pide nombre, comando y prioridad,
que es lo que acepta; job-api todavía no informa la carga del clúster ni el
porcentaje de avance, y la tarjeta del clúster lo dice en vez de inventarlo."""

import customtkinter as ctk

from ..theme import (
    PRIMARY, PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER, TERTIARY, EXITO, ERROR, SURFACE,
    SURFACE_CONTAINER_LOW, SURFACE_CONTAINER_HIGH, SURFACE_CONTAINER_HIGHEST,
    ON_SURFACE_VARIANT, INVERSE_SURFACE, INVERSE_ON_SURFACE, RADIUS_L, RADIUS_M, RADIUS_S,
    font, icon_font, glifo, mono, tint,
)

# Botón deshabilitado de Material 3 (igual que en el login).
DISABLED_BG = ("#E1E2E9", "#32353A")
DISABLED_FG = ("#9A9CA5", "#6B6E76")
from ..widgets import (primary_button, tonal_button, filter_chip, chip, pill, circle,
                       SearchBar, Skeleton, empty_state, bind_click, Dialog, DetailsDialog,
                       TipoArchivo, formatear_hace, formatear_minutos)
from ..utils import run_async, describir
from ..data.hpc import SolicitudTrabajo, EN_COLA, EJECUTANDO, COMPLETADO, FALLIDO, CANCELADO

INTERVALO_CONSULTA_MS = 3000
FILTROS = ["Todos", "Activos", "Finalizados"]

# Etiqueta, icono y color de cada estado; un solo sitio para lista y detalle.
ASPECTO = {
    EN_COLA: ("En cola", "⌛", TERTIARY),
    EJECUTANDO: ("Ejecutando", "↻", PRIMARY),
    COMPLETADO: ("Completado", "✓", EXITO),
    FALLIDO: ("Fallido", "✕", ERROR),
    CANCELADO: ("Cancelado", "⊘", ON_SURFACE_VARIANT),
}


def _texto_estado(t):
    etiqueta = ASPECTO[t.estado][0]
    if t.estado == EJECUTANDO and t.progreso is not None:
        return f"{etiqueta} · {round(t.progreso * 100)} %"
    return etiqueta


def _pasa_filtro(t, filtro):
    return filtro == "Todos" or (filtro == "Activos") == t.activo


class HpcView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.repo = app.api.hpc
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

        # Tarjeta del clúster
        c = ctk.CTkFrame(self.cuerpo, fg_color=SURFACE_CONTAINER_LOW, corner_radius=RADIUS_L)
        c.pack(fill="x", padx=4, pady=(4, 12))
        head = ctk.CTkFrame(c, fg_color="transparent")
        head.pack(fill="x", padx=22, pady=(20, 0))
        circle(head, "▣", 40, PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER, size=17).pack(side="left")
        t = ctk.CTkFrame(head, fg_color="transparent")
        t.pack(side="left", padx=12)
        ctk.CTkLabel(t, text="Clúster UPB", font=font("title_medium"), anchor="w").pack(anchor="w")
        self.c_uso = ctk.CTkLabel(t, text="", font=font("body_small"), text_color=ON_SURFACE_VARIANT, anchor="w")
        self.c_uso.pack(anchor="w")
        if self.repo.simulado:
            ctk.CTkLabel(head, text="●  En línea", text_color=EXITO, font=font("label_medium")).pack(side="right")
            chip(head, "Simulado", "warn").pack(side="right", padx=12)
        else:
            chip(head, f"job-api · {self.app.api.conf.url_trabajos}", "ok").pack(side="right", padx=12)

        self.medidores = {}
        # job-api no informa la carga: sin medidores, y las cifras son de tus trabajos.
        for nombre in (("CPU", "GPU") if self.repo.simulado else ()):
            m = ctk.CTkFrame(c, fg_color="transparent")
            m.pack(fill="x", padx=22, pady=(16 if nombre == "CPU" else 10, 0))
            r = ctk.CTkFrame(m, fg_color="transparent")
            r.pack(fill="x")
            ctk.CTkLabel(r, text=nombre, font=font("label_large")).pack(side="left")
            pct = ctk.CTkLabel(r, text="", font=font("label_large"), text_color=ON_SURFACE_VARIANT)
            pct.pack(side="right")
            barra = ctk.CTkProgressBar(m, height=8, fg_color=SURFACE_CONTAINER_HIGHEST)
            barra.pack(fill="x", pady=(6, 0))
            self.medidores[nombre] = (pct, barra)

        cifras = ctk.CTkFrame(c, fg_color="transparent")
        cifras.pack(fill="x", padx=22, pady=(18, 20))
        self.cifras = {}
        etiquetas = ["Nodos activos", "En cola", "Libres"] if self.repo.simulado else ["Ejecutando", "En cola", "Terminados"]
        for i, nombre in enumerate(etiquetas):
            cifras.grid_columnconfigure(i, weight=1, uniform="c")
            col = ctk.CTkFrame(cifras, fg_color="transparent")
            col.grid(row=0, column=i, sticky="w")
            v = ctk.CTkLabel(col, text="", font=font("title_large"), anchor="w")
            v.pack(anchor="w")
            ctk.CTkLabel(col, text=nombre, font=font("body_small"), text_color=ON_SURFACE_VARIANT).pack(anchor="w")
            self.cifras[nombre] = v

        self.filtros = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        self.filtros.pack(fill="x", padx=4, pady=(0, 6))
        self.lista = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        self.lista.pack(fill="x", padx=4)
        self.vacio = ctk.CTkFrame(self.cuerpo, fg_color="transparent")

    def _pintar_cluster(self, cl):
        if cl is None:
            self.c_uso.configure(text="El servidor aún no informa la carga de los nodos")
            self.cifras["Ejecutando"].configure(text=str(sum(1 for t in self.trabajos if t.estado == EJECUTANDO)))
            self.cifras["En cola"].configure(text=str(sum(1 for t in self.trabajos if t.estado == EN_COLA)))
            self.cifras["Terminados"].configure(text=str(sum(1 for t in self.trabajos if not t.activo)))
            return
        self.c_uso.configure(text=f"{cl.nodos_activos} de {cl.nodos_totales} nodos en uso")
        for nombre, valor in (("CPU", cl.uso_cpu), ("GPU", cl.uso_gpu)):
            pct, barra = self.medidores[nombre]
            pct.configure(text=f"{round(valor * 100)} %")
            barra.set(valor)
        self.cifras["Nodos activos"].configure(text=f"{cl.nodos_activos}/{cl.nodos_totales}")
        self.cifras["En cola"].configure(text=str(cl.trabajos_en_cola))
        self.cifras["Libres"].configure(text=str(cl.nodos_totales - cl.nodos_activos))

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
                    if _pasa_filtro(t, self.filtro) and (q in t.nombre.lower() or q in t.id.lower())]
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
                            "Envía un trabajo al clúster con \"Nuevo trabajo\".").pack()
            self.vacio.pack(pady=40)
            return
        for t in visibles:
            self.tarjetas[t.id].pack(fill="x", pady=(0, 12))

    # --- Detalles -----------------------------------------------------------
    def _detalles(self, trabajo):
        self._detalle_id = trabajo.id
        self._abrir_detalle(trabajo)

    def _abrir_detalle(self, t):
        etiqueta, icono, color = ASPECTO[t.estado]
        filas = [("Estado", _texto_estado(t)), ("Comando", t.comando), ("Prioridad", f"{t.prioridad} de 10")]
        if t.recursos:
            nodos, cpus, memoria, tiempo = t.recursos
            filas += [("Recursos", f"{nodos} nodos × {cpus} CPU · {memoria} GB RAM"),
                      ("Tiempo máximo", formatear_minutos(tiempo))]
        if t.resultado:
            filas.append(("Salida", t.resultado[:300]))
        if t.mensaje_error:
            filas.append(("Error", t.mensaje_error[:300]))
        filas += [("Enviado", formatear_hace(t.enviado_en)), ("Identificador", t.id)]
        acciones = [("Cancelar trabajo", lambda: self._cancelar(t), ERROR)] if t.activo else []
        self._dialogo_detalle = DetailsDialog(self, t.nombre, TipoArchivo(etiqueta, icono, color[0]), filas, acciones)

    def _cancelar(self, t):
        def ok(_r):
            self._mostrar_toast(f"Trabajo #{t.id_corto} cancelado")
            self.actualizar()
        run_async(self, lambda: self.repo.cancelar(t.id), ok,
                  lambda e: self._mostrar_toast(f"No se pudo cancelar: {describir(e)}"))

    def _refrescar_detalle(self):
        """La hoja sigue mostrando el progreso más reciente mientras está abierta."""
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
        d.valores["Enviado"].configure(text=formatear_hace(t.enviado_en))

    # --- Nuevo trabajo -------------------------------------------------------
    def _nuevo(self):
        NuevoTrabajoDialog(self, self._enviar)

    def _enviar(self, solicitud, dialogo):
        def ok(trabajo):
            dialogo.destroy()
            self._mostrar_toast(f"Trabajo #{trabajo.id_corto} enviado al clúster")
            self.actualizar()

        def err(e):
            dialogo.destroy()
            self._mostrar_toast(f"No se pudo enviar: {describir(e)}")

        run_async(self, lambda: self.repo.enviar_trabajo(solicitud), ok, err)

    def _mostrar_toast(self, texto):
        """Snackbar: aviso breve abajo a la izquierda."""
        self.toast.configure(text=f"   {texto}   ")
        self.toast.place(relx=0.0, rely=1.0, x=8, y=-8, anchor="sw")
        self.toast.lift()
        self.after(3500, self.toast.place_forget)


class TarjetaTrabajo(ctk.CTkFrame):
    """OutlinedCard de un trabajo; se actualiza en su sitio en cada consulta."""

    def __init__(self, master, trabajo, on_click):
        super().__init__(master, fg_color=SURFACE, border_width=1, corner_radius=RADIUS_M,
                         border_color=("#C4C6D0", "#44474F"))
        self.t = trabajo
        self.on_click = on_click
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=16, pady=(16, 0))
        self.icono = ctk.CTkLabel(fila, text="", width=40, height=40, corner_radius=RADIUS_S,
                                  font=icon_font(17))
        self.icono.pack(side="left")
        txt = ctk.CTkFrame(fila, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True, padx=12)
        ctk.CTkLabel(txt, text=trabajo.nombre, font=font("title_small"), anchor="w").pack(anchor="w")
        self.sub = ctk.CTkLabel(txt, text="", font=font("body_small"), text_color=ON_SURFACE_VARIANT, anchor="w")
        self.sub.pack(anchor="w")
        self.estado_holder = ctk.CTkFrame(fila, fg_color="transparent")
        self.estado_holder.pack(side="right")

        self.prog_box = ctk.CTkFrame(self, fg_color="transparent")
        self.barra = ctk.CTkProgressBar(self.prog_box, height=6, fg_color=SURFACE_CONTAINER_HIGHEST)
        self.barra.pack(side="left", fill="x", expand=True)
        self.pct = ctk.CTkLabel(self.prog_box, text="", font=font("label_medium"),
                                text_color=ON_SURFACE_VARIANT, width=44)
        self.pct.pack(side="left", padx=(12, 0))

        self.pie = ctk.CTkFrame(self, fg_color="transparent")
        self.pie.pack(fill="x", padx=16, pady=(12, 16))
        ctk.CTkLabel(self.pie, text=trabajo.comando, font=mono(12), text_color=ON_SURFACE_VARIANT,
                     anchor="w").pack(anchor="w")
        if trabajo.recursos:
            nodos, cpus, memoria, _ = trabajo.recursos
            linea = f"{nodos} nodos · {nodos * cpus} CPU · {memoria} GB"
        else:
            linea = f"Prioridad {trabajo.prioridad}"
        ctk.CTkLabel(self.pie, text=linea, font=font("body_small"),
                     text_color=ON_SURFACE_VARIANT, anchor="w").pack(anchor="w")
        self._estado_pintado = None
        self.actualizar(trabajo)
        bind_click(self, lambda: self.on_click(self.t), hover=SURFACE_CONTAINER_LOW)

    def actualizar(self, t):
        self.t = t
        etiqueta, icono, color = ASPECTO[t.estado]
        self.sub.configure(text=f"#{t.id_corto} · {formatear_hace(t.enviado_en)}")
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
            if t.estado == EJECUTANDO and t.progreso is not None:
                self.barra.configure(mode="determinate", progress_color=PRIMARY)
                self.pct.pack(side="left", padx=(12, 0))
                self.prog_box.pack(fill="x", padx=16, pady=(14, 0), before=self.pie)
            elif t.activo:
                # En cola, o ejecutando sin porcentaje conocido (job-api no lo informa).
                self.barra.configure(mode="indeterminate", progress_color=color)
                self.pct.pack_forget()
                self.prog_box.pack(fill="x", padx=16, pady=(14, 0), before=self.pie)
                self.barra.start()
            else:
                self.prog_box.pack_forget()
        if t.estado == EJECUTANDO and t.progreso is not None:
            self.barra.set(t.progreso)
            self.pct.configure(text=f"{round(t.progreso * 100)} %")


class NuevoTrabajoDialog(Dialog):
    """HojaNuevoTrabajo: lo que acepta job-api (nombre, comando y prioridad)."""

    def __init__(self, master, on_enviar):
        super().__init__(master, "Nuevo trabajo", 540, 470)
        self.on_enviar = on_enviar
        self.prioridad = 5
        self.enviando = False

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=26, pady=(22, 0))
        ctk.CTkLabel(body, text="Nuevo trabajo", font=font("title_large")).pack(anchor="w")
        ctk.CTkLabel(body, text="Se enviará a la cola del clúster UPB", font=font("body"),
                     text_color=ON_SURFACE_VARIANT).pack(anchor="w", pady=(2, 16))

        ctk.CTkLabel(body, text="Nombre del trabajo", font=font("label_medium"),
                     text_color=ON_SURFACE_VARIANT).pack(anchor="w")
        self.e_nombre = ctk.CTkEntry(body, height=42, placeholder_text="Simulación de fluidos", font=font("body_large"))
        self.e_nombre.pack(fill="x", pady=(4, 12))
        ctk.CTkLabel(body, text="Comando (se ejecuta tal cual en el clúster)", font=font("label_medium"),
                     text_color=ON_SURFACE_VARIANT).pack(anchor="w")
        self.e_comando = ctk.CTkEntry(body, height=42, placeholder_text="mpirun -np 4 ./simulacion", font=mono(14))
        self.e_comando.pack(fill="x", pady=(4, 16))
        for e in (self.e_nombre, self.e_comando):
            e.bind("<KeyRelease>", lambda _e: self._validar(), add="+")

        fila = ctk.CTkFrame(body, fg_color="transparent")
        fila.pack(fill="x")
        ctk.CTkLabel(fila, text="Prioridad", font=font("title_small")).pack(side="left")
        self.btn_mas = tonal_button(fila, "+", lambda: self._cambiar(1), width=40, height=40)
        self.btn_mas.pack(side="right")
        self.l_prioridad = ctk.CTkLabel(fila, text="5", width=44, font=font("title_medium"))
        self.l_prioridad.pack(side="right")
        self.btn_menos = tonal_button(fila, "−", lambda: self._cambiar(-1), width=40, height=40)
        self.btn_menos.pack(side="right")
        ctk.CTkLabel(body, text="1 es la más baja y 10 la más alta: el gestor atiende primero los de mayor prioridad.",
                     font=font("body_small"), text_color=ON_SURFACE_VARIANT, wraplength=470,
                     justify="left").pack(anchor="w", pady=(6, 0))

        self.btn = primary_button(self, "Enviar al clúster", self._enviar, width=480, height=52)
        self.btn.pack(fill="x", padx=26, pady=20, side="bottom")
        self._refrescar()
        self.after(150, self.e_nombre.focus_set)

    def _cambiar(self, d):
        self.prioridad = max(1, min(10, self.prioridad + d))
        self._refrescar()

    def _refrescar(self):
        self.l_prioridad.configure(text=str(self.prioridad))
        self.btn_menos.configure(state="normal" if self.prioridad > 1 and not self.enviando else "disabled")
        self.btn_mas.configure(state="normal" if self.prioridad < 10 and not self.enviando else "disabled")
        self._validar()

    def _validar(self):
        valido = bool(self.e_nombre.get().strip()) and bool(self.e_comando.get().strip())
        listo = valido and not self.enviando
        self.btn.configure(state="normal" if listo else "disabled",
                           fg_color=PRIMARY if listo else DISABLED_BG, text_color_disabled=DISABLED_FG,
                           text="Enviando…" if self.enviando else "Enviar al clúster")

    def _enviar(self):
        if self.enviando:
            return
        self.enviando = True
        for e in (self.e_nombre, self.e_comando):
            e.configure(state="disabled")
        self._refrescar()
        self.on_enviar(SolicitudTrabajo(self.e_nombre.get().strip(), self.e_comando.get().strip(),
                                        self.prioridad), self)
