# UPB-CIENTÍFICA — Cliente de Escritorio (Windows / Linux)

Cliente de escritorio del sistema distribuido **UPB-CIENTÍFICA** (proyecto de
**Sistemas Distribuidos 2026-20**, UPB Bucaramanga). Corresponde al consumidor
**"Desktop Windows/Linux"** de la Figura 1 del proyecto.

> **Lenguaje:** Python + CustomTkinter (el PDF no fija lenguaje para el cliente
> de escritorio; los lenguajes obligatorios aplican a los servidores).

Este cliente está **alineado con el cliente móvil** (`FrontMovilUPBCientifica`,
Kotlin + Jetpack Compose):

- **Mismo diseño:** paleta Material Design 3 (primario `#6750A4`), tarjetas,
  listas con divisores, botones redondeados, modo claro y oscuro.
- **Mismos contratos y puertos:** se conecta **directamente** a cada servicio
  con su protocolo nativo, sin pasar por el gateway del cliente Web.

| Servicio            | Protocolo | Estado en el cliente de escritorio |
|---------------------|-----------|------------------------------------|
| Authentication      | SOAP      | **Conectado** (mock `server.js` u node-soap real) |
| Distributed Storage | HTTP/REST | **Conectado** a node-repository (8084): listar, navegar carpetas, subir, descargar, eliminar |
| Streaming           | HTTP/REST | **Conectado** a node-media (8083): catálogo, búsqueda, paginación, reproducir |
| Shared File         | HTTP/REST | Simulado: el servicio no existe en el backend (compartir / revocar listos) |
| File Sync           | gRPC      | Pendiente: falta generar el stub del `.proto` (detección local de cambios) |
| HPC                 | RMI       | Pendiente: RMI solo existe en la JVM (cola local de trabajos) |

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
    ├── theme.py                  # Tokens de color Material 3 (claro/oscuro) + tipografía
    ├── assets/upb_material3.json # Tema de CustomTkinter con la paleta del móvil
    ├── widgets.py                # Componentes UI (Card, ListItem, Divider, botones, StatePanel)
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
    │   └── pendientes.py         #   File Sync (gRPC) y HPC (RMI)
    └── views/                    # Una vista por archivo
        ├── login.py              # Usuario + contraseña (igual que LoginScreen.kt)
        ├── dashboard.py          # Tiles de servicios + sesión + estado de conexión
        ├── storage.py            # Mis archivos
        ├── shared_files.py       # Compartidos conmigo
        ├── compartir_dialog.py   # Compartir con usuario/grupo y permisos Unix
        ├── streaming.py          # Catálogo del servidor + videos locales
        ├── sync.py               # Sincronización
        ├── jobs.py               # Trabajos HPC
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
- Paquetes: `customtkinter`, `Pillow` (la red usa solo la biblioteca estándar)
- Node.js (solo para el mock del Authentication Service)

En **Linux** puede que necesites Tkinter del sistema: `sudo apt install python3-tk`

## Abrir con doble clic

- **Windows:** doble clic en **`Abrir UPB-Cientifica.bat`**. La primera vez
  instala `customtkinter` y `Pillow`; si hay Node.js, levanta también el mock de
  autenticación (ventana minimizada "Mock Auth UPB") y abre la app sin consola.
- **Linux:** `./abrir.sh` (o doble clic → "Ejecutar").

Solo hace falta tener Python instalado (con "Add Python to PATH").

## Instalación y ejecución manual

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Levantar el mock del Authentication Service

```bash
cd mock-auth-server
node server.js
```

Escucha en el puerto **8080**. Usuarios de prueba: `user1 / 1234` e
`investigador / test`. Emite tokens `mock-token-<usuario>-abc123`, el formato
que aceptan Storage y Media cuando corren con `MODO_AUTENTICACION=simulado`.

### Configurar la conexión

Desde **Configuración** (o "Configurar conexión" en el login):

- **Entorno LOCAL:** todos los servicios en el host indicado (por defecto
  `127.0.0.1`; se evita `localhost` porque en Windows intenta IPv6 primero y
  añade ~2 s a cada llamada si el servicio solo escucha en IPv4).
- **Entorno LABORATORIO:** una IP por VM (SOAP 8081, Storage 8084, Media 8083,
  Sync 9090).
- Interruptores: usar mock de autenticación, Storage/Streaming simulados,
  Shared File disponible.

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
  (`dashboard`, `storage`, `shared`, `streaming`, `sync`, `jobs`, `album`, `settings`, `about`).
