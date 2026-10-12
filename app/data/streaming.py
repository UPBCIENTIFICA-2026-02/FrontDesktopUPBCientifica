# -*- coding: utf-8 -*-
"""Streaming y Photo Album (HTTP/REST, node-media:8083). Equivale a
StreamingApi.kt + StreamingRepository.kt del móvil.

Streaming (propio + compartido contigo; ordenPor = RECIENTES | MAS_VISTOS | ALFABETICO):
  GET    /streaming/catalogo?pagina=N&ordenPor=...  -> lista de ContenidoDto
  GET    /streaming/{id}/miniatura           (JPEG, la genera node-media con FFmpeg)
  GET    /streaming/buscar?criterioTexto=... -> lista de ContenidoDto
  GET    /streaming/{id}/sesion              -> {sesionId, manifestUrl}
  DELETE /streaming/{id}                     (borra el archivo en Storage y del catálogo)
El video se pide por rangos a manifestUrl (lo hace el reproductor, con el token).

Photo Album (propio + compartido contigo; ordenPor = RECIENTES | ALFABETICO):
  GET    /album/fotos?pagina=N&ordenPor=...  -> lista de FotoDto
  GET    /album/fotos/{id}/miniatura         (JPEG)
  GET    /album/fotos/{id}/contenido         (original)
  DELETE /album/fotos/{id}
  POST   /album/indexar                      -> {indexados, revisados, compartidos}
node-media reindexa solo al pedir la primera página (como mucho una vez por
minuto); "Buscar nuevas" lo fuerza al momento.
"""

# ordenPor del Contrato_Streaming -> texto para la interfaz
ORDENES_VIDEO = {"RECIENTES": "Recientes", "MAS_VISTOS": "Más vistos", "ALFABETICO": "Título (A-Z)"}
ORDENES_FOTO = {"RECIENTES": "Recientes", "ALFABETICO": "Título (A-Z)"}

from dataclasses import dataclass


@dataclass
class ContenidoDto:
    id: str
    titulo: str
    duracion_segundos: int
    fecha: str = None
    tiene_miniatura: bool = False
    visualizaciones: int = 0
    propietario: str = None
    compartido: bool = False     # te lo compartió `propietario`

    @property
    def duracion_texto(self):
        m, s = divmod(int(self.duracion_segundos or 0), 60)
        return f"{m} min" if s == 0 else f"{m} min {s:02d} s"

    @classmethod
    def from_json(cls, d):
        return cls(str(d.get("id", "")), d.get("titulo", "(sin título)"),
                   int(d.get("duracionSegundos") or 0), d.get("fecha"), bool(d.get("tieneMiniatura")),
                   int(d.get("visualizaciones") or 0), d.get("propietario"), bool(d.get("compartido")))


@dataclass
class FotoDto:
    id: str
    titulo: str
    tamano_bytes: int
    ancho: int
    alto: int
    tiene_miniatura: bool
    fecha: str = None
    propietario: str = None
    compartido: bool = False

    @classmethod
    def from_json(cls, d):
        return cls(str(d.get("id", "")), d.get("titulo", "(sin título)"), int(d.get("tamanoBytes") or 0),
                   int(d.get("ancho") or 0), int(d.get("alto") or 0), bool(d.get("tieneMiniatura")),
                   d.get("fecha"), d.get("propietario"), bool(d.get("compartido")))


class StreamingRepository:
    def __init__(self, rest=None, usar_datos_simulados=True):
        self.rest = rest
        self.simulado = usar_datos_simulados or rest is None

    # --- Streaming -----------------------------------------------------------
    def catalogo(self, pagina=0, orden="RECIENTES"):
        if self.simulado:
            datos = self._simulados() if pagina == 0 else []
            return sorted(datos, key=lambda c: c.titulo.lower()) if orden == "ALFABETICO" else datos
        return [ContenidoDto.from_json(d)
                for d in (self.rest.get_json("/streaming/catalogo", {"pagina": pagina, "ordenPor": orden}) or [])]

    def miniatura_video(self, contenido_id):
        return self.rest.get_bytes(f"/streaming/{contenido_id}/miniatura")

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
    def fotos(self, pagina=0, orden="RECIENTES"):
        if self.simulado:
            return []
        return [FotoDto.from_json(d)
                for d in (self.rest.get_json("/album/fotos", {"pagina": pagina, "ordenPor": orden}) or [])]

    def miniatura(self, foto_id):
        return self.rest.get_bytes(f"/album/fotos/{foto_id}/miniatura")

    def contenido_foto(self, foto_id):
        return self.rest.get_bytes(f"/album/fotos/{foto_id}/contenido")

    def eliminar_foto(self, foto_id):
        if self.simulado:
            raise RuntimeError("No disponible en modo simulado.")
        self.rest.delete(f"/album/fotos/{foto_id}")

    def indexar(self):
        """Busca ya mismo fotos y videos nuevos en Mis archivos y en lo compartido
        contigo. Devuelve (indexados, revisados, compartidos)."""
        if self.simulado:
            return 0, 0, 0
        d = self.rest.post_json("/album/indexar") or {}
        return int(d.get("indexados") or 0), int(d.get("revisados") or 0), int(d.get("compartidos") or 0)

    @staticmethod
    def _simulados():
        return [
            ContenidoDto("v1", "Presentación proyecto UPB", 320),
            ContenidoDto("v2", "Demo del clúster HPC", 540),
            ContenidoDto("v3", "Charla resultados 2026", 1260),
        ]
