# -*- coding: utf-8 -*-
"""Utilidades independientes de la interfaz."""

import os
import platform
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox


def human_size(nbytes):
    """Tamaño legible ("512 B", "240,0 MB"), igual que formatearTamano del móvil."""
    valor = float(nbytes or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if valor < 1024 or unit == "TB":
            return f"{valor:.0f} {unit}" if unit in ("B", "KB") else f"{valor:.1f} {unit}"
        valor /= 1024


def describir(e):
    """Mensaje que sirva para diagnosticar algo (como LoginViewModel.describir):
    si la excepción no trae texto, al menos se muestra su tipo."""
    detalle = str(e).strip() if e is not None else ""
    if not detalle and getattr(e, "__cause__", None) is not None:
        detalle = str(e.__cause__).strip()
    return detalle or f"Error inesperado ({type(e).__name__})"


def run_async(widget, fn, on_ok=None, on_err=None):
    """Ejecuta `fn` en un hilo y entrega el resultado en el hilo de Tk.

    Equivale al `viewModelScope.launch` del móvil: las llamadas de red no
    congelan la ventana. Tk no es seguro entre hilos, así que el hilo solo deja
    el resultado en una cola y la interfaz la consulta con `after`.
    """
    q = queue.Queue()

    def worker():
        try:
            q.put((True, fn()))
        except Exception as e:  # noqa: BLE001 — se entrega a la UI
            q.put((False, e))

    def poll():
        try:
            ok, value = q.get_nowait()
        except queue.Empty:
            try:
                widget.after(60, poll)
            except tk.TclError:
                pass  # la vista se destruyó mientras esperaba
            return
        try:
            if not widget.winfo_exists():
                return
        except tk.TclError:
            return
        if ok and on_ok:
            on_ok(value)
        elif not ok and on_err:
            on_err(value)

    threading.Thread(target=worker, daemon=True).start()
    widget.after(60, poll)


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
