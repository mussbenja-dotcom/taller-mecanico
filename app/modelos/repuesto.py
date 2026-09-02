"""
MODELO: Repuesto (stock).

Regla del negocio:
- Cada repuesto tiene una 'cantidad' en stock y un 'minimo' para la alerta.
- Cuando una orden se marca 'finalizada', se descuenta la cantidad de cada ítem
  que apunte a un repuesto (repuesto_id).
- Si la cantidad queda <= minimo, se considera stock bajo (alerta).
- La cantidad nunca queda negativa (CHECK en la base + control en el servicio).
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Numeric, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.nucleo.base_datos import Base


class Repuesto(Base):
    __tablename__ = "repuestos"
    __table_args__ = (
        CheckConstraint("cantidad >= 0", name="ck_cantidad_no_negativa"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    codigo: Mapped[str | None] = mapped_column(String(60), index=True)  # SKU / código interno
    cantidad: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minimo: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    precio: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notas: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
