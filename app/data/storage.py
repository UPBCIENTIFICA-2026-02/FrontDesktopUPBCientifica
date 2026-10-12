# -*- coding: utf-8 -*-
"""Distributed Storage (HTTP/REST, node-repository:8084). Equivale a
StorageApi.kt + StorageRepository.kt.

Endpoints:
  GET    /storage/directorios/{id}           -> lista de ArchivoDto
  POST   /storage/archivos (multipart)       -> ArchivoDto creado
         ?directorioDestino=...&sobrescribir=false
  GET    /storage/archivos/{id}/descargar      (admite Range: el reproductor lo usa)
  DELETE /storage/archivos/{id}                 (solo archivos)
  POST   /storage/directorios                   {nombre, directorioPadreId}
  GET    /storage/cuota                         {usados, cuota, disponibles}

En modo simulado (sin backend) se trabaja sobre un Home local en
~/.upbcientifica/home, así subir, bajar, borrar y navegar funcionan igual.
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from ..config import HOME_DIR

RAIZ = "root"


@dataclass
class ArchivoDto:
    id: str
    nombre: str
    tipo: str                      # "archivo" | "directorio"
    tamano_bytes: int = 0
    version: int = 1
    directorio_contenedor_id: str = None

    @property
    def es_directorio(self):
        return self.tipo == "directorio"

    @classmethod
    def from_json(cls, d):
        return cls(
            id=str(d.get("id", "")),
            nombre=d.get("nombre", "(sin nombre)"),
            tipo=d.get("tipo", "archivo"),
            tamano_bytes=int(d.get("tamanoBytes") or 0),
            version=int(d.get("version") or 1),
            directorio_contenedor_id=d.get("directorioContenedorId"),
        )


class StorageRepository:
    def __init__(self, rest=None, usar_datos_simulados=True):
        self.rest = rest
        self.simulado = usar_datos_simulados or rest is None

    def listar(self, directorio_id=RAIZ):
        if self.simulado:
            return self._listar_local(directorio_id)
        datos = self.rest.get_json(f"/storage/directorios/{directorio_id}") or []
        items = [ArchivoDto.from_json(d) for d in datos]
        # Carpetas primero y luego por nombre, como un explorador de archivos.
        return sorted(items, key=lambda a: (not a.es_directorio, a.nombre.lower()))

    def subir(self, ruta_local, directorio_destino=RAIZ, sobrescribir=False):
        if self.simulado:
            destino = self._ruta_local(directorio_destino) / os.path.basename(ruta_local)
            shutil.copy2(ruta_local, destino)
            return self._dto_local(destino)
        d = self.rest.post_multipart(
            "/storage/archivos", "archivo", ruta_local,
            {"directorioDestino": directorio_destino, "sobrescribir": str(sobrescribir).lower()})
        return ArchivoDto.from_json(d or {"nombre": os.path.basename(ruta_local)})

    def descargar(self, archivo_id, destino):
        if self.simulado:
            shutil.copy2(self._ruta_local(archivo_id), destino)
            return destino
        return self.rest.download(f"/storage/archivos/{archivo_id}/descargar", destino)

    def eliminar(self, archivo_id):
        if self.simulado:
            p = self._ruta_local(archivo_id)
            shutil.rmtree(p) if p.is_dir() else p.unlink()
            return
        self.rest.delete(f"/storage/archivos/{archivo_id}")

    def crear_carpeta(self, nombre, padre=RAIZ):
        if self.simulado:
            p = self._ruta_local(padre) / nombre
            p.mkdir(parents=False, exist_ok=False)
            return self._dto_local(p)
        return ArchivoDto.from_json(self.rest.post_json(
            "/storage/directorios", {"nombre": nombre, "directorioPadreId": padre}) or {"nombre": nombre})

    def cuota(self):
        """(usados, cuota) en bytes, o None en modo simulado."""
        if self.simulado:
            return None
        d = self.rest.get_json("/storage/cuota") or {}
        return int(d.get("usados") or 0), int(d.get("cuota") or 0)

    def leer(self, archivo_id):
        """Contenido completo en memoria: solo para imágenes, que el visor necesita enteras."""
        if self.simulado:
            return self._ruta_local(archivo_id).read_bytes()
        return self.rest.get_bytes(f"/storage/archivos/{archivo_id}/descargar")

    def fuente_video(self, archivo_id):
        """(url, cabeceras) para reproducir sin descargar el archivo entero."""
        if self.simulado:
            return str(self._ruta_local(archivo_id)), {}
        return self.rest.url(f"/storage/archivos/{archivo_id}/descargar"), self.rest.cabeceras_auth()

    def ruta_local(self, archivo_id):
        """Solo en modo simulado: ruta real en disco (para abrir con el sistema)."""
        return self._ruta_local(archivo_id) if self.simulado else None

    # --- Home local (modo simulado) -----------------------------------------
    def _ruta_local(self, archivo_id):
        rel = "" if archivo_id in (None, "", RAIZ) else archivo_id
        p = (HOME_DIR / rel).resolve()
        if HOME_DIR.resolve() not in (p, *p.parents):
            raise ValueError("Ruta fuera del Home")
        return p

    def _dto_local(self, p: Path):
        rel = p.relative_to(HOME_DIR).as_posix()
        padre = p.parent.relative_to(HOME_DIR).as_posix()
        return ArchivoDto(
            id=rel, nombre=p.name,
            tipo="directorio" if p.is_dir() else "archivo",
            tamano_bytes=0 if p.is_dir() else p.stat().st_size,
            version=1, directorio_contenedor_id=RAIZ if padre == "." else padre)

    def _listar_local(self, directorio_id):
        HOME_DIR.mkdir(parents=True, exist_ok=True)
        base = self._ruta_local(directorio_id)
        items = [self._dto_local(p) for p in base.iterdir()]
        return sorted(items, key=lambda a: (not a.es_directorio, a.nombre.lower()))
