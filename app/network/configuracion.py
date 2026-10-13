# -*- coding: utf-8 -*-
"""Único lugar donde se resuelven las direcciones de los servicios.

Es el equivalente de `network/Configuracion.kt` del cliente móvil, con una
diferencia: aquí los valores no están escritos en el código sino en la
configuración local (~/.upbcientifica/config.json) y se editan desde la vista
Configuración, así que cambiar de PC a laboratorio no exige tocar código.

Puertos (los mismos que usa el móvil):
  - Auth SOAP: node-soap en 8081 (/soap/user.php); mock antiguo en 8080
  - Storage (node-repository): 8084
  - Shared File (node-shared-file, en la VM node-repository): 8085
  - Photo Album + Streaming (node-media): 8083
  - HPC (job-api, fachada REST del gestor RMI, en hpc-master): 8082
  - File Sync (node-sync, gRPC): 9090
"""

import ssl
from pathlib import Path

ENTORNOS = ("LOCAL", "LABORATORIO")

# targetNamespace del WSDL de node-soap. Es un IDENTIFICADOR del contrato, no
# una dirección: no cambia aunque el servicio se mueva de máquina. El mock no
# lo valida (despacha por SOAPAction), así que sirve para ambos casos.
NAMESPACE_AUTH = "http://192.168.1.195/soap"

# CA interna que firma los certificados de las VMs (node-soap 8081 y node-sync
# 9090). Es pública: se descarga también en https://<node-web>/upbc-ca.crt.
RUTA_CA = Path(__file__).resolve().parent.parent / "assets" / "upbc-ca.crt"


class Configuracion:
    def __init__(self, cfg):
        self.cfg = cfg

    # --- Valores base -------------------------------------------------------
    @property
    def entorno(self):
        valor = self.cfg.get("entorno", "LOCAL")
        return valor if valor in ENTORNOS else "LOCAL"

    @property
    def en_laboratorio(self):
        return self.entorno == "LABORATORIO"

    @property
    def host_desarrollo(self):
        return (self.cfg.get("host_desarrollo") or "127.0.0.1").strip()

    @property
    def usar_mock_auth(self):
        return bool(self.cfg.get("usar_mock_auth", True))

    @property
    def shared_file_disponible(self):
        return bool(self.cfg.get("shared_file_disponible", False))

    @property
    def storage_simulado(self):
        return bool(self.cfg.get("storage_simulado", False))

    @property
    def streaming_simulado(self):
        return bool(self.cfg.get("streaming_simulado", False))

    @property
    def hpc_simulado(self):
        return bool(self.cfg.get("hpc_simulado", False))

    def _host(self, clave_lab):
        return self.cfg.get(clave_lab) if self.en_laboratorio else self.host_desarrollo

    # --- Direcciones --------------------------------------------------------
    @property
    def url_auth(self):
        if self.usar_mock_auth:
            return f"http://{self.host_desarrollo}:8080/AuthenticationService"
        if self.en_laboratorio:
            return f"https://{self.cfg.get('host_soap_lab')}:8081/soap/user.php"
        return f"http://{self.host_desarrollo}:8081/soap/user.php"

    @property
    def url_storage(self):
        return f"http://{self._host('host_storage_lab')}:8084/"

    @property
    def url_media(self):
        return f"http://{self._host('host_media_lab')}:8083/"

    @property
    def url_compartidos(self):
        """Shared File vive en la misma VM que Storage (shared-file-svc)."""
        return f"http://{self._host('host_storage_lab')}:8085/"

    @property
    def url_trabajos(self):
        """job-api: el escritorio no habla RMI, habla REST con la fachada del gestor."""
        return f"http://{self._host('host_hpc_lab')}:8082/"

    @property
    def direccion_sync(self):
        return f"{self._host('host_sync_lab')}:9090"

    # --- TLS ------------------------------------------------------------------
    def contexto_tls(self):
        """Contexto HTTPS: raíces del sistema más la CA interna del proyecto."""
        ctx = ssl.create_default_context()
        if RUTA_CA.exists():
            ctx.load_verify_locations(cafile=str(RUTA_CA))
        return ctx

    @property
    def ca_sync(self):
        """En el laboratorio node-sync va por gRPC/TLS; en el PC, en claro."""
        return str(RUTA_CA) if self.en_laboratorio and RUTA_CA.exists() else None

    def descripcion_auth(self):
        return "Mock (server.js)" if self.usar_mock_auth else "node-soap"
