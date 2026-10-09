# -*- coding: utf-8 -*-
"""File Sync. Equivale a data/filesync/FileSyncRepository.kt del móvil.

File Sync habla gRPC (node-sync:9090, streaming bidireccional para
DetectarCambiosLocales). Falta generar el stub del .proto, así que MIENTRAS
TANTO el ciclo de sincronización se SIMULA para que la interfaz quede lista:
detecta cambios, los "sube" con progreso y queda al día hasta el siguiente
ciclo. La conectividad SÍ es real.

Cuando exista el stub, `ciclo()` debe convertir el stream gRPC en esta misma
secuencia de estados; la interfaz no tiene que cambiar. Ojo: el servidor saca
el usuario del token (metadata `authorization: Bearer <token>`).
"""

import random
import socket
import time
from dataclasses import dataclass


@dataclass
class Sincronizando:
    progreso: float      # 0..1
    pendientes: int      # cambios que faltan por subir


@dataclass
class AlDia:
    ultima_sincronizacion: float


class SinConexion:
    pass


SIN_CONEXION = SinConexion()

INTERVALO_CICLO_MS = 60_000
REVISION_RED_MS = 3_000
PASO_MS = 450


def hay_red():
    """True si el equipo tiene una ruta de red. Un `connect` UDP no envía
    paquetes: solo pregunta al sistema operativo si sabría llegar."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 53))
            return not s.getsockname()[0].startswith("127.")
    except OSError:
        return False


class FileSyncRepository:
    def ciclo(self):
        """Generador infinito de (estado, ms_hasta_el_siguiente). Quien lo use
        avanza con `next()` cuando pase ese tiempo (en Tk, con `after`)."""
        while True:
            if not hay_red():
                yield SIN_CONEXION, REVISION_RED_MS
                continue

            # TODO: reemplazar por el stream gRPC cuando se genere el stub
            pendientes = random.randint(2, 8)
            for subidos in range(pendientes + 1):
                yield Sincronizando(subidos / pendientes, pendientes - subidos), PASO_MS
            yield AlDia(time.time()), REVISION_RED_MS

            # Espera al siguiente ciclo, pero si se cae la red lo muestra enseguida.
            esperado = REVISION_RED_MS
            ultimo = time.time()
            while esperado < INTERVALO_CICLO_MS and hay_red():
                yield AlDia(ultimo), REVISION_RED_MS
                esperado += REVISION_RED_MS
