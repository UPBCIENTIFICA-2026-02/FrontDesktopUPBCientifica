# -*- coding: utf-8 -*-
"""Ventana principal (shell). Equivale a MainScreen.kt del móvil: los mismos
destinos (Inicio, Archivos, Compartidos, Streaming, HPC), pero en una barra
lateral en vez de la barra inferior, más los módulos propios del escritorio.
A la derecha de la barra superior, como en el móvil: el estado de File Sync y
el avatar con el menú de la cuenta."""

import tkinter as tk

import customtkinter as ctk

from .theme import (
    APP_NAME, apply_theme, font, icon_font, glifo, imagen_icono, BACKGROUND, SURFACE_CONTAINER, SURFACE_CONTAINER_HIGH,
    SECONDARY_CONTAINER, SECONDARY_CONTAINER_HOVER, ON_SECONDARY_CONTAINER, ON_SURFACE,
    ON_SURFACE_VARIANT, PRIMARY, ON_PRIMARY, EXITO, ERROR, OUTLINE_VARIANT,
)
from .config import load_config, save_config
from .api_client import ApiClient
from .data.filesync import Sincronizando, AlDia, SinConfigurar, ErrorSync, SIN_CONFIGURAR
from .utils import run_async
from .widgets import chip, divider, avatar, circle, bind_click, ConfirmDialog, formatear_hace
from .views.login import LoginView
from .views.dashboard import DashboardView
from .views.storage import StorageView
from .views.shared_files import SharedFilesView
from .views.streaming import StreamingView
from .views.hpc import HpcView
from .views.sync import SyncView
from .views.album import AlbumView
from .views.settings import SettingsView
from .views.about import AboutView


class UPBApp(ctk.CTk):
    # Los cinco primeros son las pestañas del móvil (Pestana en MainScreen.kt).
    NAV = [
        ("dashboard", "Inicio"),
        ("storage", "Archivos"),
        ("shared", "Compartidos"),
        ("streaming", "Streaming"),
        ("hpc", "Cómputo HPC"),
        ("sync", "Sincronización"),
        ("album", "Álbum de fotos"),
        ("settings", "Configuración"),
        ("about", "Acerca de"),
    ]
    # En Archivos el título lo pone la ruta (migas de pan), como en el móvil.
    TITLES = {"storage": "", "shared": "Compartidos"}
    ICONS = {
        "dashboard": "⌂", "storage": "📁", "shared": "👥", "streaming": "▶", "hpc": "▣",
        "sync": "↻", "album": "🖼", "settings": "⚙", "about": "ⓘ",
    }
    SEPARADORES = ("sync", "settings")
    VIEW_CLASSES = {
        "dashboard": DashboardView, "storage": StorageView, "shared": SharedFilesView,
        "streaming": StreamingView, "hpc": HpcView, "sync": SyncView,
        "album": AlbumView, "settings": SettingsView, "about": AboutView,
    }
    # Vistas cuyos datos cambian: se reconstruyen en cada visita.
    REBUILD = ("dashboard", "sync")

    def __init__(self):
        cfg = load_config()
        apply_theme(cfg.get("appearance", "light"))
        super().__init__(fg_color=BACKGROUND)
        self.config = cfg
        self.api = ApiClient(self.config)

        self.title(APP_NAME)
        # Cabe en pantallas pequeñas (p. ej. 1366x768) sin salirse.
        ancho = min(1200, self.winfo_screenwidth() - 40)
        alto = min(780, self.winfo_screenheight() - 90)
        self.geometry(f"{ancho}x{alto}+{max(0, (self.winfo_screenwidth() - ancho) // 2)}+10")
        self.minsize(min(1000, ancho), min(620, alto))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Estado de File Sync compartido por la barra superior y el Inicio.
        self.sync_estado = SIN_CONFIGURAR
        self.sync_listeners = []
        self._sync_job = None
        self._sync_ticks = 0
        self._menu = None

        self.nav_buttons = {}
        self.current_view = None
        self.current_key = None
        self.view_cache = {}
        self._show_login()

    # --- Login / sesión -----------------------------------------------------
    def _show_login(self):
        self._stop_sync()
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

        # ---------- Barra lateral (NavigationDrawer) ----------
        self.sidebar = ctk.CTkFrame(self, width=264, corner_radius=0, fg_color=SURFACE_CONTAINER)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.pack_propagate(False)

        head = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        head.pack(fill="x", pady=(22, 18), padx=20)
        circle(head, "☁", 36, PRIMARY, ON_PRIMARY, size=18).pack(side="left")
        ctk.CTkLabel(head, text="UPB-Científica", font=font("title_large"),
                     text_color=ON_SURFACE).pack(side="left", padx=12)

        for key, label in self.NAV:
            if key in self.SEPARADORES:
                divider(self.sidebar).pack(fill="x", padx=24, pady=8)
            # Un botón tiene una sola fuente: el icono va como imagen y el texto aparte.
            icono = imagen_icono(self.ICONS[key], 20, ON_SURFACE_VARIANT)
            b = ctk.CTkButton(self.sidebar, text=f"  {label}" if icono else f"   {self.ICONS[key]}   {label}",
                              image=icono, compound="left", anchor="w",
                              height=48, corner_radius=24, fg_color="transparent",
                              text_color=ON_SURFACE_VARIANT, hover_color=SURFACE_CONTAINER_HIGH,
                              font=font("label_large"), command=lambda k=key: self.show_view(k))
            b._iconos = (icono, imagen_icono(self.ICONS[key], 20, ON_SECONDARY_CONTAINER))
            b.pack(fill="x", padx=12, pady=1)
            self.nav_buttons[key] = b

        self.mode_holder = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.mode_holder.pack(side="bottom", fill="x", padx=20, pady=18)
        self.refresh_status()

        # ---------- Zona derecha ----------
        right = ctk.CTkFrame(self, fg_color=BACKGROUND, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        topbar = ctk.CTkFrame(right, fg_color=BACKGROUND, height=68, corner_radius=0)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.pack_propagate(False)
        self.header_title = ctk.CTkLabel(topbar, text="", font=font("title_large"), text_color=ON_SURFACE)
        self.header_title.pack(side="left", padx=28)

        usuario = self.api.user or "demo"
        self.avatar_btn = avatar(topbar, usuario, 36)
        self.avatar_btn.pack(side="right", padx=(6, 24))
        bind_click(self.avatar_btn, self._toggle_menu)

        self.sync_box = ctk.CTkFrame(topbar, fg_color="transparent")
        self.sync_box.pack(side="right", padx=6)
        self.sync_icon = ctk.CTkLabel(self.sync_box, text=glifo("☁"), font=icon_font(20), width=28)
        self.sync_icon.pack(side="left")
        self.sync_text = ctk.CTkLabel(self.sync_box, text="", font=font("body_small"),
                                      text_color=ON_SURFACE_VARIANT)
        self.sync_text.pack(side="left", padx=(4, 0))
        self.sync_bar = ctk.CTkProgressBar(self.sync_box, width=70, height=4)
        # Como en el móvil, el indicador abre la pantalla de sincronización.
        bind_click(self.sync_box, lambda: self.show_view("sync"))

        self.content = ctk.CTkFrame(right, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=24, pady=(4, 18))
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.bind("<Escape>", lambda _e: self._close_menu(), add="+")
        self.bind("<Button-1>", self._click_fuera, add="+")
        self._start_sync()
        self.show_view("dashboard")

    def refresh_status(self):
        """Etiqueta de la barra lateral: modo demo o contra qué está conectado."""
        if not hasattr(self, "mode_holder"):
            return
        for w in self.mode_holder.winfo_children():
            w.destroy()
        if self.api.modo_demo:
            chip(self.mode_holder, "Modo demostración · datos simulados", "warn").pack(anchor="w")
        else:
            chip(self.mode_holder, f"● {self.api.conf.descripcion_auth()} · {self.api.conf.entorno.lower()}",
                 "ok").pack(anchor="w")

    def show_view(self, key):
        self._close_menu()
        if self.current_view is not None:
            self.current_view.grid_forget()
            if hasattr(self.current_view, "on_hide"):
                self.current_view.on_hide()
        if key in self.REBUILD or key not in self.view_cache:
            if key in self.view_cache:
                self.view_cache[key].destroy()
            self.view_cache[key] = self.VIEW_CLASSES[key](self.content, self)
        view = self.view_cache[key]
        view.grid(row=0, column=0, sticky="nsew")
        if hasattr(view, "on_show"):
            view.on_show()
        self.current_view = view
        self.current_key = key

        for k, b in self.nav_buttons.items():
            sel = k == key
            b.configure(fg_color=SECONDARY_CONTAINER if sel else "transparent",
                        text_color=ON_SECONDARY_CONTAINER if sel else ON_SURFACE_VARIANT,
                        hover_color=SECONDARY_CONTAINER_HOVER if sel else SURFACE_CONTAINER_HIGH)
            normal, activo = getattr(b, "_iconos", (None, None))
            if normal:
                b.configure(image=activo if sel else normal)
        self.header_title.configure(
            text="" if key == "dashboard" else self.TITLES.get(key, dict(self.NAV)[key]))

    def invalidate_views(self):
        """Tras cambiar la conexión, fuerza a que todas las vistas se recreen."""
        for k, v in list(self.view_cache.items()):
            if v is not self.current_view:
                v.destroy()
                del self.view_cache[k]

    # --- File Sync: indicador y programación ---------------------------------
    # La sincronización corre en un hilo (data/filesync.py). Tk no es seguro
    # entre hilos, así que aquí solo se CONSULTA su estado cada 400 ms, y cada
    # ~5 s se le pide que revise si toca una sincronización programada.
    def _start_sync(self):
        self._stop_sync()
        self._sync_ticks = 0
        # Se pinta ya: el primer tick solo repinta si el estado CAMBIA.
        self.sync_estado = self.api.filesync.estado
        self._pintar_sync(self.sync_estado)
        self._sync_tick()

    def _stop_sync(self):
        if self._sync_job:
            try:
                self.after_cancel(self._sync_job)
            except tk.TclError:
                pass
        self._sync_job = None

    def _sync_tick(self):
        fs = self.api.filesync
        self._sync_ticks += 1
        if self._sync_ticks % 12 == 1:
            fs.revisar_programacion()
        estado = fs.estado
        # AlDia "hace 3 min" cambia con el tiempo: se repinta cada ~30 s aunque no cambie.
        if estado != self.sync_estado or self._sync_ticks % 75 == 0:
            self.sync_estado = estado
            self._pintar_sync(estado)
            for cb in list(self.sync_listeners):
                try:
                    cb(estado)
                except tk.TclError:
                    self.sync_listeners.remove(cb)
        self._sync_job = self.after(400, self._sync_tick)

    def _pintar_sync(self, estado):
        try:
            if isinstance(estado, AlDia):
                self.sync_bar.pack_forget()
                self.sync_icon.configure(text=glifo("☁"), text_color=EXITO)
                self.sync_text.configure(text=f"Sincronizado · {formatear_hace(estado.ultima_sincronizacion)}"
                                         if estado.ultima_sincronizacion else "Listo para sincronizar")
            elif isinstance(estado, SinConfigurar):
                self.sync_bar.pack_forget()
                self.sync_icon.configure(text=glifo("☁"), text_color=ON_SURFACE_VARIANT)
                self.sync_text.configure(text="Configurar sincronización")
            elif isinstance(estado, ErrorSync):
                self.sync_bar.pack_forget()
                self.sync_icon.configure(text=glifo("⚠"), text_color=ERROR)
                self.sync_text.configure(text="Error al sincronizar")
            elif isinstance(estado, Sincronizando):
                self.sync_icon.configure(text=glifo("↻"), text_color=PRIMARY)
                self.sync_text.configure(
                    text=f"Sincronizando · faltan {estado.pendientes}" if estado.pendientes else "Sincronizando…")
                self.sync_bar.set(estado.progreso)
                self.sync_bar.pack(side="left", padx=(8, 0))
            else:
                self.sync_bar.pack_forget()
                self.sync_icon.configure(text=glifo("⊘"), text_color=ON_SURFACE_VARIANT)
                self.sync_text.configure(text="Esperando la red del servidor")
        except (tk.TclError, AttributeError):
            pass

    # --- Menú de la cuenta (MenuCuenta) -------------------------------------
    def _toggle_menu(self):
        if self._menu is not None:
            self._close_menu()
            return
        m = ctk.CTkToplevel(self)
        m.overrideredirect(True)
        m.configure(fg_color=OUTLINE_VARIANT)
        self.update_idletasks()
        x = self.avatar_btn.winfo_rootx() + self.avatar_btn.winfo_width() - 260
        y = self.avatar_btn.winfo_rooty() + self.avatar_btn.winfo_height() + 6
        m.geometry(f"260x330+{x}+{y}")
        box = ctk.CTkFrame(m, fg_color=SURFACE_CONTAINER, corner_radius=0)
        box.pack(fill="both", expand=True, padx=1, pady=1)
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(14, 10))
        usuario = self.api.user or "demo"
        avatar(row, usuario, 40).pack(side="left")
        t = ctk.CTkFrame(row, fg_color="transparent")
        t.pack(side="left", padx=12)
        ctk.CTkLabel(t, text=usuario, font=font("title_small"), anchor="w").pack(anchor="w")
        ctk.CTkLabel(t, text="Modo demostración" if self.api.modo_demo else "Sesión iniciada",
                     font=font("body_small"), text_color=ON_SURFACE_VARIANT, anchor="w").pack(anchor="w")
        divider(box).pack(fill="x")

        # Apariencia, como el menú de cuenta del portal web y del móvil.
        ctk.CTkLabel(box, text="Apariencia", font=font("label_medium"), text_color=ON_SURFACE_VARIANT,
                     anchor="w").pack(fill="x", padx=16, pady=(10, 2))
        actual = self.config.get("appearance", "light")
        for valor, icono, texto in (("system", "☁", "Según el sistema"), ("light", "☀", "Claro"),
                                    ("dark", "☾", "Oscuro")):
            self._opcion_menu(box, icono, texto, lambda v=valor: self._cambiar_apariencia(v),
                              marcada=actual == valor)
        divider(box).pack(fill="x", pady=(4, 0))
        self._opcion_menu(box, "↪", "Cerrar sesión", self._pedir_logout)
        m.lift()
        m.attributes("-topmost", True)
        self._menu = m

    def _opcion_menu(self, caja, icono, texto, comando, marcada=False):
        """Fila del menú: icono, texto y, si está elegida, ✓ a la derecha."""
        fila = ctk.CTkFrame(caja, fg_color="transparent", corner_radius=0, height=44)
        fila.pack(fill="x")
        fila.pack_propagate(False)
        imagen = imagen_icono(icono, 18, ON_SURFACE_VARIANT)
        boton = ctk.CTkButton(fila, text=f"  {texto}" if imagen else f"  {icono}   {texto}", image=imagen,
                              compound="left", anchor="w", height=44, corner_radius=0,
                              fg_color="transparent", hover_color=SURFACE_CONTAINER_HIGH, text_color=ON_SURFACE,
                              font=font("body"), command=comando)
        boton.pack(fill="both", expand=True)
        if marcada:
            ctk.CTkLabel(fila, text=glifo("✓"), font=icon_font(15), text_color=ON_SURFACE,
                         fg_color="transparent", width=20).place(relx=1.0, rely=0.5, x=-18, anchor="e")

    def _cambiar_apariencia(self, valor):
        """Claro / oscuro / según el sistema. Se guarda para la próxima vez."""
        self._close_menu()
        self.config["appearance"] = valor
        save_config(self.config)
        ctk.set_appearance_mode(valor)
        # Algunos widgets de Tk (lienzos, miniaturas) toman el color al crearse:
        # se reconstruyen las vistas para que todo quede en el modo nuevo.
        clave = self.current_key
        if self.current_view is not None and hasattr(self.current_view, "on_hide"):
            self.current_view.on_hide()
        for vista in self.view_cache.values():
            vista.destroy()
        self.view_cache = {}
        self.current_view = None
        if clave:
            self.show_view(clave)

    def _close_menu(self):
        if self._menu is not None:
            try:
                self._menu.destroy()
            except tk.TclError:
                pass
            self._menu = None

    def _click_fuera(self, event):
        if self._menu is None or event.widget is self.avatar_btn:
            return
        w = event.widget
        while w is not None:
            if w is self._menu or w is self.avatar_btn:
                return
            w = getattr(w, "master", None)
        self._close_menu()

    def _pedir_logout(self):
        self._close_menu()
        ConfirmDialog(self, "↪", "¿Cerrar sesión?",
                      "Tendrás que volver a ingresar tu usuario y contraseña.",
                      "Cerrar sesión", self._logout)

    def _logout(self):
        self._stop_sync()
        run_async(self, self.api.logout, lambda _r: self._show_login(), lambda _e: self._show_login())

    def _on_close(self):
        save_config(self.config)
        self.destroy()
