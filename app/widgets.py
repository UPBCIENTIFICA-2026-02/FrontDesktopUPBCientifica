# -*- coding: utf-8 -*-
"""Componentes de interfaz reutilizables (tarjetas, botones, títulos)."""

import customtkinter as ctk

from .theme import MAGENTA, MAGENTA_DARK, GRAY_BG, CARD, TEXT, MUTED, BORDER


def section_title(master, text, subtitle=None):
    box = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(box, text=text, font=ctk.CTkFont(size=22, weight="bold"),
                 text_color=TEXT).pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(box, text=subtitle, font=ctk.CTkFont(size=13),
                     text_color=MUTED).pack(anchor="w", pady=(2, 0))
    return box


def primary_button(master, text, command, width=150):
    return ctk.CTkButton(master, text=text, command=command, width=width,
                         fg_color=MAGENTA, hover_color=MAGENTA_DARK,
                         font=ctk.CTkFont(size=13, weight="bold"))


def ghost_button(master, text, command, width=150):
    return ctk.CTkButton(master, text=text, command=command, width=width,
                         fg_color="transparent", hover_color=GRAY_BG,
                         text_color=MAGENTA, border_color=MAGENTA, border_width=1,
                         font=ctk.CTkFont(size=13))


def card(master):
    return ctk.CTkFrame(master, fg_color=CARD, corner_radius=12,
                        border_width=1, border_color=BORDER)
