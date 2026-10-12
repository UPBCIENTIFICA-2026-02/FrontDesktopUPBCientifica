# -*- coding: utf-8 -*-
"""Diálogo Compartir (Contrato_SharedFile): CompartirArchivo o
CompartirDirectorio según el elemento. Una carpeta compartida comparte también
todo lo que se meta dentro después."""

import customtkinter as ctk
from tkinter import messagebox

from ..theme import ON_SURFACE, ON_SURFACE_VARIANT, ERROR, font
from ..widgets import primary_button, ghost_button, Dialog
from ..utils import run_async, describir
from ..data.sharedfile import NIVELES, USUARIO, GRUPO, texto_nivel


class CompartirDialog(Dialog):
    def __init__(self, master, api, elemento_id, nombre, es_directorio=False, on_done=None):
        super().__init__(master, "Compartir", 520, 470 if es_directorio else 440)
        self.api = api
        self.elemento_id = elemento_id
        self.es_directorio = es_directorio
        self.on_done = on_done

        ctk.CTkLabel(self, text=f"Compartir {'la carpeta ' if es_directorio else ''}«{nombre}»",
                     font=font("title_large"), text_color=ON_SURFACE, wraplength=460,
                     justify="left").pack(anchor="w", padx=24, pady=(20, 2))
        if es_directorio:
            ctk.CTkLabel(self, text="También tendrá acceso a todo lo que haya o se añada dentro.",
                         text_color=ON_SURFACE_VARIANT).pack(anchor="w", padx=24)

        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=24, pady=14)
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="Compartir con").grid(row=0, column=0, sticky="w", pady=8, padx=(0, 14))
        self.tipo = ctk.CTkSegmentedButton(f, values=["Usuario", "Grupo"], command=self._cambiar_tipo)
        self.tipo.set("Usuario")
        self.tipo.grid(row=0, column=1, sticky="w", pady=8)

        self.l_dest = ctk.CTkLabel(f, text="Usuario")
        self.l_dest.grid(row=1, column=0, sticky="w", pady=8, padx=(0, 14))
        self.e_dest = ctk.CTkEntry(f, height=36, placeholder_text="p. ej. investigador")
        self.e_dest.grid(row=1, column=1, sticky="ew", pady=8)
        self.e_dest.bind("<Return>", lambda _e: self._ok())

        ctk.CTkLabel(f, text="Permiso").grid(row=2, column=0, sticky="nw", pady=8, padx=(0, 14))
        caja = ctk.CTkFrame(f, fg_color="transparent")
        caja.grid(row=2, column=1, sticky="w", pady=8)
        self.nivel = ctk.StringVar(value=NIVELES[0][0])
        for valor, texto in NIVELES:
            ctk.CTkRadioButton(caja, text=texto, variable=self.nivel, value=valor).pack(anchor="w", pady=4)

        self.error = ctk.CTkLabel(self, text="", text_color=ERROR, wraplength=460, justify="left")
        self.error.pack(anchor="w", padx=24)
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24, pady=(4, 20))
        self.btn = primary_button(bar, "Compartir", self._ok, width=130)
        self.btn.pack(side="right")
        ghost_button(bar, "Cancelar", self.destroy, width=120).pack(side="right", padx=8)
        self.after(150, self.e_dest.focus_set)

    def _cambiar_tipo(self, valor):
        self.l_dest.configure(text=valor)
        self.e_dest.configure(placeholder_text="p. ej. investigador" if valor == "Usuario" else "p. ej. investigadores")

    def _ok(self):
        dest = self.e_dest.get().strip()
        if not dest:
            self.error.configure(text="Escribe a quién quieres compartirlo.")
            return
        tipo = USUARIO if self.tipo.get() == "Usuario" else GRUPO
        nivel = self.nivel.get()
        self.btn.configure(state="disabled", text="Compartiendo…")
        self.error.configure(text="")

        def ok(_r):
            destino = f"el grupo {dest}" if tipo == GRUPO else dest
            messagebox.showinfo("Compartido", f"Compartido con {destino}: {texto_nivel(nivel).lower()}.",
                                parent=self.master)
            if self.on_done:
                self.on_done()
            self.destroy()

        def err(e):
            self.btn.configure(state="normal", text="Compartir")
            self.error.configure(text=describir(e))

        run_async(self, lambda: self.api.shared.compartir(self.elemento_id, self.es_directorio, tipo, dest, nivel),
                  ok, err)
