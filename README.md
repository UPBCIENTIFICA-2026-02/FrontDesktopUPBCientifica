# UPB-CIENTÍFICA — Cliente de Escritorio (Windows / Linux)

Cliente de escritorio del sistema distribuido **UPB-CIENTÍFICA** (proyecto de
**Sistemas Distribuidos 2026-20**, UPB Bucaramanga). Corresponde al consumidor
**"Desktop Windows/Linux"** de la Figura 1 del proyecto.

> **Lenguaje:** Python (el PDF no fija lenguaje para el cliente de escritorio;
> los lenguajes obligatorios aplican a los servidores).

## Arquitectura del código (separación por capas)

El proyecto está organizado en módulos con responsabilidades claras, en lugar de
un único archivo, para favorecer el orden, la mantenibilidad y las pruebas:

```
upbcientifica-desktop/
├── main.py                     # Punto de entrada
├── requirements.txt
├── README.md
└── app/
    ├── config.py               # Capa de datos: persistencia (JSON) + rutas + defaults
    ├── api_client.py           # Capa de servicios: ApiClient (frontera con el backend)
    ├── theme.py                # Constantes de UI (paleta, nombre)
    ├── widgets.py              # Componentes de UI reutilizables (tarjetas, botones)
    ├── utils.py                # Utilidades (tamaños, abrir con el sistema)
    ├── app.py                  # Capa de aplicación: ventana principal y navegación
    └── views/                  # Capa de presentación: una vista por archivo
        ├── login.py
        ├── dashboard.py
        ├── jobs.py
        ├── sync.py
        ├── shared_files.py
        ├── album.py
        ├── streaming.py
        ├── settings.py
        └── about.py
```

Reglas de dependencia (bajo acoplamiento):
- `views/` dependen de `theme`, `widgets`, `utils`, `config` y reciben la
  instancia de la app como parámetro. **No** importan `app.py` (se evitan
  importaciones circulares).
- `app.py` conoce a las vistas y a `api_client`.
- `api_client.py` es el **único** punto que hablará con el backend.

## ¿Qué incluye esta entrega?

La **interfaz gráfica completa** y las **funcionalidades que operan sin backend**.

| Módulo | Estado en esta entrega |
|---|---|
| Login (usuario / contraseña / MFA) | Interfaz lista; valida localmente. **TODO:** LDAP + TOTP |
| Trabajos HPC (MPI) | Formulario + cola local (demo). **TODO:** RMI → SLURM/MPI |
| File Sync | Elegir carpeta y listar archivos (local). **TODO:** gRPC |
| Archivos compartidos | Subida a un *Home local* (demo). **TODO:** NFS + permisos Unix |
| Álbum de fotos | **Funciona:** galería real desde una carpeta local |
| Streaming | **Funciona:** reproduce videos con el reproductor del sistema |
| Configuración | **Funciona:** persistente en `~/.upbcientifica/config.json` |

## Requisitos

- Python 3.9 o superior
- Paquetes: `customtkinter`, `Pillow`

En **Linux** puede que necesites Tkinter del sistema:
```bash
sudo apt install python3-tk
```

## Instalación y ejecución

```bash
# 1) (opcional) entorno virtual
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2) dependencias
pip install -r requirements.txt

# 3) ejecutar (desde la carpeta del proyecto)
python main.py
```

En modo demostración puedes iniciar sesión con **cualquier usuario y contraseña**
no vacíos.

## Conexión con el backend (siguientes fases)

Cada método de `app/api_client.py` tiene un comentario `TODO(backend)` que indica
el servicio del diseño a invocar. Al implementar el backend **solo se cambian esos
métodos**, sin tocar la interfaz:

- **login** → `POST /api/login` (balanceador `srv-web`) → bind LDAP (`inf-ldap`) + TOTP
- **submit_job** → RMI en `srv-rmi` → `sbatch` en `hpc-master` → `mpirun` en los nodos
- **sync_now** → gRPC en `srv-grpc`
- **upload_file / list_home** → `srv-web` → almacenamiento NFS en `sto-nfs`

## Notas

- Configuración y *Home* local se guardan en `~/.upbcientifica/`.
- Modos de prueba:
  - `python main.py --smoke` (recorre las vistas y cierra; útil para CI/headless)
  - `python main.py --stay view=<nombre>` (abre una vista; útil para capturas)
