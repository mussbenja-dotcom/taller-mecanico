"""
MODELO: Pago (cuenta corriente).

Cada pago que hace un cliente sobre una orden se registra acá. El saldo de una
orden se calcula como: total de la orden - suma de sus pagos. Así se puede
registrar seña, pagos parciales, o el pago total, y saber cuánto debe cada uno.
"""
from datetime import datetime, date
from sqlalchemy import Integer, Numeric, Date, DateTime, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.nucleo.base_datos import Base


class Pago(Base):
    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    orden_id: Mapped[int] = mapped_column(
        ForeignKey("ordenes_trabajo.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    monto: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    nota: Mapped[str | None] = mapped_column(String(200))  # ej: "seña", "efectivo", "transferencia"
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
