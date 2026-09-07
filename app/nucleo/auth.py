"""
Autenticación con roles (admin / empleado).

DOS usuarios fijos, configurables por variables de entorno (.env):
  ADMIN_USUARIO=admin
  ADMIN_PASSWORD=taller2025
  EMPLEADO_USUARIO=empleado
  EMPLEADO_PASSWORD=taller123

Roles:
  - admin: ve y hace todo.
  - empleado: solo órdenes + diagnóstico IA. No ve métricas, stock ni precios.

NOTA: login básico (usuarios fijos, token en memoria). Para producción seria
conviene guardar usuarios en la base con contraseñas hasheadas. Suficiente
para arrancar con un dueño y un empleado.
"""
import os
import secrets

# usuarios fijos: {usuario: (password, rol)}
_USUARIOS = {
    os.getenv("ADMIN_USUARIO", "admin"): (
        os.getenv("ADMIN_PASSWORD", "taller2025"), "admin"
    ),
    os.getenv("EMPLEADO_USUARIO", "empleado"): (
        os.getenv("EMPLEADO_PASSWORD", "taller123"), "empleado"
    ),
}

# token -> rol
_TOKENS: dict[str, str] = {}


def verificar_credenciales(usuario: str, password: str) -> str | None:
    """Devuelve el rol si las credenciales son válidas, si no None."""
    datos = _USUARIOS.get(usuario)
    if not datos:
        return None
    pass_ok, rol = datos
    if secrets.compare_digest(password, pass_ok):
        return rol
    return None


def crear_token(rol: str) -> str:
    token = secrets.token_urlsafe(32)
    _TOKENS[token] = rol
    return token


def rol_de_token(token: str | None) -> str | None:
    return _TOKENS.get(token) if token else None


def token_valido(token: str | None) -> bool:
    return bool(token) and token in _TOKENS


def cerrar_sesion(token: str) -> None:
    _TOKENS.pop(token, None)


# ============================================================
# Dependencias de FastAPI para validar rol en el BACKEND.
# Hasta ahora el control de rol vivía solo en el frontend (esconder botones).
# Esto agrega validación real: aunque alguien llame la API directo, se controla.
# El frontend manda el token en el header "Authorization: Bearer <token>".
# ============================================================
from fastapi import Header, HTTPException


def _extraer_token(authorization: str | None) -> str | None:
    """Saca el token del header 'Authorization: Bearer <token>'."""
    if not authorization:
        return None
    partes = authorization.split()
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1]
    return authorization  # por si mandan el token pelado


def requiere_rol(*roles_permitidos: str):
    """
    Devuelve una dependencia que exige que el usuario tenga uno de los roles
    indicados. Uso: Depends(requiere_rol("admin")).
    """
    async def verificar(authorization: str | None = Header(default=None)) -> str:
        token = _extraer_token(authorization)
        rol = rol_de_token(token)
        if not rol:
            raise HTTPException(401, "No autenticado. Iniciá sesión.")
        if roles_permitidos and rol not in roles_permitidos:
            raise HTTPException(403, "No tenés permisos para esta acción.")
        return rol
    return verificar
