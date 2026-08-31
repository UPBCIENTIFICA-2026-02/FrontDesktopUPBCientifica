# -*- coding: utf-8 -*-
"""Vista de archivos compartidos (Home local simulado)."""

import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..theme import TEXT, MUTED, MAGENTA, GRAY_BG, CARD
from ..widgets import section_title, primary_button, ghost_button
from ..utils import human_size, open_with_system
from ..config import HOME_DIR


class SharedFilesView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        section_title(self, "Archivos compartidos",
                      "Sube archivos a tu Home. Aquí se copian a un Home local (demo); el backend usará NFS con cuota y permisos Unix.").pack(anchor="w", pady=(0, 16))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        primary_button(bar, "Subir archivo(s)", self._upload, width=160).pack(side="left")
        ghost_button(bar, "Abrir carpeta Home", lambda: open_with_system(str(HOME_DIR)), width=170).pack(side="left", padx=8)
        ghost_button(bar, "Actualizar", self._refresh, width=110).pack(side="left")

        ctk.CTkLabel(self, text=f"Home local: {HOME_DIR}", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(0, 8))

        self.listing = ctk.CTkScrollableFrame(self, fg_color=CARD, corner_radius=12)
        self.listing.pack(fill="both", expand=True)
        self._refresh()

    def _upload(self):
        paths = filedialog.askopenfilenames(title="Seleccionar archivos para subir")
        if not paths:
            return
        n = 0
        for p in paths:
            try:
                self.app.api.upload_file(p)
                n += 1
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo subir:\n{e}")
        self._refresh()
        if n:
            messagebox.showinfo("Listo", f"{n} archivo(s) copiado(s) al Home local (demo).\n\n"
                                         "Con el backend se subirán al Home del usuario en el servidor (NFS).")

    def _refresh(self):
        for w in self.listing.winfo_children():
            w.destroy()
        items = self.app.api.list_home()
        if not items:
            ctk.CTkLabel(self.listing, text="Tu Home local está vacío. Sube archivos para comenzar.",
                         text_color=MUTED).pack(pady=24)
            return
        for name, size in items:
            r = ctk.CTkFrame(self.listing, fg_color=GRAY_BG, corner_radius=8)
            r.pack(fill="x", padx=8, pady=3)
            ctk.CTkLabel(r, text=name, text_color=TEXT, anchor="w").pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(r, text=human_size(size), text_color=MUTED).pack(side="left", padx=6)
            ctk.CTkButton(r, text="Abrir", width=70, fg_color="transparent", text_color=MAGENTA,
                          hover_color=GRAY_BG, border_width=1, border_color=MAGENTA,
                          command=lambda n=name: open_with_system(str(HOME_DIR / n))).pack(side="right", padx=10)
            ctk.CTkLabel(r, text="permisos: rw- (demo)", text_color=MUTED,
                         font=ctk.CTkFont(size=11)).pack(side="right", padx=6)
