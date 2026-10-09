# -*- coding: utf-8 -*-
"""Guarda el token emitido por Authentication Service y lo expone a los demás
repositorios (Storage, Shared File, Streaming, Sync), como TokenManager.kt.

A diferencia del móvil, el token vive solo en memoria: al cerrar la app la
sesión termina. Es la opción más segura en un PC compartido de laboratorio y
evita guardar credenciales en claro en ~/.upbcientifica.
"""

import threading


class TokenManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._token = None

    def save_token(self, token):
        with self._lock:
            self._token = token

    def current_token(self):
        with self._lock:
            return self._token

    def clear(self):
        with self._lock:
            self._token = None
