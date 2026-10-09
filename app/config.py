# -*- coding: utf-8 -*-
"""Capa de persistencia: rutas, valores por defecto y lectura/escritura de la
configuración local del cliente (JSON en el home del usuario)."""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".upbcientifica"
CONFIG_FILE = CONFIG_DIR / "config.json"
HOME_DIR = CONFIG_DIR / "home"           # Home local para el modo simulado de Storage
DOWNLOAD_DIR = Path.home() / "Downloads"

# Extensiones reconocidas
IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
VID_EXT = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v")

DEFAULT_CONFIG = {
    # --- Conexión (mismo modelo que network/Configuracion.kt del móvil) ---
    "entorno": "LOCAL",                  # LOCAL (servicios en este PC) | LABORATORIO
    "host_desarrollo": "127.0.0.1",      # dónde corren los servicios en modo LOCAL (127.0.0.1 evita
                                         # el intento IPv6 de "localhost" en Windows, ~2 s)
    "host_soap_lab": "192.168.1.195",
    "host_storage_lab": "192.168.1.195",
    "host_media_lab": "192.168.1.195",
    "host_sync_lab": "192.168.1.195",
    "usar_mock_auth": True,              # mock-auth-server/server.js en el 8080
    "storage_simulado": False,           # False = node-repository real (8084)
    "streaming_simulado": False,         # False = node-media real (8083)
    "shared_file_disponible": False,     # el servicio aún no existe en el backend

    # --- Preferencias del cliente ---
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
    cfg["jobs"] = []
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    cfg.pop("server_url", None)  # campo de la versión anterior, ya sin uso
    return cfg


def save_config(cfg):
    """Guarda la configuración en disco."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print("No se pudo guardar la configuración:", e)
