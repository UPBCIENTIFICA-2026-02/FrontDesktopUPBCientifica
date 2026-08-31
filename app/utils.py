# -*- coding: utf-8 -*-
"""Utilidades independientes de la interfaz."""

import os
import platform
import subprocess
from tkinter import messagebox


def human_size(nbytes):
    """Formatea un tamaño en bytes de forma legible."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024:
            return f"{nbytes:.0f} {unit}" if unit == "B" else f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"


def open_with_system(path):
    """Abre un archivo con la aplicación por defecto del sistema (Win/Linux/Mac)."""
    try:
        if platform.system() == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
        return True
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{e}")
        return False
