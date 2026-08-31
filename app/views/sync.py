# -*- coding: utf-8 -*-
"""Vista de File Sync."""

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..theme import TEXT, MUTED, MAGENTA, MAGENTA_DARK, GREEN, CARD
from ..widgets import section_title, card, primary_button, ghost_button
from ..utils import human_size
from ..config import save_config


class SyncView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        section_title(self, "File Sync",
                      "Copia síncrona de una carpeta local con el servidor (por gRPC, cuando el backend esté listo).").pack(anchor="w", pady=(0, 16))

        top = card(self)
        top.pack(fill="x")
        inner = ctk.CTkFrame(top, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)
        inner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(inner, text="Carpeta local", text_color=TEXT).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=6)
        self.l_folder = ctk.CTkLabel(inner, text=self.app.config.get("sync_folder") or "ninguna carpeta seleccionada",
                                     text_color=TEXT if self.app.config.get("sync_folder") else MUTED, anchor="w")
        self.l_folder.grid(row=0, column=1, sticky="ew", pady=6)
        ghost_button(inner, "Elegir carpeta", self._pick, width=130).grid(row=0, column=2, padx=(8, 0), pady=6)

        ctk.CTkLabel(inner, text="Programación", text_color=TEXT).grid(row=1, column=0, sticky="w", padx=(0, 12), pady=6)
        self.sched = ctk.CTkOptionMenu(inner, values=["Manual", "Cada hora", "Diaria 22:00", "Al conectar Wi-Fi"],
                                       fg_color=MAGENTA, button_color=MAGENTA_DARK)
        self.sched.set(self.app.config.get("sync_schedule", "Manual"))
        self.sched.grid(row=1, column=1, sticky="w", pady=6)

        brow = ctk.CTkFrame(inner, fg_color="transparent")
        brow.grid(row=2, column=1, sticky="w", pady=(12, 0))
        primary_button(brow, "Sincronizar ahora", self._sync, width=170).pack(side="left")
        ghost_button(brow, "Guardar", self._save, width=110).pack(side="left", padx=8)

        self.summary = ctk.CTkLabel(self, text="", text_color=GREEN, font=ctk.CTkFont(size=13, weight="bold"))
        self.summary.pack(anchor="w", pady=(10, 6))

        ctk.CTkLabel(self, text="Archivos en la carpeta local", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).pack(anchor="w", pady=(8, 6))
        self.listing = ctk.CTkScrollableFrame(self, fg_color=CARD, corner_radius=12, height=200)
        self.listing.pack(fill="both", expand=True)
        self._refresh_listing()

    def _pick(self):
        p = filedialog.askdirectory(title="Carpeta a sincronizar")
        if p:
            self.app.config["sync_folder"] = p
            self.l_folder.configure(text=p, text_color=TEXT)
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
                 f"Se sincronizarán con el servidor cuando el backend esté disponible.")

    def _refresh_listing(self):
        for w in self.listing.winfo_children():
            w.destroy()
        folder = self.app.config.get("sync_folder")
        if not folder or not os.path.isdir(folder):
            ctk.CTkLabel(self.listing, text="Elige una carpeta para ver sus archivos.", text_color=MUTED).pack(pady=20)
            return
        count = 0
        for name in sorted(os.listdir(folder)):
            full = os.path.join(folder, name)
            if os.path.isfile(full):
                count += 1
                r = ctk.CTkFrame(self.listing, fg_color="transparent")
                r.pack(fill="x", padx=12, pady=2)
                ctk.CTkLabel(r, text=name, text_color=TEXT, anchor="w").pack(side="left")
                ctk.CTkLabel(r, text=human_size(os.path.getsize(full)), text_color=MUTED).pack(side="right")
                if count >= 300:
                    break
        if count == 0:
            ctk.CTkLabel(self.listing, text="La carpeta no tiene archivos.", text_color=MUTED).pack(pady=20)
