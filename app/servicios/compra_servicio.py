"""
SERVICIO de Compra = registrar compras y sumar stock.

Al registrar una compra:
- se guarda el registro (fecha, cantidad, costo unitario, proveedor)
- se SUMA la cantidad al stock del repuesto
Todo en una sola transacción.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos import Compra, Repuesto
from app.esquemas.compra import CompraCrear


class ServicioCompra:

    @staticmethod
    async def registrar(sesion: AsyncSession, datos: CompraCrear) -> Compra:
        compra = Compra(**datos.model_dump())
        sesion.add(compra)
        # sumar la cantidad comprada al stock del repuesto
        rep = await sesion.get(Repuesto, datos.repuesto_id, with_for_update=True)
        if rep:
            rep.cantidad = rep.cantidad + int(datos.cantidad)
        await sesion.commit()
        await sesion.refresh(compra)
        return compra

    @staticmethod
    async def listar_de_repuesto(sesion: AsyncSession, repuesto_id: int) -> list[Compra]:
        res = await sesion.execute(
            select(Compra).where(Compra.repuesto_id == repuesto_id)
            .order_by(Compra.fecha.desc(), Compra.id.desc())
        )
        return list(res.scalars().all())
