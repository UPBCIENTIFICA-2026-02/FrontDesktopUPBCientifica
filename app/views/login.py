# -*- coding: utf-8 -*-
"""Vista de inicio de sesión."""

import customtkinter as ctk
from tkinter import messagebox

from ..theme import GRAY_BG, MAGENTA, MUTED
from ..widgets import card, primary_button
from ..config import save_config


class LoginView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=GRAY_BG)
        self.app = app

        centro = card(self)
        centro.place(relx=0.5, rely=0.5, anchor="center")
        pad = ctk.CTkFrame(centro, fg_color="transparent")
        pad.pack(padx=40, pady=36)

        ctk.CTkLabel(pad, text="UPB-CIENTÍFICA", font=ctk.CTkFont(size=30, weight="bold"),
                     text_color=MAGENTA).pack()
        ctk.CTkLabel(pad, text="Cliente de Escritorio  ·  Windows / Linux",
                     text_color=MUTED, font=ctk.CTkFont(size=13)).pack(pady=(2, 22))

        self.e_server = ctk.CTkEntry(pad, width=320, placeholder_text="Servidor")
        self.e_server.insert(0, self.app.config.get("server_url", ""))
        self.e_server.pack(pady=6)
        self.e_user = ctk.CTkEntry(pad, width=320, placeholder_text="Usuario")
        self.e_user.pack(pady=6)
        self.e_pass = ctk.CTkEntry(pad, width=320, placeholder_text="Contraseña", show="\u2022")
        self.e_pass.pack(pady=6)
        self.e_otp = ctk.CTkEntry(pad, width=320, placeholder_text="Código MFA (opcional en demo)")
        self.e_otp.pack(pady=6)

        primary_button(pad, "Ingresar", self._login, width=320).pack(pady=(16, 8))
        ctk.CTkLabel(pad, text="Modo demostración: la autenticación real se hará contra\n"
                               "LDAP + MFA cuando el backend esté disponible.",
                     text_color=MUTED, font=ctk.CTkFont(size=11), justify="center").pack()

        self.e_user.bind("<Return>", lambda e: self.e_pass.focus_set())
        self.e_pass.bind("<Return>", lambda e: self._login())

    def _login(self):
        user = self.e_user.get().strip()
        pwd = self.e_pass.get().strip()
        if not user or not pwd:
            messagebox.showwarning("Datos incompletos",
                                   "Ingresa usuario y contraseña.\n(En modo demo aceptamos cualquier valor no vacío.)")
            return
        self.app.config["server_url"] = self.e_server.get().strip() or self.app.config["server_url"]
        self.app.config["username"] = user
        save_config(self.app.config)
        if self.app.api.login(user, pwd, self.e_otp.get().strip()):
            self.app.enter_main()
        else:
            messagebox.showerror("Error", "No se pudo iniciar sesión.")
