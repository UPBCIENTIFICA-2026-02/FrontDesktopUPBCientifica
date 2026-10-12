# -*- coding: utf-8 -*-
"""Visores DENTRO de la app: imágenes y videos se ven aquí, sin abrir otra
aplicación ni el navegador (el token no sale de la app). Mismo criterio que
VisorMedia.kt del móvil.

  VisorImagen  rueda del ratón para ampliar, arrastrar para mover, doble clic
               para volver a encajar.
  Reproductor  video con audio (PyAV + sounddevice), al estilo de ffplay: un
               hilo lee, otro decodifica video y otro audio. Pide el video
               por rangos al servidor con la cabecera Authorization, así que se puede
               saltar en la línea de tiempo sin descargarlo entero.
"""

import io
import queue
import threading
import time
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk

from ..theme import font
from ..widgets import ConfirmDialog

try:
    import av
except ImportError:          # sin PyAV no hay reproductor (requirements.txt lo instala)
    av = None
try:
    import sounddevice as sd
except Exception:            # sin audio el video se ve igual, en silencio
    sd = None

NEGRO = "#000000"
BARRA = "#1E1F24"
TEXTO = "#FFFFFF"
TENUE = "#B9BBC4"


def _hhmmss(segundos):
    s = int(max(0, segundos))
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class _VentanaVisor(ctk.CTkToplevel):
    """Ventana negra con barra superior: título y, si se pide, papelera."""

    def __init__(self, master, titulo, on_eliminar=None, ancho=980, alto=680):
        super().__init__(master, fg_color=NEGRO)
        self.title(titulo)
        top = master.winfo_toplevel()
        top.update_idletasks()
        x = top.winfo_rootx() + max(0, (top.winfo_width() - ancho) // 2)
        y = top.winfo_rooty() + max(0, (top.winfo_height() - alto) // 3)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(480, 360)
        self.transient(top)
        self.after(80, self._enfocar)

        barra = ctk.CTkFrame(self, fg_color=BARRA, corner_radius=0, height=48)
        barra.pack(fill="x", side="top")
        ctk.CTkLabel(barra, text=titulo, text_color=TEXTO, font=font("title_medium"),
                     anchor="w").pack(side="left", padx=16, pady=8, fill="x", expand=True)
        ctk.CTkButton(barra, text="✕", width=40, height=34, fg_color="transparent", hover_color="#33353B",
                      text_color=TEXTO, command=self.cerrar).pack(side="right", padx=6)
        if on_eliminar:
            def pedir():
                ConfirmDialog(self, "🗑", "¿Eliminar?",
                              f"«{titulo}» se borrará también de Mis archivos. No se puede deshacer.",
                              "Eliminar", lambda: (self.cerrar(), on_eliminar()))
            ctk.CTkButton(barra, text="Eliminar", width=110, height=34, fg_color="transparent",
                          hover_color="#33353B", text_color="#FFB4AB", command=pedir).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.bind("<Escape>", lambda _e: self.cerrar())

    def _enfocar(self):
        try:
            self.lift()
            self.focus_force()
        except tk.TclError:
            pass

    def cerrar(self):
        try:
            self.destroy()
        except tk.TclError:
            pass


class VisorImagen(_VentanaVisor):
    """`origen`: bytes de la imagen, o una función que los devuelve (se llama en
    un hilo, así la ventana aparece enseguida con "Cargando…")."""

    def __init__(self, master, titulo, origen, on_eliminar=None):
        super().__init__(master, titulo, on_eliminar)
        self.lienzo = tk.Canvas(self, bg=NEGRO, highlightthickness=0, cursor="fleur")
        self.lienzo.pack(fill="both", expand=True)
        self.imagen = None          # PIL original
        self._foto = None           # PhotoImage en pantalla (referencia viva)
        self.escala = None          # None = encajar en la ventana
        self.desplazamiento = [0, 0]
        self._arrastre = None
        self._mensaje("Cargando…")

        self.lienzo.bind("<Configure>", lambda _e: self._pintar())
        self.lienzo.bind("<MouseWheel>", self._rueda)                 # Windows / macOS
        self.lienzo.bind("<Button-4>", lambda e: self._zoom(1.15, e))  # Linux
        self.lienzo.bind("<Button-5>", lambda e: self._zoom(1 / 1.15, e))
        self.lienzo.bind("<ButtonPress-1>", self._inicio_arrastre)
        self.lienzo.bind("<B1-Motion>", self._arrastrar)
        self.lienzo.bind("<Double-Button-1>", lambda _e: self._encajar())

        if callable(origen):
            from ..utils import run_async, describir
            run_async(self, origen, self._cargar, lambda e: self._mensaje(describir(e)))
        else:
            self._cargar(origen)

    def _cargar(self, datos):
        try:
            img = Image.open(io.BytesIO(datos))
            img.load()
            self.imagen = img.convert("RGBA") if img.mode not in ("RGB", "RGBA") else img
        except Exception as e:  # noqa: BLE001
            self._mensaje(f"No es una imagen que se pueda mostrar ({e}).")
            return
        self._encajar()

    def _mensaje(self, texto):
        self.lienzo.delete("all")
        self.lienzo.create_text(self.lienzo.winfo_width() // 2 or 480, self.lienzo.winfo_height() // 2 or 300,
                                text=texto, fill=TENUE, font=("Segoe UI", 13), width=600)

    def _encaje(self):
        w, h = max(self.lienzo.winfo_width(), 50), max(self.lienzo.winfo_height(), 50)
        return min(w / self.imagen.width, h / self.imagen.height, 1.0)

    def _encajar(self):
        self.escala = None
        self.desplazamiento = [0, 0]
        self._pintar()

    def _pintar(self):
        if self.imagen is None:
            return
        escala = self.escala or self._encaje()
        w = max(1, int(self.imagen.width * escala))
        h = max(1, int(self.imagen.height * escala))
        self._foto = ImageTk.PhotoImage(self.imagen.resize((w, h), Image.LANCZOS if escala < 1 else Image.NEAREST))
        cx = self.lienzo.winfo_width() // 2 + self.desplazamiento[0]
        cy = self.lienzo.winfo_height() // 2 + self.desplazamiento[1]
        self.lienzo.delete("all")
        self.lienzo.create_image(cx, cy, image=self._foto, anchor="center")

    def _rueda(self, e):
        self._zoom(1.15 if e.delta > 0 else 1 / 1.15, e)

    def _zoom(self, factor, _e=None):
        if self.imagen is None:
            return
        actual = self.escala or self._encaje()
        nueva = max(self._encaje(), min(actual * factor, 8.0))
        self.escala = None if abs(nueva - self._encaje()) < 1e-3 else nueva
        if self.escala is None:
            self.desplazamiento = [0, 0]
        self._pintar()

    def _inicio_arrastre(self, e):
        self._arrastre = (e.x, e.y)

    def _arrastrar(self, e):
        if self._arrastre is None or self.escala is None:
            return
        dx, dy = e.x - self._arrastre[0], e.y - self._arrastre[1]
        self._arrastre = (e.x, e.y)
        self.desplazamiento[0] += dx
        self.desplazamiento[1] += dy
        self._pintar()


class _BufferAudio:
    """Bytes de audio (PCM s16 estéreo) entre el hilo que decodifica y la tarjeta de sonido."""

    def __init__(self):
        self._partes = []
        self._total = 0
        self._candado = threading.Lock()

    def poner(self, datos):
        with self._candado:
            self._partes.append(datos)
            self._total += len(datos)

    def sacar(self, n):
        """Hasta n bytes (menos si no hay). Lo llama la tarjeta de sonido: tiene que ser rápido."""
        with self._candado:
            if not self._total:
                return b""
            salida = bytearray()
            while self._partes and len(salida) < n:
                parte = self._partes[0]
                falta = n - len(salida)
                if len(parte) <= falta:
                    salida += parte
                    self._partes.pop(0)
                else:
                    salida += parte[:falta]
                    self._partes[0] = parte[falta:]
            self._total -= len(salida)
            return bytes(salida)

    def bytes_pendientes(self):
        with self._candado:
            return self._total

    def vaciar(self):
        with self._candado:
            self._partes.clear()
            self._total = 0


class Reproductor(_VentanaVisor):
    """Reproductor de video. `fuente`: (url_o_ruta, cabeceras) o una función que
    la devuelve (por ejemplo, abrir la sesión de streaming); se llama en un hilo.

    Diseño de ffplay (el reproductor de ffmpeg), en tres hilos:
      lector  lee el archivo y reparte los paquetes comprimidos en una cola de
              video y otra de audio. Son pequeños: caben decenas de segundos.
      video   decodifica y escala (en C) los cuadros a la cola de cuadros.
      audio   decodifica y deja PCM para la tarjeta de sonido, que lo pide
              desde su propio hilo (callback) y suena continuo.
    Así un archivo que guarda el video en bloques de 2 s sin audio entre medias
    (las grabaciones de juegos, por ejemplo) no bloquea el audio: con un solo
    hilo, la cola de cuadros se llenaba, el audio se quedaba sin datos, el reloj
    se paraba y el video se congelaba del todo.

    El audio es el reloj: cada cuadro se muestra cuando le toca según lo que ya
    sonó, y si llega tarde se descarta. Si el audio se quedara sin datos, el
    reloj sigue con el del sistema: la imagen nunca se congela.
    """

    TASA_AUDIO = 48000
    BYTES_POR_MUESTRA = 4                 # s16 estéreo
    MARGEN_AUDIO_S = 1.5                  # audio decodificado por delante
    MARGEN_CUADROS = 30                   # cuadros listos por delante
    MAX_PAQUETES = 3000                   # paquetes comprimidos por cola (decenas de segundos)

    def __init__(self, master, titulo, fuente, on_eliminar=None):
        super().__init__(master, titulo, on_eliminar)
        self.lienzo = tk.Canvas(self, bg=NEGRO, highlightthickness=0)
        self.lienzo.pack(fill="both", expand=True)

        controles = ctk.CTkFrame(self, fg_color=BARRA, corner_radius=0)
        controles.pack(fill="x", side="bottom")
        self.btn = ctk.CTkButton(controles, text="❚❚", width=44, height=34, fg_color="transparent",
                                 hover_color="#33353B", text_color=TEXTO, font=ctk.CTkFont(size=16),
                                 command=self.alternar_pausa, state="disabled")
        self.btn.pack(side="left", padx=(10, 4), pady=8)
        self.tiempo = ctk.CTkLabel(controles, text="0:00 / 0:00", text_color=TENUE, width=110)
        self.tiempo.pack(side="right", padx=12)
        self.barra = ctk.CTkSlider(controles, from_=0, to=1, number_of_steps=None, state="disabled")
        self.barra.set(0)
        self.barra.pack(side="left", fill="x", expand=True, padx=8)
        self.barra.bind("<ButtonPress-1>", lambda _e: setattr(self, "_arrastrando", True))
        self.barra.bind("<ButtonRelease-1>", self._soltar_barra)

        # --- Compartido entre hilos ---
        self._paq_video = queue.Queue(maxsize=self.MAX_PAQUETES)   # ("paq", gen, paquete) | ("salto", gen) | ("fin", gen)
        self._paq_audio = queue.Queue(maxsize=self.MAX_PAQUETES)
        self._cuadros = queue.Queue(maxsize=self.MARGEN_CUADROS)   # (gen, pts, imagen PIL)
        self._avisos = queue.Queue()                                # ("info", dur) | ("error", msg)
        self._audio = _BufferAudio()
        self._detener = threading.Event()
        self._generacion = 0          # sube en cada salto: lo anterior se descarta
        self._seek_a = None
        self._desde = 0.0             # tras un salto, lo anterior a esto no se muestra
        self._objetivo = (960, 560)
        self._flujo_video = self._flujo_audio = None
        self._salida = None
        self._latencia = 0.0
        self._hay_audio = False
        # Reloj de audio: pts del primer audio tras abrir/saltar + muestras ya sonadas.
        self._audio_base = None
        self._muestras = 0
        # Reloj de respaldo (sistema): sin audio, o si el audio se queda sin datos.
        self._ancla = None
        self._ultimo_reloj = None     # (valor, instante) de la última lectura que avanzó
        self._pausa_desde = None
        self._duracion = 0.0
        self._siguiente = None
        self._foto = None
        self._id_imagen = None
        self._arrastrando = False
        self._fin = False
        self._fin_video = None        # generación en la que cada decodificador llegó al final
        self._fin_audio = None

        self.lienzo.bind("<Configure>", self._redimensionar)
        self.bind("<space>", lambda _e: self.alternar_pausa())
        self._texto("Cargando video…")

        if av is None:
            self._texto("Falta el paquete PyAV para reproducir video:  pip install av")
            return
        if callable(fuente):
            from ..utils import run_async, describir
            run_async(self, fuente, self._iniciar, lambda e: self._texto(describir(e)))
        else:
            self._iniciar(fuente)

    # --------------------------------------------------------------- arranque
    def _iniciar(self, fuente):
        url, cabeceras = fuente
        threading.Thread(target=self._leer, args=(url, cabeceras or {}), daemon=True).start()
        self.after(8, self._tic)

    def _texto(self, mensaje):
        self.lienzo.delete("all")
        self._foto = self._id_imagen = None
        self.lienzo.create_text(max(self.lienzo.winfo_width(), 960) // 2, max(self.lienzo.winfo_height(), 560) // 2,
                                text=mensaje, fill=TENUE, font=("Segoe UI", 13), width=640)

    def _redimensionar(self, e):
        self._objetivo = (max(e.width, 160), max(e.height, 90))

    def _poner(self, cola, item):
        """put que no se queda colgado si se cierra la ventana o se pide un salto."""
        while not self._detener.is_set():
            if self._seek_a is not None and item[0] == "paq":
                return False
            try:
                cola.put(item, timeout=0.05)
                return True
            except queue.Full:
                continue
        return False

    # ------------------------------------------------------ tarjeta de sonido
    def _callback_audio(self, salida, cuadros, _tiempo, _estado):
        """Lo llama PortAudio desde su hilo cada pocos milisegundos."""
        n = cuadros * self.BYTES_POR_MUESTRA
        datos = self._audio.sacar(n)
        salida[:len(datos)] = datos
        if len(datos) < n:
            salida[len(datos):] = b"\x00" * (n - len(datos))   # silencio si aún no hay
        self._muestras += len(datos) // self.BYTES_POR_MUESTRA

    # ------------------------------------------------------------- hilo lector
    def _leer(self, url, cabeceras):
        contenedor = None
        try:
            opciones = {}
            if "://" in url and cabeceras:
                opciones["headers"] = "".join(f"{k}: {v}\r\n" for k, v in cabeceras.items())
            contenedor = av.open(url, options=opciones, timeout=15)
            video = contenedor.streams.video[0] if contenedor.streams.video else None
            audio = contenedor.streams.audio[0] if contenedor.streams.audio else None
            if video is None:
                raise RuntimeError("El archivo no tiene pista de video.")
            video.thread_type = "AUTO"          # decodificación en varios núcleos
            self._flujo_video = video
            if audio is not None and sd is not None:
                try:
                    self._salida = sd.RawOutputStream(samplerate=self.TASA_AUDIO, channels=2, dtype="int16",
                                                      callback=self._callback_audio, latency="high")
                    self._latencia = float(self._salida.latency or 0)
                    self._flujo_audio = audio
                except Exception:               # sin dispositivo de audio: se ve en silencio
                    self._salida = None
            self._hay_audio = self._flujo_audio is not None
            self._avisos.put(("info", contenedor.duration / 1_000_000 if contenedor.duration else 0.0))

            threading.Thread(target=self._decodificar_video, daemon=True).start()
            if self._hay_audio:
                threading.Thread(target=self._decodificar_audio, daemon=True).start()
                self._salida.start()

            flujos = [video] + ([self._flujo_audio] if self._hay_audio else [])
            paquetes = contenedor.demux(*flujos)
            gen = self._generacion
            while not self._detener.is_set():
                if self._seek_a is not None:
                    destino, gen = self._seek_a, self._generacion
                    self._seek_a = None
                    contenedor.seek(int(max(0.0, destino) * 1_000_000))   # unidades AV_TIME_BASE
                    paquetes = contenedor.demux(*flujos)
                    for cola in (self._paq_video, self._paq_audio):
                        while True:
                            try:
                                cola.get_nowait()
                            except queue.Empty:
                                break
                    self._desde = destino
                    self._poner(self._paq_video, ("salto", gen))
                    if self._hay_audio:
                        self._poner(self._paq_audio, ("salto", gen))
                try:
                    paquete = next(paquetes)
                except StopIteration:
                    self._poner(self._paq_video, ("fin", gen))
                    if self._hay_audio:
                        self._poner(self._paq_audio, ("fin", gen))
                    while not self._detener.is_set() and self._seek_a is None:
                        time.sleep(0.05)
                    continue
                if paquete.size == 0:           # paquete vacío de vaciado: lo genera el demuxer
                    continue
                cola = self._paq_video if paquete.stream is video else self._paq_audio
                self._poner(cola, ("paq", gen, paquete))
        except Exception as e:  # noqa: BLE001
            self._avisos.put(("error", f"No se pudo reproducir: {e}"))
        finally:
            self._detener.set()
            for recurso in (self._salida, contenedor):
                try:
                    if recurso is not None:
                        recurso.close()
                except Exception:
                    pass

    # ------------------------------------------------------------- hilo video
    def _decodificar_video(self):
        flujo = self._flujo_video
        while not self._detener.is_set():
            try:
                item = self._paq_video.get(timeout=0.1)
            except queue.Empty:
                continue
            tipo, gen = item[0], item[1]
            if gen != self._generacion:
                continue
            try:
                if tipo == "salto":
                    flujo.codec_context.flush_buffers()
                    continue
                cuadros = flujo.decode(item[2]) if tipo == "paq" else flujo.decode(None)
                for cuadro in cuadros:
                    if self._detener.is_set() or gen != self._generacion:
                        break
                    if cuadro.pts is None:
                        continue
                    pts = float(cuadro.pts * cuadro.time_base)
                    if pts < self._desde - 0.04:     # el salto cae en el cuadro clave anterior
                        continue
                    self._poner(self._cuadros, ("cuadro", gen, pts, self._preparar(cuadro)))
            except Exception:  # noqa: BLE001 — un paquete dañado no tumba el video
                pass
            if tipo == "fin":
                # Fuera del try: vaciar el decodificador al final puede lanzar
                # (EOF) y aun así el video terminó.
                self._fin_video = gen

    def _preparar(self, cuadro):
        """Escala el cuadro al tamaño del lienzo EN C (swscale) y lo pasa a PIL."""
        ancho, alto = self._objetivo
        escala = min(ancho / cuadro.width, alto / cuadro.height)
        w = max(2, int(cuadro.width * escala) // 2 * 2)
        h = max(2, int(cuadro.height * escala) // 2 * 2)
        return cuadro.reformat(width=w, height=h, format="rgb24").to_image()

    # ------------------------------------------------------------- hilo audio
    def _decodificar_audio(self):
        flujo = self._flujo_audio
        remuestreo = av.AudioResampler(format="s16", layout="stereo", rate=self.TASA_AUDIO)
        maximo = int(self.MARGEN_AUDIO_S * self.TASA_AUDIO * self.BYTES_POR_MUESTRA)
        while not self._detener.is_set():
            # Por delante solo ~1,5 s de audio; esperar aquí NO frena al video.
            if self._audio.bytes_pendientes() > maximo:
                time.sleep(0.01)
                continue
            try:
                item = self._paq_audio.get(timeout=0.1)
            except queue.Empty:
                continue
            tipo, gen = item[0], item[1]
            if gen != self._generacion:
                continue
            try:
                if tipo == "salto":
                    flujo.codec_context.flush_buffers()
                    remuestreo = av.AudioResampler(format="s16", layout="stereo", rate=self.TASA_AUDIO)
                    continue
                cuadros = flujo.decode(item[2]) if tipo == "paq" else flujo.decode(None)
                for cuadro in cuadros:
                    if gen != self._generacion or cuadro.pts is None:
                        break
                    pts = float(cuadro.pts * cuadro.time_base)
                    if pts < self._desde - 0.04:
                        continue
                    if self._audio_base is None:
                        self._audio_base = pts
                    for parte in remuestreo.resample(cuadro):
                        self._audio.poner(parte.to_ndarray().tobytes())
            except Exception:  # noqa: BLE001
                pass
            if tipo == "fin":
                self._fin_audio = gen

    # ------------------------------------------------------- hilo de la UI
    def _reloj(self, pts_pendiente):
        """Segundos del video que tocan AHORA.

        Con audio, lo marca lo que ya sonó. Si el audio deja de avanzar sin
        estar en pausa (se quedó sin datos, o terminó antes que el video), se
        sigue con el reloj del sistema desde la última lectura: nunca se para."""
        ahora = time.monotonic()
        if self._pausa_desde is not None:
            return self._ultimo_reloj[0] if self._ultimo_reloj else None
        if self._hay_audio and self._audio_base is not None:
            reloj = self._audio_base + self._muestras / self.TASA_AUDIO - self._latencia
            if self._ultimo_reloj is None or reloj > self._ultimo_reloj[0] + 1e-4:
                self._ultimo_reloj = (reloj, ahora)
                return reloj
            if ahora - self._ultimo_reloj[1] < 0.2:      # un hueco corto es normal entre bloques
                return self._ultimo_reloj[0]
        elif self._ultimo_reloj is None:
            # Video mudo, o audio que aún no empieza: arranca con el primer cuadro.
            self._ultimo_reloj = (pts_pendiente, ahora)
            return pts_pendiente
        valor, instante = self._ultimo_reloj
        return valor + (ahora - instante)

    def _tic(self):
        if self._detener.is_set() and self._cuadros.empty():
            return
        while True:
            try:
                aviso = self._avisos.get_nowait()
            except queue.Empty:
                break
            if aviso[0] == "info":
                self._duracion = aviso[1]
                self.barra.configure(to=max(self._duracion, 1), state="normal")
                self.btn.configure(state="normal")
            elif aviso[0] == "error":
                self._texto(aviso[1])
                return

        mostrar = None
        while True:
            if self._siguiente is None:
                try:
                    self._siguiente = self._cuadros.get_nowait()
                except queue.Empty:
                    break
            _, gen, pts, imagen = self._siguiente
            if gen != self._generacion:          # de antes de un salto
                self._siguiente = None
                continue
            reloj = self._reloj(pts)
            if reloj is None or pts > reloj + 0.01:
                break                                       # todavía no le toca
            mostrar = (pts, imagen)                         # le toca; si hay uno más nuevo, gana ese
            self._siguiente = None
        if mostrar:
            self._mostrar(mostrar[1])
            self._actualizar_tiempo(mostrar[0])

        terminado = (self._fin_video == self._generacion
                     and (not self._hay_audio or self._fin_audio == self._generacion))
        if terminado and self._siguiente is None and self._cuadros.empty() and not self._fin \
                and self._audio.bytes_pendientes() == 0:
            self._fin = True
            self.btn.configure(text="↻")
        self.after(8, self._tic)

    def _mostrar(self, imagen):
        if self._foto is not None and (self._foto.width(), self._foto.height()) == imagen.size:
            self._foto.paste(imagen)                       # misma imagen en pantalla: más rápido
        else:
            self._foto = ImageTk.PhotoImage(imagen)
            self.lienzo.delete("all")
            self._id_imagen = self.lienzo.create_image(0, 0, image=self._foto, anchor="center")
        self.lienzo.coords(self._id_imagen, self.lienzo.winfo_width() // 2, self.lienzo.winfo_height() // 2)

    def _actualizar_tiempo(self, pts):
        self.tiempo.configure(text=f"{_hhmmss(pts)} / {_hhmmss(self._duracion)}")
        if not self._arrastrando:
            self.barra.set(pts)

    # ------------------------------------------------------------ controles
    def alternar_pausa(self):
        if self._fin:                      # terminó: volver a empezar
            self._fin = False
            self.btn.configure(text="❚❚")
            self._saltar(0)
            return
        if self._pausa_desde is None:
            self._reloj(0)                 # fija el último valor antes de parar
            self._pausa_desde = time.monotonic()
            if self._salida:
                self._salida.stop()        # el reloj de audio se detiene con él
            self.btn.configure(text="▶")
        else:
            if self._ultimo_reloj is not None:   # el reloj de respaldo no cuenta la pausa
                self._ultimo_reloj = (self._ultimo_reloj[0], time.monotonic())
            self._pausa_desde = None
            if self._salida:
                self._salida.start()
            self.btn.configure(text="❚❚")

    def _soltar_barra(self, _e):
        self._arrastrando = False
        if self._duracion:
            self._fin = False
            self.btn.configure(text="▶" if self._pausa_desde is not None else "❚❚")
            self._saltar(self.barra.get())

    def _saltar(self, segundos):
        self._generacion += 1
        self._siguiente = None
        while True:                         # lo que había en cola es de antes del salto
            try:
                self._cuadros.get_nowait()
            except queue.Empty:
                break
        self._audio.vaciar()
        self._audio_base = None
        self._muestras = 0
        self._ultimo_reloj = None
        if self._pausa_desde is not None:
            self._pausa_desde = time.monotonic()
        self._seek_a = float(segundos)

    def cerrar(self):
        self._detener.set()
        super().cerrar()
