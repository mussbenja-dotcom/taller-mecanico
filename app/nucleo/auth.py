"""
Autenticación con roles (admin / empleado), contra la base de datos.

- Las contraseñas se guardan HASHEADAS con bcrypt (nunca en texto plano).
- El login lo maneja ServicioUsuario (habla con la base). Acá viven:
    * el hashing / verificación de contraseñas
    * la gestión de tokens de sesión (en memoria)
    * la dependencia requiere_rol para proteger endpoints en el backend
"""
import secrets
import bcrypt
from fastapi import Header, HTTPException


# ---------- contraseñas (bcrypt) ----------
def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


# ---------- tokens de sesión ----------
# token -> {"usuario": str, "rol": str}
_TOKENS: dict[str, dict] = {}


def crear_token(usuario: str, rol: str) -> str:
    token = secrets.token_urlsafe(32)
    _TOKENS[token] = {"usuario": usuario, "rol": rol}
    return token


def datos_de_token(token: str | None) -> dict | None:
    return _TOKENS.get(token) if token else None


def rol_de_token(token: str | None) -> str | None:
    d = _TOKENS.get(token) if token else None
    return d["rol"] if d else None


def usuario_de_token(token: str | None) -> str | None:
    d = _TOKENS.get(token) if token else None
    return d["usuario"] if d else None


def token_valido(token: str | None) -> bool:
    return bool(token) and token in _TOKENS


def cerrar_sesion(token: str) -> None:
    _TOKENS.pop(token, None)


# ---------- dependencias de FastAPI ----------
def _extraer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    partes = authorization.split()
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1]
    return authorization


def requiere_rol(*roles_permitidos: str):
    """Dependencia que exige uno de los roles. Uso: Depends(requiere_rol("admin"))."""
    async def verificar(authorization: str | None = Header(default=None)) -> str:
        token = _extraer_token(authorization)
        rol = rol_de_token(token)
        if not rol:
            raise HTTPException(401, "No autenticado. Iniciá sesión.")
        if roles_permitidos and rol not in roles_permitidos:
            raise HTTPException(403, "No tenés permisos para esta acción.")
        return rol
    return verificar
