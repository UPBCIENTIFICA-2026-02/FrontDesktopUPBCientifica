# -*- coding: utf-8 -*-
"""Vista de trabajos HPC (MPI)."""

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..theme import ON_SURFACE, ON_SURFACE_VARIANT, font
from ..widgets import section_title, card, primary_button, ghost_button, banner, chip, divider, StatePanel


class JobsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.code_path = ""
        self.data_path = ""
        section_title(self, "Trabajos HPC (MPI)",
                      "Prepara y encola trabajos para el clúster (SLURM/MPI).").pack(anchor="w", pady=(0, 12))

        banner(self, "Envío al clúster pendiente",
               "El contrato de HPC exige RMI, que solo existe en la JVM (tampoco está en Android). "
               "Hasta que HPC exponga gRPC/REST, los trabajos se guardan en una cola local de demostración.").pack(fill="x", pady=(0, 12))

        form = card(self)
        form.pack(fill="x")
        inner = ctk.CTkFrame(form, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)
        inner.grid_columnconfigure(1, weight=1)

        def label(r, t):
            ctk.CTkLabel(inner, text=t, text_color=ON_SURFACE).grid(row=r, column=0, sticky="w", pady=6, padx=(0, 16))

        label(0, "Nombre del trabajo")
        self.e_name = ctk.CTkEntry(inner, height=36, placeholder_text="p. ej. simulacion_fluidos")
        self.e_name.grid(row=0, column=1, columnspan=2, sticky="ew", pady=6)

        label(1, "Archivo de código")
        self.l_code = ctk.CTkLabel(inner, text="ningún archivo seleccionado", text_color=ON_SURFACE_VARIANT, anchor="w")
        self.l_code.grid(row=1, column=1, sticky="ew", pady=6)
        ghost_button(inner, "Examinar", self._pick_code, width=110, height=34).grid(row=1, column=2, padx=(8, 0), pady=6)

        label(2, "Datos / dataset")
        self.l_data = ctk.CTkLabel(inner, text="ninguna carpeta seleccionada", text_color=ON_SURFACE_VARIANT, anchor="w")
        self.l_data.grid(row=2, column=1, sticky="ew", pady=6)
        ghost_button(inner, "Examinar", self._pick_data, width=110, height=34).grid(row=2, column=2, padx=(8, 0), pady=6)

        label(3, "Nodos")
        self.e_nodes = ctk.CTkOptionMenu(inner, values=["1", "2", "3", "4"], width=100)
        self.e_nodes.set("2")
        self.e_nodes.grid(row=3, column=1, sticky="w", pady=6)

        label(4, "Tareas (np)")
        self.e_tasks = ctk.CTkEntry(inner, height=36, placeholder_text="p. ej. 8", width=120)
        self.e_tasks.grid(row=4, column=1, sticky="w", pady=6)

        primary_button(inner, "Enviar trabajo", self._submit, width=170).grid(row=5, column=1, sticky="w", pady=(12, 0))

        ctk.CTkLabel(self, text="Trabajos enviados", font=font("title_medium"),
                     text_color=ON_SURFACE).pack(anchor="w", pady=(18, 6))
        self.table = StatePanel(self, height=200)
        self.table.pack(fill="both", expand=True)
        self._refresh_table()

    def _pick_code(self):
        p = filedialog.askopenfilename(title="Seleccionar archivo de código",
                                       filetypes=[("Código", "*.c *.cpp *.py *.f90 *.f *.sh"), ("Todos", "*.*")])
        if p:
            self.code_path = p
            self.l_code.configure(text=os.path.basename(p), text_color=ON_SURFACE)

    def _pick_data(self):
        p = filedialog.askdirectory(title="Seleccionar carpeta de datos")
        if p:
            self.data_path = p
            self.l_data.configure(text=p, text_color=ON_SURFACE)

    def _submit(self):
        name = self.e_name.get().strip()
        if not name:
            messagebox.showwarning("Faltan datos", "Escribe un nombre para el trabajo.")
            return
        if not self.code_path:
            messagebox.showwarning("Faltan datos", "Selecciona el archivo de código.")
            return
        tareas = self.e_tasks.get().strip()
        if tareas and not tareas.isdigit():
            messagebox.showwarning("Dato inválido", "Las tareas (np) deben ser un número entero.")
            return
        job = {
            "nombre": name,
            "codigo": os.path.basename(self.code_path),
            "datos": self.data_path or "(sin datos)",
            "nodos": self.e_nodes.get(),
            "tareas": tareas or "-",
        }
        self.app.api.submit_job(job)
        self.e_name.delete(0, "end")
        self.e_tasks.delete(0, "end")
        self.code_path = ""
        self.data_path = ""
        self.l_code.configure(text="ningún archivo seleccionado", text_color=ON_SURFACE_VARIANT)
        self.l_data.configure(text="ninguna carpeta seleccionada", text_color=ON_SURFACE_VARIANT)
        self._refresh_table()
        messagebox.showinfo("Trabajo encolado",
                            "El trabajo se guardó localmente en estado 'Encolado (demo)'.\n\n"
                            "Cuando HPC esté disponible se enviará al clúster (SLURM/MPI).")

    def _refresh_table(self):
        jobs = self.app.config["jobs"]
        if not jobs:
            self.table.empty("Aún no has enviado trabajos.")
            return
        self.table.clear()
        headers = ["Nombre", "Código", "Nodos", "Tareas", "Estado", "Fecha"]
        weights = [3, 3, 1, 1, 2, 2]
        hrow = ctk.CTkFrame(self.table, fg_color="transparent")
        hrow.pack(fill="x", padx=12, pady=(8, 4))
        for i, h in enumerate(headers):
            hrow.grid_columnconfigure(i, weight=weights[i], uniform="j")
            ctk.CTkLabel(hrow, text=h, font=font("label_small"), text_color=ON_SURFACE_VARIANT,
                         anchor="w").grid(row=0, column=i, sticky="ew", padx=4)
        for j in jobs:
            divider(self.table).pack(fill="x", padx=12)
            r = ctk.CTkFrame(self.table, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=2)
            vals = [j.get("nombre", "-"), j.get("codigo", "-"), j.get("nodos", "-"),
                    j.get("tareas", "-"), j.get("estado", "-"), j.get("fecha", "-")]
            for i, v in enumerate(vals):
                r.grid_columnconfigure(i, weight=weights[i], uniform="j")
                if i == 4:
                    chip(r, str(v), "warn").grid(row=0, column=i, sticky="w", padx=4, pady=6)
                else:
                    ctk.CTkLabel(r, text=str(v), text_color=ON_SURFACE, anchor="w").grid(
                        row=0, column=i, sticky="ew", padx=4, pady=6)
