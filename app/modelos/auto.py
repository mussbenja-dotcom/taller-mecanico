"""
MODELO: Auto.
Representa la tabla 'autos'. Cada auto pertenece a un cliente.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, SmallInteger, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.nucleo.base_datos import Base


class Auto(Base):
    __tablename__ = "autos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    marca: Mapped[str | None] = mapped_column(String(60))
    modelo: Mapped[str | None] = mapped_column(String(60))
    anio: Mapped[int | None] = mapped_column(SmallInteger)
    patente: Mapped[str | None] = mapped_column(String(15), index=True)
    color: Mapped[str | None] = mapped_column(String(30))
    kilometraje: Mapped[int | None] = mapped_column(Integer)
    vin: Mapped[str | None] = mapped_column(String(40))
    notas: Mapped[str | None] = mapped_column(Text)
    # nota pública que aparece en el QR/historial del vehículo (opcional)
    nota_qr: Mapped[str | None] = mapped_column(Text)
    # token único para el QR de historial del vehículo
    qr_token: Mapped[str] = mapped_column(
        String(36), default=lambda: str(uuid.uuid4()), unique=True
    )
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cliente: Mapped["Cliente"] = relationship(back_populates="autos")  # noqa: F821
