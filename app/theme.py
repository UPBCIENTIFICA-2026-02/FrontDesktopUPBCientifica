# -*- coding: utf-8 -*-
"""Constantes de interfaz: nombre de la app y paleta.

La paleta es la MISMA que usa el cliente móvil: la app Android envuelve todo en
`MaterialTheme { ... }` sin esquema propio, así que hereda el esquema base de
Material Design 3 (primario morado #6750A4). Aquí se replican esos tokens con
sus nombres de Material 3 para que ambos clientes se vean como la misma app.

Cada color es una tupla (claro, oscuro): CustomTkinter elige el valor según el
modo de apariencia activo, así el modo oscuro usa el esquema oscuro de M3.
"""

from pathlib import Path

import customtkinter as ctk

APP_NAME = "UPB-CIENTÍFICA — Cliente de Escritorio"

# --- Tokens de color Material 3 (esquema base, claro / oscuro) --------------
PRIMARY = ("#6750A4", "#D0BCFF")
ON_PRIMARY = ("#FFFFFF", "#381E72")
PRIMARY_HOVER = ("#7965AF", "#BCA8F0")
PRIMARY_CONTAINER = ("#EADDFF", "#4F378B")
ON_PRIMARY_CONTAINER = ("#21005D", "#EADDFF")
SECONDARY_CONTAINER = ("#E8DEF8", "#4A4458")
SECONDARY_CONTAINER_HOVER = ("#D9CDEC", "#5A536A")
ON_SECONDARY_CONTAINER = ("#1D192B", "#E8DEF8")
TERTIARY_CONTAINER = ("#FFD8E4", "#633B48")
ON_TERTIARY_CONTAINER = ("#31111D", "#FFD8E4")

BACKGROUND = ("#FFFBFE", "#1C1B1F")
SURFACE = ("#FFFBFE", "#1C1B1F")
SURFACE_CONTAINER_LOW = ("#F7F2FA", "#1D1B20")      # ElevatedCard
SURFACE_CONTAINER = ("#F3EDF7", "#211F26")          # barras / navegación
SURFACE_CONTAINER_HIGH = ("#ECE6F0", "#2B2930")     # hover sobre tarjetas
ON_SURFACE = ("#1C1B1F", "#E6E1E5")
ON_SURFACE_VARIANT = ("#49454F", "#CAC4D0")
OUTLINE = ("#79747E", "#938F99")
OUTLINE_VARIANT = ("#CAC4D0", "#49454F")             # HorizontalDivider

ERROR = ("#B3261E", "#F2B8B5")
ERROR_CONTAINER = ("#F9DEDC", "#8C1D18")
ON_ERROR_CONTAINER = ("#410E0B", "#F9DEDC")
SUCCESS = ("#1B6C3A", "#8BD6A0")
SUCCESS_CONTAINER = ("#D3F5DC", "#0F5226")
WARNING = ("#7A5900", "#F2C14E")
WARNING_CONTAINER = ("#FFEFC7", "#5B4300")

# --- Alias de compatibilidad con los nombres antiguos del proyecto ---------
MAGENTA = PRIMARY
MAGENTA_DARK = PRIMARY_HOVER
PURPLE = PRIMARY
GRAY_BG = SURFACE_CONTAINER
CARD = SURFACE_CONTAINER_LOW
TEXT = ON_SURFACE
MUTED = ON_SURFACE_VARIANT
GREEN = SUCCESS
AMBER = WARNING
BORDER = OUTLINE_VARIANT

THEME_FILE = Path(__file__).parent / "assets" / "upb_material3.json"


def apply_theme(appearance="light"):
    """Activa el tema Material 3 en todos los widgets de CustomTkinter."""
    ctk.set_appearance_mode(appearance)
    ctk.set_default_color_theme(str(THEME_FILE))


# Escala tipográfica (Material 3, adaptada a escritorio)
def font(role="body"):
    sizes = {
        "headline_medium": (28, "normal"),
        "headline_small": (24, "normal"),
        "title_large": (22, "normal"),
        "title_medium": (16, "bold"),
        "title_small": (14, "bold"),
        "body_large": (16, "normal"),
        "body": (14, "normal"),
        "body_small": (12, "normal"),
        "label_large": (14, "bold"),
        "label_small": (11, "bold"),
    }
    size, weight = sizes.get(role, (14, "normal"))
    return ctk.CTkFont(size=size, weight=weight)
