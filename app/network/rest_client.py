# -*- coding: utf-8 -*-
"""Cliente REST (equivalente a RestClient.kt + AuthHeaderInterceptor).

Un mismo patrón sirve para Storage, Shared File, Streaming y HPC: cada uno solo
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
    """Fallo al hablar con un servicio REST, con un mensaje legible.

    `codigo` es el código de error del servicio ("SHR-003", "NO_ENCONTRADO"...)
    y `estado` el HTTP, por si la vista quiere distinguir casos."""

    def __init__(self, mensaje, estado=None, codigo=None):
        super().__init__(mensaje)
        self.estado = estado
        self.codigo = codigo


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

    def get_bytes(self, path):
        with self._request("GET", path) as resp:
            return resp.read()

    def delete(self, path, params=None):
        self._request("DELETE", path, params).close()

    def post_json(self, path, payload=None):
        return self._con_cuerpo("POST", path, payload)

    def patch_json(self, path, payload):
        return self._con_cuerpo("PATCH", path, payload)

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

    def url(self, path):
        """URL absoluta de una ruta del servicio (para el reproductor de video)."""
        return urllib.parse.urljoin(self.base_url, path.lstrip("/"))

    def cabeceras_auth(self):
        """Cabecera con el token: el reproductor la manda en cada petición por rangos."""
        token = self.tokens.current_token()
        return {"Authorization": f"Bearer {token}"} if token else {}

    # --- Interno ------------------------------------------------------------
    def _con_cuerpo(self, metodo, path, payload):
        data = json.dumps(payload if payload is not None else {}).encode("utf-8")
        return self._json(self._request(metodo, path, body=data,
                                        headers={"Content-Type": "application/json"}))

    def _request(self, method, path, params=None, body=None, headers=None):
        url = self.url(path)
        if params:
            url += "?" + urllib.parse.urlencode(params)
        h = {"Accept": "application/json"}
        h.update(headers or {})
        h.update(self.cabeceras_auth())
        req = urllib.request.Request(url, data=body, method=method, headers=h)
        try:
            return urllib.request.urlopen(req, timeout=self.TIMEOUT)
        except urllib.error.HTTPError as e:
            raise self._error_http(e) from e
        except urllib.error.URLError as e:
            raise ServicioError(
                f"No se pudo conectar con {self.nombre} en {self.base_url} ({e.reason}). "
                "¿Está encendido?") from e
        except TimeoutError as e:
            raise ServicioError(f"{self.nombre} no respondió a tiempo ({self.base_url}).") from e

    def _error_http(self, e):
        """Los servicios responden { error, mensaje }: se muestra el mensaje tal cual."""
        crudo = e.read().decode("utf-8", "replace")
        codigo, mensaje = None, None
        try:
            datos = json.loads(crudo)
            codigo, mensaje = datos.get("error"), datos.get("mensaje")
        except (ValueError, AttributeError):
            pass
        if mensaje:
            return ServicioError(mensaje, e.code, codigo)
        if e.code == 401:
            return ServicioError(f"{self.nombre}: la sesión no es válida. Vuelve a iniciar sesión.", 401, codigo)
        if e.code == 403:
            return ServicioError(f"{self.nombre}: no tienes permiso para hacer esto.", 403, codigo)
        return ServicioError(f"{self.nombre} respondió HTTP {e.code}: {crudo[:200]}", e.code, codigo)

    def _json(self, resp):
        with resp:
            raw = resp.read().decode("utf-8", "replace")
        if not raw.strip():
            return None
        try:
            return json.loads(raw)
        except ValueError as e:
            raise ServicioError(f"{self.nombre} no devolvió JSON: {raw[:200]}") from e
