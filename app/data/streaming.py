# -*- coding: utf-8 -*-
"""Streaming y Photo Album (HTTP/REST, node-media:8083). Equivale a
StreamingApi.kt + StreamingRepository.kt del móvil.

Streaming:
  GET    /streaming/catalogo?pagina=N        -> lista de ContenidoDto
  GET    /streaming/buscar?criterioTexto=... -> lista de ContenidoDto
  GET    /streaming/{id}/sesion              -> {sesionId, manifestUrl}
  DELETE /streaming/{id}                     (borra el archivo en Storage y del catálogo)
El video se pide por rangos a manifestUrl (lo hace el reproductor, con el token).

Photo Album:
  GET    /album/fotos?pagina=N               -> lista de FotoDto
  GET    /album/fotos/{id}/miniatura         (JPEG)
  GET    /album/fotos/{id}/contenido         (original)
  DELETE /album/fotos/{id}
  POST   /album/indexar                      -> {indexados, revisados}
Lo subido a Storage no aparece aquí hasta indexar.
"""

from dataclasses import dataclass


@dataclass
class ContenidoDto:
    id: str
    titulo: str
    duracion_segundos: int
    fecha: str = None

    @property
    def duracion_texto(self):
        m, s = divmod(int(self.duracion_segundos or 0), 60)
        return f"{m} min" if s == 0 else f"{m} min {s:02d} s"

    @classmethod
    def from_json(cls, d):
        return cls(str(d.get("id", "")), d.get("titulo", "(sin título)"),
                   int(d.get("duracionSegundos") or 0), d.get("fecha"))


@dataclass
class FotoDto:
    id: str
    titulo: str
    tamano_bytes: int
    ancho: int
    alto: int
    tiene_miniatura: bool
    fecha: str = None

    @classmethod
    def from_json(cls, d):
        return cls(str(d.get("id", "")), d.get("titulo", "(sin título)"), int(d.get("tamanoBytes") or 0),
                   int(d.get("ancho") or 0), int(d.get("alto") or 0), bool(d.get("tieneMiniatura")),
                   d.get("fecha"))


class StreamingRepository:
    def __init__(self, rest=None, usar_datos_simulados=True):
        self.rest = rest
        self.simulado = usar_datos_simulados or rest is None

    # --- Streaming -----------------------------------------------------------
    def catalogo(self, pagina=0):
        if self.simulado:
            return self._simulados() if pagina == 0 else []
        return [ContenidoDto.from_json(d)
                for d in (self.rest.get_json("/streaming/catalogo", {"pagina": pagina}) or [])]

    def buscar(self, criterio):
        if self.simulado:
            return [c for c in self._simulados() if criterio.lower() in c.titulo.lower()]
        return [ContenidoDto.from_json(d)
                for d in (self.rest.get_json("/streaming/buscar", {"criterioTexto": criterio}) or [])]

    def reproducir(self, contenido_id):
        """Abre una sesión y devuelve (url, cabeceras) para el reproductor."""
        if self.simulado:
            raise RuntimeError("No hay video real en modo simulado.")
        d = self.rest.get_json(f"/streaming/{contenido_id}/sesion") or {}
        manifest = d.get("manifestUrl", "")
        if not manifest:
            raise RuntimeError("node-media no devolvió la URL del video.")
        # Llega como ruta relativa ("/streaming/{id}/contenido").
        url = manifest if "://" in manifest else self.rest.url(manifest)
        return url, self.rest.cabeceras_auth()

    def eliminar_video(self, contenido_id):
        if self.simulado:
            raise RuntimeError("No disponible en modo simulado.")
        self.rest.delete(f"/streaming/{contenido_id}")

    # --- Photo Album ---------------------------------------------------------
    def fotos(self, pagina=0):
        if self.simulado:
            return []
        return [FotoDto.from_json(d) for d in (self.rest.get_json("/album/fotos", {"pagina": pagina}) or [])]

    def miniatura(self, foto_id):
        return self.rest.get_bytes(f"/album/fotos/{foto_id}/miniatura")

    def contenido_foto(self, foto_id):
        return self.rest.get_bytes(f"/album/fotos/{foto_id}/contenido")

    def eliminar_foto(self, foto_id):
        if self.simulado:
            raise RuntimeError("No disponible en modo simulado.")
        self.rest.delete(f"/album/fotos/{foto_id}")

    def indexar(self):
        """Busca en Mis archivos fotos y videos nuevos. Devuelve (indexados, revisados)."""
        if self.simulado:
            return 0, 0
        d = self.rest.post_json("/album/indexar") or {}
        return int(d.get("indexados") or 0), int(d.get("revisados") or 0)

    @staticmethod
    def _simulados():
        return [
            ContenidoDto("v1", "Presentación proyecto UPB", 320),
            ContenidoDto("v2", "Demo del clúster HPC", 540),
            ContenidoDto("v3", "Charla resultados 2026", 1260),
        ]
