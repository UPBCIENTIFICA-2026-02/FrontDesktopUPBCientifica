# -*- coding: utf-8 -*-
"""Capa de servicios: ApiClient es el ÚNICO punto de contacto con el sistema
distribuido. Hoy funciona en modo demostración (local). Cada método marca con
TODO(backend) el servicio real del diseño que se invocará en las próximas fases.
"""

import os
import shutil
from datetime import datetime

from .config import HOME_DIR, save_config


class ApiClient:
    def __init__(self, config):
        self.config = config
        self.online = False          # aún no hay backend
        self.user = None

    # --- Autenticación (LDAP + MFA) ---
    def login(self, user, password, otp=""):
        # TODO(backend): POST {server}/api/login -> balanceador srv-web
        #                -> bind LDAP (inf-ldap) + validación TOTP (MFA).
        # Demo: acepta cualquier usuario/contraseña no vacíos.
        if user and password:
            self.user = user
            return True
        return False

    def logout(self):
        self.user = None

    # --- Trabajos HPC (RMI -> SLURM/MPI) ---
    def submit_job(self, job):
        # TODO(backend): RMI enviarTrabajo() en srv-rmi -> sbatch en hpc-master
        #                -> mpirun en los nodos de cómputo. Datos vía NFS.
        # Demo: se guarda localmente con estado 'Encolado (demo)'.
        job["estado"] = "Encolado (demo)"
        job["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.config["jobs"].insert(0, job)
        save_config(self.config)
        return job

    # --- File Sync (gRPC) ---
    def sync_now(self, folder):
        # TODO(backend): gRPC IniciarSync() en srv-grpc -> compara con el Home
        #                del usuario en NFS y transfiere las diferencias.
        # Demo: escanea la carpeta local y devuelve un resumen.
        files = []
        if folder and os.path.isdir(folder):
            for root, _dirs, names in os.walk(folder):
                for n in names:
                    files.append(os.path.join(root, n))
        return {"detectados": len(files), "carpeta": folder}

    # --- Shared Files (formulario de carga -> NFS) ---
    def upload_file(self, path):
        # TODO(backend): subir vía {server}/api/files (srv-web) -> Home del
        #                usuario (NFS en sto-nfs), con cuota y permisos Unix.
        # Demo: copia el archivo al Home local simulado.
        dest = HOME_DIR / os.path.basename(path)
        shutil.copy2(path, dest)
        return dest

    def list_home(self):
        items = []
        for p in sorted(HOME_DIR.glob("*")):
            if p.is_file():
                items.append((p.name, p.stat().st_size))
        return items
