# -*- coding: utf-8 -*-
"""Vista de Sincronización (File Sync)."""

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..theme import ON_SURFACE, ON_SURFACE_VARIANT, SUCCESS, font
from ..widgets import section_title, card, primary_button, ghost_button, banner, StatePanel, list_item
from ..utils import human_size
from ..config import save_config


class SyncView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        section_title(self, "Sincronización",
                      "Copia síncrona de una carpeta local con tu Home en el servidor.").pack(anchor="w", pady=(0, 12))

        banner(self, "Sincronización simulada",
               f"File Sync habla gRPC (node-sync en {app.api.conf.direccion_sync}). Igual que en el móvil, "
               "el indicador de la barra superior muestra un ciclo simulado (la conectividad sí es real) "
               "hasta que se genere el stub del .proto. Aquí eliges la carpeta local que se sincronizará.").pack(
            fill="x", pady=(0, 12))

        top = card(self)
        top.pack(fill="x")
        inner = ctk.CTkFrame(top, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)
        inner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(inner, text="Carpeta local", text_color=ON_SURFACE).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=6)
        folder = self.app.config.get("sync_folder")
        self.l_folder = ctk.CTkLabel(inner, text=folder or "ninguna carpeta seleccionada",
                                     text_color=ON_SURFACE if folder else ON_SURFACE_VARIANT, anchor="w")
        self.l_folder.grid(row=0, column=1, sticky="ew", pady=6)
        ghost_button(inner, "Elegir carpeta", self._pick, width=140).grid(row=0, column=2, padx=(8, 0), pady=6)

        ctk.CTkLabel(inner, text="Programación", text_color=ON_SURFACE).grid(row=1, column=0, sticky="w", padx=(0, 16), pady=6)
        self.sched = ctk.CTkOptionMenu(inner, values=["Manual", "Cada hora", "Diaria 22:00", "Al conectar Wi-Fi"])
        self.sched.set(self.app.config.get("sync_schedule", "Manual"))
        self.sched.grid(row=1, column=1, sticky="w", pady=6)

        brow = ctk.CTkFrame(inner, fg_color="transparent")
        brow.grid(row=2, column=1, sticky="w", pady=(12, 0))
        primary_button(brow, "⟳  Sincronizar ahora", self._sync, width=180).pack(side="left")
        ghost_button(brow, "Guardar", self._save, width=110).pack(side="left", padx=8)

        self.summary = ctk.CTkLabel(self, text="", text_color=SUCCESS, font=font("title_small"))
        self.summary.pack(anchor="w", pady=(10, 4))

        ctk.CTkLabel(self, text="Archivos en la carpeta local", font=font("title_medium"),
                     text_color=ON_SURFACE).pack(anchor="w", pady=(4, 6))
        self.listing = StatePanel(self, height=200)
        self.listing.pack(fill="both", expand=True)
        self._refresh_listing()

    def _pick(self):
        p = filedialog.askdirectory(title="Carpeta a sincronizar")
        if p:
            self.app.config["sync_folder"] = p
            save_config(self.app.config)
            self.l_folder.configure(text=p, text_color=ON_SURFACE)
            self._refresh_listing()

    def _save(self):
        self.app.config["sync_schedule"] = self.sched.get()
        save_config(self.app.config)
        messagebox.showinfo("Guardado", "Configuración de sincronización guardada.")

    def _sync(self):
        folder = self.app.config.get("sync_folder")
        if not folder:
            messagebox.showwarning("Sin carpeta", "Primero elige una carpeta local.")
            return
        res = self.app.api.sync_now(folder)
        self.summary.configure(
            text=f"Se detectaron {res['detectados']} archivo(s). "
                 "Se sincronizarán con el servidor cuando File Sync esté disponible.")

    def _refresh_listing(self):
        folder = self.app.config.get("sync_folder")
        if not folder or not os.path.isdir(folder):
            self.listing.empty("Elige una carpeta para ver sus archivos.")
            return
        self.listing.clear()
        count = 0
        for name in sorted(os.listdir(folder)):
            full = os.path.join(folder, name)
            if os.path.isfile(full):
                count += 1
                list_item(self.listing, "📄", name, human_size(os.path.getsize(full)))
                if count >= 300:
                    break
        if count == 0:
            self.listing.empty("La carpeta no tiene archivos.")
