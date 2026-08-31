# -*- coding: utf-8 -*-
"""Capa de persistencia: rutas, valores por defecto y lectura/escritura de la
configuración local del cliente (JSON en el home del usuario)."""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".upbcientifica"
CONFIG_FILE = CONFIG_DIR / "config.json"
HOME_DIR = CONFIG_DIR / "home"           # "Home" local simulado (Shared Files)

# Extensiones reconocidas
IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
VID_EXT = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v")

DEFAULT_CONFIG = {
    "server_url": "https://srv-web.upbcientifica.local",
    "username": "",
    "appearance": "light",
    "album_folder": "",
    "video_folder": "",
    "sync_folder": "",
    "sync_schedule": "Manual",
    "jobs": [],       # trabajos HPC creados localmente (demo)
}


def load_config():
    """Crea los directorios locales y devuelve la configuración (con defaults)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


def save_config(cfg):
    """Guarda la configuración en disco."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print("No se pudo guardar la configuración:", e)
