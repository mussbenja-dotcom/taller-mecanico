"""
MODELO: LogAccion (auditoría).

Registra acciones sensibles del sistema (ej: borrar una orden) para poder
auditar quién hizo qué y cuándo. Tabla simple, se agrega sin romper nada.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.nucleo.base_datos import Base


class LogAccion(Base):
    __tablename__ = "logs_accion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario: Mapped[str | None] = mapped_column(String(100))   # quién hizo la acción
    accion: Mapped[str] = mapped_column(String(60), nullable=False)  # ej: "borrar_orden"
    detalle: Mapped[str | None] = mapped_column(Text)          # ej: "Orden #42"
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
