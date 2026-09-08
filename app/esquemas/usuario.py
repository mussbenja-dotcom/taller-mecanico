"""ESQUEMAS de Usuario (Pydantic)."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class LoginDatos(BaseModel):
    usuario: str      # email (admin) o nombre (empleado)
    password: str


class EmpleadoCrear(BaseModel):
    nombre: str
    password: str


class EmpleadoActualizar(BaseModel):
    nombre: str | None = None
    password: str | None = None   # si viene, se cambia la contraseña
    activo: bool | None = None


class UsuarioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario: str
    nombre: str
    rol: str
    activo: bool
    creado_en: datetime
