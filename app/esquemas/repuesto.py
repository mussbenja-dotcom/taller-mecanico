"""ESQUEMAS de Repuesto (Pydantic)."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class RepuestoBase(BaseModel):
    nombre: str
    codigo: str | None = None
    precio: Decimal = Decimal(0)
    cantidad: int = 0
    minimo: int = 1


class RepuestoCrear(RepuestoBase):
    pass


class RepuestoActualizar(BaseModel):
    nombre: str | None = None
    codigo: str | None = None
    precio: Decimal | None = None
    cantidad: int | None = None
    minimo: int | None = None


class RepuestoAjustarStock(BaseModel):
    """Sumar (positivo) o restar (negativo) unidades. Ej: entrada de mercadería +10."""
    delta: int


class RepuestoRespuesta(RepuestoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stock_bajo: bool = False  # se calcula: cantidad <= minimo
    creado_en: datetime
    actualizado_en: datetime
