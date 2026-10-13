# -*- coding: utf-8 -*-
"""Cliente SOAP 1.1 mínimo, sin librerías externas (igual que SoapClient.kt).

Arma el sobre como XML, lo envía por POST y devuelve el árbol de la respuesta.
"""

import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


class SoapClient:
    def __init__(self, endpoint_url, namespace, timeout=15, contexto_ssl=None):
        self.endpoint_url = endpoint_url
        self.namespace = namespace
        self.timeout = timeout
        # node-soap va por HTTPS con un certificado de la CA interna del proyecto.
        self.contexto_ssl = contexto_ssl

    def invoke(self, operation, params):
        """Invoca una operación. `params` va en el orden que declara el WSDL.

        La respuesta se parsea TAMBIÉN cuando el servidor contesta con error: un
        500 de SOAP trae un Fault con el motivo (el mock responde 500 con el
        detalle cuando las credenciales no valen).
        """
        body = self._envelope(operation, params).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url, data=body, method="POST",
            headers={
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": f"{self.namespace}/{operation}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.contexto_ssl) as resp:
                codigo, xml = resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            codigo, xml = e.code, e.read().decode("utf-8", "replace")
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"No se pudo conectar con el servicio de autenticación en "
                f"{self.endpoint_url} ({e.reason}).") from e
        except TimeoutError as e:
            raise ConnectionError(
                f"El servicio de autenticación no respondió a tiempo ({self.endpoint_url}).") from e

        if not xml.strip():
            raise RuntimeError(
                f"El servicio de autenticación respondió vacío (HTTP {codigo}) en {operation}")
        try:
            return ET.fromstring(xml)
        except ET.ParseError as e:
            raise RuntimeError(
                f"El servicio de autenticación no devolvió XML en {operation} "
                f"(HTTP {codigo}): {xml[:200]}") from e

    def _envelope(self, operation, params):
        """El elemento de la operación va en el namespace del WSDL; sus HIJOS no.

        users.wsdl no declara `elementFormDefault`, así que rige "unqualified":
        con `xmlns=` por defecto los hijos heredarían el namespace y PHP los
        leería vacíos, respondiendo "usuario o contraseña incorrectos".
        """
        params_xml = "".join(
            f"<{k}>{escape('' if v is None else str(v))}</{k}>" for k, v in params.items())
        return (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" '
            f'xmlns:ns="{self.namespace}">'
            f"<soap:Body><ns:{operation}>{params_xml}</ns:{operation}></soap:Body>"
            "</soap:Envelope>"
        )


def tag_text(root, local_name):
    """Texto del primer elemento con ese nombre local, ignorando el namespace."""
    for el in root.iter():
        if isinstance(el.tag, str) and el.tag.rsplit("}", 1)[-1] == local_name:
            return (el.text or "").strip()
    return None
