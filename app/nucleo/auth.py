"""
Autenticación simple para el dueño del taller.

IMPORTANTE (leer): esto es un login BÁSICO, pensado para uso local o para un
único dueño. Guarda usuario/contraseña en variables de entorno y entrega un
token simple. Para producción en internet conviene reforzarlo (contraseñas
hasheadas en base, expiración de tokens, etc.) — es el "Paso 3" que quedó pendiente.

Usuario y contraseña por defecto (cambialos en el archivo .env):
  ADMIN_USUARIO=admin
  ADMIN_PASSWORD=taller2025
"""
import os
import secrets

USUARIO = os.getenv("ADMIN_USUARIO", "admin")
PASSWORD = os.getenv("ADMIN_PASSWORD", "taller2025")

# token de sesión que se genera al arrancar (simple, en memoria)
_TOKENS_VALIDOS: set[str] = set()


def verificar_credenciales(usuario: str, password: str) -> bool:
    # comparación segura contra timing attacks
    u_ok = secrets.compare_digest(usuario, USUARIO)
    p_ok = secrets.compare_digest(password, PASSWORD)
    return u_ok and p_ok


def crear_token() -> str:
    token = secrets.token_urlsafe(32)
    _TOKENS_VALIDOS.add(token)
    return token


def token_valido(token: str | None) -> bool:
    return bool(token) and token in _TOKENS_VALIDOS


def cerrar_sesion(token: str) -> None:
    _TOKENS_VALIDOS.discard(token)
