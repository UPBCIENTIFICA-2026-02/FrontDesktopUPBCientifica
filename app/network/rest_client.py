# -*- coding: utf-8 -*-
"""Cliente REST (equivalente a RestClient.kt + AuthHeaderInterceptor).

Un mismo patrón sirve para Storage, Shared File y Streaming: cada uno solo
cambia la URL base. A cada llamada se le añade el token de sesión emitido por
Authentication Service en el header `Authorization: Bearer <token>`.
Solo usa la biblioteca estándar (urllib), sin dependencias nuevas.
"""

import json
import mimetypes
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
import uuid


class ServicioError(Exception):
    """Fallo al hablar con un servicio REST, con un mensaje legible."""


class RestClient:
    # Subir o bajar un archivo grande tarda más que una llamada normal, pero
    # sin límite una VM caída deja la pantalla colgada.
    TIMEOUT = 60

    def __init__(self, base_url, token_manager, nombre_servicio="servicio"):
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.tokens = token_manager
        self.nombre = nombre_servicio

    # --- API pública --------------------------------------------------------
    def get_json(self, path, params=None):
        return self._json(self._request("GET", path, params))

    def delete(self, path):
        self._request("DELETE", path).close()

    def post_json(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        return self._json(self._request("POST", path, body=data,
                                        headers={"Content-Type": "application/json"}))

    def post_multipart(self, path, campo, file_path, params=None):
        boundary = uuid.uuid4().hex
        nombre = os.path.basename(file_path)
        tipo = mimetypes.guess_type(nombre)[0] or "application/octet-stream"
        with open(file_path, "rb") as f:
            contenido = f.read()
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{campo}"; filename="{nombre}"\r\n'
            f"Content-Type: {tipo}\r\n\r\n"
        ).encode("utf-8") + contenido + f"\r\n--{boundary}--\r\n".encode("utf-8")
        return self._json(self._request(
            "POST", path, params, body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}))

    def download(self, path, destino):
        resp = self._request("GET", path)
        with resp, open(destino, "wb") as out:
            shutil.copyfileobj(resp, out)
        return destino

    # --- Interno ------------------------------------------------------------
    def _request(self, method, path, params=None, body=None, headers=None):
        url = urllib.parse.urljoin(self.base_url, path.lstrip("/"))
        if params:
            url += "?" + urllib.parse.urlencode(params)
        h = {"Accept": "application/json"}
        h.update(headers or {})
        token = self.tokens.current_token()
        if token:
            h["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=body, method=method, headers=h)
        try:
            return urllib.request.urlopen(req, timeout=self.TIMEOUT)
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8", "replace")[:200]
            if e.code in (401, 403):
                raise ServicioError(
                    f"{self.nombre}: sesión no autorizada (HTTP {e.code}). "
                    "Vuelve a iniciar sesión.") from e
            raise ServicioError(f"{self.nombre} respondió HTTP {e.code}: {detalle}") from e
        except urllib.error.URLError as e:
            raise ServicioError(
                f"No se pudo conectar con {self.nombre} en {self.base_url} ({e.reason}).") from e
        except TimeoutError as e:
            raise ServicioError(f"{self.nombre} no respondió a tiempo ({self.base_url}).") from e

    def _json(self, resp):
        with resp:
            raw = resp.read().decode("utf-8", "replace")
        if not raw.strip():
            return None
        try:
            return json.loads(raw)
        except ValueError as e:
            raise ServicioError(f"{self.nombre} no devolvió JSON: {raw[:200]}") from e
