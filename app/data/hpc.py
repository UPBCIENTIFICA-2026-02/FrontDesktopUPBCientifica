# -*- coding: utf-8 -*-
"""HPC Service. Equivale a data/hpc/HpcRepository.kt del móvil.

⚠️ RMI BLOQUEADO: el contrato (Contrato_HPC) exige RMI, que solo existe en la
JVM (ni Python ni Android lo tienen). Decisión pendiente con Dev C: que HPC
exponga también gRPC/REST para clientes no-JVM.

Para que la interfaz quede lista, este repositorio SIMULA las tres operaciones
del contrato con la misma forma que tendrán:
    EnviarTrabajo          -> enviar_trabajo
    ConsultarEstadoTrabajo -> consultar_trabajos
    ObtenerEstadoCluster   -> estado_cluster

El estado de cada trabajo se deduce del tiempo transcurrido desde que se envió
(en cola unos segundos, luego ejecutando, luego terminado), así que la pantalla
"ve avanzar" los trabajos al consultar periódicamente, igual que hará con el
servicio real. Cuando se defina el protocolo, solo cambia el cuerpo de estas
funciones.
"""

import math
import random
import threading
import time
from dataclasses import dataclass

EN_COLA, EJECUTANDO, COMPLETADO, FALLIDO = "EN_COLA", "EJECUTANDO", "COMPLETADO", "FALLIDO"
NODOS_TOTALES = 16
MIN = 60
HORA = 60 * MIN


@dataclass
class SolicitudTrabajo:
    nombre: str
    comando: str
    nodos: int
    cpus_por_nodo: int
    memoria_gb: int
    tiempo_maximo_min: int


@dataclass
class TrabajoHpc:
    id: str
    nombre: str
    comando: str
    nodos: int
    cpus_por_nodo: int
    memoria_gb: int
    tiempo_maximo_min: int
    estado: str
    progreso: float          # 0..1; solo tiene sentido en EJECUTANDO
    enviado_en: float        # epoch en segundos

    @property
    def activo(self):
        return self.estado in (EN_COLA, EJECUTANDO)


@dataclass
class EstadoCluster:
    nodos_activos: int
    nodos_totales: int
    uso_cpu: float
    uso_gpu: float
    trabajos_en_cola: int


@dataclass
class _Registro:
    id: str
    solicitud: SolicitudTrabajo
    enviado_en: float
    espera_en_cola: float
    duracion: float
    falla: bool


class HpcRepository:
    def __init__(self):
        self._lock = threading.Lock()
        self._siguiente = 1043
        ahora = time.time()
        S = SolicitudTrabajo
        self._registros = [
            _Registro("1039", S("Dinámica molecular · proteína 4HHB", "gromacs mdrun -deffnm md_4hhb",
                                4, 32, 64, 240), ahora - 3 * HORA, 20, 2 * HORA, False),
            _Registro("1040", S("Entrenamiento CNN · imágenes satelitales", "python train.py --epochs 50 --gpu",
                                2, 16, 32, 120), ahora - HORA, 10, 25 * MIN, True),
            _Registro("1041", S("Simulación CFD · túnel de viento", "mpirun -np 64 ./openfoam_run.sh",
                                2, 32, 64, 180), ahora - 40, 5, 150, False),
            _Registro("1042", S("Análisis genómico · lote 12", "snakemake --cores 16 -s pipeline.smk",
                                1, 16, 32, 60), ahora - 2, 25, 90, False),
        ]

    def enviar_trabajo(self, solicitud):
        time.sleep(0.7)  # latencia de red simulada
        with self._lock:
            r = _Registro(str(self._siguiente), solicitud, time.time(),
                          random.uniform(5, 12), random.uniform(45, 90), False)
            self._siguiente += 1
            self._registros.append(r)
        return self._a_trabajo(r, time.time())

    def consultar_trabajos(self):
        """Más recientes primero."""
        time.sleep(0.25)
        ahora = time.time()
        with self._lock:
            trabajos = [self._a_trabajo(r, ahora) for r in self._registros]
        return sorted(trabajos, key=lambda t: t.enviado_en, reverse=True)

    def estado_cluster(self, trabajos=None):
        trabajos = trabajos if trabajos is not None else self.consultar_trabajos()
        propios = sum(t.nodos for t in trabajos if t.estado == EJECUTANDO)
        t = time.time() / 20.0
        ajenos = int(7 + 2 * math.sin(t))          # carga de otros usuarios
        activos = min(propios + ajenos, NODOS_TOTALES)
        return EstadoCluster(
            nodos_activos=activos,
            nodos_totales=NODOS_TOTALES,
            uso_cpu=max(0.0, min(1.0, activos / NODOS_TOTALES * 0.92)),
            uso_gpu=max(0.0, min(1.0, 0.45 + 0.2 * math.sin(t * 1.7))),
            trabajos_en_cola=3 + sum(1 for x in trabajos if x.estado == EN_COLA),
        )

    def consultar_todo(self):
        """Clúster + trabajos en una sola llamada (lo que pinta la pantalla)."""
        trabajos = self.consultar_trabajos()
        return self.estado_cluster(trabajos), trabajos

    @staticmethod
    def _a_trabajo(r, ahora):
        en_ejecucion = (ahora - r.enviado_en) - r.espera_en_cola
        if en_ejecucion < 0:
            estado, progreso = EN_COLA, 0.0
        elif en_ejecucion < r.duracion:
            estado, progreso = EJECUTANDO, en_ejecucion / r.duracion
        else:
            estado, progreso = (FALLIDO if r.falla else COMPLETADO), 1.0
        s = r.solicitud
        return TrabajoHpc(r.id, s.nombre, s.comando, s.nodos, s.cpus_por_nodo, s.memoria_gb,
                          s.tiempo_maximo_min, estado, progreso, r.enviado_en)
