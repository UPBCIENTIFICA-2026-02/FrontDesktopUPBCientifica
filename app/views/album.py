# -*- coding: utf-8 -*-
"""Vista de álbum de fotos (galería local)."""

import os
import customtkinter as ctk
from tkinter import filedialog

from ..theme import (ON_SURFACE_VARIANT as MUTED, WARNING as AMBER, SURFACE_CONTAINER as GRAY_BG,
                     SURFACE_CONTAINER_LOW as CARD, SURFACE_CONTAINER_HIGH, OUTLINE_VARIANT)
from ..widgets import section_title, primary_button
from ..utils import open_with_system
from ..config import IMG_EXT, save_config

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class AlbumView(ctk.CTkFrame):
    THUMB = (150, 150)
    COLS = 4

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._thumbs = []  # mantener referencias para evitar GC
        section_title(self, "Álbum de fotos",
                      "Explora y visualiza imágenes de una carpeta local (funciona sin backend).").pack(anchor="w", pady=(0, 16))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        primary_button(bar, "🖼  Elegir carpeta de imágenes", self._pick, width=240).pack(side="left")
        self.info = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.info.pack(side="left", padx=12)

        self.gallery = ctk.CTkScrollableFrame(self, fg_color=CARD, corner_radius=12,
                                              border_width=1, border_color=OUTLINE_VARIANT)
        self.gallery.pack(fill="both", expand=True)

        if not HAS_PIL:
            ctk.CTkLabel(self.gallery, text="Instala Pillow para ver las imágenes:  pip install Pillow",
                         text_color=AMBER).pack(pady=30)
        else:
            folder = self.app.config.get("album_folder")
            if folder and os.path.isdir(folder):
                self._load(folder)
            else:
                ctk.CTkLabel(self.gallery, text="Elige una carpeta con imágenes para mostrar la galería.",
                             text_color=MUTED).pack(pady=30)

    def _pick(self):
        p = filedialog.askdirectory(title="Carpeta con imágenes")
        if p:
            self.app.config["album_folder"] = p
            save_config(self.app.config)
            self._load(p)

    def _load(self, folder):
        for w in self.gallery.winfo_children():
            w.destroy()
        self._thumbs.clear()
        if not HAS_PIL:
            return
        files = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(IMG_EXT)]
        self.info.configure(text=f"{len(files)} imagen(es) en {os.path.basename(folder)}")
        if not files:
            ctk.CTkLabel(self.gallery, text="La carpeta no contiene imágenes.", text_color=MUTED).pack(pady=30)
            return
        for c in range(self.COLS):
            self.gallery.grid_columnconfigure(c, weight=1)
        r = c = 0
        for name in files[:200]:
            full = os.path.join(folder, name)
            try:
                im = Image.open(full)
                im.thumbnail(self.THUMB)
                cimg = ctk.CTkImage(light_image=im, dark_image=im, size=im.size)
                self._thumbs.append(cimg)
            except Exception:
                continue
            cell = ctk.CTkFrame(self.gallery, fg_color=GRAY_BG, corner_radius=10)
            cell.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
            ctk.CTkButton(cell, image=cimg, text="", fg_color="transparent",
                          hover_color=SURFACE_CONTAINER_HIGH, command=lambda p=full: self._view(p)).pack(padx=6, pady=(6, 2))
            ctk.CTkLabel(cell, text=(name[:22] + "\u2026") if len(name) > 23 else name,
                         text_color=MUTED, font=ctk.CTkFont(size=11)).pack(pady=(0, 6))
            c += 1
            if c >= self.COLS:
                c = 0
                r += 1

    def _view(self, path):
        if not HAS_PIL:
            return
        top = ctk.CTkToplevel(self)
        top.title(os.path.basename(path))
        top.geometry("820x640")
        top.after(50, top.lift)
        try:
            im = Image.open(path)
            im.thumbnail((780, 560))
            cimg = ctk.CTkImage(light_image=im, dark_image=im, size=im.size)
            lbl = ctk.CTkLabel(top, image=cimg, text="")
            lbl.image = cimg  # evitar GC
            lbl.pack(padx=10, pady=10, expand=True)
        except Exception as e:
            ctk.CTkLabel(top, text=f"No se pudo abrir la imagen:\n{e}").pack(pady=30)
        primary_button(top, "Abrir con el sistema", lambda: open_with_system(path), width=200).pack(pady=(0, 12))
