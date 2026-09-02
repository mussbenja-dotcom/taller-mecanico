"""ESQUEMAS de Auto (Pydantic)."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AutoBase(BaseModel):
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = None
    patente: str | None = None
    color: str | None = None
    kilometraje: int | None = None
    vin: str | None = None
    notas: str | None = None
    nota_qr: str | None = None


class AutoCrear(AutoBase):
    pass


class AutoActualizar(AutoBase):
    pass


class AutoRespuesta(AutoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cliente_id: int
    qr_token: str
    creado_en: datetime
    actualizado_en: datetime
