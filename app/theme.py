# -*- coding: utf-8 -*-
"""Constantes de interfaz: nombre de la app, paleta, tipografía y formas.

La paleta es la MISMA que define el cliente móvil en ui/theme/Theme.kt
(UpbCientificaTheme): primario azul, secundario turquesa, terciario violeta y
neutros fríos, con su esquema claro y oscuro. Si allí se cambia la identidad
visual, basta con copiar aquí los valores.

Cada color es una tupla (claro, oscuro): CustomTkinter elige el valor según el
modo de apariencia activo.
"""

from pathlib import Path

import customtkinter as ctk

APP_NAME = "UPB-CIENTÍFICA — Cliente de Escritorio"

# --- Esquema de color (Theme.kt: ColoresClaros / ColoresOscuros) -----------
PRIMARY = ("#1A5BC0", "#AFC6FF")
ON_PRIMARY = ("#FFFFFF", "#002E69")
PRIMARY_HOVER = ("#2F6BCB", "#C3D4FF")
PRIMARY_CONTAINER = ("#D9E2FF", "#004494")
ON_PRIMARY_CONTAINER = ("#001A41", "#D9E2FF")

SECONDARY = ("#006970", "#4FD8E3")
SECONDARY_CONTAINER = ("#9AF0F9", "#004F54")
SECONDARY_CONTAINER_HOVER = ("#88E4EE", "#0B5F65")
ON_SECONDARY_CONTAINER = ("#002022", "#9AF0F9")

TERTIARY = ("#7A4E9C", "#E0B6FF")
TERTIARY_CONTAINER = ("#F2DAFF", "#603681")
ON_TERTIARY_CONTAINER = ("#2F004C", "#F2DAFF")

INVERSE_SURFACE = ("#2E3036", "#E1E2E9")
INVERSE_ON_SURFACE = ("#EFF0F7", "#2E3036")

BACKGROUND = ("#F9F9FF", "#111318")
SURFACE = ("#F9F9FF", "#111318")
SURFACE_VARIANT = ("#E0E2EC", "#44474F")
SURFACE_CONTAINER_LOWEST = ("#FFFFFF", "#0C0E13")
SURFACE_CONTAINER_LOW = ("#F2F3FA", "#191C21")
SURFACE_CONTAINER = ("#EDEDF4", "#1D2025")
SURFACE_CONTAINER_HIGH = ("#E7E8EE", "#272A2F")
SURFACE_CONTAINER_HIGHEST = ("#E1E2E9", "#32353A")
ON_SURFACE = ("#191C21", "#E1E2E9")
ON_SURFACE_VARIANT = ("#44474F", "#C4C6D0")
OUTLINE = ("#74777F", "#8E9099")
OUTLINE_VARIANT = ("#C4C6D0", "#44474F")

ERROR = ("#BA1A1A", "#FFB4AB")
ERROR_CONTAINER = ("#FFDAD6", "#93000A")
ON_ERROR_CONTAINER = ("#410002", "#FFDAD6")

# Theme.kt: ColorScheme.exito (Material 3 no trae rol "success").
EXITO = ("#188038", "#81C995")
SUCCESS = EXITO
SUCCESS_CONTAINER = ("#D4EFDA", "#1E3A26")
WARNING = ("#7A5900", "#F2C14E")
WARNING_CONTAINER = ("#FFEFC7", "#4A3800")

# --- Alias de compatibilidad con los nombres antiguos del proyecto ---------
MAGENTA = PRIMARY
MAGENTA_DARK = PRIMARY_HOVER
PURPLE = PRIMARY
GRAY_BG = SURFACE_CONTAINER
CARD = SURFACE_CONTAINER_LOW
TEXT = ON_SURFACE
MUTED = ON_SURFACE_VARIANT
GREEN = EXITO
AMBER = WARNING
BORDER = OUTLINE_VARIANT

# --- Formas (Theme.kt: Formas) ---------------------------------------------
RADIUS_XS = 6
RADIUS_S = 10
RADIUS_M = 16
RADIUS_L = 24

THEME_FILE = Path(__file__).parent / "assets" / "upb_material3.json"


def apply_theme(appearance="light"):
    """Activa el tema en todos los widgets de CustomTkinter."""
    ctk.set_appearance_mode(appearance)
    ctk.set_default_color_theme(str(THEME_FILE))


def is_dark():
    return ctk.get_appearance_mode().lower() == "dark"


def resolve(color):
    """Tupla (claro, oscuro) -> el hex del modo activo (para widgets de Tk)."""
    if isinstance(color, (tuple, list)):
        return color[1] if is_dark() else color[0]
    return color


def _mix(c1, c2, a):
    """Mezcla c1 sobre c2 con opacidad a (0..1)."""
    c1, c2 = c1.lstrip("#"), c2.lstrip("#")
    r = [round(int(c1[i:i + 2], 16) * a + int(c2[i:i + 2], 16) * (1 - a)) for i in (0, 2, 4)]
    return "#{:02X}{:02X}{:02X}".format(*r)


def tint(color, alpha=0.14, over=SURFACE):
    """Color translúcido "pintado" sobre una superficie, como `color.copy(alpha)`.
    Acepta hex o tuplas y devuelve una tupla (claro, oscuro)."""
    c = color if isinstance(color, (tuple, list)) else (color, color)
    o = over if isinstance(over, (tuple, list)) else (over, over)
    return (_mix(c[0], o[0], alpha), _mix(c[1], o[1], alpha))


# --- Tipografía (Material 3; en el móvil los títulos van en SemiBold) -------
def font(role="body"):
    sizes = {
        "headline_medium": (28, "bold"),
        "headline_small": (24, "bold"),
        "title_large": (22, "bold"),
        "title_medium": (16, "bold"),
        "title_small": (14, "bold"),
        "body_large": (16, "normal"),
        "body": (14, "normal"),
        "body_small": (12, "normal"),
        "label_large": (14, "bold"),
        "label_medium": (12, "bold"),
        "label_small": (11, "bold"),
        "section": (12, "bold"),
    }
    size, weight = sizes.get(role, (14, "normal"))
    return ctk.CTkFont(size=size, weight=weight)


# --- Iconos ------------------------------------------------------------------
# Los emoji (📁 🖼 👥…) con "Segoe UI Symbol" salen monocromos y deformes. En
# Windows 10/11 hay una fuente de iconos de verdad: Segoe Fluent Icons (11) o
# Segoe MDL2 Assets (10). El código sigue escribiendo el emoji (se lee mejor) y
# `glifo()` lo cambia por el icono equivalente. En Linux, o si no hay ninguna
# de las dos fuentes, se deja el emoji como estaba.
_FUENTES_ICONOS = [("Segoe Fluent Icons", "SegoeIcons.ttf"), ("Segoe MDL2 Assets", "segmdl2.ttf")]
_ICONOS = {
    "⌂": 0xE80F, "📁": 0xE8B7, "📂": 0xE838, "👥": 0xE716, "▶": 0xE768, "▣": 0xE950,
    "↻": 0xE895, "🖼": 0xEB9F, "⚙": 0xE713, "ⓘ": 0xE946, "☁": 0xE753, "👤": 0xE77B,
    "🔒": 0xE72E, "⚠": 0xE7BA, "👁": 0xE890, "🙈": 0xED1A, "🔍": 0xE721, "🔎": 0xE721,
    "✕": 0xE711, "🗑": 0xE74D, "📕": 0xEA90, "▦": 0xE80A, "📄": 0xE8A5, "📊": 0xE786,
    "🎬": 0xE714, "♪": 0xE8D6, "📦": 0xF012, "</>": 0xE943, "{ }": 0xE9D2, "📃": 0xE7C3,
    "⌛": 0xE823, "✓": 0xE73E, "⊘": 0xE733, "↪": 0xF3B1, "⋮": 0xE712, "☰": 0xE8FD,
    "＋": 0xE710, "+": 0xE710, "−": 0xE738, "↑": 0xE898, "⬇": 0xE896,
    "☀": 0xE706, "☾": 0xE708,
}
_familia_iconos = None      # se detecta en el primer uso (hace falta la ventana Tk)


def _familia():
    global _familia_iconos
    if _familia_iconos is None:
        import tkinter.font as tkfont
        try:
            disponibles = set(tkfont.families())
        except Exception:       # todavía no hay ventana: se reintenta luego
            return None
        _familia_iconos = next((f for f, _ in _FUENTES_ICONOS if f in disponibles), "")
    return _familia_iconos or None


def glifo(texto):
    """Emoji -> icono de la fuente de iconos de Windows (si la hay)."""
    if texto in _ICONOS and _familia():
        return chr(_ICONOS[texto])
    return texto


def icon_font(size=16):
    """Fuente de los iconos: Segoe Fluent Icons / MDL2 si existen; si no, Segoe UI Symbol."""
    return ctk.CTkFont(family=_familia() or "Segoe UI Symbol", size=size)


def imagen_avatar(inicial, color, tamano):
    """Círculo con la inicial, dibujado con PIL a 4x y reducido: bordes suaves y
    la letra centrada de verdad a cualquier tamaño (con un CTkFrame redondo y
    una etiqueta encima, a 18 px la letra salía diminuta y descentrada)."""
    from PIL import Image, ImageDraw, ImageFont
    f = 4
    lado = tamano * f
    fuente = None
    for archivo in ("C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            fuente = ImageFont.truetype(archivo, int(lado * 0.52))
            break
        except OSError:
            continue
    if fuente is None:
        return None
    img = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, lado - 1, lado - 1), fill=color)
    d.text((lado / 2, lado / 2), inicial, font=fuente, fill="#FFFFFF", anchor="mm")
    img = img.resize((tamano * 2, tamano * 2), Image.LANCZOS)   # 2x: nítido en pantallas con escala
    return ctk.CTkImage(light_image=img, dark_image=img, size=(tamano, tamano))


def imagen_icono(texto, tamano=20, color=("#44474F", "#C4C6D0")):
    """El icono como imagen (CTkImage), para ponerlo junto a texto en un botón:
    un botón tiene una sola fuente, y el texto no puede ir en la de iconos.
    Devuelve None si no hay fuente de iconos (el llamador deja el emoji)."""
    familia = _familia()
    if not familia or texto not in _ICONOS:
        return None
    from PIL import Image, ImageDraw, ImageFont
    archivo = dict(_FUENTES_ICONOS)[familia]
    try:
        fuente = ImageFont.truetype(str(Path("C:/Windows/Fonts") / archivo), int(tamano * 2))
    except OSError:
        return None

    def dibujar(c):
        img = Image.new("RGBA", (tamano * 2, tamano * 2), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((tamano, tamano), chr(_ICONOS[texto]), font=fuente, fill=c, anchor="mm")
        return img

    claro, oscuro = color if isinstance(color, tuple) else (color, color)
    return ctk.CTkImage(light_image=dibujar(claro), dark_image=dibujar(oscuro), size=(tamano, tamano))


def mono(size=12):
    return ctk.CTkFont(family="Consolas", size=size)
