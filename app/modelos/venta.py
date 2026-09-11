"""
MODELO: Venta de mostrador.

Para cuando viene un cliente a comprar algo del stock (una bujía, un foco,
un filtro) SIN que haya un vehículo ni una orden de trabajo de por medio.

Diferencias clave con la Orden de trabajo:
- No lleva auto_id: el cliente es opcional (puede ser una venta anónima,
  "consumidor final"). Si se carga, es un cliente_id directo, sin pasar por
  un auto.
- No maneja cuenta corriente / estados: se cobra en el momento, se descuenta
  el stock al toque y queda registrada. No hay 'pendiente' ni 'saldo'.
- Igual que en OrdenItem/PresupuestoItem, repuesto_id es un entero simple
  (sin FK dura) para no bloquear el borrado de un repuesto que ya se vendió
  alguna vez.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.nucleo.base_datos import Base


class Venta(Base):
    __tablename__ = "ventas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # cliente opcional: None = venta anónima ("consumidor final")
    cliente_id: Mapped[int | None] = mapped_column(
        ForeignKey("clientes.id", ondelete="SET NULL"), index=True
    )
    forma_pago: Mapped[str | None] = mapped_column(String(30))  # efectivo, transferencia, tarjeta...
    notas: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cliente: Mapped["Cliente"] = relationship()  # noqa: F821
    items: Mapped[list["VentaItem"]] = relationship(
        back_populates="venta", cascade="all, delete-orphan"
    )


class VentaItem(Base):
    __tablename__ = "venta_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # sin FK dura a propósito (mismo criterio que OrdenItem.repuesto_id)
    repuesto_id: Mapped[int | None] = mapped_column(Integer, index=True)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)  # nombre del repuesto al momento de vender
    cantidad: Mapped[float] = mapped_column(Numeric(10, 2), default=1)
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    venta: Mapped["Venta"] = relationship(back_populates="items")
