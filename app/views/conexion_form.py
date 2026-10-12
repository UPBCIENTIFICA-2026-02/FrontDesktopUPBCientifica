# -*- coding: utf-8 -*-
"""Formulario de conexión a los servicios (lo que en el móvil se edita a mano en
network/Configuracion.kt). Se usa en Configuración y en el diálogo del login."""

import customtkinter as ctk

from ..theme import ON_SURFACE, ON_SURFACE_VARIANT, font
from ..network.configuracion import ENTORNOS
from ..widgets import primary_button, ghost_button


class ConexionForm(ctk.CTkFrame):
    SWITCHES = [
        ("usar_mock_auth", "Usar el mock de autenticación antiguo (server.js, puerto 8080)"),
        ("storage_simulado", "Storage con datos simulados (Home local en vez de node-repository)"),
        ("streaming_simulado", "Streaming y fotos simulados (en vez de node-media)"),
        ("shared_file_disponible", "Shared File disponible (node-shared-file, puerto 8085)"),
        ("hpc_simulado", "HPC simulado (en vez de job-api, puerto 8082)"),
    ]
    HOSTS_LAB = [
        ("host_soap_lab", "Auth SOAP (8081)"),
        ("host_storage_lab", "Storage (8084) y Shared File (8085)"),
        ("host_media_lab", "Media / Streaming (8083)"),
        ("host_sync_lab", "File Sync gRPC (9090)"),
        ("host_hpc_lab", "HPC job-api (8082)"),
    ]

    def __init__(self, master, cfg):
        super().__init__(master, fg_color="transparent")
        self.cfg = cfg
        self.grid_columnconfigure(1, weight=1)

        r = 0
        ctk.CTkLabel(self, text="Entorno", text_color=ON_SURFACE).grid(row=r, column=0, sticky="w", padx=(0, 16), pady=8)
        self.entorno = ctk.CTkSegmentedButton(self, values=list(ENTORNOS), command=self._toggle)
        self.entorno.set(cfg.get("entorno", "LOCAL"))
        self.entorno.grid(row=r, column=1, sticky="w", pady=8)

        r += 1
        ctk.CTkLabel(self, text="Host de los servicios", text_color=ON_SURFACE).grid(row=r, column=0, sticky="w", padx=(0, 16), pady=8)
        self.e_host = ctk.CTkEntry(self, height=36, placeholder_text="localhost o IP del PC con los servicios")
        self.e_host.insert(0, cfg.get("host_desarrollo", "127.0.0.1"))
        self.e_host.grid(row=r, column=1, sticky="ew", pady=8)

        r += 1
        self.lab_box = ctk.CTkFrame(self, fg_color="transparent")
        self.lab_box.grid(row=r, column=0, columnspan=2, sticky="ew")
        self.lab_box.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.lab_box, text="VMs del laboratorio", font=font("title_small"),
                     text_color=ON_SURFACE).grid(row=0, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.e_lab = {}
        for i, (key, label) in enumerate(self.HOSTS_LAB, start=1):
            ctk.CTkLabel(self.lab_box, text=label, text_color=ON_SURFACE_VARIANT).grid(row=i, column=0, sticky="w", padx=(0, 16), pady=4)
            e = ctk.CTkEntry(self.lab_box, height=34)
            e.insert(0, cfg.get(key, ""))
            e.grid(row=i, column=1, sticky="ew", pady=4)
            self.e_lab[key] = e

        r += 1
        self.switches = {}
        sw_box = ctk.CTkFrame(self, fg_color="transparent")
        sw_box.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for key, label in self.SWITCHES:
            s = ctk.CTkSwitch(sw_box, text=label, switch_width=44, switch_height=22)
            if cfg.get(key):
                s.select()
            s.pack(anchor="w", pady=5)
            self.switches[key] = s

        self._toggle(self.entorno.get())

    def _toggle(self, entorno):
        if entorno == "LABORATORIO":
            self.lab_box.grid()
        else:
            self.lab_box.grid_remove()

    def aplicar(self):
        """Vuelca los valores del formulario a la configuración."""
        self.cfg["entorno"] = self.entorno.get()
        self.cfg["host_desarrollo"] = self.e_host.get().strip() or "127.0.0.1"
        for key, e in self.e_lab.items():
            self.cfg[key] = e.get().strip()
        for key, s in self.switches.items():
            self.cfg[key] = bool(s.get())


class ConexionDialog(ctk.CTkToplevel):
    """Diálogo modal con el formulario de conexión."""

    def __init__(self, master, cfg, on_saved):
        super().__init__(master)
        self.title("Conexión con los servicios")
        self.geometry("660x690")
        self.resizable(False, True)
        self.on_saved = on_saved
        self.transient(master.winfo_toplevel())
        self.after(80, self._focus)

        ctk.CTkLabel(self, text="Conexión con los servicios", font=font("title_large"),
                     text_color=ON_SURFACE).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(self, text="Mismas direcciones y puertos que usa el cliente móvil.",
                     text_color=ON_SURFACE_VARIANT).pack(anchor="w", padx=24)
        self.form = ConexionForm(self, cfg)
        self.form.pack(fill="both", expand=True, padx=24, pady=12)
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24, pady=(0, 20))
        primary_button(bar, "Guardar", self._save, width=120).pack(side="right")
        ghost_button(bar, "Cancelar", self.destroy, width=120).pack(side="right", padx=8)

    def _focus(self):
        self.lift()
        self.focus_force()
        try:
            self.grab_set()
        except Exception:
            pass

    def _save(self):
        self.form.aplicar()
        self.on_saved()
        self.destroy()
