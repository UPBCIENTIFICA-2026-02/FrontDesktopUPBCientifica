# -*- coding: utf-8 -*-
"""Ventana principal (shell): barra lateral, cabecera y navegación entre vistas."""

import customtkinter as ctk

from .theme import (
    APP_NAME, apply_theme, font, BACKGROUND, SURFACE_CONTAINER, SECONDARY_CONTAINER,
    SECONDARY_CONTAINER_HOVER, ON_SECONDARY_CONTAINER, ON_SURFACE, ON_SURFACE_VARIANT,
    SURFACE_CONTAINER_HIGH, PRIMARY,
)
from .config import load_config, save_config
from .api_client import ApiClient
from .utils import run_async
from .widgets import chip, divider, ghost_button, text_button
from .views.login import LoginView
from .views.dashboard import DashboardView
from .views.storage import StorageView
from .views.shared_files import SharedFilesView
from .views.streaming import StreamingView
from .views.sync import SyncView
from .views.jobs import JobsView
from .views.album import AlbumView
from .views.settings import SettingsView
from .views.about import AboutView


class UPBApp(ctk.CTk):
    # Mismo orden que los tiles del Home del móvil, más los módulos de escritorio.
    NAV = [
        ("dashboard", "Inicio"),
        ("storage", "Mis archivos"),
        ("shared", "Compartidos conmigo"),
        ("streaming", "Streaming"),
        ("sync", "Sincronización"),
        ("jobs", "Trabajos HPC"),
        ("album", "Álbum de fotos"),
        ("settings", "Configuración"),
        ("about", "Acerca de"),
    ]
    ICONS = {
        "dashboard": "⌂", "storage": "📁", "shared": "🔗", "streaming": "▶",
        "sync": "⟳", "jobs": "⚙", "album": "🖼", "settings": "☰", "about": "ⓘ",
    }
    VIEW_CLASSES = {
        "dashboard": DashboardView, "storage": StorageView, "shared": SharedFilesView,
        "streaming": StreamingView, "sync": SyncView, "jobs": JobsView,
        "album": AlbumView, "settings": SettingsView, "about": AboutView,
    }
    # Vistas cuyos datos cambian: se reconstruyen en cada visita.
    REBUILD = ("dashboard", "storage", "shared", "sync", "jobs")

    def __init__(self):
        cfg = load_config()
        apply_theme(cfg.get("appearance", "light"))
        super().__init__(fg_color=BACKGROUND)
        self.config = cfg
        self.api = ApiClient(self.config)

        self.title(APP_NAME)
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.nav_buttons = {}
        self.current_view = None
        self.current_key = None
        self.view_cache = {}
        self._show_login()

    # --- Login / sesión -----------------------------------------------------
    def _show_login(self):
        for w in self.winfo_children():
            w.destroy()
        self.nav_buttons = {}
        self.current_view = None
        self.current_key = None
        self.view_cache = {}
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=0)
        self.login = LoginView(self, self)
        self.login.pack(fill="both", expand=True)

    def enter_main(self):
        self.login.destroy()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Barra lateral (Navigation Drawer de Material 3)
        self.sidebar = ctk.CTkFrame(self, width=272, corner_radius=0, fg_color=SURFACE_CONTAINER)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.pack_propagate(False)

        head = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        head.pack(fill="x", pady=(22, 14), padx=24)
        ctk.CTkLabel(head, text="UPB-CIENTÍFICA", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=PRIMARY).pack(anchor="w")
        ctk.CTkLabel(head, text="Cliente de escritorio", font=font("body_small"),
                     text_color=ON_SURFACE_VARIANT).pack(anchor="w")

        for key, label in self.NAV:
            if key == "settings":
                divider(self.sidebar).pack(fill="x", padx=24, pady=8)
            b = ctk.CTkButton(self.sidebar, text=f"  {self.ICONS[key]}  {label}", anchor="w",
                              height=46, corner_radius=23, fg_color="transparent",
                              text_color=ON_SURFACE_VARIANT, hover_color=SURFACE_CONTAINER_HIGH,
                              font=font("label_large"), command=lambda k=key: self.show_view(k))
            b.pack(fill="x", padx=12, pady=1)
            self.nav_buttons[key] = b

        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=16)
        ctk.CTkLabel(bottom, text=f"👤  {self.api.user or '-'}", text_color=ON_SURFACE,
                     font=font("title_small"), anchor="w").pack(fill="x", padx=6)
        roles = ", ".join(self.api.sesion.roles) if self.api.sesion and self.api.sesion.roles else (
            "modo demostración" if self.api.modo_demo else "sin roles")
        ctk.CTkLabel(bottom, text=roles, text_color=ON_SURFACE_VARIANT, font=font("body_small"),
                     anchor="w").pack(fill="x", padx=6, pady=(0, 10))
        self.btn_logout = ghost_button(bottom, "Cerrar sesión", self._logout, width=200)
        self.btn_logout.pack(fill="x")

        # Zona derecha: barra superior (TopAppBar) + contenido
        right = ctk.CTkFrame(self, fg_color=BACKGROUND, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        topbar = ctk.CTkFrame(right, fg_color=BACKGROUND, height=64, corner_radius=0)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.pack_propagate(False)
        self.btn_back = text_button(topbar, "←", lambda: self.show_view("dashboard"),
                                    width=44, height=44, color=ON_SURFACE)
        self.btn_back.configure(font=ctk.CTkFont(size=22))
        self.header_title = ctk.CTkLabel(topbar, text="Inicio", font=font("title_large"),
                                         text_color=ON_SURFACE)
        self.header_title.pack(side="left", padx=(24, 0))
        self.status_holder = ctk.CTkFrame(topbar, fg_color="transparent")
        self.status_holder.pack(side="right", padx=20)
        self.refresh_status()
        divider(right).grid(row=1, column=0, sticky="ew")

        self.content = ctk.CTkFrame(right, fg_color="transparent")
        self.content.grid(row=2, column=0, sticky="nsew", padx=24, pady=18)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.show_view("dashboard")

    def refresh_status(self):
        """Chip de la barra superior: con quién y contra qué está conectado."""
        if not hasattr(self, "status_holder"):
            return
        for w in self.status_holder.winfo_children():
            w.destroy()
        if self.api.modo_demo:
            chip(self.status_holder, "Modo demostración · datos simulados", "warn").pack()
        else:
            chip(self.status_holder,
                 f"● Sesión activa · {self.api.conf.descripcion_auth()} · {self.api.conf.entorno.lower()}",
                 "ok").pack()

    def show_view(self, key):
        if self.current_view is not None:
            self.current_view.grid_forget()
        if key in self.REBUILD or key not in self.view_cache:
            if key in self.view_cache:
                self.view_cache[key].destroy()
            self.view_cache[key] = self.VIEW_CLASSES[key](self.content, self)
        view = self.view_cache[key]
        view.grid(row=0, column=0, sticky="nsew")
        self.current_view = view
        self.current_key = key

        for k, b in self.nav_buttons.items():
            if k == key:
                b.configure(fg_color=SECONDARY_CONTAINER, text_color=ON_SECONDARY_CONTAINER,
                            hover_color=SECONDARY_CONTAINER_HOVER)
            else:
                b.configure(fg_color="transparent", text_color=ON_SURFACE_VARIANT,
                            hover_color=SURFACE_CONTAINER_HIGH)
        if hasattr(self, "header_title"):
            self.header_title.configure(text=dict(self.NAV).get(key, ""))
            # Flecha de volver al Inicio, como PantallaConVolver en el móvil.
            if key == "dashboard":
                self.btn_back.pack_forget()
                self.header_title.pack_configure(padx=(24, 0))
            else:
                self.btn_back.pack(side="left", padx=(12, 0), before=self.header_title)
                self.header_title.pack_configure(padx=(4, 0))

    def invalidate_views(self):
        """Tras cambiar la conexión, fuerza a que todas las vistas se recreen."""
        for k, v in list(self.view_cache.items()):
            if v is not self.current_view:
                v.destroy()
                del self.view_cache[k]

    def _logout(self):
        self.btn_logout.configure(state="disabled", text="Cerrando sesión…")
        run_async(self, self.api.logout, lambda _r: self._show_login(), lambda _e: self._show_login())

    def _on_close(self):
        save_config(self.config)
        self.destroy()
