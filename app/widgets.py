# -*- coding: utf-8 -*-
"""Componentes de interfaz reutilizables. Son los equivalentes de escritorio de
ui/components del móvil: Avatar, BarraBusqueda, EncabezadoSeccion, EstadoVacio,
EstadoError, EsqueletoLista, IconoTipoArchivo, HojaDetalles, más los básicos de
Material 3 (Card, ListItem, Divider, botones, chips)."""

import time
import tkinter as tk
import zlib
from dataclasses import dataclass

import customtkinter as ctk
from customtkinter.windows.widgets.appearance_mode import AppearanceModeTracker

from .theme import (
    PRIMARY, ON_PRIMARY, PRIMARY_HOVER, PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER,
    SECONDARY_CONTAINER, SECONDARY_CONTAINER_HOVER, ON_SECONDARY_CONTAINER,
    SURFACE, SURFACE_CONTAINER_LOW, SURFACE_CONTAINER_HIGH, SURFACE_CONTAINER_HIGHEST,
    ON_SURFACE, ON_SURFACE_VARIANT, OUTLINE, OUTLINE_VARIANT, ERROR_CONTAINER,
    ON_ERROR_CONTAINER, SUCCESS_CONTAINER, EXITO, WARNING, WARNING_CONTAINER,
    RADIUS_S, RADIUS_M, RADIUS_L, font, icon_font, tint,
)


# =============================================================================
# Formato (ui/components/TipoArchivo.kt)
# =============================================================================
def formatear_tamano(nbytes):
    """1536 -> "1.5 KB". Sin decimales para B y KB."""
    valor = float(nbytes or 0)
    unidades = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while valor >= 1024 and i < len(unidades) - 1:
        valor /= 1024
        i += 1
    return f"{valor:.0f} {unidades[i]}" if i <= 1 else f"{valor:.1f} {unidades[i]}"


def formatear_duracion(segundos):
    """3725 -> "1:02:05"; 95 -> "1:35". Formato de reproductor de video."""
    segundos = int(segundos or 0)
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def formatear_hace(instante, ahora=None):
    """Marca de tiempo (s) -> "hace un momento", "hace 5 min", "hace 2 h"..."""
    seg = max(0, int((ahora or time.time()) - instante))
    if seg < 60:
        return "hace un momento"
    if seg < 3600:
        return f"hace {seg // 60} min"
    if seg < 86400:
        return f"hace {seg // 3600} h"
    dias = seg // 86400
    return "hace 1 día" if dias == 1 else f"hace {dias} días"


def formatear_minutos(minutos):
    """90 -> "1 h 30 min"; 45 -> "45 min"."""
    h, m = divmod(int(minutos), 60)
    if h == 0:
        return f"{m} min"
    return f"{h} h" if m == 0 else f"{h} h {m} min"


# =============================================================================
# Tipo de archivo: icono y color por extensión (como en Drive)
# =============================================================================
@dataclass(frozen=True)
class TipoArchivo:
    etiqueta: str
    icono: str
    color: str


CARPETA = TipoArchivo("Carpeta", "📁", "#5F6B7A")
_PDF = TipoArchivo("PDF", "📕", "#D93025")
_HOJA = TipoArchivo("Hoja de cálculo", "▦", "#188038")
_DOC = TipoArchivo("Documento", "📄", "#1A73E8")
_PRES = TipoArchivo("Presentación", "📊", "#E37400")
_IMG = TipoArchivo("Imagen", "🖼", "#C5221F")
_VID = TipoArchivo("Video", "🎬", "#D93025")
_AUD = TipoArchivo("Audio", "♪", "#9334E6")
_ZIP = TipoArchivo("Comprimido", "📦", "#795548")
_COD = TipoArchivo("Código", "</>", "#007B83")
_DAT = TipoArchivo("Datos", "{ }", "#007B83")
_GEN = TipoArchivo("Archivo", "📃", "#5F6368")

_EXT = {}
for _tipo, _exts in [
    (_PDF, "pdf"), (_HOJA, "csv tsv xls xlsx ods"), (_DOC, "doc docx odt txt md rtf tex"),
    (_PRES, "ppt pptx odp"), (_IMG, "png jpg jpeg gif webp svg bmp tif tiff"),
    (_VID, "mp4 mkv mov avi webm"), (_AUD, "mp3 wav flac ogg m4a"),
    (_ZIP, "zip rar 7z tar gz tgz bz2"),
    (_COD, "py java kt c cpp h js ts r m sh ipynb"),
    (_DAT, "json xml yaml yml h5 hdf5 nc parquet mat npy"),
]:
    for _e in _exts.split():
        _EXT[_e] = _tipo


def tipo_archivo(nombre, es_carpeta=False):
    if es_carpeta:
        return CARPETA
    ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    return _EXT.get(ext, _GEN)


def icono_tipo(master, tipo, tamano=40, over=SURFACE):
    """Icono del tipo sobre un cuadrado redondeado con su color muy tenue."""
    f = ctk.CTkFrame(master, width=tamano, height=tamano, corner_radius=RADIUS_S,
                     fg_color=tint(tipo.color, 0.14, over))
    f.pack_propagate(False)
    f.grid_propagate(False)
    ctk.CTkLabel(f, text=tipo.icono, text_color=tipo.color, fg_color="transparent",
                 font=icon_font(max(11, int(tamano * 0.42)))).place(relx=0.5, rely=0.5, anchor="center")
    return f


def circle(master, texto, tamano, fondo, color, size=None, bold=False):
    """Círculo de verdad con un glifo centrado (un CTkLabel redondo se ensancha)."""
    f = ctk.CTkFrame(master, width=tamano, height=tamano, corner_radius=tamano // 2, fg_color=fondo)
    f.pack_propagate(False)
    f.grid_propagate(False)
    fuente = (ctk.CTkFont(size=size or int(tamano * 0.42), weight="bold") if bold
              else icon_font(size or int(tamano * 0.45)))
    f.label = ctk.CTkLabel(f, text=texto, text_color=color, fg_color="transparent", font=fuente)
    f.label.place(relx=0.5, rely=0.5, anchor="center")
    return f


# =============================================================================
# Avatar
# =============================================================================
_COLORES_AVATAR = ["#1A73E8", "#188038", "#D93025", "#E37400",
                   "#9334E6", "#007B83", "#C5221F", "#5F6368"]


def avatar(master, texto, tamano=36):
    """Círculo con la inicial. El color depende del texto (estable entre ejecuciones)."""
    inicial = (texto or "?").strip()[:1].upper() or "?"
    color = _COLORES_AVATAR[zlib.crc32((texto or "").lower().encode()) % len(_COLORES_AVATAR)]
    return circle(master, inicial, tamano, color, "#FFFFFF", bold=True)


# =============================================================================
# Títulos y textos
# =============================================================================
def section_title(master, text, subtitle=None):
    box = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(box, text=text, font=font("title_large"), text_color=ON_SURFACE).pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(box, text=subtitle, font=font("body"), text_color=ON_SURFACE_VARIANT,
                     justify="left", wraplength=760).pack(anchor="w", pady=(2, 0))
    return box


def section_header(master, texto):
    """Encabezado de sección en mayúsculas pequeñas ("CARPETAS", "ARCHIVOS")."""
    return ctk.CTkLabel(master, text=texto.upper(), font=font("section"),
                        text_color=ON_SURFACE_VARIANT, anchor="w")


# =============================================================================
# Botones (Material 3)
# =============================================================================
def primary_button(master, text, command, width=150, height=40):
    """Button (filled)."""
    return ctk.CTkButton(master, text=text, command=command, width=width, height=height,
                         corner_radius=height // 2, fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
                         text_color=ON_PRIMARY, font=font("label_large"))


def tonal_button(master, text, command, width=150, height=40):
    """FilledTonalButton."""
    return ctk.CTkButton(master, text=text, command=command, width=width, height=height,
                         corner_radius=height // 2, fg_color=SECONDARY_CONTAINER,
                         hover_color=SECONDARY_CONTAINER_HOVER,
                         text_color=ON_SECONDARY_CONTAINER, font=font("label_large"))


def ghost_button(master, text, command, width=150, height=40):
    """OutlinedButton."""
    return ctk.CTkButton(master, text=text, command=command, width=width, height=height,
                         corner_radius=height // 2, fg_color="transparent",
                         hover_color=SURFACE_CONTAINER_HIGH, text_color=PRIMARY,
                         border_color=OUTLINE, border_width=1, font=font("label_large"))


outlined_button = ghost_button


def text_button(master, text, command, width=100, height=36, color=PRIMARY):
    """TextButton."""
    return ctk.CTkButton(master, text=text, command=command, width=width, height=height,
                         corner_radius=height // 2, fg_color="transparent",
                         hover_color=SURFACE_CONTAINER_HIGH, text_color=color,
                         font=font("label_large"))


def icon_button(master, glyph, command, size=40, color=ON_SURFACE_VARIANT, tooltip=None):
    """IconButton: glifo dentro de un círculo que solo se ve al pasar el ratón."""
    return ctk.CTkButton(master, text=glyph, command=command, width=size, height=size,
                         corner_radius=size // 2, fg_color="transparent",
                         hover_color=SURFACE_CONTAINER_HIGH, text_color=color,
                         font=icon_font(int(size * 0.42)))


def filter_chip(master, text, selected, command):
    """FilterChip: relleno tonal si está seleccionado, contorno si no."""
    return ctk.CTkButton(
        master, text=("✓  " if selected else "") + text, command=command, height=32,
        width=10, corner_radius=8, border_width=0 if selected else 1, border_color=OUTLINE_VARIANT,
        fg_color=SECONDARY_CONTAINER if selected else "transparent",
        hover_color=SECONDARY_CONTAINER_HOVER if selected else SURFACE_CONTAINER_HIGH,
        text_color=ON_SECONDARY_CONTAINER if selected else ON_SURFACE_VARIANT,
        font=font("label_large"))


# =============================================================================
# Superficies
# =============================================================================
def card(master, **kw):
    """ElevatedCard (surfaceContainerLow)."""
    kw.setdefault("corner_radius", RADIUS_L)
    return ctk.CTkFrame(master, fg_color=SURFACE_CONTAINER_LOW, **kw)


def outlined_card(master, **kw):
    """OutlinedCard."""
    kw.setdefault("corner_radius", RADIUS_M)
    return ctk.CTkFrame(master, fg_color=SURFACE, border_width=1, border_color=OUTLINE_VARIANT, **kw)


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
    return Divider(master)


def chip(master, text, kind="info"):
    """Etiqueta de estado."""
    colors = {
        "info": (PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER),
        "ok": (SUCCESS_CONTAINER, EXITO),
        "warn": (WARNING_CONTAINER, WARNING),
        "error": (ERROR_CONTAINER, ON_ERROR_CONTAINER),
        "neutral": (SECONDARY_CONTAINER, ON_SECONDARY_CONTAINER),
    }
    bg, fg = colors.get(kind, colors["info"])
    return ctk.CTkLabel(master, text=f"  {text}  ", fg_color=bg, text_color=fg,
                        corner_radius=8, height=26, font=font("label_small"))


def pill(master, text, color, over=SURFACE):
    """Etiqueta redondeada con el color del estado muy tenue de fondo."""
    return ctk.CTkLabel(master, text=f"  {text}  ", fg_color=tint(color, 0.14, over),
                        text_color=color, corner_radius=12, height=24, font=font("label_small"))


def banner(master, title, text, kind="warn"):
    """Aviso destacado (estado de un servicio pendiente, etc.)."""
    colors = {
        "warn": (WARNING_CONTAINER, WARNING),
        "info": (PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER),
        "error": (ERROR_CONTAINER, ON_ERROR_CONTAINER),
    }
    bg, fg = colors.get(kind, colors["warn"])
    box = ctk.CTkFrame(master, fg_color=bg, corner_radius=RADIUS_M)
    ctk.CTkLabel(box, text=title, text_color=fg, font=font("title_small"),
                 anchor="w").pack(anchor="w", padx=16, pady=(12, 0))
    ctk.CTkLabel(box, text=text, text_color=fg, font=font("body"), justify="left",
                 anchor="w", wraplength=820).pack(anchor="w", padx=16, pady=(2, 12))
    return box


def bind_click(widget, callback, hover=None):
    """Hace clicable un frame y todos sus hijos (como `Modifier.clickable`)."""
    widgets = [widget]
    stack = list(widget.winfo_children())
    while stack:
        w = stack.pop()
        widgets.append(w)
        stack.extend(w.winfo_children())
    normal = widget.cget("fg_color") if hover else None

    for w in widgets:
        w.bind("<Button-1>", lambda _e: callback(), add="+")
        try:
            w.configure(cursor="hand2")
        except Exception:
            pass
        if hover:
            w.bind("<Enter>", lambda _e: widget.configure(fg_color=hover), add="+")
            w.bind("<Leave>", lambda _e: widget.configure(fg_color=normal), add="+")


# =============================================================================
# Buscador en forma de píldora (BarraBusqueda)
# =============================================================================
class SearchBar(ctk.CTkFrame):
    def __init__(self, master, placeholder, on_change, height=52):
        super().__init__(master, fg_color=SURFACE_CONTAINER_HIGH, corner_radius=height // 2, height=height)
        self.on_change = on_change
        self.pack_propagate(False)
        ctk.CTkLabel(self, text="🔍", text_color=ON_SURFACE_VARIANT, width=24,
                     font=icon_font(15)).pack(side="left", padx=(18, 6))
        # Sin textvariable: con ella CustomTkinter no muestra el texto guía.
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder,
                                  border_width=0, fg_color=SURFACE_CONTAINER_HIGH,
                                  font=font("body_large"), height=height - 12)
        self.entry.pack(side="left", fill="x", expand=True)
        self.btn_clear = icon_button(self, "✕", self.clear, size=36)
        self.trailing = ctk.CTkFrame(self, fg_color="transparent", width=1, height=1)
        self.trailing.pack(side="right", padx=(0, 8))
        self._ultimo = ""
        self.entry.bind("<KeyRelease>", lambda _e: self._changed(), add="+")

    @property
    def value(self):
        return self.entry.get()

    def reset(self, placeholder=None):
        """Vacía la búsqueda sin avisar (al cambiar de carpeta)."""
        self.entry.delete(0, "end")
        self._ultimo = ""
        self.btn_clear.pack_forget()
        if placeholder:
            self.entry.configure(placeholder_text=placeholder)
        if self.focus_get() is not self.entry._entry:
            self.entry._activate_placeholder()

    def clear(self):
        self.entry.delete(0, "end")
        self.entry.focus_set()
        self._changed()

    def _changed(self):
        texto = self.entry.get()
        if texto:
            self.btn_clear.pack(side="right", before=self.trailing)
        else:
            self.btn_clear.pack_forget()
        if texto != self._ultimo:
            self._ultimo = texto
            self.on_change(texto)


# =============================================================================
# Estados de una lista (UiState): esqueleto, vacío y error
# =============================================================================
def empty_state(master, icono, titulo, mensaje, accion=None):
    """EstadoVacio: icono en círculo, título, mensaje y acción opcional."""
    box = ctk.CTkFrame(master, fg_color="transparent")
    circle(box, icono, 96, PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER, size=40).pack(pady=(0, 18))
    ctk.CTkLabel(box, text=titulo, font=font("title_large"), text_color=ON_SURFACE).pack()
    ctk.CTkLabel(box, text=mensaje, font=font("body"), text_color=ON_SURFACE_VARIANT,
                 wraplength=440, justify="center").pack(pady=(8, 0))
    if accion:
        texto, comando = accion
        tonal_button(box, texto, comando, width=140).pack(pady=(18, 0))
    return box


class Skeleton(ctk.CTkFrame):
    """EsqueletoLista: filas "fantasma" que pulsan mientras llega la respuesta."""

    def __init__(self, master, filas=7):
        super().__init__(master, fg_color="transparent")
        self._bloques = []
        for i in range(filas):
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=10)
            b = ctk.CTkFrame(row, width=40, height=40, corner_radius=RADIUS_S)
            b.pack(side="left")
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", padx=16, fill="x", expand=True)
            l1 = ctk.CTkFrame(col, height=14, width=380 if i % 2 == 0 else 260, corner_radius=7)
            l1.pack(anchor="w")
            l2 = ctk.CTkFrame(col, height=10, width=150, corner_radius=5)
            l2.pack(anchor="w", pady=(8, 0))
            self._bloques += [b, l1, l2]
        self._fase = False
        self._pulsar()

    def _pulsar(self):
        try:
            color = SURFACE_CONTAINER_HIGHEST if self._fase else SURFACE_CONTAINER_HIGH
            for b in self._bloques:
                b.configure(fg_color=color)
            self._fase = not self._fase
            self.after(450, self._pulsar)
        except tk.TclError:
            pass


class StatePanel(ctk.CTkScrollableFrame):
    """Lista que pinta los estados del `UiState` del móvil: esqueleto mientras
    carga, EstadoError con "Reintentar", EstadoVacio y, en Success, lo que dibuje
    quien la usa tras llamar a `clear()`."""

    def __init__(self, master, **kw):
        kw.setdefault("fg_color", "transparent")
        kw.setdefault("corner_radius", 0)
        super().__init__(master, **kw)

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def loading(self, _text=None):
        self.clear()
        Skeleton(self).pack(fill="x")

    def error(self, message, retry=None):
        self.clear()
        empty_state(self, "☁", "No se pudo cargar", message,
                    ("Reintentar", retry) if retry else None).pack(pady=50)

    def empty(self, message, icono="📂", titulo=None, accion=None):
        self.clear()
        if titulo:
            empty_state(self, icono, titulo, message, accion).pack(pady=50)
        else:
            ctk.CTkLabel(self, text=message, text_color=ON_SURFACE_VARIANT).pack(pady=30)


# =============================================================================
# ListItem
# =============================================================================
def list_item(master, icon, headline, supporting=None, tipo=None, on_click=None):
    """ListItem de Material 3. `icon` puede ser un glifo o se usa el `tipo` de
    archivo para el icono coloreado. Devuelve (fila, contenedor_derecho)."""
    row = ctk.CTkFrame(master, fg_color="transparent", corner_radius=RADIUS_S)
    row.pack(fill="x", padx=4, pady=1)
    if tipo is not None:
        icono_tipo(row, tipo).pack(side="left", padx=(12, 4), pady=10)
    else:
        ctk.CTkLabel(row, text=icon, width=40, font=icon_font(20)).pack(side="left", padx=(12, 4), pady=10)
    texts = ctk.CTkFrame(row, fg_color="transparent")
    texts.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=8)
    ctk.CTkLabel(texts, text=headline, text_color=ON_SURFACE, font=font("body_large"),
                 anchor="w").pack(anchor="w", fill="x")
    if supporting:
        if isinstance(supporting, str):
            ctk.CTkLabel(texts, text=supporting, text_color=ON_SURFACE_VARIANT, font=font("body"),
                         anchor="w").pack(anchor="w", fill="x")
        else:
            supporting(texts)
    trailing = ctk.CTkFrame(row, fg_color="transparent", width=1, height=1)
    trailing.pack(side="right", padx=8)
    if on_click:
        bind_click(row, on_click, hover=SURFACE_CONTAINER_HIGH)
    return row, trailing


# =============================================================================
# Diálogos
# =============================================================================
class Dialog(ctk.CTkToplevel):
    """Ventana modal base, centrada sobre la principal."""

    def __init__(self, master, title, width=480, height=420):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        top = master.winfo_toplevel()
        self.transient(top)
        top.update_idletasks()
        x = top.winfo_rootx() + (top.winfo_width() - width) // 2
        y = top.winfo_rooty() + max(20, (top.winfo_height() - height) // 3)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.after(80, self._focus)

    def _focus(self):
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except tk.TclError:
            pass


class DetailsDialog(Dialog):
    """HojaDetalles: ficha de un elemento (nombre, tipo y pares etiqueta/valor),
    como el panel "Detalles" de Drive. `acciones` = [(texto, comando, estilo)]."""

    def __init__(self, master, nombre, tipo, filas, acciones=()):
        super().__init__(master, "Detalles", 500, 150 + 62 * len(filas) + (70 if acciones else 0))
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(22, 0))
        icono_tipo(head, tipo, 48).pack(side="left")
        t = ctk.CTkFrame(head, fg_color="transparent")
        t.pack(side="left", padx=16, fill="x", expand=True)
        ctk.CTkLabel(t, text=nombre, font=font("title_medium"), anchor="w",
                     wraplength=360, justify="left").pack(anchor="w")
        ctk.CTkLabel(t, text=tipo.etiqueta, font=font("body"), text_color=ON_SURFACE_VARIANT,
                     anchor="w").pack(anchor="w")
        divider(self).pack(fill="x", padx=24, pady=(18, 6))
        ctk.CTkLabel(self, text="Detalles", font=font("title_small")).pack(anchor="w", padx=24, pady=(4, 2))
        self.valores = {}
        for etiqueta, valor in filas:
            ctk.CTkLabel(self, text=etiqueta, font=font("label_medium"),
                         text_color=ON_SURFACE_VARIANT).pack(anchor="w", padx=24, pady=(8, 0))
            self.valores[etiqueta] = ctk.CTkLabel(self, text=valor, font=font("body_large"),
                                                  wraplength=440, justify="left")
            self.valores[etiqueta].pack(anchor="w", padx=24)
        if acciones:
            bar = ctk.CTkFrame(self, fg_color="transparent")
            bar.pack(fill="x", padx=24, pady=(18, 18), side="bottom")
            for texto, comando, estilo in reversed(acciones):
                def run(c=comando):
                    self.destroy()
                    c()
                fab = {"primary": primary_button, "tonal": tonal_button,
                       "outlined": ghost_button}.get(estilo)
                if fab:
                    fab(bar, texto, run, width=120, height=36).pack(side="right", padx=(8, 0))
                else:
                    text_button(bar, texto, run, width=90, color=estilo or PRIMARY).pack(side="right", padx=(8, 0))


class ConfirmDialog(Dialog):
    """AlertDialog con icono, título, texto y dos acciones."""

    def __init__(self, master, icono, titulo, texto, confirmar, on_confirm):
        super().__init__(master, titulo, 420, 250)
        ctk.CTkLabel(self, text=icono, font=icon_font(26), text_color=ON_SURFACE_VARIANT).pack(pady=(24, 6))
        ctk.CTkLabel(self, text=titulo, font=font("headline_small")).pack()
        ctk.CTkLabel(self, text=texto, font=font("body"), text_color=ON_SURFACE_VARIANT,
                     wraplength=360).pack(pady=(10, 0))
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(side="bottom", fill="x", padx=20, pady=18)

        def ok():
            self.destroy()
            on_confirm()
        text_button(bar, confirmar, ok, width=120).pack(side="right")
        text_button(bar, "Cancelar", self.destroy, width=100).pack(side="right")
