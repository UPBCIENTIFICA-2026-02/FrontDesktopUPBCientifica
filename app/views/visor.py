# -*- coding: utf-8 -*-
"""Visores DENTRO de la app: imágenes y videos se ven aquí, sin abrir otra
aplicación ni el navegador (el token no sale de la app). Mismo criterio que
VisorMedia.kt del móvil.

  VisorImagen  rueda del ratón para ampliar, arrastrar para mover, doble clic
               para volver a encajar.
  Reproductor  video con audio (PyAV + sounddevice). Pide el video por rangos
               al servidor con la cabecera Authorization, así que se puede
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
            ctk.CTkButton(barra, text="🗑  Eliminar", width=110, height=34, fg_color="transparent",
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


class Reproductor(_VentanaVisor):
    """Reproductor de video. `fuente`: (url_o_ruta, cabeceras) o una función que
    la devuelve (por ejemplo, abrir la sesión de streaming); se llama en un hilo."""

    TASA_AUDIO = 48000

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

        # Estado compartido con el hilo de decodificación.
        self._cola = queue.Queue(maxsize=24)   # ("cuadro", pts, img) | ("info", dur) | ("fin",) | ("error", msg)
        self._detener = threading.Event()
        self._pausado = threading.Event()
        self._seek_a = None
        self._objetivo = (960, 560)            # tamaño máximo de cuadro (lo fija el lienzo)
        # Reloj (hilo de Tk): pts que corresponde al instante `_ancla`.
        self._ancla = None
        self._pausa_desde = None
        self._duracion = 0.0
        self._siguiente = None
        self._foto = None
        self._arrastrando = False
        self._fin = False

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
        threading.Thread(target=self._decodificar, args=(url, cabeceras or {}), daemon=True).start()
        self.after(15, self._tic)

    def _texto(self, mensaje):
        self.lienzo.delete("all")
        self.lienzo.create_text(max(self.lienzo.winfo_width(), 960) // 2, max(self.lienzo.winfo_height(), 560) // 2,
                                text=mensaje, fill=TENUE, font=("Segoe UI", 13), width=640)

    def _redimensionar(self, e):
        self._objetivo = (max(e.width, 160), max(e.height, 90))

    # ------------------------------------------------- hilo de decodificación
    def _poner(self, item):
        """put que no se queda colgado si se cierra la ventana o se pide un salto."""
        while not self._detener.is_set():
            if self._seek_a is not None and item[0] == "cuadro":
                return
            try:
                self._cola.put(item, timeout=0.1)
                return
            except queue.Full:
                continue

    def _decodificar(self, url, cabeceras):
        contenedor = salida = None
        try:
            opciones = {}
            if "://" in url and cabeceras:
                opciones["headers"] = "".join(f"{k}: {v}\r\n" for k, v in cabeceras.items())
            contenedor = av.open(url, options=opciones, timeout=15)
            video = contenedor.streams.video[0] if contenedor.streams.video else None
            audio = contenedor.streams.audio[0] if contenedor.streams.audio else None
            if video is None:
                raise RuntimeError("El archivo no tiene pista de video.")
            video.thread_type = "AUTO"
            duracion = contenedor.duration / 1_000_000 if contenedor.duration else 0.0
            self._poner(("info", duracion))

            remuestreo = None
            if audio is not None and sd is not None:
                try:
                    remuestreo = av.AudioResampler(format="s16", layout="stereo", rate=self.TASA_AUDIO)
                    salida = sd.RawOutputStream(samplerate=self.TASA_AUDIO, channels=2, dtype="int16")
                    salida.start()
                except Exception:   # sin dispositivo de audio: se ve en silencio
                    remuestreo = salida = None

            flujos = [video] + ([audio] if salida else [])
            paquetes = contenedor.demux(*flujos)
            while not self._detener.is_set():
                if self._seek_a is not None:
                    destino = self._seek_a
                    contenedor.seek(int(destino * 1_000_000))      # unidades AV_TIME_BASE
                    paquetes = contenedor.demux(*flujos)
                    self._seek_a = None
                    self._poner(("saltado",))
                if self._pausado.is_set():
                    time.sleep(0.05)
                    continue
                try:
                    paquete = next(paquetes)
                except StopIteration:
                    self._poner(("fin",))
                    while not self._detener.is_set() and self._seek_a is None:
                        time.sleep(0.05)
                    continue
                for cuadro in paquete.decode():
                    if self._detener.is_set() or self._seek_a is not None:
                        break
                    if paquete.stream is video:
                        if cuadro.pts is None:
                            continue
                        img = cuadro.to_image()
                        img.thumbnail(self._objetivo)
                        self._poner(("cuadro", float(cuadro.pts * cuadro.time_base), img))
                    elif salida:
                        # write() bloquea al ritmo del audio: eso marca el paso del hilo.
                        for parte in remuestreo.resample(cuadro):
                            salida.write(parte.to_ndarray().tobytes())
        except Exception as e:  # noqa: BLE001
            self._poner(("error", f"No se pudo reproducir: {e}"))
        finally:
            for recurso in (salida, contenedor):
                try:
                    if recurso is not None:
                        recurso.close()
                except Exception:
                    pass

    # ------------------------------------------------------- hilo de la UI
    def _reloj(self):
        if self._ancla is None:
            return None
        ahora = self._pausa_desde if self._pausa_desde is not None else time.monotonic()
        return ahora - self._ancla

    def _tic(self):
        if self._detener.is_set():
            return
        try:
            # Mensajes de control y, como mucho, el siguiente cuadro pendiente.
            while self._siguiente is None:
                item = self._cola.get_nowait()
                tipo = item[0]
                if tipo == "cuadro":
                    self._siguiente = item
                elif tipo == "info":
                    self._duracion = item[1]
                    self.barra.configure(to=max(self._duracion, 1), state="normal")
                    self.btn.configure(state="normal")
                elif tipo == "saltado":
                    self._ancla = None
                elif tipo == "fin":
                    self._fin = True
                    self.btn.configure(text="↻")
                elif tipo == "error":
                    self._texto(item[1])
                    return
        except queue.Empty:
            pass

        if self._siguiente is not None and self._pausa_desde is None:
            _, pts, img = self._siguiente
            if self._ancla is None:                 # primer cuadro tras abrir o saltar
                self._ancla = time.monotonic() - pts
            reloj = self._reloj()
            if pts <= reloj + 0.015:
                if reloj - pts < 0.25 or self._cola.empty():   # muy atrasado: se descarta
                    self._mostrar(img)
                self._siguiente = None
                self._actualizar_tiempo(pts)
        self.after(10, self._tic)

    def _mostrar(self, img):
        self._foto = ImageTk.PhotoImage(img)
        self.lienzo.delete("all")
        self.lienzo.create_image(self.lienzo.winfo_width() // 2, self.lienzo.winfo_height() // 2,
                                 image=self._foto, anchor="center")

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
            self._pausa_desde = time.monotonic()
            self._pausado.set()
            self.btn.configure(text="▶")
        else:
            if self._ancla is not None:
                self._ancla += time.monotonic() - self._pausa_desde
            self._pausa_desde = None
            self._pausado.clear()
            self.btn.configure(text="❚❚")

    def _soltar_barra(self, _e):
        self._arrastrando = False
        if self._duracion:
            self._fin = False
            self.btn.configure(text="▶" if self._pausa_desde is not None else "❚❚")
            self._saltar(self.barra.get())

    def _saltar(self, segundos):
        self._siguiente = None
        while True:                         # lo que había en cola es de antes del salto
            try:
                self._cola.get_nowait()
            except queue.Empty:
                break
        self._ancla = None
        if self._pausa_desde is not None:
            self._pausa_desde = time.monotonic()
        self._seek_a = float(segundos)

    def cerrar(self):
        self._detener.set()
        super().cerrar()
