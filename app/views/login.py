# -*- coding: utf-8 -*-
"""Vista de inicio de sesión. Mismo flujo que LoginScreen.kt del móvil:
usuario + contraseña, botón deshabilitado con campos vacíos, "Ingresando..."
mientras se espera al servicio y el error del servidor en rojo debajo."""

import customtkinter as ctk

from ..theme import BACKGROUND, ON_SURFACE, ON_SURFACE_VARIANT, ERROR, PRIMARY, ON_PRIMARY, font

# Botón deshabilitado de Material 3: superficie gris y texto atenuado.
DISABLED_BG = ("#E6E0E9", "#36343B")
DISABLED_FG = ("#9E99A3", "#7A7580")
from ..widgets import primary_button, text_button, divider
from ..config import save_config
from ..utils import run_async, describir
from .conexion_form import ConexionDialog


class LoginView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=BACKGROUND)
        self.app = app
        self.cargando = False

        col = ctk.CTkFrame(self, fg_color="transparent", width=380)
        col.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(col, text="UPB-CIENTÍFICA", font=font("headline_medium"),
                     text_color=ON_SURFACE).pack(anchor="w")
        ctk.CTkLabel(col, text="Cliente de escritorio · Windows / Linux",
                     text_color=ON_SURFACE_VARIANT, font=font("body")).pack(anchor="w", pady=(2, 24))

        self.e_user = ctk.CTkEntry(col, width=380, height=52, placeholder_text="Usuario",
                                   font=font("body_large"))
        self.e_user.pack(fill="x", pady=(0, 8))
        self.e_user.insert(0, self.app.config.get("username", ""))
        self.e_pass = ctk.CTkEntry(col, width=380, height=52, placeholder_text="Contraseña",
                                   show="•", font=font("body_large"))
        self.e_pass.pack(fill="x", pady=(0, 16))

        self.btn = primary_button(col, "Ingresar", self._login, width=380, height=44)
        self.btn.pack(fill="x")

        self.error = ctk.CTkLabel(col, text="", text_color=ERROR, wraplength=380, justify="left")
        self.error.pack(anchor="w", pady=(8, 0))

        divider(col).pack(fill="x", pady=(14, 10))
        self.l_server = ctk.CTkLabel(col, text="", text_color=ON_SURFACE_VARIANT,
                                     font=font("body_small"), justify="left", wraplength=380)
        self.l_server.pack(anchor="w")
        links = ctk.CTkFrame(col, fg_color="transparent")
        links.pack(fill="x", pady=(6, 0))
        text_button(links, "Configurar conexión", self._conexion, width=150).pack(side="left")
        text_button(links, "Entrar sin servidor (demo)", self._demo, width=190,
                    color=ON_SURFACE_VARIANT).pack(side="right")
        self._pintar_servidor()

        for e in (self.e_user, self.e_pass):
            e.bind("<KeyRelease>", lambda _e: self._actualizar_boton())
        self.e_user.bind("<Return>", lambda e: self.e_pass.focus_set())
        self.e_pass.bind("<Return>", lambda e: self._login())
        self._actualizar_boton()
        self.after(100, lambda: (self.e_pass if self.e_user.get() else self.e_user).focus_set())

    def _pintar_servidor(self):
        c = self.app.api.conf
        self.l_server.configure(
            text=f"Autenticación: {c.descripcion_auth()}  ·  entorno {c.entorno.lower()}\n{c.url_auth}")

    def _actualizar_boton(self):
        """Deshabilitado con campos vacíos: no se manda una petición que ya se
        sabe que va a fallar."""
        listo = bool(self.e_user.get().strip()) and bool(self.e_pass.get()) and not self.cargando
        self.btn.configure(state="normal" if listo else "disabled",
                           fg_color=PRIMARY if listo else DISABLED_BG,
                           text_color_disabled=DISABLED_FG, text_color=ON_PRIMARY,
                           text="Ingresando..." if self.cargando else "Ingresar")

    def _login(self):
        # El usuario se recorta; la contraseña NO (un espacio puede ser parte de ella).
        user = self.e_user.get().strip()
        pwd = self.e_pass.get()
        if not user or not pwd or self.cargando:
            return
        self.cargando = True
        self.error.configure(text="")
        self._actualizar_boton()
        self.app.config["username"] = user
        save_config(self.app.config)
        run_async(self, lambda: self.app.api.login(user, pwd), self._ok, self._fail)

    def _ok(self, _sesion):
        self.app.enter_main()

    def _fail(self, e):
        self.cargando = False
        self.error.configure(text=describir(e))
        self._actualizar_boton()

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
