"""
ESQUEMAS de Cliente (Pydantic).
Definen qué datos entran (crear/actualizar) y qué datos salen (respuesta).
Es el "contrato": valida antes de que el dato llegue a la lógica.
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.esquemas.auto import AutoRespuesta


class ClienteBase(BaseModel):
    nombre: str
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    notas: str | None = None


class ClienteCrear(ClienteBase):
    pass


class ClienteActualizar(BaseModel):
    nombre: str | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    notas: str | None = None


class ClienteRespuesta(ClienteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    creado_en: datetime
    actualizado_en: datetime


class ClienteConAutos(ClienteRespuesta):
    autos: list[AutoRespuesta] = []
