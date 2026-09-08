"""CONTROLADOR de autenticación: login y logout (contra la base de datos)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.nucleo.base_datos import obtener_sesion
from app.nucleo import auth
from app.servicios.usuario_servicio import ServicioUsuario
from app.esquemas.usuario import LoginDatos

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(datos: LoginDatos, sesion: AsyncSession = Depends(obtener_sesion)):
    u = await ServicioUsuario.autenticar(sesion, datos.usuario.strip(), datos.password)
    if not u:
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    token = auth.crear_token(u.usuario, u.rol)
    return {"token": token, "usuario": u.usuario, "nombre": u.nombre, "rol": u.rol}


class LogoutDatos(BaseModel):
    token: str


@router.post("/logout")
async def logout(datos: LogoutDatos):
    auth.cerrar_sesion(datos.token)
    return {"ok": True}
