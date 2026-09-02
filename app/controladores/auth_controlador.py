"""CONTROLADOR de autenticación: login y logout del dueño."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.nucleo import auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginDatos(BaseModel):
    usuario: str
    password: str


@router.post("/login")
async def login(datos: LoginDatos):
    if not auth.verificar_credenciales(datos.usuario, datos.password):
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    token = auth.crear_token()
    return {"token": token, "usuario": datos.usuario}


class LogoutDatos(BaseModel):
    token: str


@router.post("/logout")
async def logout(datos: LogoutDatos):
    auth.cerrar_sesion(datos.token)
    return {"ok": True}
