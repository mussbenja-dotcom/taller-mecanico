"""
MODELO: Usuario.

Usuarios del sistema, guardados en la base (antes estaban fijos en el código).
- El ADMIN entra con email + contraseña.
- Los EMPLEADOS los crea el admin con nombre + contraseña (sin email).
La contraseña NUNCA se guarda en texto plano: se guarda su hash (bcrypt).

Para login unificado se usa el campo 'usuario' como identificador:
- para el admin, 'usuario' es su email.
- para el empleado, 'usuario' es su nombre.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.nucleo.base_datos import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # identificador de login: email (admin) o nombre (empleado). Único.
    usuario: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)  # nombre para mostrar
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False, default="empleado")  # 'admin' | 'empleado'
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
