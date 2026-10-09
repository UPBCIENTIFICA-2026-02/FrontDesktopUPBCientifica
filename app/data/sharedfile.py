# -*- coding: utf-8 -*-
"""Shared File (HTTP/REST). Equivale a SharedFileApi.kt + SharedFileRepository.kt.

Endpoints esperados:
  POST   /shared-file/compartir            -> {compartidoId}
  GET    /shared-file/compartidos-conmigo  -> lista de RecursoCompartidoDto
  DELETE /shared-file/compartir/{id}

Sigue SIMULADO a propósito: ningún servicio del backend responde aún las rutas
`/shared-file` (el diagrama lo ubica como `shared-file-svc` dentro de la VM de
node-repository). Cuando exista, basta activar "Shared File disponible" en
Configuración.
"""

from dataclasses import dataclass


@dataclass
class RecursoCompartidoDto:
    compartido_id: str
    archivo_id: str
    nombre_archivo: str
    propietario: str
    permiso_unix: str            # p. ej. "r--"

    @classmethod
    def from_json(cls, d):
        return cls(
            compartido_id=str(d.get("compartidoId", "")),
            archivo_id=str(d.get("archivoId", "")),
            nombre_archivo=d.get("nombreArchivo", "(sin nombre)"),
            propietario=d.get("propietario", "-"),
            permiso_unix=d.get("permisoUnix", "---"),
        )


class SharedFileRepository:
    def __init__(self, rest=None, usar_datos_simulados=True):
        self.rest = rest
        self.simulado = usar_datos_simulados or rest is None
        self._simulados = [
            RecursoCompartidoDto("s1", "10", "paper_borrador.docx", "maria.lopez", "r--"),
            RecursoCompartidoDto("s2", "11", "dataset_compartido.zip", "carlos.ruiz", "rw-"),
        ]
        self._contador = 0

    def compartir(self, archivo_id, permiso_unix, usuario_id=None, grupo_id=None):
        if self.simulado:
            self._contador += 1
            return f"mock-shared-{self._contador}"
        d = self.rest.post_json("/shared-file/compartir", {
            "archivoId": archivo_id,
            "destinatarioUsuarioId": usuario_id or None,
            "destinatarioGrupoId": grupo_id or None,
            "permisoUnix": permiso_unix,
        }) or {}
        return str(d.get("compartidoId", ""))

    def compartidos_conmigo(self):
        if self.simulado:
            return list(self._simulados)
        return [RecursoCompartidoDto.from_json(d)
                for d in (self.rest.get_json("/shared-file/compartidos-conmigo") or [])]

    def revocar(self, compartido_id):
        if self.simulado:
            self._simulados = [r for r in self._simulados if r.compartido_id != compartido_id]
            return
        self.rest.delete(f"/shared-file/compartir/{compartido_id}")
