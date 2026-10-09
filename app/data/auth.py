# -*- coding: utf-8 -*-
"""Authentication Service (SOAP). Equivale a AuthRepository.kt + AuthModels.kt.

Contrato: operaciones `login`, `validarToken` y `logout` del WSDL de node-soap
(users.wsdl). `login`/`logout` existen ahí como alias de `iniciarSesion` /
`cerrarSesion` con la forma que usan los clientes (roles y servicios como una
cadena separada por comas).
"""

from dataclasses import dataclass, field

from ..network.soap_client import tag_text


@dataclass
class SessionResult:
    token: str
    usuario: str
    roles: list = field(default_factory=list)
    servicios_autorizados: list = field(default_factory=list)


class AuthError(Exception):
    pass


class CredencialesInvalidas(AuthError):
    def __init__(self):
        super().__init__("Usuario o contraseña incorrectos")


class CuentaBloqueada(AuthError):
    def __init__(self):
        super().__init__("La cuenta está bloqueada")


class AuthRepository:
    def __init__(self, soap, token_manager):
        self.soap = soap
        self.tokens = token_manager

    def login(self, usuario, contrasena, origen_cliente="desktop"):
        resp = self.soap.invoke("login", {
            "usuario": usuario,
            "contrasena": contrasena,
            "origenCliente": origen_cliente,
        })
        token = tag_text(resp, "token")
        if not token:
            # Sin token, el servidor ya explicó por qué en alguno de estos
            # elementos: así se distingue una clave mal escrita de un LDAP caído.
            motivo = (tag_text(resp, "message") or tag_text(resp, "error")
                      or tag_text(resp, "faultstring"))
            if not motivo:
                raise AuthError("El servicio de autenticación no devolvió token")
            m = motivo.lower()
            if "bloquead" in m:
                raise CuentaBloqueada()
            if "incorrect" in m or "inválid" in m or "invalid" in m:
                raise CredencialesInvalidas()
            raise AuthError(motivo)

        self.tokens.save_token(token)
        return SessionResult(
            token=token,
            usuario=usuario,
            roles=_lista(tag_text(resp, "roles")),
            servicios_autorizados=_lista(tag_text(resp, "mapaServiciosAutorizados")),
        )

    def validar_token(self):
        token = self.tokens.current_token()
        if not token:
            return False
        resp = self.soap.invoke("validarToken", {"token": token})
        return (tag_text(resp, "valido") or "").lower() == "true"

    def logout(self):
        """El token se borra pase lo que pase: si el servidor no responde, la
        sesión local tiene que cerrarse igual."""
        token = self.tokens.current_token()
        if not token:
            return
        try:
            self.soap.invoke("logout", {"token": token})
        finally:
            self.tokens.clear()


def _lista(valor):
    """"a,b, c" -> ["a","b","c"]; None o vacío -> []."""
    return [p.strip() for p in (valor or "").split(",") if p.strip()]
