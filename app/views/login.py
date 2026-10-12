# -*- coding: utf-8 -*-
"""Vista de inicio de sesión. Mismo diseño y flujo que LoginScreen.kt del móvil:
fondo en degradado (primaryContainer -> surface), logo, tarjeta "Iniciar
sesión", campos con icono, ojo para ver la contraseña, error del servidor en
una caja roja y botón deshabilitado mientras falten datos o se esté ingresando.
Además, lo propio del escritorio: configurar la conexión y entrar en modo demo."""

import tkinter as tk

import customtkinter as ctk
from customtkinter.windows.widgets.appearance_mode import AppearanceModeTracker

from ..theme import (
    PRIMARY, ON_PRIMARY, PRIMARY_CONTAINER, SURFACE, SURFACE_CONTAINER_LOW, ON_SURFACE,
    ON_SURFACE_VARIANT, OUTLINE, ERROR_CONTAINER, ON_ERROR_CONTAINER, RADIUS_L, RADIUS_S,
    font, icon_font, glifo, resolve, _mix,
)
from ..widgets import primary_button, text_button, icon_button
from ..config import save_config
from ..utils import run_async, describir
from .conexion_form import ConexionDialog

# Botón deshabilitado de Material 3: superficie gris y texto atenuado.
DISABLED_BG = ("#E1E2E9", "#32353A")
DISABLED_FG = ("#9A9CA5", "#6B6E76")
CARD_W = 440


class LoginView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=SURFACE, corner_radius=0)
        self.app = app
        self.cargando = False
        self.ver = False

        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        # ---------- Tarjeta del formulario ----------
        self.card = ctk.CTkFrame(self.canvas, width=CARD_W, fg_color=SURFACE_CONTAINER_LOW,
                                 corner_radius=RADIUS_L, bg_color=SURFACE)
        inner = ctk.CTkFrame(self.card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=28, pady=26)
        ctk.CTkLabel(inner, text="Iniciar sesión", font=font("title_large")).pack(anchor="w")
        ctk.CTkLabel(inner, text="Usa tu cuenta institucional", font=font("body"),
                     text_color=ON_SURFACE_VARIANT).pack(anchor="w", pady=(2, 20))

        self.e_user = self._campo(inner, "👤", "Usuario")
        self.e_user.insert(0, self.app.config.get("username", ""))
        self.e_pass = self._campo(inner, "🔒", "Contraseña", password=True)

        self.err_box = ctk.CTkFrame(inner, fg_color=ERROR_CONTAINER, corner_radius=RADIUS_S)
        ctk.CTkLabel(self.err_box, text="⚠", text_color=ON_ERROR_CONTAINER,
                     font=ctk.CTkFont(size=18)).pack(side="left", padx=(12, 8), pady=10)
        self.err_text = ctk.CTkLabel(self.err_box, text="", text_color=ON_ERROR_CONTAINER,
                                     wraplength=CARD_W - 120, justify="left", font=font("body"))
        self.err_text.pack(side="left", pady=10, padx=(0, 12))

        self.btn = primary_button(inner, "Ingresar", self._login, width=CARD_W - 56, height=52)
        self.btn.pack(fill="x", pady=(24, 0))

        # ---------- Debajo de la tarjeta: conexión y modo demo ----------
        self.extra = ctk.CTkFrame(self.canvas, fg_color=SURFACE, bg_color=SURFACE, width=CARD_W)
        self.l_server = ctk.CTkLabel(self.extra, text="", text_color=ON_SURFACE_VARIANT,
                                     font=font("body_small"), justify="center")
        self.l_server.pack()
        links = ctk.CTkFrame(self.extra, fg_color="transparent")
        links.pack(pady=(4, 0))
        text_button(links, "Configurar conexión", self._conexion, width=160).pack(side="left")
        text_button(links, "Entrar sin servidor (demo)", self._demo, width=200,
                    color=ON_SURFACE_VARIANT).pack(side="left")
        self._pintar_servidor()

        self.win_card = self.canvas.create_window(0, 0, window=self.card, anchor="n")
        self.win_extra = self.canvas.create_window(0, 0, window=self.extra, anchor="n")
        self.canvas.bind("<Configure>", lambda _e: self._dibujar())
        AppearanceModeTracker.add(self._on_mode, self)

        for e in (self.e_user, self.e_pass):
            e.bind("<KeyRelease>", lambda _e: self._actualizar_boton(), add="+")
        self.e_user.bind("<Return>", lambda e: self.e_pass.focus_set())
        self.e_pass.bind("<Return>", lambda e: self._login())
        self._actualizar_boton()
        self.after(120, lambda: (self.e_pass if self.e_user.get() else self.e_user).focus_set())

    def destroy(self):
        AppearanceModeTracker.remove(self._on_mode)
        super().destroy()

    # --- Campo con icono a la izquierda (OutlinedTextField + leadingIcon) ----
    def _campo(self, master, icono, placeholder, password=False):
        box = ctk.CTkFrame(master, fg_color=SURFACE, border_width=1, border_color=OUTLINE,
                           corner_radius=RADIUS_S, height=54)
        box.pack(fill="x", pady=(0, 12))
        box.pack_propagate(False)
        ctk.CTkLabel(box, text=glifo(icono), text_color=ON_SURFACE_VARIANT, width=26,
                     font=icon_font(16)).pack(side="left", padx=(14, 4))
        entry = ctk.CTkEntry(box, placeholder_text=placeholder, border_width=0, fg_color=SURFACE,
                             font=font("body_large"), height=44, show="•" if password else "")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        if password:
            self.btn_ver = icon_button(box, "👁", self._toggle_ver, size=40)
            self.btn_ver.pack(side="right", padx=(0, 6))
        entry.bind("<FocusIn>", lambda _e: box.configure(border_color=PRIMARY, border_width=2), add="+")
        entry.bind("<FocusOut>", lambda _e: box.configure(border_color=OUTLINE, border_width=1), add="+")
        return entry

    def _toggle_ver(self):
        self.ver = not self.ver
        self.e_pass.configure(show="" if self.ver else "•")
        self.btn_ver.configure(text=glifo("🙈" if self.ver else "👁"))

    # --- Fondo en degradado, logo y título dibujados en el lienzo ------------
    def _on_mode(self, _mode):
        self.after(10, self._dibujar)

    def _dibujar(self):
        c = self.canvas
        w, h = c.winfo_width(), c.winfo_height()
        if w < 10 or h < 10:
            return
        c.delete("fondo")
        arriba, abajo = resolve(PRIMARY_CONTAINER), resolve(SURFACE)
        corte = int(h * 0.55)
        paso = 3
        for y in range(0, h, paso):
            a = 1 - min(1.0, y / corte)
            c.create_rectangle(0, y, w, y + paso, fill=_mix(arriba, abajo, a), width=0, tags="fondo")
        c.tag_lower("fondo")

        # Bloque centrado: logo + título + subtítulo + tarjeta + enlaces
        alto_card = self.card.winfo_reqheight()
        alto_extra = self.extra.winfo_reqheight()
        total = 72 + 18 + 36 + 26 + 28 + alto_card + 14 + alto_extra
        y = max(16, (h - total) // 2)
        cx = w // 2
        c.delete("marca")
        c.create_oval(cx - 36, y, cx + 36, y + 72, fill=resolve(PRIMARY), width=0, tags="marca")
        c.create_text(cx, y + 37, text="☁", fill=resolve(ON_PRIMARY), font=("Segoe UI Symbol", 30),
                      tags="marca")
        y += 72 + 18
        c.create_text(cx, y, text="UPB-CIENTÍFICA", anchor="n", fill=resolve(ON_SURFACE),
                      font=("Roboto", 26, "bold"), tags="marca")
        y += 36
        c.create_text(cx, y, text="Tus archivos, datos y resultados de investigación en un solo lugar",
                      anchor="n", fill=resolve(ON_SURFACE_VARIANT), font=("Roboto", 12), tags="marca")
        y += 26 + 28
        c.coords(self.win_card, cx, y)
        # Las esquinas de la tarjeta toman el color del degradado a esa altura.
        self.card.configure(bg_color=_mix(arriba, abajo, 1 - min(1.0, (y + 12) / corte)))
        c.coords(self.win_extra, cx, y + alto_card + 14)

    # --- Lógica (igual que LoginViewModel) ----------------------------------
    def _pintar_servidor(self):
        conf = self.app.api.conf
        self.l_server.configure(
            text=f"Autenticación: {conf.descripcion_auth()} · entorno {conf.entorno.lower()} · {conf.url_auth}")

    def _actualizar_boton(self):
        """Deshabilitado con campos vacíos: no se manda una petición que ya se
        sabe que va a fallar."""
        listo = bool(self.e_user.get().strip()) and bool(self.e_pass.get()) and not self.cargando
        self.btn.configure(state="normal" if listo else "disabled",
                           fg_color=PRIMARY if listo else DISABLED_BG,
                           text_color_disabled=DISABLED_FG, text_color=ON_PRIMARY,
                           text="Ingresando…" if self.cargando else "Ingresar")
        estado = "disabled" if self.cargando else "normal"
        self.e_user.configure(state=estado)
        self.e_pass.configure(state=estado)

    def _mostrar_error(self, mensaje):
        if mensaje:
            self.err_text.configure(text=mensaje)
            self.err_box.pack(fill="x", pady=(4, 0), before=self.btn)
        else:
            self.err_box.pack_forget()
        self.after(30, self._dibujar)

    def _login(self):
        # El usuario se recorta; la contraseña NO (un espacio puede ser parte de ella).
        user = self.e_user.get().strip()
        pwd = self.e_pass.get()
        if not user or not pwd or self.cargando:
            return
        self.cargando = True
        self._mostrar_error("")
        self._actualizar_boton()
        self.app.config["username"] = user
        save_config(self.app.config)
        run_async(self, lambda: self.app.api.login(user, pwd), self._ok, self._fail)

    def _ok(self, _sesion):
        self.app.enter_main()

    def _fail(self, e):
        self.cargando = False
        self._actualizar_boton()
        self._mostrar_error(describir(e))

    def _demo(self):
        self.app.api.entrar_demo(self.e_user.get().strip() or "demo")
        save_config(self.app.config)
        self.app.enter_main()

    def _conexion(self):
        def guardado():
            save_config(self.app.config)
            self.app.api.reconfigurar()
            self._pintar_servidor()
        ConexionDialog(self, self.app.config, guardado)
