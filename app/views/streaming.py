# -*- coding: utf-8 -*-
"""Vista de streaming de video (reproducción local)."""

import os
import customtkinter as ctk
from tkinter import filedialog

from ..theme import TEXT, MUTED, CARD, GRAY_BG
from ..widgets import section_title, primary_button
from ..utils import human_size, open_with_system
from ..config import VID_EXT, save_config


class StreamingView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        section_title(self, "Streaming de video",
                      "Reproduce videos de una carpeta local con el reproductor del sistema. El streaming HLS remoto llegará con el backend.").pack(anchor="w", pady=(0, 16))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        primary_button(bar, "Elegir carpeta de videos", self._pick, width=210).pack(side="left")
        self.info = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.info.pack(side="left", padx=12)

        self.listing = ctk.CTkScrollableFrame(self, fg_color=CARD, corner_radius=12)
        self.listing.pack(fill="both", expand=True)

        folder = self.app.config.get("video_folder")
        if folder and os.path.isdir(folder):
            self._load(folder)
        else:
            ctk.CTkLabel(self.listing, text="Elige una carpeta con videos.", text_color=MUTED).pack(pady=30)

    def _pick(self):
        p = filedialog.askdirectory(title="Carpeta con videos")
        if p:
            self.app.config["video_folder"] = p
            save_config(self.app.config)
            self._load(p)

    def _load(self, folder):
        for w in self.listing.winfo_children():
            w.destroy()
        vids = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(VID_EXT)]
        self.info.configure(text=f"{len(vids)} video(s)")
        if not vids:
            ctk.CTkLabel(self.listing, text="La carpeta no contiene videos.", text_color=MUTED).pack(pady=30)
            return
        for name in vids:
            full = os.path.join(folder, name)
            r = ctk.CTkFrame(self.listing, fg_color=GRAY_BG, corner_radius=8)
            r.pack(fill="x", padx=8, pady=3)
            ctk.CTkLabel(r, text=name, text_color=TEXT, anchor="w").pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(r, text=human_size(os.path.getsize(full)), text_color=MUTED).pack(side="left", padx=6)
            primary_button(r, "Reproducir", lambda p=full: open_with_system(p), width=120).pack(side="right", padx=10, pady=6)
