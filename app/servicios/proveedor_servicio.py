"""SERVICIO de Proveedor = CRUD básico."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos import Proveedor
from app.esquemas.proveedor import ProveedorCrear, ProveedorActualizar


class ServicioProveedor:

    @staticmethod
    async def listar(sesion: AsyncSession, q: str | None = None) -> list[Proveedor]:
        consulta = select(Proveedor).order_by(Proveedor.nombre)
        if q:
            consulta = consulta.where(Proveedor.nombre.ilike(f"%{q}%"))
        res = await sesion.execute(consulta)
        return list(res.scalars().all())

    @staticmethod
    async def obtener(sesion: AsyncSession, proveedor_id: int) -> Proveedor | None:
        return await sesion.get(Proveedor, proveedor_id)

    @staticmethod
    async def crear(sesion: AsyncSession, datos: ProveedorCrear) -> Proveedor:
        prov = Proveedor(**datos.model_dump())
        sesion.add(prov)
        await sesion.commit()
        await sesion.refresh(prov)
        return prov

    @staticmethod
    async def actualizar(sesion: AsyncSession, prov: Proveedor, datos: ProveedorActualizar) -> Proveedor:
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(prov, campo, valor)
        await sesion.commit()
        await sesion.refresh(prov)
        return prov

    @staticmethod
    async def borrar(sesion: AsyncSession, prov: Proveedor) -> None:
        await sesion.delete(prov)
        await sesion.commit()
