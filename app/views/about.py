# -*- coding: utf-8 -*-
"""Vista Acerca de."""

import customtkinter as ctk

from ..theme import TEXT
from ..widgets import section_title, card


class AboutView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        section_title(self, "Acerca de", "Cliente de escritorio del proyecto UPB-CIENTÍFICA").pack(anchor="w", pady=(0, 16))
        c = card(self)
        c.pack(fill="both", expand=True)
        txt = (
            "UPB-CIENTÍFICA — Cliente de Escritorio (Windows / Linux)\n"
            "Sistemas Distribuidos 2026-20 · Ingeniería de Sistemas e Informática · UPB Bucaramanga\n\n"
            "Este cliente corresponde al consumidor 'Desktop Windows/Linux' de la Figura 1 del proyecto.\n"
            "Tecnología: Python + CustomTkinter (el PDF no fija lenguaje para el cliente de escritorio).\n\n"
            "Estado actual: interfaz gráfica y funcionalidades locales (álbum, archivos, video, configuración,\n"
            "formulario de trabajos). La comunicación con el backend (SOAP/RMI/gRPC/HTTP, LDAP+MFA, MPI, NFS)\n"
            "está encapsulada en la clase ApiClient como stub y se conectará en las siguientes fases.\n\n"
            "Módulos previstos que se activarán con el backend:\n"
            "  •  Autenticación real contra LDAP + segundo factor (TOTP)\n"
            "  •  Envío de trabajos por RMI hacia SLURM/MPI en el clúster\n"
            "  •  File Sync por gRPC y Shared Files sobre NFS con cuota y permisos Unix\n"
            "  •  Photo Album y Streaming (HLS) servidos desde el Home del usuario\n"
        )
        ctk.CTkLabel(c, text=txt, justify="left", text_color=TEXT,
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=20)
