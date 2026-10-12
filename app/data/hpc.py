# -*- coding: utf-8 -*-
"""HPC Service. Equivale a data/hpc/HpcRepository.kt del móvil.

El contrato habla RMI, que solo existe en la JVM. El escritorio (como el móvil
y el portal) habla REST con **job-api**, la fachada HTTP del gestor RMI
(repositorio RMIUPBCientifica, puerto 8082):

    GET    /jobs           -> trabajos del usuario del token
    GET    /jobs/{id}
    POST   /jobs           {nombre, comando, prioridad 1-10} -> {id}
    DELETE /jobs/{id}      -> {id, cancelado}

`HpcRepository` usa job-api. `SimuladorHpc` (modo demostración) imita las
mismas operaciones sin servidor: el estado avanza con el tiempo.

job-api todavía no expone el estado del clúster (Contrato_HPC: /cluster/estado)
ni el porcentaje de avance: `estado_cluster` es None y `progreso` es None con el
servicio real, y la pantalla lo dice en vez de inventar cifras.
"""

import calendar
import math
import random
import threading
import time
from dataclasses import dataclass

EN_COLA, EJECUTANDO, COMPLETADO, FALLIDO, CANCELADO = "EN_COLA", "EJECUTANDO", "COMPLETADO", "FALLIDO", "CANCELADO"
_ESTADOS_API = {"QUEUED": EN_COLA, "RUNNING": EJECUTANDO, "COMPLETED": COMPLETADO,
                "FAILED": FALLIDO, "CANCELLED": CANCELADO}
NODOS_TOTALES = 16
MIN = 60
HORA = 60 * MIN


@dataclass
class SolicitudTrabajo:
    """Lo que acepta job-api (SubmitJobRequest.java)."""
    nombre: str
    comando: str
    prioridad: int = 5          # 1 (baja) .. 10 (alta)


@dataclass
class TrabajoHpc:
    id: str
    nombre: str
    comando: str
    prioridad: int
    estado: str
    progreso: object            # 0..1 en EJECUTANDO, o None si el servidor no lo informa
    enviado_en: float           # epoch en segundos
    resultado: str = None       # salida del comando (COMPLETADO)
    mensaje_error: str = None   # motivo (FALLIDO)
    recursos: tuple = None      # (nodos, cpus_por_nodo, memoria_gb, tiempo_max_min): solo el simulador

    @property
    def activo(self):
        return self.estado in (EN_COLA, EJECUTANDO)

    @property
    def id_corto(self):
        """job-api usa UUID: en pantalla basta con el principio."""
        return self.id[:8]


@dataclass
class EstadoCluster:
    nodos_activos: int
    nodos_totales: int
    uso_cpu: float
    uso_gpu: float
    trabajos_en_cola: int


def _epoch_iso(texto):
    """"2026-10-11T03:40:17.7169415Z" -> segundos epoch (UTC)."""
    if not texto:
        return 0.0
    try:
        base = time.strptime(texto[:19], "%Y-%m-%dT%H:%M:%S")
        fraccion = "".join(ch for ch in texto[20:] if ch.isdigit())[:6]
        return calendar.timegm(base) + (int(fraccion) / 10 ** len(fraccion) if fraccion else 0.0)
    except ValueError:
        return 0.0


class HpcRepository:
    """job-api real."""

    simulado = False

    def __init__(self, rest):
        self.rest = rest

    def enviar_trabajo(self, solicitud):
        r = self.rest.post_json("/jobs", {"nombre": solicitud.nombre, "comando": solicitud.comando,
                                          "prioridad": solicitud.prioridad}) or {}
        return self._a_trabajo(self.rest.get_json(f"/jobs/{r.get('id')}") or {})

    def consultar_trabajos(self):
        trabajos = [self._a_trabajo(d) for d in (self.rest.get_json("/jobs") or [])]
        return sorted(trabajos, key=lambda t: t.enviado_en, reverse=True)

    def cancelar(self, trabajo_id):
        self.rest.delete(f"/jobs/{trabajo_id}")

    def consultar_todo(self):
        """(estado del clúster, trabajos). job-api aún no informa el clúster: None."""
        return None, self.consultar_trabajos()

    @staticmethod
    def _a_trabajo(d):
        return TrabajoHpc(
            id=str(d.get("id", "")), nombre=d.get("nombre", ""), comando=d.get("comando", ""),
            prioridad=int(d.get("prioridad") or 5),
            estado=_ESTADOS_API.get(d.get("estado"), FALLIDO), progreso=None,
            enviado_en=_epoch_iso(d.get("fechaCreacion")),
            resultado=d.get("resultado"), mensaje_error=d.get("mensajeError"))


@dataclass
class _Registro:
    id: str
    solicitud: SolicitudTrabajo
    recursos: tuple
    enviado_en: float
    espera_en_cola: float
    duracion: float
    falla: bool
    cancelado: bool = False


class SimuladorHpc:
    """Modo demostración: mismas operaciones sin servidor."""

    simulado = True

    def __init__(self):
        self._lock = threading.Lock()
        self._siguiente = 1043
        ahora = time.time()
        S = SolicitudTrabajo
        self._registros = [
            _Registro("1039", S("Dinámica molecular · proteína 4HHB", "gromacs mdrun -deffnm md_4hhb", 7),
                      (4, 32, 64, 240), ahora - 3 * HORA, 20, 2 * HORA, False),
            _Registro("1040", S("Entrenamiento CNN · imágenes satelitales", "python train.py --epochs 50 --gpu", 5),
                      (2, 16, 32, 120), ahora - HORA, 10, 25 * MIN, True),
            _Registro("1041", S("Simulación CFD · túnel de viento", "mpirun -np 64 ./openfoam_run.sh", 8),
                      (2, 32, 64, 180), ahora - 40, 5, 150, False),
            _Registro("1042", S("Análisis genómico · lote 12", "snakemake --cores 16 -s pipeline.smk", 3),
                      (1, 16, 32, 60), ahora - 2, 25, 90, False),
        ]

    def enviar_trabajo(self, solicitud):
        time.sleep(0.7)  # latencia de red simulada
        with self._lock:
            r = _Registro(str(self._siguiente), solicitud, (1, 16, 32, 60), time.time(),
                          random.uniform(5, 12), random.uniform(45, 90), False)
            self._siguiente += 1
            self._registros.append(r)
        return self._a_trabajo(r, time.time())

    def consultar_trabajos(self):
        time.sleep(0.25)
        ahora = time.time()
        with self._lock:
            trabajos = [self._a_trabajo(r, ahora) for r in self._registros]
        return sorted(trabajos, key=lambda t: t.enviado_en, reverse=True)

    def cancelar(self, trabajo_id):
        with self._lock:
            for r in self._registros:
                if r.id == trabajo_id:
                    r.cancelado = True

    def consultar_todo(self):
        trabajos = self.consultar_trabajos()
        propios = sum(t.recursos[0] for t in trabajos if t.estado == EJECUTANDO and t.recursos)
        t = time.time() / 20.0
        activos = min(propios + int(7 + 2 * math.sin(t)), NODOS_TOTALES)
        cluster = EstadoCluster(
            nodos_activos=activos, nodos_totales=NODOS_TOTALES,
            uso_cpu=max(0.0, min(1.0, activos / NODOS_TOTALES * 0.92)),
            uso_gpu=max(0.0, min(1.0, 0.45 + 0.2 * math.sin(t * 1.7))),
            trabajos_en_cola=3 + sum(1 for x in trabajos if x.estado == EN_COLA))
        return cluster, trabajos

    @staticmethod
    def _a_trabajo(r, ahora):
        en_ejecucion = (ahora - r.enviado_en) - r.espera_en_cola
        if r.cancelado:
            estado, progreso = CANCELADO, 0.0
        elif en_ejecucion < 0:
            estado, progreso = EN_COLA, 0.0
        elif en_ejecucion < r.duracion:
            estado, progreso = EJECUTANDO, en_ejecucion / r.duracion
        else:
            estado, progreso = (FALLIDO if r.falla else COMPLETADO), 1.0
        s = r.solicitud
        return TrabajoHpc(r.id, s.nombre, s.comando, s.prioridad, estado, progreso, r.enviado_en,
                          resultado="Terminado sin errores" if estado == COMPLETADO else None,
                          mensaje_error="Código de salida 1: memoria insuficiente" if estado == FALLIDO else None,
                          recursos=r.recursos)
