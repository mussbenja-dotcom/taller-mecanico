"""ESQUEMAS de Venta de mostrador (Pydantic)."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class VentaItemCrear(BaseModel):
    repuesto_id: int
    cantidad: Decimal = Decimal(1)
    # opcionales: si no se mandan, se toman del repuesto (nombre y precio actual)
    descripcion: str | None = None
    precio_unitario: Decimal | None = None


class VentaItemRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    repuesto_id: int | None
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    subtotal: Decimal = Decimal(0)


class VentaCrear(BaseModel):
    cliente_id: int | None = None  # None = venta anónima ("consumidor final")
    forma_pago: str | None = None
    notas: str | None = None
    items: list[VentaItemCrear] = []


class VentaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cliente_id: int | None
    forma_pago: str | None
    notas: str | None
    creado_en: datetime
    items: list[VentaItemRespuesta] = []
    total: Decimal = Decimal(0)
