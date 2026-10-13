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
    # VPS del laboratorio (pasd_nodo1..3, solo desde la red cableada):
    "host_soap_lab": "10.154.12.219",    # pasd_nodo1: node-soap (HTTPS 8081) + node-web
    "host_storage_lab": "10.154.12.221", # pasd_nodo2: Storage 8084 + Shared File 8085
    "host_media_lab": "10.154.12.222",   # pasd_nodo3: node-media 8083
    "host_sync_lab": "10.154.12.221",    # pasd_nodo2: node-sync (gRPC/TLS 9090)
    "host_hpc_lab": "10.154.12.222",     # pasd_nodo3: job-api 8082 (fachada REST del gestor RMI)
    "usar_mock_auth": False,             # False = Auth SOAP real en el 8081 (node-soap o auth-local)
    "storage_simulado": False,           # False = node-repository real (8084)
    "streaming_simulado": False,         # False = node-media real (8083)
    "shared_file_disponible": True,      # node-shared-file (8085, VM node-repository)
    "hpc_simulado": False,               # False = job-api real (8082)

    # --- Preferencias del cliente ---
    "username": "",
    "appearance": "light",
    "album_folder": "",
    "video_folder": "",
    "vista_archivos": "lista",           # "lista" | "cuadricula"
    "version_config": 3,
}

# Versión 2: los servicios reales ya existen. Una configuración guardada con la
# versión anterior traía el mock de autenticación en el 8080 (ahí está ahora
# node-web) y Shared File apagado; se corrigen una sola vez al cargarla.
_MIGRACION_V2 = {"usar_mock_auth": False, "shared_file_disponible": True, "hpc_simulado": False}

# Versión 3: los servicios del laboratorio se desplegaron en las VPS
# (2026-10-13). Las direcciones viejas (192.168.1.195, 192.168.56.10) ya no
# existen; se sustituyen solo si el usuario no había puesto otras.
_HOSTS_LAB = ("host_soap_lab", "host_storage_lab", "host_media_lab", "host_sync_lab", "host_hpc_lab")
_HOSTS_VIEJOS = ("192.168.1.195", "192.168.56.10", "")


def load_config():
    """Crea los directorios locales y devuelve la configuración (con defaults)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    cfg = dict(DEFAULT_CONFIG)
    guardada = {}
    if CONFIG_FILE.exists():
        try:
            guardada = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg.update(guardada)
        except Exception:
            guardada = {}
    # Campos ya sin uso. sync_folder/sync_schedule: File Sync guarda ahora su
    # configuración por usuario en filesync/<uid>.json (data/filesync.py).
    for viejo in ("server_url", "jobs", "album_folder", "video_folder", "sync_folder", "sync_schedule"):
        cfg.pop(viejo, None)
    # La versión se mira en lo GUARDADO: los valores por defecto ya traen la 2,
    # y un archivo antiguo (sin el campo) parecería al día.
    if guardada and int(guardada.get("version_config") or 1) < 2:
        cfg.update(_MIGRACION_V2)
        cfg["version_config"] = 2
        save_config(cfg)
    if guardada and int(cfg.get("version_config") or 1) < 3:
        for clave in _HOSTS_LAB:
            if cfg.get(clave, "") in _HOSTS_VIEJOS:
                cfg[clave] = DEFAULT_CONFIG[clave]
        cfg["version_config"] = 3
        save_config(cfg)
    return cfg


def save_config(cfg):
    """Guarda la configuración en disco."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print("No se pudo guardar la configuración:", e)
