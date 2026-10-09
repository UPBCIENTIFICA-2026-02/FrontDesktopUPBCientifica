# -*- coding: utf-8 -*-
"""Streaming (HTTP/REST, node-media:8083). Equivale a StreamingApi.kt +
StreamingRepository.kt.

Endpoints:
  GET /streaming/catalogo?pagina=N           -> lista de ContenidoDto
  GET /streaming/buscar?criterioTexto=...    -> lista de ContenidoDto
  GET /streaming/{id}/sesion                 -> {sesionId, manifestUrl}
El video se sirve por HTTP con rangos desde manifestUrl.
"""

from dataclasses import dataclass


@dataclass
class ContenidoDto:
    id: str
    titulo: str
    duracion_segundos: int

    @property
    def duracion_texto(self):
        m, s = divmod(int(self.duracion_segundos or 0), 60)
        return f"{m} min" if s == 0 else f"{m} min {s:02d} s"

    @classmethod
    def from_json(cls, d):
        return cls(str(d.get("id", "")), d.get("titulo", "(sin título)"),
                   int(d.get("duracionSegundos") or 0))


@dataclass
class SesionStreamingDto:
    sesion_id: str
    manifest_url: str


class StreamingRepository:
    def __init__(self, rest=None, usar_datos_simulados=True):
        self.rest = rest
        self.simulado = usar_datos_simulados or rest is None

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
        if self.simulado:
            return SesionStreamingDto("mock-sesion", "http://mock/manifest.m3u8")
        d = self.rest.get_json(f"/streaming/{contenido_id}/sesion") or {}
        manifest = d.get("manifestUrl", "")
        # Si el servidor devuelve una ruta relativa, se completa con su URL base.
        if manifest.startswith("/"):
            manifest = self.rest.base_url.rstrip("/") + manifest
        return SesionStreamingDto(str(d.get("sesionId", "")), manifest)

    @staticmethod
    def _simulados():
        return [
            ContenidoDto("v1", "Presentación proyecto UPB", 320),
            ContenidoDto("v2", "Demo del clúster HPC", 540),
            ContenidoDto("v3", "Charla resultados 2026", 1260),
        ]
