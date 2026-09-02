"""
Configuración central de la aplicación.
Lee variables de entorno (archivo .env) con valores por defecto para desarrollo.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Base de datos.
    # Sin configurar nada: usa SQLite local (desarrollo).
    # Para Neon: postgresql+asyncpg://user:pass@ep-xxx-pooler.../db?sslmode=require
    # (recordar: endpoint POOLER + sslmode=require, SIN channel_binding)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./taller_dev.db",
    )

    # En desarrollo crea las tablas solo. En producción conviene usar migraciones.
    CREAR_TABLAS_AL_INICIAR: bool = os.getenv("CREAR_TABLAS", "1") == "1"


config = Config()
