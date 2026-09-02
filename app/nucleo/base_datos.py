"""
Conexión a la base de datos (capa de infraestructura).
Nada de lógica de negocio acá: solo el motor y la sesión.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.nucleo.config import config

engine = create_async_engine(config.DATABASE_URL, echo=False, future=True)

SesionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Clase base de la que heredan todos los MODELOS."""
    pass


async def obtener_sesion():
    """Dependencia de FastAPI: entrega una sesión de base de datos por request."""
    async with SesionLocal() as sesion:
        yield sesion
