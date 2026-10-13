# -*- coding: utf-8 -*-
"""File Sync. Equivale a data/filesync/ del móvil (FileSyncRepository.kt y
MotorSincronizacion.kt).

Una carpeta local del PC se respalda de forma síncrona en una carpeta del Home
(node-sync, gRPC 9090). node-sync guarda a través de Distributed Storage, así
que lo sincronizado aparece en "Mis archivos", cuenta para la cuota y queda
versionado.

ANTES este módulo SIMULABA el ciclo (progreso aleatorio) porque faltaba el stub
gRPC. AHORA los stubs están en network/filesync_pb y la sincronización es real:

  1. Recorre la carpeta y calcula el SHA-256 de cada archivo (con caché por
     tamaño+fecha para no releer lo que no cambió).
  2. IniciarSync con cada archivo, su hash y su hash BASE (el de la última
     sincronización correcta), más los que se borraron desde entonces. El
     SERVIDOR decide qué hacer; el cliente no reimplementa las reglas.
  3. Aplica las acciones: subir, bajar, borrar aquí, borrar allá, o CONFLICTO
     -> MANTENER_AMBOS (la copia local se renombra y sube, y se baja la del
     servidor). Nunca se descarta contenido en silencio.
  4. Guarda la nueva base. Si se corta a mitad, lo hecho queda registrado.

Programación (ProgramarSincronizacion): manual, al conectarse a la red del
servidor, cada hora o diaria a una hora. La ejecuta este mismo cliente mientras
está abierto con la sesión iniciada (el token vive solo en memoria, ver
session/token_manager.py). El servidor saca el usuario del token, nunca del
mensaje.
"""

import hashlib
import json
import os
import socket
import tempfile
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

import grpc

from ..config import CONFIG_DIR
from ..network.filesync_pb import filesync_pb2 as pb
from ..network.filesync_pb import filesync_pb2_grpc as pb_grpc

# --- Estados que pinta la interfaz (indicador superior, Inicio y la vista) ----


class SinConfigurar:
    """Aún no se eligió qué carpeta del PC respaldar."""


@dataclass
class Sincronizando:
    progreso: float      # 0..1
    pendientes: int      # cambios que faltan
    detalle: str = ""


@dataclass
class AlDia:
    ultima_sincronizacion: float     # 0 = nunca
    conflictos: int = 0


class SinConexion:
    """No se alcanza node-sync: se reintenta al volver a la red del servidor."""


@dataclass
class ErrorSync:
    mensaje: str
    ultima_sincronizacion: float = 0


SIN_CONFIGURAR = SinConfigurar()
SIN_CONEXION = SinConexion()

# --- Programación ------------------------------------------------------------
MANUAL = "MANUAL"
AL_CONECTAR = "AL_CONECTAR"
CADA_HORA = "CADA_HORA"
DIARIA = "DIARIA"

# modoDisparo del contrato para cada programación
_MODO = {MANUAL: "MANUAL", AL_CONECTAR: "AUTOMATICO_AL_CONECTAR", CADA_HORA: "PROGRAMADO", DIARIA: "PROGRAMADO"}


def carpeta_remota_por_defecto():
    return f"Respaldo {socket.gethostname()}".strip()


@dataclass
class ConfigSync:
    carpeta: str = ""                        # carpeta local del PC
    carpeta_remota: str = field(default_factory=carpeta_remota_por_defecto)
    programacion: str = MANUAL
    hora: int = 22
    minuto: int = 0
    base: dict = field(default_factory=dict)      # ruta en el Home -> hash en la última sync
    huellas: dict = field(default_factory=dict)   # ruta local -> [tamaño, mtime_ns, hash]
    ultima_sync: float = 0
    ultimo_resumen: dict = None


class AlmacenSync:
    """Configuración y manifiesto por usuario: ~/.upbcientifica/filesync/<uid>.json."""

    def __init__(self, directorio=None):
        self.dir = Path(directorio or CONFIG_DIR / "filesync")
        self._lock = threading.Lock()

    def _archivo(self, uid):
        seguro = "".join(c if c.isalnum() or c in "._-" else "_" for c in uid)
        return self.dir / f"{seguro}.json"

    def cargar(self, uid):
        with self._lock:
            try:
                datos = json.loads(self._archivo(uid).read_text(encoding="utf-8"))
                conocidos = {k: v for k, v in datos.items() if k in ConfigSync.__dataclass_fields__}
                return ConfigSync(**conocidos)
            except (OSError, ValueError, TypeError):
                return ConfigSync()

    def guardar(self, uid, config):
        with self._lock:
            self.dir.mkdir(parents=True, exist_ok=True)
            destino = self._archivo(uid)
            tmp = destino.with_suffix(".tmp")
            tmp.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, destino)


# --- Errores ---------------------------------------------------------------------


class SyncAbortada(Exception):
    """Fallo que detiene toda la sincronización (no solo un archivo)."""

    def __init__(self, mensaje, sin_red=False):
        super().__init__(mensaje)
        self.sin_red = sin_red


def _traducir(e):
    """grpc.RpcError -> excepción con un mensaje para el usuario."""
    codigo = e.code()
    if codigo in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED):
        return SyncAbortada("No se alcanza el servidor de sincronización (node-sync)", sin_red=True)
    if codigo == grpc.StatusCode.UNAUTHENTICATED:
        return SyncAbortada("Tu sesión ya no es válida. Vuelve a iniciar sesión para sincronizar.")
    if codigo == grpc.StatusCode.RESOURCE_EXHAUSTED:
        return SyncAbortada("No queda espacio en tu cuota de almacenamiento")
    return OSError(e.details() or codigo.name)


IGNORAR_SUFIJOS = (".tmp", "~", ".part", ".crdownload")


def _ignorar(nombre):
    """Ocultos, temporales y archivos de sistema: no son datos del usuario y
    cambian solos, lo que provocaría subidas sin fin."""
    n = nombre.lower()
    return nombre.startswith((".", "~$")) or n.endswith(IGNORAR_SUFIJOS) or n in ("desktop.ini", "thumbs.db")


def _sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


TROZO = 256 * 1024


# --- Motor -------------------------------------------------------------------------


class MotorSincronizacion:
    def __init__(self, direccion, token, ca=None):
        # Con `ca` (PEM de la CA que firma a node-sync) el canal va por TLS, como
        # en el laboratorio; sin ella, en claro (syncd local de desarrollo).
        if ca:
            with open(ca, "rb") as f:
                self.canal = grpc.secure_channel(direccion, grpc.ssl_channel_credentials(f.read()))
        else:
            self.canal = grpc.insecure_channel(direccion)
        self.stub = pb_grpc.FileSyncStub(self.canal)
        self.md = [("authorization", f"Bearer {token}")]

    def cerrar(self):
        self.canal.close()

    def alcanzable(self):
        """El servidor responde en pocos segundos (o rechaza el token: está ahí)."""
        try:
            self.stub.EstadoSync(pb.EstadoRequest(dispositivo=socket.gethostname()), metadata=self.md, timeout=4)
            return True
        except grpc.RpcError as e:
            return e.code() == grpc.StatusCode.UNAUTHENTICATED

    def sincronizar(self, config, modo, progreso):
        """Ejecuta una sincronización y devuelve el resumen. Actualiza
        config.base y config.huellas con lo hecho (aunque falle a mitad)."""
        local = Path(config.carpeta)
        if not local.is_dir():
            raise SyncAbortada(f"La carpeta local no existe: {config.carpeta}")
        remota = config.carpeta_remota.strip("/ ")

        def a_local(ruta):
            return local.joinpath(*ruta[len(remota) + 1:].split("/"))

        # --- 1. Estado local, con la caché de hashes ---------------------------
        progreso(Sincronizando(0, 0, "Revisando la carpeta local"))
        locales, huellas = {}, {}
        for raiz, dirs, archivos in os.walk(local):
            dirs[:] = [d for d in dirs if not _ignorar(d)]
            for nombre in archivos:
                if _ignorar(nombre):
                    continue
                p = Path(raiz, nombre)
                rel = p.relative_to(local).as_posix()
                try:
                    st = p.stat()
                    previa = config.huellas.get(rel)
                    if previa and previa[0] == st.st_size and previa[1] == st.st_mtime_ns:
                        h = previa[2]
                    else:
                        h = _sha256(p)
                except OSError:
                    continue        # bloqueado por otro programa: entra en la próxima
                huellas[rel] = [st.st_size, st.st_mtime_ns, h]
                locales[f"{remota}/{rel}"] = h

        base = {r: h for r, h in config.base.items() if r.startswith(remota + "/")}
        metas = [pb.FileMeta(ruta=r, hash=h, hash_base=base.get(r, "")) for r, h in locales.items()]
        metas += [pb.FileMeta(ruta=r, hash_base=h, eliminado=True) for r, h in base.items() if r not in locales]

        # --- 2. El servidor decide -------------------------------------------
        try:
            resp = self.stub.IniciarSync(
                pb.SyncRequest(dispositivo=socket.gethostname(), carpeta=remota, archivos=metas,
                               modo_disparo=_MODO.get(modo, "MANUAL")),
                metadata=self.md, timeout=60)
        except grpc.RpcError as e:
            raise _traducir(e) from e

        pendientes = [a for a in resp.acciones if a.accion != pb.IGUAL]
        for a in resp.acciones:
            if a.accion == pb.IGUAL:
                base[a.ruta] = a.hash_servidor

        eventos = []
        cuenta = {"subidos": 0, "bajados": 0, "borrados": 0, "conflictos": 0, "errores": 0}
        try:
            # --- 3. Aplicar ----------------------------------------------------
            for i, a in enumerate(pendientes):
                progreso(Sincronizando(i / len(pendientes), len(pendientes) - i, a.ruta.rsplit("/", 1)[-1]))
                try:
                    if a.accion == pb.SUBIR:
                        self._subir(a.ruta, a_local(a.ruta))
                        base[a.ruta] = locales[a.ruta]
                        cuenta["subidos"] += 1
                        eventos.append((a.ruta, "SUBIDO", None))
                    elif a.accion == pb.BAJAR:
                        self._bajar(a, a_local(a.ruta))
                        base[a.ruta] = a.hash_servidor
                        cuenta["bajados"] += 1
                        eventos.append((a.ruta, "BAJADO", None))
                    elif a.accion == pb.BORRAR:
                        try:
                            a_local(a.ruta).unlink()
                        except FileNotFoundError:
                            pass
                        base.pop(a.ruta, None)
                        cuenta["borrados"] += 1
                        eventos.append((a.ruta, "BORRADO_LOCAL", None))
                    elif a.accion == pb.BORRAR_SERVIDOR:
                        try:
                            self.stub.EliminarArchivo(pb.EliminarRequest(ruta=a.ruta), metadata=self.md, timeout=60)
                        except grpc.RpcError as e:
                            if e.code() != grpc.StatusCode.NOT_FOUND:
                                raise _traducir(e) from e
                        base.pop(a.ruta, None)
                        cuenta["borrados"] += 1
                        eventos.append((a.ruta, "BORRADO_SERVIDOR", None))
                    elif a.accion == pb.CONFLICTO:
                        # MANTENER_AMBOS: la copia local pasa a ser la "copia de conflicto".
                        actual = a_local(a.ruta)
                        if actual.exists():
                            copia = a_local(a.ruta_conflicto)
                            os.replace(actual, copia)
                            self._subir(a.ruta_conflicto, copia)
                            base[a.ruta_conflicto] = _sha256(copia)
                        self._bajar(a, actual)
                        base[a.ruta] = a.hash_servidor
                        cuenta["conflictos"] += 1
                        eventos.append((a.ruta, "CONFLICTO", a.ruta_conflicto.rsplit("/", 1)[-1]))
                except SyncAbortada:
                    raise
                except Exception as e:  # noqa: BLE001 — un archivo no detiene a los demás
                    cuenta["errores"] += 1
                    eventos.append((a.ruta, "ERROR", str(e) or type(e).__name__))
            progreso(Sincronizando(1, 0, "Terminando"))
        finally:
            # --- 4. Lo hecho queda registrado aunque se haya cortado -----------
            vivos = {r: h for r, h in base.items() if r in locales or a_local(r).exists()}
            config.base = {**{r: h for r, h in config.base.items() if not r.startswith(remota + "/")}, **vivos}
            tocados = {a_local(r).relative_to(local).as_posix() for r, t, _ in eventos if t != "SUBIDO"}
            config.huellas = {r: v for r, v in huellas.items() if r not in tocados}

        return {"fecha": time.time(), "modo": modo, **cuenta,
                "eventos": [{"ruta": r, "tipo": t, "detalle": d} for r, t, d in eventos[-100:]]}

    def _subir(self, ruta, archivo):
        def trozos():
            with open(archivo, "rb") as f:
                primero = True
                while True:
                    b = f.read(TROZO)
                    if not b and not primero:
                        return
                    yield pb.FileChunk(ruta=ruta if primero else "", contenido=b)
                    primero = False
                    if not b:
                        return     # archivo vacío: basta con la ruta
        try:
            self.stub.SubirArchivo(trozos(), metadata=self.md, timeout=3600)
        except grpc.RpcError as e:
            raise _traducir(e) from e

    def _bajar(self, accion, destino):
        """Descarga a un temporal en la misma carpeta, verifica el SHA-256 y
        solo entonces reemplaza: un corte nunca deja el archivo a medias."""
        destino.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".sync-", suffix=".part", dir=destino.parent)
        try:
            h = hashlib.sha256()
            with os.fdopen(fd, "wb") as f:
                try:
                    for ch in self.stub.DescargarArchivo(pb.DownloadRequest(ruta=accion.ruta),
                                                         metadata=self.md, timeout=3600):
                        f.write(ch.contenido)
                        h.update(ch.contenido)
                except grpc.RpcError as e:
                    raise _traducir(e) from e
            if accion.hash_servidor and h.hexdigest() != accion.hash_servidor:
                raise OSError("cambió en el servidor durante la descarga; se reintentará (SYNC-006)")
            os.replace(tmp, destino)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


# --- Repositorio (lo usa la interfaz) ---------------------------------------------


class FileSyncRepository:
    """Estado compartido de File Sync y su programación.

    La sincronización corre en un hilo; la interfaz consulta `estado` con
    `after` (Tk no es seguro entre hilos) y llama a `revisar_programacion()`
    periódicamente para que se disparen las automáticas. Nunca corren dos a la
    vez (contrato: la siguiente programada espera a que termine la actual).
    """

    def __init__(self, tokens, direccion, almacen=None):
        self.tokens = tokens
        self.direccion = direccion
        self.ca_tls = None  # PEM de la CA de node-sync; None = canal en claro
        self.almacen = almacen or AlmacenSync()
        self.uid = None
        self.config = ConfigSync()
        self.estado = SIN_CONFIGURAR
        self._hilo = None
        self._lock = threading.Lock()
        self._servidor_visible = None     # para detectar la llegada a la red del servidor
        self._ultima_revision_red = 0

    # --- Sesión --------------------------------------------------------------
    def iniciar_sesion(self, uid, direccion=None):
        self.uid = uid
        if direccion:
            self.direccion = direccion
        self.config = self.almacen.cargar(uid)
        self._servidor_visible = None
        self._ultima_revision_red = 0
        self.estado = self._estado_en_reposo()

    def cerrar_sesion(self):
        self.uid = None
        self.config = ConfigSync()
        self.estado = SIN_CONFIGURAR

    @property
    def ocupado(self):
        return self._hilo is not None and self._hilo.is_alive()

    def _estado_en_reposo(self):
        c = self.config
        error = (c.ultimo_resumen or {}).get("mensaje_error")
        if not c.carpeta:
            return SIN_CONFIGURAR
        if error:
            return ErrorSync(error, c.ultima_sync)
        return AlDia(c.ultima_sync, (c.ultimo_resumen or {}).get("conflictos", 0))

    # --- Configuración -----------------------------------------------------------
    def guardar_config(self, **cambios):
        """Cambia la configuración. Otra carpeta local o remota = copia nueva:
        la base anterior describía otra carpeta y usarla haría creer que se
        borró todo."""
        if not self.uid:
            return
        c = self.config
        if ("carpeta" in cambios and cambios["carpeta"] != c.carpeta) or \
                ("carpeta_remota" in cambios and cambios["carpeta_remota"] != c.carpeta_remota):
            c.base, c.huellas, c.ultima_sync, c.ultimo_resumen = {}, {}, 0, None
        for k, v in cambios.items():
            setattr(c, k, v)
        if "programacion" in cambios:
            self._servidor_visible = None     # "al conectarse" vuelve a evaluar desde cero
            self._ultima_revision_red = 0
        self.almacen.guardar(self.uid, c)
        if not self.ocupado:
            self.estado = self._estado_en_reposo()

    # --- Ejecución -------------------------------------------------------------
    def sincronizar_ahora(self, modo=MANUAL):
        """Lanza una sincronización en segundo plano. False si no se pudo."""
        with self._lock:
            if self.ocupado or not self.uid or not self.config.carpeta:
                return False
            token = self.tokens.current_token()
            if not token:
                return False
            self.estado = Sincronizando(0, 0, "Conectando")
            self._hilo = threading.Thread(target=self._ejecutar, args=(self.uid, token, modo), daemon=True)
            self._hilo.start()
            return True

    def _ejecutar(self, uid, token, modo):
        motor = MotorSincronizacion(self.direccion, token, self.ca_tls)
        config = self.config
        inicio = time.time()

        def progreso(e):
            if self.uid == uid:
                self.estado = e
        try:
            resumen = motor.sincronizar(config, modo, progreso)
            config.ultima_sync = resumen["fecha"]
            config.ultimo_resumen = resumen
            nuevo = AlDia(resumen["fecha"], resumen["conflictos"])
        except SyncAbortada as e:
            config.ultimo_resumen = {"fecha": inicio, "modo": modo, "mensaje_error": str(e)}
            nuevo = SIN_CONEXION if e.sin_red and modo != MANUAL else ErrorSync(str(e), config.ultima_sync)
        except Exception as e:  # noqa: BLE001
            config.ultimo_resumen = {"fecha": inicio, "modo": modo, "mensaje_error": str(e) or type(e).__name__}
            nuevo = ErrorSync(config.ultimo_resumen["mensaje_error"], config.ultima_sync)
        finally:
            motor.cerrar()
        if self.uid == uid:          # la sesión no cambió mientras sincronizaba
            self.almacen.guardar(uid, config)
            self.estado = nuevo

    def revisar_programacion(self, ahora=None):
        """Dispara la sincronización programada si toca. Se llama cada pocos
        segundos desde la interfaz; es barata salvo la comprobación de red
        (una cada 30 s, en un hilo, y solo con "al conectarse")."""
        c = self.config
        if not self.uid or not c.carpeta or self.ocupado or c.programacion == MANUAL:
            return
        ahora = ahora or datetime.now()
        ultima = datetime.fromtimestamp(c.ultima_sync) if c.ultima_sync else None
        intento = (c.ultimo_resumen or {}).get("fecha", 0)
        # Tras un fallo se esperan 5 min antes de reintentar, para no insistir sin parar.
        reintento_ok = not (c.ultimo_resumen or {}).get("mensaje_error") or time.time() - intento > 300

        if c.programacion == CADA_HORA:
            if (ultima is None or ahora - ultima >= timedelta(hours=1)) and reintento_ok:
                self.sincronizar_ahora(CADA_HORA)
        elif c.programacion == DIARIA:
            hoy = ahora.replace(hour=c.hora, minute=c.minuto, second=0, microsecond=0)
            if ahora >= hoy and (ultima is None or ultima < hoy) and reintento_ok:
                self.sincronizar_ahora(DIARIA)
        elif c.programacion == AL_CONECTAR:
            if time.time() - self._ultima_revision_red < 30:
                return
            self._ultima_revision_red = time.time()
            threading.Thread(target=self._revisar_red, daemon=True).start()

    def _revisar_red(self):
        """'Al conectarse': sincroniza cuando el servidor PASA a ser alcanzable
        (el PC llegó a la red del servidor), no cada vez que se comprueba."""
        token = self.tokens.current_token()
        if not token:
            return
        motor = MotorSincronizacion(self.direccion, token, self.ca_tls)
        try:
            visible = motor.alcanzable()
        finally:
            motor.cerrar()
        antes, self._servidor_visible = self._servidor_visible, visible
        if visible and antes is not True:
            self.sincronizar_ahora(AL_CONECTAR)
        elif not visible and not self.ocupado and self.config.carpeta:
            self.estado = SIN_CONEXION
