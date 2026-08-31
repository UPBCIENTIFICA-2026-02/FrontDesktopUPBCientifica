# -*- coding: utf-8 -*-
"""Vista de inicio / panel."""

from pathlib import Path
import customtkinter as ctk

from ..theme import TEXT, MUTED, MAGENTA, AMBER, CARD
from ..widgets import section_title, card, primary_button, ghost_button


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        section_title(self, "Inicio",
                      "Cliente de escritorio del sistema distribuido UPB-CIENTÍFICA").pack(anchor="w", pady=(0, 16))

        status = card(self)
        status.pack(fill="x", pady=(0, 16))
        row = ctk.CTkFrame(status, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=14)
        ctk.CTkLabel(row, text="Estado:", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).pack(side="left")
        ctk.CTkLabel(row, text="  Modo demostración (sin conexión al backend)  ",
                     fg_color="#FEF3C7", text_color=AMBER, corner_radius=8,
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10)
        ctk.CTkLabel(row, text=f"Servidor configurado: {self.app.config['server_url']}",
                     text_color=MUTED, font=ctk.CTkFont(size=12)).pack(side="right")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x")
        for i in range(3):
            grid.grid_columnconfigure(i, weight=1, uniform="c")
        self._stat(grid, 0, "Trabajos HPC", str(len(self.app.config["jobs"])), "en cola local")
        self._stat(grid, 1, "Archivos en Home", str(len(self.app.api.list_home())), "carga local (demo)")
        album = self.app.config.get("album_folder") or ""
        self._stat(grid, 2, "Carpeta de álbum", Path(album).name if album else "—", album or "sin definir")

        qa = card(self)
        qa.pack(fill="x", pady=(16, 0))
        ctk.CTkLabel(qa, text="Accesos rápidos", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).pack(anchor="w", padx=16, pady=(14, 6))
        qrow = ctk.CTkFrame(qa, fg_color="transparent")
        qrow.pack(fill="x", padx=16, pady=(0, 14))
        primary_button(qrow, "Enviar trabajo HPC", lambda: self.app.show_view("jobs")).pack(side="left", padx=(0, 8))
        ghost_button(qrow, "Álbum de fotos", lambda: self.app.show_view("album")).pack(side="left", padx=8)
        ghost_button(qrow, "Sincronizar", lambda: self.app.show_view("sync")).pack(side="left", padx=8)

    def _stat(self, parent, col, title, value, note):
        c = card(parent)
        c.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0))
        ctk.CTkLabel(c, text=title, text_color=MUTED, font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(c, text=value, text_color=MAGENTA, font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", padx=16)
        ctk.CTkLabel(c, text=note, text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16, pady=(0, 14))
