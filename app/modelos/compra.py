"""
MODELO: Compra (historial de compras de repuestos).

Cada vez que el taller compra un repuesto, se registra una Compra con la fecha,
la cantidad y el costo unitario de esa compra. Guardar el historial permite
después ver cómo evolucionó el precio de cada repuesto en el tiempo (métrica de
"cuánto aumentó cada producto").

Al registrar una compra, se suma la cantidad al stock del repuesto.
"""
from datetime import datetime, date
from sqlalchemy import Integer, Numeric, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.nucleo.base_datos import Base


class Compra(Base):
    __tablename__ = "compras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repuesto_id: Mapped[int] = mapped_column(
        ForeignKey("repuestos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proveedor_id: Mapped[int | None] = mapped_column(Integer)  # opcional
    fecha: Mapped[date] = mapped_column(Date, nullable=False)   # fecha de la compra
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    costo_unitario: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
