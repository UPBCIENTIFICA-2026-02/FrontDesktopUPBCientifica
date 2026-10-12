# UPB-CIENTÍFICA — Cliente de Escritorio (Windows / Linux)

Cliente de escritorio del sistema distribuido **UPB-CIENTÍFICA** (proyecto de
**Sistemas Distribuidos 2026-20**, UPB Bucaramanga). Corresponde al consumidor
**"Desktop Windows/Linux"** de la Figura 1 del proyecto.

> **Lenguaje:** Python + CustomTkinter (el PDF no fija lenguaje para el cliente
> de escritorio; los lenguajes obligatorios aplican a los servidores).

Este cliente está **alineado con el cliente móvil** (`FrontMovilUPBCientifica`,
Kotlin + Jetpack Compose):

- **Mismo diseño:** la paleta del tema `UpbCientificaTheme` del móvil (azul
  `#1A5BC0`, turquesa y violeta, neutros fríos), con modo claro y oscuro, y las
  mismas pantallas: inicio con saludo y estado de sincronización, iconos por
  tipo de archivo, buscador en píldora, migas de pan, vista de lista o
  cuadrícula, hoja de detalles, avatar con menú de cuenta y pestaña HPC.
- **Mismos contratos y puertos:** se conecta **directamente** a cada servicio
  con su protocolo nativo, sin pasar por el gateway del cliente Web.

| Servicio            | Protocolo | Estado en el cliente de escritorio |
|---------------------|-----------|------------------------------------|
| Authentication      | SOAP      | **Conectado** a node-soap (8081, `/soap/user.php`) |
| Distributed Storage | HTTP/REST | **Conectado** a node-repository (8084): navegar, subir, crear carpeta, descargar, eliminar, cuota |
| Shared File         | HTTP/REST | **Conectado** a node-shared-file (8085): compartir archivos y carpetas con usuarios o grupos, "Conmigo" / "Que comparto", cambiar permiso, dejar de compartir |
| Streaming           | HTTP/REST | **Conectado** a node-media (8083): catálogo, reproducción **dentro de la app**, eliminar, buscar contenido nuevo |
| Photo Album         | HTTP/REST | **Conectado** a node-media (8083): miniaturas, visor con zoom, eliminar |
| HPC                 | REST → RMI | **Conectado** a job-api (8082), la fachada REST del gestor RMI: enviar (nombre, comando, prioridad), listar, ver salida y cancelar |
| File Sync           | gRPC      | Simulado: indicador en la barra superior (conectividad real, ciclo simulado hasta generar el stub del `.proto`) |

**Imágenes y videos se ven dentro de la app** (`app/views/visor.py`): el
reproductor (PyAV + sounddevice) pide el video por rangos con el token en la
cabecera, así que se puede saltar en la línea de tiempo y nada se abre en el
navegador ni en otro programa.

Además, cada servicio REST puede pasar a **modo simulado** desde Configuración, y
el login ofrece **"Entrar sin servidor (demo)"** para usar la app sin backend.

## Arquitectura del código (separación por capas)

Misma filosofía por capas que el móvil (`ui/` → `data/` → `network/` + `session/`):

```
upbcientifica-desktop/
├── main.py                       # Punto de entrada
├── requirements.txt
├── mock-auth-server/server.js    # Mock SOAP del Authentication Service (el mismo del móvil)
└── app/
    ├── api_client.py             # Composición de dependencias (como MainActivity.kt)
    ├── config.py                 # Persistencia (JSON) + rutas + valores por defecto
    ├── theme.py                  # Paleta de ui/theme/Theme.kt (claro/oscuro), formas y tipografía
    ├── assets/upb_material3.json # Tema de CustomTkinter con la paleta del móvil
    ├── widgets.py                # Componentes de ui/components (Avatar, BarraBusqueda, EstadoVacio,
    │                             #   EsqueletoLista, IconoTipoArchivo, HojaDetalles, botones, chips)
    ├── utils.py                  # Utilidades (tamaños, hilos para red, abrir con el sistema)
    ├── app.py                    # Ventana principal: navegación lateral + barra superior
    ├── network/                  # Clientes de bajo nivel (como network/ del móvil)
    │   ├── configuracion.py      #   URLs de cada servicio según el entorno
    │   ├── soap_client.py        #   SOAP 1.1 sobre urllib (Auth)
    │   └── rest_client.py        #   REST + header Authorization: Bearer <token>
    ├── session/token_manager.py  # Token de sesión (en memoria)
    ├── data/                     # Un módulo por servicio (como data/ del móvil)
    │   ├── auth.py               #   login / validarToken / logout
    │   ├── storage.py            #   /storage/...
    │   ├── sharedfile.py         #   /shared-file/...
    │   ├── streaming.py          #   /streaming/...
    │   ├── hpc.py                #   EnviarTrabajo / ConsultarEstadoTrabajo / ObtenerEstadoCluster (simulado)
    │   └── filesync.py           #   Ciclo de sincronización (simulado) + conectividad real
    └── views/                    # Una vista por archivo
        ├── login.py              # Usuario + contraseña (igual que LoginScreen.kt)
        ├── dashboard.py          # Saludo, estado de sync, tarjetas de servicios, conexión
        ├── storage.py            # Mis archivos (buscar, ordenar, lista/cuadrícula, detalles)
        ├── shared_files.py       # Compartidos conmigo
        ├── compartir_dialog.py   # Compartir con usuario/grupo y permisos Unix
        ├── streaming.py          # Catálogo en cuadrícula + videos locales
        ├── hpc.py                # Clúster, trabajos y "Nuevo trabajo"
        ├── sync.py               # Carpeta local a sincronizar
        ├── album.py              # Álbum de fotos
        ├── settings.py           # Conexión + apariencia
        ├── conexion_form.py      # Formulario de conexión (Configuración y login)
        └── about.py
```

Reglas de dependencia (bajo acoplamiento):
- `views/` dependen de `theme`, `widgets`, `utils`, `config` y reciben la app
  como parámetro; **no** importan `app.py`.
- Las vistas solo hablan con `app.api` (ApiClient); nunca saben si por debajo
  hay SOAP, REST o datos simulados.
- Las llamadas de red corren en un hilo (`utils.run_async`), así la ventana no
  se congela; cada lista pinta los estados *Cargando / Error / Vacío / Datos*
  (el `UiState` del móvil).

## Requisitos

- Python 3.9 o superior
- Paquetes (`requirements.txt`): `customtkinter`, `Pillow`, `av` (PyAV, trae
  ffmpeg incluido) y `sounddevice` (audio del reproductor). La red usa solo la
  biblioteca estándar.
- Los servicios encendidos. En el PC de desarrollo los arranca
  `UPB-CIENTIFICA/despliegue/cluster-virtualbox/7-iniciar-servicios-windows.ps1 -HpcLocal`.

En **Linux** puede que necesites Tkinter del sistema: `sudo apt install python3-tk`

## Abrir con doble clic

- **Windows:** doble clic en **`Abrir UPB-Cientifica.bat`**. La primera vez
  instala las dependencias y abre la app sin consola. Ya no lanza el mock de
  autenticación: el puerto 8080 es ahora el de node-web.
- **Linux:** `./abrir.sh` (o doble clic → "Ejecutar").

Solo hace falta tener Python instalado (con "Add Python to PATH").

## Instalación y ejecución manual

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Autenticación

Por defecto la app usa el Authentication Service real en el **8081**
(node-soap, o `herramientas/auth-local.js` del monorepo en desarrollo). Usuarios
de prueba: `user1 / 1234`, `investigador / test`, `estudiante / test`.

El mock antiguo (`mock-auth-server/server.js`, puerto 8080) sigue disponible
desde Configuración, pero choca con node-web si están en el mismo PC.

### Configurar la conexión

Desde **Configuración** (o "Configurar conexión" en el login):

- **Entorno LOCAL:** todos los servicios en el host indicado (por defecto
  `127.0.0.1`; se evita `localhost` porque en Windows intenta IPv6 primero y
  añade ~2 s a cada llamada si el servicio solo escucha en IPv4).
- **Entorno LABORATORIO:** una IP por VM (SOAP 8081, Storage 8084 y Shared
  File 8085 en la VM node-repository, Media 8083, Sync 9090, job-api 8082 en
  hpc-master).
- Interruptores: mock de autenticación, Storage/Streaming/HPC simulados,
  Shared File disponible.

Una configuración guardada por una versión anterior (mock activado, Shared File
apagado) se corrige sola la primera vez que se abre la app.

Se guarda en `~/.upbcientifica/config.json`. En modo simulado, Storage usa un
Home local en `~/.upbcientifica/home`.

## Notas para los desarrolladores de los servidores

Los endpoints y campos son **exactamente los del cliente móvil** (ver la docstring
de cada módulo en `app/data/`):

- **Auth (SOAP):** `login(usuario, contrasena, origenCliente="desktop")` →
  `token`, `roles`, `mapaServiciosAutorizados`; `validarToken(token)`; `logout(token)`.
  La operación va con prefijo `ns:` y sus hijos sin namespace (`unqualified`).
- **Storage (REST):** `GET /storage/directorios/{id}` (raíz = `root`),
  `POST /storage/archivos` (multipart, campo `archivo`, `?directorioDestino=&sobrescribir=`),
  `GET /storage/archivos/{id}/descargar`, `DELETE /storage/archivos/{id}`.
- **Shared File (REST):** `POST /shared-file/compartir`,
  `GET /shared-file/compartidos-conmigo`, `DELETE /shared-file/compartir/{id}`.
- **Streaming (REST):** `GET /streaming/catalogo?pagina=N`,
  `GET /streaming/buscar?criterioTexto=...`, `GET /streaming/{id}/sesion`.

## Modos de prueba

- `python main.py --smoke` — recorre todas las vistas en modo demo y cierra.
- `python main.py --stay view=<nombre>` — abre una vista en modo demo
  (`dashboard`, `storage`, `shared`, `streaming`, `hpc`, `sync`, `album`, `settings`, `about`).
