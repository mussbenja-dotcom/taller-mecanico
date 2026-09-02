"""
SERVICIO de Auto = LÓGICA DE NEGOCIO de vehículos.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos import Auto
from app.esquemas.auto import AutoCrear, AutoActualizar


class ServicioAuto:

    @staticmethod
    async def listar_de_cliente(sesion: AsyncSession, cliente_id: int) -> list[Auto]:
        resultado = await sesion.execute(
            select(Auto).where(Auto.cliente_id == cliente_id)
        )
        return list(resultado.scalars().all())

    @staticmethod
    async def obtener(sesion: AsyncSession, auto_id: int) -> Auto | None:
        return await sesion.get(Auto, auto_id)

    @staticmethod
    async def crear(sesion: AsyncSession, cliente_id: int, datos: AutoCrear) -> Auto:
        auto = Auto(cliente_id=cliente_id, **datos.model_dump())
        sesion.add(auto)
        await sesion.commit()
        await sesion.refresh(auto)
        return auto

    @staticmethod
    async def actualizar(sesion: AsyncSession, auto: Auto, datos: AutoActualizar) -> Auto:
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(auto, campo, valor)
        await sesion.commit()
        await sesion.refresh(auto)
        return auto

    @staticmethod
    async def borrar(sesion: AsyncSession, auto: Auto) -> None:
        await sesion.delete(auto)
        await sesion.commit()
