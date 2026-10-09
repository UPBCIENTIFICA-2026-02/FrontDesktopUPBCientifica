# -*- coding: utf-8 -*-
"""Diálogo para compartir un archivo (POST /shared-file/compartir)."""

import customtkinter as ctk
from tkinter import messagebox

from ..theme import ON_SURFACE, ON_SURFACE_VARIANT, ERROR, font
from ..widgets import primary_button, ghost_button
from ..utils import run_async, describir


class CompartirDialog(ctk.CTkToplevel):
    def __init__(self, master, api, archivo_id="", nombre="", on_done=None):
        super().__init__(master)
        self.api = api
        self.on_done = on_done
        self.title("Compartir archivo")
        self.geometry("520x470")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(80, self._focus)

        ctk.CTkLabel(self, text="Compartir archivo", font=font("title_large"),
                     text_color=ON_SURFACE).pack(anchor="w", padx=24, pady=(20, 2))
        ctk.CTkLabel(self, text=nombre or "Indica el ID del archivo en Storage.",
                     text_color=ON_SURFACE_VARIANT).pack(anchor="w", padx=24)

        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=24, pady=14)
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="ID del archivo").grid(row=0, column=0, sticky="w", pady=8, padx=(0, 14))
        self.e_id = ctk.CTkEntry(f, height=36)
        self.e_id.insert(0, archivo_id)
        self.e_id.grid(row=0, column=1, sticky="ew", pady=8)

        ctk.CTkLabel(f, text="Compartir con").grid(row=1, column=0, sticky="w", pady=8, padx=(0, 14))
        self.tipo = ctk.CTkSegmentedButton(f, values=["Usuario", "Grupo"])
        self.tipo.set("Usuario")
        self.tipo.grid(row=1, column=1, sticky="w", pady=8)

        ctk.CTkLabel(f, text="ID destinatario").grid(row=2, column=0, sticky="w", pady=8, padx=(0, 14))
        self.e_dest = ctk.CTkEntry(f, height=36, placeholder_text="p. ej. maria.lopez o investigadores")
        self.e_dest.grid(row=2, column=1, sticky="ew", pady=8)

        ctk.CTkLabel(f, text="Permisos (Unix)").grid(row=3, column=0, sticky="nw", pady=8, padx=(0, 14))
        perms = ctk.CTkFrame(f, fg_color="transparent")
        perms.grid(row=3, column=1, sticky="w", pady=8)
        self.p_r = ctk.CTkCheckBox(perms, text="Lectura (r)", command=self._preview)
        self.p_w = ctk.CTkCheckBox(perms, text="Escritura (w)", command=self._preview)
        self.p_x = ctk.CTkCheckBox(perms, text="Ejecución (x)", command=self._preview)
        for cb in (self.p_r, self.p_w, self.p_x):
            cb.pack(anchor="w", pady=3)
        self.p_r.select()
        self.l_perm = ctk.CTkLabel(f, text="", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"))
        self.l_perm.grid(row=4, column=1, sticky="w")
        self._preview()

        self.error = ctk.CTkLabel(self, text="", text_color=ERROR, wraplength=460)
        self.error.pack(anchor="w", padx=24)
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24, pady=(4, 20))
        self.btn = primary_button(bar, "Compartir", self._ok, width=130)
        self.btn.pack(side="right")
        ghost_button(bar, "Cancelar", self.destroy, width=120).pack(side="right", padx=8)

    def _focus(self):
        self.lift()
        self.focus_force()
        try:
            self.grab_set()
        except Exception:
            pass

    def _permiso(self):
        return ("r" if self.p_r.get() else "-") + ("w" if self.p_w.get() else "-") + \
               ("x" if self.p_x.get() else "-")

    def _preview(self):
        self.l_perm.configure(text=self._permiso())

    def _ok(self):
        archivo = self.e_id.get().strip()
        dest = self.e_dest.get().strip()
        if not archivo or not dest:
            self.error.configure(text="Completa el ID del archivo y el destinatario.")
            return
        if self._permiso() == "---":
            self.error.configure(text="Elige al menos un permiso.")
            return
        es_usuario = self.tipo.get() == "Usuario"
        self.btn.configure(state="disabled", text="Compartiendo…")

        def call():
            return self.api.shared.compartir(
                archivo, self._permiso(),
                usuario_id=dest if es_usuario else None,
                grupo_id=None if es_usuario else dest)

        def ok(compartido_id):
            simulado = " (simulado)" if self.api.shared.simulado else ""
            messagebox.showinfo("Compartido",
                                f"Archivo compartido con {dest} ({self._permiso()}){simulado}.\n"
                                f"ID de compartición: {compartido_id}", parent=self)
            if self.on_done:
                self.on_done()
            self.destroy()

        def err(e):
            self.btn.configure(state="normal", text="Compartir")
            self.error.configure(text=describir(e))

        run_async(self, call, ok, err)
