# -*- coding: utf-8 -*-
"""Capa de servicios: ApiClient es el ÚNICO punto de contacto de la interfaz
con el sistema distribuido.

Hace lo mismo que la "composición manual de dependencias" de MainActivity.kt
en el móvil: decide qué implementación usa cada repositorio (real o simulada)
a partir de la configuración. Las vistas nunca saben si por debajo hay SOAP,
REST o datos de prueba.

  Servicio             Protocolo   Destino
  Authentication       SOAP        node-soap (8081) o el mock antiguo (8080)
  Distributed Storage  REST        node-repository:8084 (o Home local en demo)
  Shared File          REST        node-shared-file:8085 (VM node-repository)
  Streaming + Album    REST        node-media:8083
  HPC                  REST        job-api:8082, la fachada REST del gestor RMI
  File Sync            gRPC        node-sync:9090 (guarda a través de Storage)
"""

import socket
from urllib.parse import urlparse

from .network.configuracion import Configuracion, NAMESPACE_AUTH
from .network.soap_client import SoapClient
from .network.rest_client import RestClient
from .session.token_manager import TokenManager
from .data.auth import AuthRepository
from .data.storage import StorageRepository
from .data.sharedfile import SharedFileRepository
from .data.streaming import StreamingRepository
from .data.hpc import HpcRepository, SimuladorHpc
from .data.filesync import FileSyncRepository


class ApiClient:
    def __init__(self, config):
        self.config = config
        self.tokens = TokenManager()
        self.sesion = None          # SessionResult tras un login real
        self.modo_demo = False      # True = sin servidor, todo simulado
        self.filesync = None
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
            RestClient(c.url_media, self.tokens, "node-media"),
            usar_datos_simulados=demo or c.streaming_simulado)
        self.shared = SharedFileRepository(
            RestClient(c.url_compartidos, self.tokens, "Shared File"),
            disponible=not demo and c.shared_file_disponible)
        # El simulador guarda estado: se conserva mientras no cambie el modo.
        if demo or c.hpc_simulado:
            if not isinstance(getattr(self, "hpc", None), SimuladorHpc):
                self.hpc = SimuladorHpc()
        else:
            self.hpc = HpcRepository(RestClient(c.url_trabajos, self.tokens, "HPC (job-api)"))
        # File Sync guarda estado (sesión, sincronización en curso): se conserva
        # y solo se le actualiza la dirección.
        if self.filesync is None:
            self.filesync = FileSyncRepository(self.tokens, c.direccion_sync)
        else:
            self.filesync.direccion = c.direccion_sync

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
        self._nueva_sesion()
        self.filesync.iniciar_sesion(self.sesion.usuario, self.conf.direccion_sync)
        return self.sesion

    def _nueva_sesion(self):
        """Los trabajos simulados de una cuenta no deben verse en la siguiente."""
        if isinstance(getattr(self, "hpc", None), SimuladorHpc):
            self.hpc = SimuladorHpc()

    def entrar_demo(self, usuario):
        """Entra sin servidor: todos los servicios con datos simulados/locales."""
        self.modo_demo = True
        self.sesion = None
        self.config["username"] = usuario or "demo"
        self.hpc = SimuladorHpc()
        self.filesync.cerrar_sesion()    # sin servidor no hay nada que sincronizar
        self.reconfigurar()

    def logout(self):
        try:
            self.auth.logout()
        except Exception:
            pass  # la sesión local se cierra igual (el token ya se borró)
        self.sesion = None
        self.modo_demo = False
        self.filesync.cerrar_sesion()
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
            ("Shared File", "HTTP/REST", c.url_compartidos, modo(not c.shared_file_disponible)),
            ("Streaming y fotos", "HTTP/REST", c.url_media, modo(c.streaming_simulado)),
            ("HPC (job-api)", "HTTP/REST → RMI", c.url_trabajos, modo(c.hpc_simulado)),
            ("File Sync", "gRPC", c.direccion_sync, "demo" if demo else "real"),
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

