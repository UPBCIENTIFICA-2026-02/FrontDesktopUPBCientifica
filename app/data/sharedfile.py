# -*- coding: utf-8 -*-
"""Shared File (HTTP/REST). Equivale a SharedFileApi.kt + SharedFileRepository.kt.

Servicio: node-shared-file (puerto 8085, VM node-repository), Contrato_SharedFile.
  POST   /shared-file/compartir             CompartirArchivo     {archivoId, destinatarioTipo, destinatarioId, nivelPermiso}
  POST   /shared-file/compartir-directorio  CompartirDirectorio  {directorioId, ...}
  PATCH  /shared-file/compartir/{id}        ActualizarPermisosCompartidos {nuevoNivelPermiso}
  DELETE /shared-file/compartir/{id}        DejarDeCompartir
  GET    /shared-file/compartidos-conmigo   ListarCompartidosConmigo
  GET    /shared-file/que-yo-comparto       ListarQueYoComparto

Lo que hay DENTRO de una carpeta compartida y los bytes de los archivos se
piden a Storage (data/storage.py): Storage ya aplica la compartición en sus
permisos, así que el destinatario los abre con su propio token.
"""

from dataclasses import dataclass

USUARIO, GRUPO = "USUARIO", "GRUPO"

# Niveles del contrato, en orden. El tercero permite volver a compartir.
NIVELES = [
    ("LECTURA", "Solo ver"),
    ("LECTURA_ESCRITURA", "Ver y editar"),
    ("LECTURA_ESCRITURA_COMPARTIR", "Ver, editar y compartir"),
]


def texto_nivel(nivel):
    return dict(NIVELES).get(nivel, nivel)


@dataclass
class RelacionCompartido:
    compartido_id: str
    elemento_id: str
    elemento_tipo: str            # ARCHIVO | DIRECTORIO
    nombre: str
    tamano_bytes: int
    propietario: str
    compartido_por: str
    destinatario_tipo: str        # USUARIO | GRUPO
    destinatario_id: str
    nivel_permiso: str
    fecha_compartido: str = None
    fecha_expiracion: str = None

    @property
    def es_directorio(self):
        return self.elemento_tipo == "DIRECTORIO"

    @property
    def destinatario_legible(self):
        return f"grupo {self.destinatario_id}" if self.destinatario_tipo == GRUPO else self.destinatario_id

    @classmethod
    def from_json(cls, d):
        return cls(
            compartido_id=str(d.get("compartidoId", "")),
            elemento_id=str(d.get("elementoId", "")),
            elemento_tipo=d.get("elementoTipo", "ARCHIVO"),
            nombre=d.get("nombre", "(sin nombre)"),
            tamano_bytes=int(d.get("tamanoBytes") or 0),
            propietario=d.get("propietario", "-"),
            compartido_por=d.get("compartidoPor", "-"),
            destinatario_tipo=d.get("destinatarioTipo", USUARIO),
            destinatario_id=d.get("destinatarioId", ""),
            nivel_permiso=d.get("nivelPermiso", "LECTURA"),
            fecha_compartido=d.get("fechaCompartido"),
            fecha_expiracion=d.get("fechaExpiracion"),
        )


class SharedFileRepository:
    """Sin servicio (modo demo o Shared File desactivado en Configuración) NO
    finge: avisa de que no está disponible, en vez de inventar datos."""

    NO_DISPONIBLE = ("Shared File está desactivado en Configuración "
                     "(\"Shared File disponible\") o estás en modo demostración.")

    def __init__(self, rest=None, disponible=True):
        self.rest = rest
        self.simulado = not disponible or rest is None

    def _api(self):
        if self.simulado:
            raise RuntimeError(self.NO_DISPONIBLE)
        return self.rest

    def compartir(self, elemento_id, es_directorio, destinatario_tipo, destinatario_id, nivel):
        """CompartirArchivo o CompartirDirectorio, según lo que sea."""
        if es_directorio:
            cuerpo = {"directorioId": elemento_id, "destinatarioTipo": destinatario_tipo,
                      "destinatarioId": destinatario_id, "nivelPermiso": nivel}
            return self._api().post_json("/shared-file/compartir-directorio", cuerpo) or {}
        cuerpo = {"archivoId": elemento_id, "destinatarioTipo": destinatario_tipo,
                  "destinatarioId": destinatario_id, "nivelPermiso": nivel}
        return self._api().post_json("/shared-file/compartir", cuerpo) or {}

    def compartidos_conmigo(self):
        return [RelacionCompartido.from_json(d)
                for d in (self._api().get_json("/shared-file/compartidos-conmigo") or [])]

    def que_yo_comparto(self):
        return [RelacionCompartido.from_json(d)
                for d in (self._api().get_json("/shared-file/que-yo-comparto") or [])]

    def cambiar_nivel(self, compartido_id, nivel):
        """Devuelve la advertencia SHR-201 si la hay (o None)."""
        r = self._api().patch_json(f"/shared-file/compartir/{compartido_id}",
                                   {"nuevoNivelPermiso": nivel}) or {}
        return (r.get("advertencia") or {}).get("mensaje")

    def revocar(self, compartido_id):
        self._api().delete(f"/shared-file/compartir/{compartido_id}")
