"""
Migración aditiva: agrega la columna 'nota_qr' a la tabla 'autos'.

Corré esto UNA vez si ya tenías la base con datos:
    python migrate.py

Es seguro: si la columna ya existe, no hace nada. No borra datos.
"""
import asyncio
from sqlalchemy import text
from app.nucleo.base_datos import engine


async def main():
    async with engine.begin() as conn:
        # ver qué columnas tiene la tabla autos
        def columnas(sync_conn):
            from sqlalchemy import inspect
            insp = inspect(sync_conn)
            return [c["name"] for c in insp.get_columns("autos")]

        cols = await conn.run_sync(columnas)

        if "nota_qr" in cols:
            print("La columna 'nota_qr' ya existe. Nada que hacer.")
            return

        await conn.execute(text("ALTER TABLE autos ADD COLUMN nota_qr TEXT"))
        print("✅ Columna 'nota_qr' agregada a 'autos'. Datos intactos.")


asyncio.run(main())
