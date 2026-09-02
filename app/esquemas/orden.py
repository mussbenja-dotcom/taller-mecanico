"""ESQUEMAS de Orden de Trabajo (Pydantic)."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class OrdenItemBase(BaseModel):
    descripcion: str
    cantidad: Decimal = Decimal(1)
    precio_unitario: Decimal = Decimal(0)
    es_repuesto: bool = True
    repuesto_id: int | None = None


class OrdenItemCrear(OrdenItemBase):
    pass


class OrdenItemRespuesta(OrdenItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subtotal: Decimal = Decimal(0)


class OrdenCrear(BaseModel):
    auto_id: int
    descripcion: str | None = None
    notas: str | None = None
    items: list[OrdenItemCrear] = []


class OrdenDesdePresupuesto(BaseModel):
    """Crear una orden copiando los datos de un presupuesto existente."""
    presupuesto_id: int


class OrdenActualizar(BaseModel):
    """La orden NO se borra, pero se pueden ajustar datos e ítems mientras no esté cerrada."""
    descripcion: str | None = None
    notas: str | None = None
    items: list[OrdenItemCrear] | None = None


class OrdenCambiarEstado(BaseModel):
    estado: str  # 'pendiente' | 'finalizada' | 'cobrada'


class OrdenRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    auto_id: int
    presupuesto_id: int | None
    descripcion: str | None
    estado: str
    notas: str | None
    creado_en: datetime
    actualizado_en: datetime
    finalizada_en: datetime | None
    items: list[OrdenItemRespuesta] = []
    total: Decimal = Decimal(0)
