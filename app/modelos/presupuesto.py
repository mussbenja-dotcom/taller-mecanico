"""
MODELO: Presupuesto y sus ítems.

Reglas del negocio:
- El presupuesto se hace sobre un auto (y por lo tanto un cliente).
- Es EDITABLE y se puede BORRAR (a diferencia de la orden, que queda grabada).
- Tiene ítems: cada uno es un repuesto o mano de obra, con cantidad y precio.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.nucleo.base_datos import Base


class Presupuesto(Base):
    __tablename__ = "presupuestos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    auto_id: Mapped[int] = mapped_column(
        ForeignKey("autos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    descripcion: Mapped[str | None] = mapped_column(String(200))  # ej: "Service completo"
    notas: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    auto: Mapped["Auto"] = relationship()  # noqa: F821
    items: Mapped[list["PresupuestoItem"]] = relationship(
        back_populates="presupuesto", cascade="all, delete-orphan"
    )


class PresupuestoItem(Base):
    __tablename__ = "presupuesto_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(
        ForeignKey("presupuestos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)  # "Filtro de aceite" / "Mano de obra"
    cantidad: Mapped[float] = mapped_column(Numeric(10, 2), default=1)
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    # es_repuesto=True: es un repuesto (a futuro descontará stock). False: mano de obra u otro.
    es_repuesto: Mapped[bool] = mapped_column(default=True)

    presupuesto: Mapped["Presupuesto"] = relationship(back_populates="items")
