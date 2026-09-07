"""ESQUEMAS de Proveedor (Pydantic)."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProveedorBase(BaseModel):
    nombre: str
    telefono: str | None = None
    notas: str | None = None


class ProveedorCrear(ProveedorBase):
    pass


class ProveedorActualizar(BaseModel):
    nombre: str | None = None
    telefono: str | None = None
    notas: str | None = None


class ProveedorRespuesta(ProveedorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    creado_en: datetime
    actualizado_en: datetime
