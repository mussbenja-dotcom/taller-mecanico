"""
Conexión a la base de datos (capa de infraestructura).
Nada de lógica de negocio acá: solo el motor y la sesión.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.nucleo.config import config

# Detectar si usamos PostgreSQL (Neon) para pasarle opciones específicas.
_es_postgres = config.DATABASE_URL.startswith("postgresql")

# Con Neon + asyncpg hay que desactivar el caché de "prepared statements".
# Si no, cuando cambia el esquema de la base (agregar columna, cambiar tipo)
# aparece el error 'InvalidCachedStatementError'. Esto lo evita.
_connect_args = {"statement_cache_size": 0} if _es_postgres else {}

engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=_connect_args,
    pool_pre_ping=True,   # verifica la conexión antes de usarla (Neon a veces la cierra)
)

SesionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Clase base de la que heredan todos los MODELOS."""
    pass


async def obtener_sesion():
    """Dependencia de FastAPI: entrega una sesión de base de datos por request."""
    async with SesionLocal() as sesion:
        yield sesion
