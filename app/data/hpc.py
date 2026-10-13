# -*- coding: utf-8 -*-
"""HPC Service (Contrato_HPC). Equivale a data/hpc/HpcRepository.kt del móvil.

El contrato habla RMI, que solo existe en la JVM. El escritorio (como el móvil
y el portal) habla REST con **job-api**, la fachada HTTP del gestor RMI
(repositorio RMIUPBCientifica, puerto 8082):

    POST   /jobs                 {nombreTrabajo, rutaCodigo, rutaDataset, numeroProcesos,
                                  tiempoMaximoEjecucion, prioridad, parametrosEjecucion}
    GET    /jobs                 trabajos del usuario del token
    GET    /jobs/{id}/logs       salida estándar y de error
    DELETE /jobs/{id}            cancelar
    POST   /jobs/{id}/reintento  reintentar un trabajo fallido
    GET    /cluster/estado       nodos de la malla, procesos en uso, cola

El trabajo es CÓDIGO FUENTE y DATASET del Home del usuario (no un comando de
shell): `subir_al_home` deja el archivo elegido en "Trabajos HPC/" y devuelve
su ruta. El resultado vuelve al Home, en "Resultados HPC/<nombre>-<id>".

ANTES se enviaba {nombre, comando, prioridad 1-10} y el gestor ejecutaba el
comando con bash en su propia máquina, sin MPI.

`SimuladorHpc` (modo demostración) imita las mismas operaciones sin servidor.
"""

import calendar
import os
import threading
import time
from dataclasses import dataclass, field

PENDIENTE = "PENDIENTE"
EN_COLA = "EN_COLA"
EJECUTANDO = "EJECUTANDO"
COMPLETADO = "COMPLETADO"
GUARDANDO = "COMPLETADO_PENDIENTE_ALMACENAMIENTO"
FALLIDO = "FALLIDO"
TIMEOUT = "FALLIDO_TIMEOUT"
CANCELADO = "CANCELADO"
ACTIVOS = (PENDIENTE, EN_COLA, EJECUTANDO, GUARDANDO)
PRIORIDADES = ("BAJA", "NORMAL", "ALTA")
CARPETA_TRABAJOS = "Trabajos HPC"
MIN = 60


@dataclass
class SolicitudTrabajo:
    """Campos de EnviarTrabajo (Contrato_HPC §3.1)."""
    nombre: str
    ruta_codigo: str
    ruta_dataset: str = ""
    procesos: int = 4
    tiempo_maximo_s: int = 600
    prioridad: str = "NORMAL"
    parametros: dict = field(default_factory=dict)

    def a_json(self):
        return {"nombreTrabajo": self.nombre, "rutaCodigo": self.ruta_codigo,
                "rutaDataset": self.ruta_dataset or None, "numeroProcesos": self.procesos,
                "tiempoMaximoEjecucion": self.tiempo_maximo_s, "prioridad": self.prioridad,
                "parametrosEjecucion": self.parametros}


@dataclass
class TrabajoHpc:
    id: str
    nombre: str
    ruta_codigo: str
    ruta_dataset: str
    procesos: int
    tiempo_maximo_s: int
    prioridad: str
    estado: str
    enviado_en: float               # epoch en segundos
    posicion_cola: int = 0
    nodos: tuple = ()
    ruta_resultado: str = None      # carpeta del Home con la salida
    incompleto: bool = False        # salida parcial de un FALLIDO_TIMEOUT
    mensaje_error: str = None
    codigo_salida: int = None
    original_id: str = None         # si es un reintento

    @property
    def activo(self):
        return self.estado in ACTIVOS

    @property
    def reintentable(self):
        return self.estado in (FALLIDO, TIMEOUT)

    @property
    def con_logs(self):
        return self.estado not in (PENDIENTE, EN_COLA)

    @property
    def id_corto(self):
        """job-api usa UUID: en pantalla basta con el principio."""
        return self.id[:8]


@dataclass
class EstadoCluster:
    """ObtenerEstadoCluster + ObtenerEstadoCola (Contrato_HPC §3.9)."""
    nodos_totales: int
    nodos_disponibles: int
    nodos_en_falla: int
    procesos_totales: int
    procesos_en_uso: int
    trabajos_en_cola: int
    trabajos_ejecutando: int
    espera_promedio_s: int
    ejecutor_conectado: bool
    nodos: list                     # [(id, estado, capacidad, carga, origen)]

    @property
    def uso(self):
        return self.procesos_en_uso / self.procesos_totales if self.procesos_totales else 0.0


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
    """job-api real. `storage` (StorageRepository) sube el código al Home."""

    simulado = False

    def __init__(self, rest, storage=None):
        self.rest = rest
        self.storage = storage

    def subir_al_home(self, ruta_local):
        """Sube un archivo del PC a "Trabajos HPC/" del Home y devuelve su ruta en el Home."""
        carpeta = next((a for a in self.storage.listar() if a.es_directorio and a.nombre == CARPETA_TRABAJOS), None)
        if carpeta is None:
            carpeta = self.storage.crear_carpeta(CARPETA_TRABAJOS)
        self.storage.subir(ruta_local, carpeta.id, sobrescribir=True)
        return f"/{CARPETA_TRABAJOS}/{os.path.basename(ruta_local)}"

    def enviar_trabajo(self, solicitud):
        r = self.rest.post_json("/jobs", solicitud.a_json()) or {}
        return self._a_trabajo(self.rest.get_json(f"/jobs/{r.get('trabajoId')}") or {})

    def consultar_trabajos(self):
        trabajos = [self._a_trabajo(d) for d in (self.rest.get_json("/jobs") or [])]
        return sorted(trabajos, key=lambda t: t.enviado_en, reverse=True)

    def consultar_todo(self):
        """(estado del clúster, trabajos)."""
        return self._a_cluster(self.rest.get_json("/cluster/estado") or {}), self.consultar_trabajos()

    def cancelar(self, trabajo_id):
        self.rest.delete(f"/jobs/{trabajo_id}")

    def reintentar(self, trabajo_id):
        r = self.rest.post_json(f"/jobs/{trabajo_id}/reintento", {}) or {}
        return r.get("trabajoId"), r.get("advertencia")

    def logs(self, trabajo_id):
        return (self.rest.get_json(f"/jobs/{trabajo_id}/logs") or {}).get("logsEjecucion") or ""

    @staticmethod
    def _a_trabajo(d):
        return TrabajoHpc(
            id=str(d.get("id", "")), nombre=d.get("nombreTrabajo", ""),
            ruta_codigo=d.get("rutaCodigo") or "", ruta_dataset=d.get("rutaDataset") or "",
            procesos=int(d.get("numeroProcesos") or 1), tiempo_maximo_s=int(d.get("tiempoMaximoEjecucion") or 0),
            prioridad=d.get("prioridad") or "NORMAL", estado=d.get("estado") or FALLIDO,
            enviado_en=_epoch_iso(d.get("fechaEnvio")), posicion_cola=int(d.get("posicionCola") or 0),
            nodos=tuple(d.get("nodosAsignados") or ()), ruta_resultado=d.get("rutaResultado"),
            incompleto=bool(d.get("resultadoIncompleto")), mensaje_error=d.get("mensajeError"),
            codigo_salida=d.get("codigoSalida"), original_id=d.get("trabajoOriginalId"))

    @staticmethod
    def _a_cluster(d):
        return EstadoCluster(
            nodos_totales=int(d.get("nodosTotales") or 0), nodos_disponibles=int(d.get("nodosDisponibles") or 0),
            nodos_en_falla=int(d.get("nodosEnFalla") or 0), procesos_totales=int(d.get("procesosTotales") or 0),
            procesos_en_uso=int(d.get("procesosEnUso") or 0), trabajos_en_cola=int(d.get("trabajosEnCola") or 0),
            trabajos_ejecutando=int(d.get("trabajosEjecutando") or 0),
            espera_promedio_s=int(d.get("tiempoEsperaPromedioEstimadoSegundos") or 0),
            ejecutor_conectado=bool(d.get("ejecutorConectado")),
            nodos=[(n.get("id"), n.get("estado"), n.get("capacidadProcesos"), n.get("cargaActual"), n.get("origen"))
                   for n in d.get("nodos") or []])


@dataclass
class _Registro:
    trabajo: TrabajoHpc
    espera: float
    duracion: float
    falla: bool = False


class SimuladorHpc:
    """Modo demostración: mismas operaciones sin servidor. El estado avanza con el tiempo."""

    simulado = True
    PROCESOS = 16

    def __init__(self):
        self._lock = threading.Lock()
        self._n = 1043
        ahora = time.time()
        self._registros = [
            _Registro(self._nuevo("Dinámica molecular · 4HHB", "/Proyectos/md.c", "/Proyectos/4hhb.pdb", 8, ahora - 3 * 3600),
                      20, 7200),
            _Registro(self._nuevo("Monte Carlo · π", "/Proyectos/pi.c", "", 4, ahora - 3600), 10, 600, True),
            _Registro(self._nuevo("Simulación CFD · túnel de viento", "/Proyectos/cfd.cpp", "/Datos/malla.dat", 8,
                                  ahora - 40), 5, 150),
            _Registro(self._nuevo("Análisis genómico · lote 12", "/Proyectos/genoma.py", "/Datos/lote12.csv", 4,
                                  ahora - 2), 25, 90),
        ]

    def _nuevo(self, nombre, codigo, dataset, procesos, enviado, prioridad="NORMAL", tiempo=3600):
        self._n += 1
        return TrabajoHpc(str(self._n) + "-demo", nombre, codigo, dataset, procesos, tiempo, prioridad, EN_COLA, enviado)

    def subir_al_home(self, ruta_local):
        return f"/{CARPETA_TRABAJOS}/{os.path.basename(ruta_local)}"

    def enviar_trabajo(self, solicitud):
        time.sleep(0.6)
        with self._lock:
            t = self._nuevo(solicitud.nombre, solicitud.ruta_codigo, solicitud.ruta_dataset, solicitud.procesos,
                            time.time(), solicitud.prioridad, solicitud.tiempo_maximo_s)
            self._registros.append(_Registro(t, 6, 45))
        return self._avanzar(self._registros[-1], time.time())

    def consultar_trabajos(self):
        time.sleep(0.2)
        ahora = time.time()
        with self._lock:
            trabajos = [self._avanzar(r, ahora) for r in self._registros]
        return sorted(trabajos, key=lambda t: t.enviado_en, reverse=True)

    def consultar_todo(self):
        trabajos = self.consultar_trabajos()
        en_uso = min(self.PROCESOS, sum(t.procesos for t in trabajos if t.estado == EJECUTANDO))
        nodos = [(f"hpc-worker{i}", "OCUPADO" if en_uso > (i - 1) * 4 + 3 else "DISPONIBLE", 4,
                  max(0, min(4, en_uso - (i - 1) * 4)), "LABORATORIO") for i in range(1, 5)]
        return EstadoCluster(4, sum(1 for n in nodos if n[1] == "DISPONIBLE"), 0, self.PROCESOS, en_uso,
                             sum(1 for t in trabajos if t.estado == EN_COLA),
                             sum(1 for t in trabajos if t.estado == EJECUTANDO), 8, True, nodos), trabajos

    def cancelar(self, trabajo_id):
        with self._lock:
            for r in self._registros:
                if r.trabajo.id == trabajo_id:
                    r.trabajo.estado = CANCELADO

    def reintentar(self, trabajo_id):
        with self._lock:
            o = next(r.trabajo for r in self._registros if r.trabajo.id == trabajo_id)
            t = self._nuevo(o.nombre, o.ruta_codigo, o.ruta_dataset, o.procesos, time.time(), o.prioridad)
            t.original_id = o.id
            self._registros.append(_Registro(t, 4, 40))
        return t.id, "El reintento usa la versión actual del código."

    def logs(self, trabajo_id):
        return "=== salida estándar ===\nrango 0/4: listo\nrango 1/4: listo\nrango 2/4: listo\nrango 3/4: listo\n"

    @staticmethod
    def _avanzar(r, ahora):
        t = r.trabajo
        if t.estado == CANCELADO:
            return t
        transcurrido = ahora - t.enviado_en - r.espera
        if transcurrido < 0:
            t.estado = EN_COLA
        elif transcurrido < r.duracion:
            t.estado, t.nodos = EJECUTANDO, ("hpc-worker1", "hpc-worker2")
        elif r.falla:
            t.estado, t.mensaje_error, t.codigo_salida = FALLIDO, "mpirun terminó con código 1", 1
        else:
            t.estado = COMPLETADO
            t.ruta_resultado = f"/Resultados HPC/{t.nombre.split(' ')[0]}-{t.id_corto}"
        return t
