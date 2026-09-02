"""ESQUEMAS de Presupuesto (Pydantic)."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


# ---- ítems ----
class ItemBase(BaseModel):
    descripcion: str
    cantidad: Decimal = Decimal(1)
    precio_unitario: Decimal = Decimal(0)
    es_repuesto: bool = True


class ItemCrear(ItemBase):
    pass


class ItemRespuesta(ItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subtotal: Decimal = Decimal(0)  # se calcula en el servicio


# ---- presupuesto ----
class PresupuestoCrear(BaseModel):
    auto_id: int
    descripcion: str | None = None
    notas: str | None = None
    items: list[ItemCrear] = []


class PresupuestoActualizar(BaseModel):
    descripcion: str | None = None
    notas: str | None = None
    # si mandan items, reemplazan a los actuales
    items: list[ItemCrear] | None = None


class PresupuestoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    auto_id: int
    descripcion: str | None
    notas: str | None
    creado_en: datetime
    actualizado_en: datetime
    items: list[ItemRespuesta] = []
    total: Decimal = Decimal(0)  # se calcula en el servicio
