# -*- coding: utf-8 -*-
"""Componentes de interfaz reutilizables, equivalentes a los de Material 3 que
usa el cliente móvil (ElevatedCard, ListItem, HorizontalDivider, Button,
OutlinedButton, TextButton, CircularProgressIndicator...)."""

import tkinter as tk

import customtkinter as ctk
from customtkinter.windows.widgets.appearance_mode import AppearanceModeTracker

from .theme import (
    PRIMARY, ON_PRIMARY, PRIMARY_HOVER, SECONDARY_CONTAINER, SECONDARY_CONTAINER_HOVER,
    ON_SECONDARY_CONTAINER, SURFACE_CONTAINER_LOW, SURFACE_CONTAINER_HIGH, ON_SURFACE,
    ON_SURFACE_VARIANT, OUTLINE, OUTLINE_VARIANT, ERROR, ERROR_CONTAINER, ON_ERROR_CONTAINER,
    SUCCESS, SUCCESS_CONTAINER, WARNING, WARNING_CONTAINER, PRIMARY_CONTAINER,
    ON_PRIMARY_CONTAINER, font,
)


def section_title(master, text, subtitle=None):
    box = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(box, text=text, font=font("headline_small"), text_color=ON_SURFACE).pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(box, text=subtitle, font=font("body"), text_color=ON_SURFACE_VARIANT,
                     justify="left", wraplength=760).pack(anchor="w", pady=(2, 0))
    return box


# --- Botones (Material 3) ---------------------------------------------------
def primary_button(master, text, command, width=150, height=40):
    """Button (filled)."""
    return ctk.CTkButton(master, text=text, command=command, width=width, height=height,
                         corner_radius=20, fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
                         text_color=ON_PRIMARY, font=font("label_large"))


def tonal_button(master, text, command, width=150, height=40):
    """FilledTonalButton."""
    return ctk.CTkButton(master, text=text, command=command, width=width, height=height,
                         corner_radius=20, fg_color=SECONDARY_CONTAINER,
                         hover_color=SECONDARY_CONTAINER_HOVER,
                         text_color=ON_SECONDARY_CONTAINER, font=font("label_large"))


def ghost_button(master, text, command, width=150, height=40):
    """OutlinedButton."""
    return ctk.CTkButton(master, text=text, command=command, width=width, height=height,
                         corner_radius=20, fg_color="transparent", hover_color=SURFACE_CONTAINER_HIGH,
                         text_color=PRIMARY, border_color=OUTLINE, border_width=1,
                         font=font("label_large"))


outlined_button = ghost_button


def text_button(master, text, command, width=100, height=36, color=PRIMARY):
    """TextButton."""
    return ctk.CTkButton(master, text=text, command=command, width=width, height=height,
                         corner_radius=20, fg_color="transparent", hover_color=SURFACE_CONTAINER_HIGH,
                         text_color=color, font=font("label_large"))


# --- Superficies ------------------------------------------------------------
def card(master, **kw):
    """ElevatedCard: superficie tonal con esquinas de 12 px."""
    return ctk.CTkFrame(master, fg_color=SURFACE_CONTAINER_LOW, corner_radius=12,
                        border_width=1, border_color=OUTLINE_VARIANT, **kw)


class Divider(tk.Frame):
    """HorizontalDivider de 1 px. Un CTkFrame de 1 px no llega a dibujarse, así
    que se usa un Frame de Tk que sigue el modo claro/oscuro."""

    def __init__(self, master, color=OUTLINE_VARIANT):
        self._color = color
        super().__init__(master, height=1, bd=0, highlightthickness=0,
                         bg=self._pick(AppearanceModeTracker.get_mode()))
        AppearanceModeTracker.add(self._on_mode, self)

    def _pick(self, mode):
        return self._color[1] if mode == 1 else self._color[0]

    def _on_mode(self, mode_string):
        try:
            self.configure(bg=self._pick(1 if str(mode_string).lower() == "dark" else 0))
        except tk.TclError:
            pass

    def destroy(self):
        AppearanceModeTracker.remove(self._on_mode)
        super().destroy()


def divider(master):
    """HorizontalDivider."""
    return Divider(master)


def chip(master, text, kind="info"):
    """Etiqueta de estado (AssistChip)."""
    colors = {
        "info": (PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER),
        "ok": (SUCCESS_CONTAINER, SUCCESS),
        "warn": (WARNING_CONTAINER, WARNING),
        "error": (ERROR_CONTAINER, ON_ERROR_CONTAINER),
        "neutral": (SECONDARY_CONTAINER, ON_SECONDARY_CONTAINER),
    }
    bg, fg = colors.get(kind, colors["info"])
    return ctk.CTkLabel(master, text=f"  {text}  ", fg_color=bg, text_color=fg,
                        corner_radius=8, height=26, font=font("label_small"))


def banner(master, title, text, kind="warn"):
    """Aviso destacado (estado de un servicio pendiente, etc.)."""
    colors = {
        "warn": (WARNING_CONTAINER, WARNING),
        "info": (PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER),
        "error": (ERROR_CONTAINER, ON_ERROR_CONTAINER),
    }
    bg, fg = colors.get(kind, colors["warn"])
    box = ctk.CTkFrame(master, fg_color=bg, corner_radius=12)
    ctk.CTkLabel(box, text=title, text_color=fg, font=font("title_small"),
                 anchor="w").pack(anchor="w", padx=16, pady=(12, 0))
    ctk.CTkLabel(box, text=text, text_color=fg, font=font("body"), justify="left",
                 anchor="w", wraplength=820).pack(anchor="w", padx=16, pady=(2, 12))
    return box


def list_item(master, icon, headline, supporting=None):
    """ListItem de Material 3: icono a la izquierda, título y texto de apoyo.

    Devuelve (fila, contenedor_derecho) para que quien lo use añada acciones
    al final de la fila (trailingContent).
    """
    row = ctk.CTkFrame(master, fg_color="transparent", corner_radius=0)
    row.pack(fill="x", padx=4)
    ctk.CTkLabel(row, text=icon, width=40, font=ctk.CTkFont(size=20)).pack(side="left", padx=(12, 4), pady=10)
    texts = ctk.CTkFrame(row, fg_color="transparent")
    texts.pack(side="left", fill="x", expand=True, pady=8)
    ctk.CTkLabel(texts, text=headline, text_color=ON_SURFACE, font=font("body_large"),
                 anchor="w").pack(anchor="w", fill="x")
    if supporting:
        ctk.CTkLabel(texts, text=supporting, text_color=ON_SURFACE_VARIANT, font=font("body"),
                     anchor="w").pack(anchor="w", fill="x")
    trailing = ctk.CTkFrame(row, fg_color="transparent")
    trailing.pack(side="right", padx=8)
    divider(master).pack(fill="x", padx=4)
    return row, trailing


class StatePanel(ctk.CTkScrollableFrame):
    """Lista que pinta los cuatro estados del `UiState` del móvil:
    Idle (vacío), Loading (indicador de progreso), Error (texto en rojo) y
    Success (lo dibuja quien lo usa tras llamar a `clear()`)."""

    def __init__(self, master, **kw):
        kw.setdefault("fg_color", SURFACE_CONTAINER_LOW)
        kw.setdefault("corner_radius", 12)
        super().__init__(master, **kw)

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def loading(self, text="Cargando…"):
        self.clear()
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.pack(pady=40)
        bar = ctk.CTkProgressBar(box, mode="indeterminate", width=220)
        bar.pack()
        bar.start()
        ctk.CTkLabel(box, text=text, text_color=ON_SURFACE_VARIANT).pack(pady=(10, 0))

    def error(self, message, retry=None):
        self.clear()
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.pack(pady=30, padx=20)
        ctk.CTkLabel(box, text=message, text_color=ERROR, wraplength=640,
                     justify="center", font=font("body")).pack()
        if retry:
            ghost_button(box, "Reintentar", retry, width=130).pack(pady=(12, 0))

    def empty(self, message):
        self.clear()
        ctk.CTkLabel(self, text=message, text_color=ON_SURFACE_VARIANT).pack(pady=30)
