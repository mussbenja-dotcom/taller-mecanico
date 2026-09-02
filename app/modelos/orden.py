"""
MODELO: Orden de Trabajo y sus ítems.

Reglas del negocio (importantes, salen de lo que pidió el cliente):
- La orden QUEDA GRABADA de forma permanente. NO se borra nunca.
  (por eso NO lleva endpoint de borrado en el controlador)
- Estados: 'pendiente' -> 'finalizada' -> 'cobrada'.
- 'finalizada' es el estado clave: cuando la orden se marca finalizada, en la
  Etapa 3 se descontará el stock. NO se usa 'cobrada' para eso, porque el auto
  se puede entregar/cobrar después, pero el trabajo ya salió bien.
- Puede nacer de un presupuesto (presupuesto_id) o crearse directa.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.nucleo.base_datos import Base

# Estados válidos de una orden.
ESTADOS_ORDEN = ("pendiente", "finalizada", "cobrada")


class OrdenTrabajo(Base):
    __tablename__ = "ordenes_trabajo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    auto_id: Mapped[int] = mapped_column(
        ForeignKey("autos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # de qué presupuesto nació (opcional). Si el presupuesto se borra, la orden queda.
    presupuesto_id: Mapped[int | None] = mapped_column(
        ForeignKey("presupuestos.id", ondelete="SET NULL")
    )
    descripcion: Mapped[str | None] = mapped_column(String(200))
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", index=True)
    notas: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # marca de tiempo del momento en que se finalizó (para métricas y para el stock)
    finalizada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    auto: Mapped["Auto"] = relationship()  # noqa: F821
    items: Mapped[list["OrdenItem"]] = relationship(
        back_populates="orden", cascade="all, delete-orphan"
    )


class OrdenItem(Base):
    __tablename__ = "orden_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    orden_id: Mapped[int] = mapped_column(
        ForeignKey("ordenes_trabajo.id", ondelete="CASCADE"), nullable=False, index=True
    )
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    cantidad: Mapped[float] = mapped_column(Numeric(10, 2), default=1)
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    es_repuesto: Mapped[bool] = mapped_column(default=True)
    # a futuro: id del repuesto en el stock, para descontar al finalizar (Etapa 3)
    repuesto_id: Mapped[int | None] = mapped_column(Integer)

    orden: Mapped["OrdenTrabajo"] = relationship(back_populates="items")
