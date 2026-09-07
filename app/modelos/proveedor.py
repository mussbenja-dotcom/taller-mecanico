"""
MODELO: Proveedor.

Representa un proveedor de repuestos. Se usa para el disparador de compra:
cuando falta stock de un repuesto que tiene proveedor asignado, se puede
generar un pedido de reposición por WhatsApp al proveedor.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.nucleo.base_datos import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    telefono: Mapped[str | None] = mapped_column(String(30))  # para WhatsApp (con código país)
    notas: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
