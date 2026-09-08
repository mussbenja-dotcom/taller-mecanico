"""ESQUEMAS de Compra (Pydantic)."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class CompraCrear(BaseModel):
    repuesto_id: int
    proveedor_id: int | None = None
    fecha: date
    cantidad: int
    costo_unitario: Decimal


class CompraRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    repuesto_id: int
    proveedor_id: int | None
    fecha: date
    cantidad: int
    costo_unitario: Decimal
    creado_en: datetime
