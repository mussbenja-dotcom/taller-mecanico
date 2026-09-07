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
    marca_compatible: str | None = None
    modelo_compatible: str | None = None
    proveedor_id: int | None = None


class RepuestoCrear(RepuestoBase):
    pass


class RepuestoActualizar(BaseModel):
    nombre: str | None = None
    codigo: str | None = None
    precio: Decimal | None = None
    cantidad: int | None = None
    minimo: int | None = None
    marca_compatible: str | None = None
    modelo_compatible: str | None = None
    proveedor_id: int | None = None


class RepuestoAjustarStock(BaseModel):
    """Sumar (positivo) o restar (negativo) unidades. Ej: entrada de mercadería +10."""
    delta: int


class RepuestoRespuesta(RepuestoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reservado: int = 0                 # unidades reservadas
    disponible: int = 0               # cantidad - reservado (calculado)
    stock_bajo: bool = False          # se calcula: cantidad <= minimo
    compatible: bool = False          # si matchea la marca/modelo del auto consultado
    creado_en: datetime
    actualizado_en: datetime
