# -*- coding: utf-8 -*-
"""Ventana principal (shell): barra lateral, cabecera y navegación entre vistas."""

import customtkinter as ctk

from .theme import APP_NAME, MAGENTA, TEXT, MUTED, GRAY_BG, AMBER
from .config import load_config, save_config
from .api_client import ApiClient
from .views.login import LoginView
from .views.dashboard import DashboardView
from .views.jobs import JobsView
from .views.sync import SyncView
from .views.shared_files import SharedFilesView
from .views.album import AlbumView
from .views.streaming import StreamingView
from .views.settings import SettingsView
from .views.about import AboutView


class UPBApp(ctk.CTk):
    NAV = [
        ("dashboard", "Inicio"),
        ("jobs", "Trabajos HPC"),
        ("sync", "File Sync"),
        ("shared", "Archivos compartidos"),
        ("album", "Álbum de fotos"),
        ("streaming", "Streaming"),
        ("settings", "Configuración"),
        ("about", "Acerca de"),
    ]
    VIEW_CLASSES = {
        "dashboard": DashboardView, "jobs": JobsView, "sync": SyncView,
        "shared": SharedFilesView, "album": AlbumView, "streaming": StreamingView,
        "settings": SettingsView, "about": AboutView,
    }

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.api = ApiClient(self.config)
        ctk.set_appearance_mode(self.config.get("appearance", "light"))
        ctk.set_default_color_theme("blue")

        self.title(APP_NAME)
        self.geometry("1120x720")
        self.minsize(940, 620)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.nav_buttons = {}
        self.current_view = None
        self.view_cache = {}

        self.login = LoginView(self, self)
        self.login.pack(fill="both", expand=True)

    def enter_main(self):
        self.login.destroy()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#FFFFFF")
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        head = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        head.pack(fill="x", pady=(18, 12), padx=16)
        ctk.CTkLabel(head, text="UPB-CIENTÍFICA", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=MAGENTA).pack(anchor="w")
        ctk.CTkLabel(head, text="Cliente de escritorio", font=ctk.CTkFont(size=11),
                     text_color=MUTED).pack(anchor="w")

        for key, label in self.NAV:
            b = ctk.CTkButton(self.sidebar, text=label, anchor="w", height=38,
                              fg_color="transparent", text_color=TEXT, hover_color=GRAY_BG,
                              font=ctk.CTkFont(size=13), corner_radius=8,
                              command=lambda k=key: self.show_view(k))
            b.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = b

        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=10, pady=14)
        ctk.CTkLabel(bottom, text=f"Usuario: {self.config.get('username','-')}",
                     text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=6, pady=(0, 8))
        ctk.CTkButton(bottom, text="Cerrar sesión", height=34, fg_color="transparent",
                      text_color=MAGENTA, border_color=MAGENTA, border_width=1, hover_color=GRAY_BG,
                      command=self._logout).pack(fill="x")

        right = ctk.CTkFrame(self, fg_color=GRAY_BG, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        topbar = ctk.CTkFrame(right, fg_color="#FFFFFF", height=54, corner_radius=0)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        self.header_title = ctk.CTkLabel(topbar, text="Inicio", font=ctk.CTkFont(size=16, weight="bold"),
                                         text_color=TEXT)
        self.header_title.pack(side="left", padx=20)
        ctk.CTkLabel(topbar, text="  demo / sin conexión  ", fg_color="#FEF3C7", text_color=AMBER,
                     corner_radius=8, font=ctk.CTkFont(size=11, weight="bold")).pack(side="right", padx=20)

        self.content = ctk.CTkFrame(right, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=22, pady=18)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.show_view("dashboard")

    def show_view(self, key):
        if self.current_view is not None:
            self.current_view.grid_forget()
        # Reconstruye vistas con datos cambiantes; cachea el resto
        if key in ("dashboard", "jobs", "shared", "sync") or key not in self.view_cache:
            if key in self.view_cache:
                self.view_cache[key].destroy()
            self.view_cache[key] = self.VIEW_CLASSES[key](self.content, self)
        view = self.view_cache[key]
        view.grid(row=0, column=0, sticky="nsew")
        self.current_view = view

        for k, b in self.nav_buttons.items():
            if k == key:
                b.configure(fg_color=MAGENTA, text_color="#FFFFFF")
            else:
                b.configure(fg_color="transparent", text_color=TEXT)
        if hasattr(self, "header_title"):
            self.header_title.configure(text=dict(self.NAV).get(key, ""))

    def _logout(self):
        self.api.logout()
        for w in self.winfo_children():
            w.destroy()
        self.nav_buttons = {}
        self.current_view = None
        self.view_cache = {}
        self.login = LoginView(self, self)
        self.login.pack(fill="both", expand=True)

    def _on_close(self):
        save_config(self.config)
        self.destroy()
