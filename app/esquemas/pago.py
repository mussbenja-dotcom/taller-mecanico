"""ESQUEMAS de Pago (cuenta corriente)."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class PagoCrear(BaseModel):
    orden_id: int
    fecha: date
    monto: Decimal
    nota: str | None = None


class PagoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    orden_id: int
    fecha: date
    monto: Decimal
    nota: str | None
    creado_en: datetime
