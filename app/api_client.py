# -*- coding: utf-8 -*-
"""Capa de servicios: ApiClient es el ÚNICO punto de contacto de la interfaz
con el sistema distribuido.

Hace lo mismo que la "composición manual de dependencias" de MainActivity.kt
en el móvil: decide qué implementación usa cada repositorio (real o simulada)
a partir de la configuración. Las vistas nunca saben si por debajo hay SOAP,
REST o datos de prueba.

  Servicio             Protocolo   Estado
  Authentication       SOAP        Real (mock server.js o node-soap)
  Distributed Storage  REST        Real (node-repository:8084) o Home local
  Streaming            REST        Real (node-media:8083) o catálogo simulado
  Shared File          REST        Simulado (el servicio no existe aún)
  File Sync            gRPC        Pendiente (local)
  HPC                  RMI         Pendiente (cola local)
"""

import os
import socket
from datetime import datetime
from urllib.parse import urlparse

from .config import save_config
from .network.configuracion import Configuracion, NAMESPACE_AUTH
from .network.soap_client import SoapClient
from .network.rest_client import RestClient
from .session.token_manager import TokenManager
from .data.auth import AuthRepository
from .data.storage import StorageRepository
from .data.sharedfile import SharedFileRepository
from .data.streaming import StreamingRepository


class ApiClient:
    def __init__(self, config):
        self.config = config
        self.tokens = TokenManager()
        self.sesion = None          # SessionResult tras un login real
        self.modo_demo = False      # True = sin servidor, todo simulado
        self.reconfigurar()

    # --- Composición de dependencias ---------------------------------------
    def reconfigurar(self):
        """Reconstruye los repositorios. Se llama al guardar la configuración."""
        self.conf = Configuracion(self.config)
        c = self.conf
        demo = self.modo_demo

        self.auth = AuthRepository(SoapClient(c.url_auth, NAMESPACE_AUTH), self.tokens)
        self.storage = StorageRepository(
            RestClient(c.url_storage, self.tokens, "Storage"),
            usar_datos_simulados=demo or c.storage_simulado)
        self.streaming = StreamingRepository(
            RestClient(c.url_media, self.tokens, "Streaming"),
            usar_datos_simulados=demo or c.streaming_simulado)
        self.shared = SharedFileRepository(
            RestClient(c.url_storage, self.tokens, "Shared File"),
            usar_datos_simulados=demo or not c.shared_file_disponible)

    # --- Autenticación (SOAP) ----------------------------------------------
    @property
    def user(self):
        if self.sesion:
            return self.sesion.usuario
        return self.config.get("username") if self.modo_demo else None

    def login(self, usuario, contrasena):
        """Login real contra Authentication Service. Lanza AuthError/ConnectionError."""
        self.modo_demo = False
        self.reconfigurar()
        self.sesion = self.auth.login(usuario, contrasena, origen_cliente="desktop")
        return self.sesion

    def entrar_demo(self, usuario):
        """Entra sin servidor: todos los servicios con datos simulados/locales."""
        self.modo_demo = True
        self.sesion = None
        self.config["username"] = usuario or "demo"
        self.reconfigurar()

    def logout(self):
        try:
            self.auth.logout()
        except Exception:
            pass  # la sesión local se cierra igual (el token ya se borró)
        self.sesion = None
        self.modo_demo = False
        self.tokens.clear()

    # --- Estado de los servicios -------------------------------------------
    def servicios(self):
        """Tabla de servicios para el panel de Inicio: (nombre, protocolo, destino, modo)."""
        c = self.conf
        demo = self.modo_demo

        def modo(simulado):
            return "simulado" if (demo or simulado) else "real"

        return [
            ("Authentication", "SOAP", c.url_auth, "demo" if demo else c.descripcion_auth()),
            ("Distributed Storage", "HTTP/REST", c.url_storage, modo(c.storage_simulado)),
            ("Streaming", "HTTP/REST", c.url_media, modo(c.streaming_simulado)),
            ("Shared File", "HTTP/REST", c.url_storage, modo(not c.shared_file_disponible)),
            ("File Sync", "gRPC", c.direccion_sync, "pendiente"),
            ("HPC", "RMI", "srv-rmi", "pendiente"),
        ]

    @staticmethod
    def probar_conexion(destino, timeout=2.0):
        """True si hay algo escuchando en host:puerto (no valida el protocolo)."""
        if "://" in destino:
            u = urlparse(destino)
            host, port = u.hostname, u.port or (443 if u.scheme == "https" else 80)
        elif ":" in destino:
            host, port = destino.rsplit(":", 1)
            port = int(port)
        else:
            return False
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    # --- Trabajos HPC (RMI -> SLURM/MPI) — pendiente ------------------------
    def submit_job(self, job):
        # TODO(backend): RMI enviarTrabajo() en srv-rmi -> sbatch en hpc-master
        #                -> mpirun en los nodos de cómputo. Ver data/pendientes.py.
        job["estado"] = "Encolado (demo)"
        job["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.config["jobs"].insert(0, job)
        save_config(self.config)
        return job

    # --- File Sync (gRPC) — pendiente ---------------------------------------
    def sync_now(self, folder):
        # TODO(backend): gRPC en node-sync (9090) con metadata
        #                `authorization: Bearer <token>`. Ver data/pendientes.py.
        files = []
        if folder and os.path.isdir(folder):
            for root, _dirs, names in os.walk(folder):
                for n in names:
                    files.append(os.path.join(root, n))
        return {"detectados": len(files), "carpeta": folder}
