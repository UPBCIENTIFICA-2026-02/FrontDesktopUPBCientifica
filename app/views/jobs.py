# -*- coding: utf-8 -*-
"""Vista de trabajos HPC (MPI)."""

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..theme import TEXT, MUTED, MAGENTA, MAGENTA_DARK, AMBER, GRAY_BG, CARD
from ..widgets import section_title, card, primary_button, ghost_button


class JobsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.code_path = ""
        self.data_path = ""
        section_title(self, "Trabajos HPC (MPI)",
                      "Prepara y encola trabajos para el clúster. El envío real se hará por RMI hacia SLURM.").pack(anchor="w", pady=(0, 16))

        form = card(self)
        form.pack(fill="x")
        inner = ctk.CTkFrame(form, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)
        inner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(inner, text="Nombre del trabajo", text_color=TEXT).grid(row=0, column=0, sticky="w", pady=6, padx=(0, 12))
        self.e_name = ctk.CTkEntry(inner, placeholder_text="p. ej. simulacion_fluidos")
        self.e_name.grid(row=0, column=1, columnspan=2, sticky="ew", pady=6)

        ctk.CTkLabel(inner, text="Archivo de código", text_color=TEXT).grid(row=1, column=0, sticky="w", pady=6, padx=(0, 12))
        self.l_code = ctk.CTkLabel(inner, text="ningún archivo seleccionado", text_color=MUTED, anchor="w")
        self.l_code.grid(row=1, column=1, sticky="ew", pady=6)
        ghost_button(inner, "Examinar", self._pick_code, width=110).grid(row=1, column=2, padx=(8, 0), pady=6)

        ctk.CTkLabel(inner, text="Datos / dataset", text_color=TEXT).grid(row=2, column=0, sticky="w", pady=6, padx=(0, 12))
        self.l_data = ctk.CTkLabel(inner, text="ninguna carpeta seleccionada", text_color=MUTED, anchor="w")
        self.l_data.grid(row=2, column=1, sticky="ew", pady=6)
        ghost_button(inner, "Examinar", self._pick_data, width=110).grid(row=2, column=2, padx=(8, 0), pady=6)

        ctk.CTkLabel(inner, text="Nodos", text_color=TEXT).grid(row=3, column=0, sticky="w", pady=6, padx=(0, 12))
        self.e_nodes = ctk.CTkOptionMenu(inner, values=["1", "2", "3", "4"], fg_color=MAGENTA, button_color=MAGENTA_DARK)
        self.e_nodes.set("2")
        self.e_nodes.grid(row=3, column=1, sticky="w", pady=6)

        ctk.CTkLabel(inner, text="Tareas (np)", text_color=TEXT).grid(row=4, column=0, sticky="w", pady=6, padx=(0, 12))
        self.e_tasks = ctk.CTkEntry(inner, placeholder_text="p. ej. 8", width=120)
        self.e_tasks.grid(row=4, column=1, sticky="w", pady=6)

        primary_button(inner, "Enviar trabajo", self._submit, width=170).grid(row=5, column=1, sticky="w", pady=(12, 0))

        ctk.CTkLabel(self, text="Trabajos enviados", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).pack(anchor="w", pady=(18, 6))
        self.table = ctk.CTkScrollableFrame(self, fg_color=CARD, corner_radius=12, height=220)
        self.table.pack(fill="both", expand=True)
        self._refresh_table()

    def _pick_code(self):
        p = filedialog.askopenfilename(title="Seleccionar archivo de código",
                                       filetypes=[("Código", "*.c *.cpp *.py *.f90 *.f *.sh"), ("Todos", "*.*")])
        if p:
            self.code_path = p
            self.l_code.configure(text=os.path.basename(p), text_color=TEXT)

    def _pick_data(self):
        p = filedialog.askdirectory(title="Seleccionar carpeta de datos")
        if p:
            self.data_path = p
            self.l_data.configure(text=p, text_color=TEXT)

    def _submit(self):
        name = self.e_name.get().strip()
        if not name:
            messagebox.showwarning("Faltan datos", "Escribe un nombre para el trabajo.")
            return
        if not self.code_path:
            messagebox.showwarning("Faltan datos", "Selecciona el archivo de código.")
            return
        job = {
            "nombre": name,
            "codigo": os.path.basename(self.code_path),
            "datos": self.data_path or "(sin datos)",
            "nodos": self.e_nodes.get(),
            "tareas": self.e_tasks.get().strip() or "-",
        }
        self.app.api.submit_job(job)
        self.e_name.delete(0, "end")
        self.e_tasks.delete(0, "end")
        self.code_path = ""
        self.data_path = ""
        self.l_code.configure(text="ningún archivo seleccionado", text_color=MUTED)
        self.l_data.configure(text="ninguna carpeta seleccionada", text_color=MUTED)
        self._refresh_table()
        messagebox.showinfo("Trabajo encolado",
                            "El trabajo se guardó localmente en estado 'Encolado (demo)'.\n\n"
                            "Cuando el backend esté disponible se enviará por RMI al clúster (SLURM/MPI).")

    def _refresh_table(self):
        for w in self.table.winfo_children():
            w.destroy()
        headers = ["Nombre", "Código", "Nodos", "Tareas", "Estado", "Fecha"]
        weights = [3, 3, 1, 1, 2, 2]
        hrow = ctk.CTkFrame(self.table, fg_color="transparent")
        hrow.pack(fill="x", padx=8, pady=(8, 4))
        for i, h in enumerate(headers):
            hrow.grid_columnconfigure(i, weight=weights[i])
            ctk.CTkLabel(hrow, text=h, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=MUTED, anchor="w").grid(row=0, column=i, sticky="ew", padx=4)
        jobs = self.app.config["jobs"]
        if not jobs:
            ctk.CTkLabel(self.table, text="Aún no has enviado trabajos.", text_color=MUTED).pack(pady=20)
            return
        for j in jobs:
            r = ctk.CTkFrame(self.table, fg_color=GRAY_BG, corner_radius=8)
            r.pack(fill="x", padx=8, pady=3)
            vals = [j.get("nombre", "-"), j.get("codigo", "-"), j.get("nodos", "-"),
                    j.get("tareas", "-"), j.get("estado", "-"), j.get("fecha", "-")]
            for i, v in enumerate(vals):
                r.grid_columnconfigure(i, weight=weights[i])
                color = AMBER if (i == 4) else TEXT
                ctk.CTkLabel(r, text=str(v), text_color=color, anchor="w",
                             font=ctk.CTkFont(size=12)).grid(row=0, column=i, sticky="ew", padx=4, pady=6)
