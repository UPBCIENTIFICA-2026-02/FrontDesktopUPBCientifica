# -*- coding: utf-8 -*-
"""Vista de Cómputo HPC. Igual que HpcScreen.kt del móvil: tarjeta del clúster
(nodos, CPU, GPU, cola), filtros Todos / Activos / Finalizados, buscador,
tarjetas de trabajo con su estado y progreso, hoja de detalles y formulario
"Nuevo trabajo". Mientras la vista está en pantalla se consulta el estado cada
3 s (ConsultarEstadoTrabajo / ObtenerEstadoCluster), sin parpadeo: las
tarjetas se actualizan en su sitio."""

import customtkinter as ctk

from ..theme import (
    PRIMARY, PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER, TERTIARY, EXITO, ERROR, SURFACE,
    SURFACE_CONTAINER_LOW, SURFACE_CONTAINER_HIGH, SURFACE_CONTAINER_HIGHEST,
    ON_SURFACE_VARIANT, INVERSE_SURFACE, INVERSE_ON_SURFACE, RADIUS_L, RADIUS_M, RADIUS_S,
    font, icon_font, mono, tint,
)

# Botón deshabilitado de Material 3 (igual que en el login).
DISABLED_BG = ("#E1E2E9", "#32353A")
DISABLED_FG = ("#9A9CA5", "#6B6E76")
from ..widgets import (primary_button, tonal_button, filter_chip, chip, pill, circle,
                       SearchBar, Skeleton, empty_state, bind_click, Dialog, DetailsDialog,
                       TipoArchivo, formatear_hace, formatear_minutos)
from ..utils import run_async, describir
from ..data.hpc import SolicitudTrabajo, EN_COLA, EJECUTANDO, COMPLETADO, FALLIDO

INTERVALO_CONSULTA_MS = 3000
FILTROS = ["Todos", "Activos", "Finalizados"]

# Etiqueta, icono y color de cada estado; un solo sitio para lista y detalle.
ASPECTO = {
    EN_COLA: ("En cola", "⌛", TERTIARY),
    EJECUTANDO: ("Ejecutando", "↻", PRIMARY),
    COMPLETADO: ("Completado", "✓", EXITO),
    FALLIDO: ("Fallido", "✕", ERROR),
}


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
        ctk.CTkLabel(head, text="●  En línea", text_color=EXITO, font=font("label_medium")).pack(side="right")
        chip(head, "Simulado · RMI pendiente", "warn").pack(side="right", padx=12)

        self.medidores = {}
        for nombre in ("CPU", "GPU"):
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
        for i, nombre in enumerate(["Nodos activos", "En cola", "Libres"]):
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
                    if _pasa_filtro(t, self.filtro) and (q in t.nombre.lower() or q in t.id)]
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
        estado = f"{etiqueta} · {round(t.progreso * 100)} %" if t.estado == EJECUTANDO else etiqueta
        self._dialogo_detalle = DetailsDialog(self, t.nombre, TipoArchivo(etiqueta, icono, color[0]), [
            ("Estado", estado),
            ("Comando", t.comando),
            ("Recursos", f"{t.nodos} nodos × {t.cpus_por_nodo} CPU · {t.memoria_gb} GB RAM"),
            ("Tiempo máximo", formatear_minutos(t.tiempo_maximo_min)),
            ("Enviado", formatear_hace(t.enviado_en)),
            ("Identificador", f"#{t.id}"),
        ])

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
        etiqueta = ASPECTO[t.estado][0]
        d.valores["Estado"].configure(
            text=f"{etiqueta} · {round(t.progreso * 100)} %" if t.estado == EJECUTANDO else etiqueta)
        d.valores["Enviado"].configure(text=formatear_hace(t.enviado_en))

    # --- Nuevo trabajo -------------------------------------------------------
    def _nuevo(self):
        NuevoTrabajoDialog(self, self._enviar)

    def _enviar(self, solicitud, dialogo):
        def ok(trabajo):
            dialogo.destroy()
            self._mostrar_toast(f"Trabajo #{trabajo.id} enviado al clúster")
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
        ctk.CTkLabel(self.pie, text=f"{trabajo.nodos} nodos · {trabajo.nodos * trabajo.cpus_por_nodo} CPU · "
                                    f"{trabajo.memoria_gb} GB", font=font("body_small"),
                     text_color=ON_SURFACE_VARIANT, anchor="w").pack(anchor="w")
        self._estado_pintado = None
        self.actualizar(trabajo)
        bind_click(self, lambda: self.on_click(self.t), hover=SURFACE_CONTAINER_LOW)

    def actualizar(self, t):
        self.t = t
        etiqueta, icono, color = ASPECTO[t.estado]
        self.sub.configure(text=f"#{t.id} · {formatear_hace(t.enviado_en)}")
        if self._estado_pintado != t.estado:
            self._estado_pintado = t.estado
            self.icono.configure(text=icono, text_color=color, fg_color=tint(color, 0.14, SURFACE))
            for w in self.estado_holder.winfo_children():
                w.destroy()
            p = pill(self.estado_holder, etiqueta, color)
            p.pack()
            for w in [p] + list(p.winfo_children()):
                w.bind("<Button-1>", lambda _e: self.on_click(self.t))
            self.barra.stop()
            if t.estado == EJECUTANDO:
                self.barra.configure(mode="determinate", progress_color=PRIMARY)
                self.pct.pack(side="left", padx=(12, 0))
                self.prog_box.pack(fill="x", padx=16, pady=(14, 0), before=self.pie)
            elif t.estado == EN_COLA:
                self.barra.configure(mode="indeterminate", progress_color=color)
                self.pct.pack_forget()
                self.prog_box.pack(fill="x", padx=16, pady=(14, 0), before=self.pie)
                self.barra.start()
            else:
                self.prog_box.pack_forget()
        if t.estado == EJECUTANDO:
            self.barra.set(t.progreso)
            self.pct.configure(text=f"{round(t.progreso * 100)} %")


class NuevoTrabajoDialog(Dialog):
    """HojaNuevoTrabajo: nombre, comando, nodos, CPU, memoria y tiempo máximo."""

    def __init__(self, master, on_enviar):
        super().__init__(master, "Nuevo trabajo", 540, 680)
        self.on_enviar = on_enviar
        self.nodos, self.cpus, self.memoria, self.tiempo = 1, 16, 32, 60
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
        ctk.CTkLabel(body, text="Comando", font=font("label_medium"), text_color=ON_SURFACE_VARIANT).pack(anchor="w")
        self.e_comando = ctk.CTkEntry(body, height=42, placeholder_text="python simulacion.py --pasos 1000",
                                      font=mono(14))
        self.e_comando.pack(fill="x", pady=(4, 16))
        for e in (self.e_nombre, self.e_comando):
            e.bind("<KeyRelease>", lambda _e: self._validar(), add="+")

        # Contador de nodos
        fila = ctk.CTkFrame(body, fg_color="transparent")
        fila.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(fila, text="Nodos", font=font("title_small")).pack(side="left")
        self.btn_mas = tonal_button(fila, "+", lambda: self._nodos(1), width=40, height=40)
        self.btn_mas.pack(side="right")
        self.l_nodos = ctk.CTkLabel(fila, text="1", width=44, font=font("title_medium"))
        self.l_nodos.pack(side="right")
        self.btn_menos = tonal_button(fila, "−", lambda: self._nodos(-1), width=40, height=40)
        self.btn_menos.pack(side="right")

        self.grupos = {}
        self._grupo(body, "CPU por nodo", "cpus", [4, 8, 16, 32], str)
        self._grupo(body, "Memoria", "memoria", [8, 16, 32, 64], lambda v: f"{v} GB")
        self._grupo(body, "Tiempo máximo", "tiempo", [30, 60, 240, 720], formatear_minutos)

        self.total = ctk.CTkLabel(body, text="", fg_color=SURFACE_CONTAINER_HIGH, corner_radius=RADIUS_S,
                                  height=40, anchor="w", font=font("body"))
        self.total.pack(fill="x", pady=(4, 0))

        self.btn = primary_button(self, "Enviar al clúster", self._enviar, width=480, height=52)
        self.btn.pack(fill="x", padx=26, pady=20, side="bottom")
        self._refrescar()
        self.after(150, self.e_nombre.focus_set)

    def _grupo(self, master, etiqueta, attr, opciones, texto):
        ctk.CTkLabel(master, text=etiqueta, font=font("title_small")).pack(anchor="w")
        fila = ctk.CTkFrame(master, fg_color="transparent")
        fila.pack(fill="x", pady=(6, 14))
        self.grupos[attr] = (fila, opciones, texto)

    def _nodos(self, d):
        self.nodos = max(1, min(8, self.nodos + d))
        self._refrescar()

    def _elegir(self, attr, valor):
        setattr(self, attr, valor)
        self._refrescar()

    def _refrescar(self):
        self.l_nodos.configure(text=str(self.nodos))
        self.btn_menos.configure(state="normal" if self.nodos > 1 and not self.enviando else "disabled")
        self.btn_mas.configure(state="normal" if self.nodos < 8 and not self.enviando else "disabled")
        for attr, (fila, opciones, texto) in self.grupos.items():
            for w in fila.winfo_children():
                w.destroy()
            for v in opciones:
                b = filter_chip(fila, texto(v), getattr(self, attr) == v, lambda a=attr, v=v: self._elegir(a, v))
                if self.enviando:
                    b.configure(state="disabled")
                b.pack(side="left", padx=(0, 8))
        self.total.configure(
            text=f"   Total: {self.nodos * self.cpus} CPU · {self.memoria * self.nodos} GB de RAM")
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
                                        self.nodos, self.cpus, self.memoria, self.tiempo), self)
