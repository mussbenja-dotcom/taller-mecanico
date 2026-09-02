"""
SERVICIO de Presupuesto = lógica de negocio.

Incluye el cálculo de subtotales y total (no se guardan en la base, se calculan
al vuelo cada vez que se pide el presupuesto).
"""
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos import Presupuesto, PresupuestoItem
from app.esquemas.presupuesto import PresupuestoCrear, PresupuestoActualizar


def _armar_respuesta(p: Presupuesto) -> dict:
    """Arma el diccionario de respuesta calculando subtotales y total."""
    items = []
    total = Decimal(0)
    for it in p.items:
        subtotal = Decimal(it.cantidad) * Decimal(it.precio_unitario)
        total += subtotal
        items.append({
            "id": it.id,
            "descripcion": it.descripcion,
            "cantidad": it.cantidad,
            "precio_unitario": it.precio_unitario,
            "es_repuesto": it.es_repuesto,
            "subtotal": subtotal,
        })
    return {
        "id": p.id, "auto_id": p.auto_id, "descripcion": p.descripcion,
        "notas": p.notas, "creado_en": p.creado_en, "actualizado_en": p.actualizado_en,
        "items": items, "total": total,
    }


class ServicioPresupuesto:

    @staticmethod
    async def listar_de_auto(sesion: AsyncSession, auto_id: int) -> list[dict]:
        consulta = (
            select(Presupuesto)
            .options(selectinload(Presupuesto.items))
            .where(Presupuesto.auto_id == auto_id)
            .order_by(Presupuesto.creado_en.desc())
        )
        res = await sesion.execute(consulta)
        return [_armar_respuesta(p) for p in res.scalars().all()]

    @staticmethod
    async def obtener(sesion: AsyncSession, presupuesto_id: int) -> Presupuesto | None:
        consulta = (
            select(Presupuesto)
            .options(selectinload(Presupuesto.items))
            .where(Presupuesto.id == presupuesto_id)
        )
        res = await sesion.execute(consulta)
        return res.scalar_one_or_none()

    @staticmethod
    async def obtener_respuesta(sesion: AsyncSession, presupuesto_id: int) -> dict | None:
        p = await ServicioPresupuesto.obtener(sesion, presupuesto_id)
        return _armar_respuesta(p) if p else None

    @staticmethod
    async def crear(sesion: AsyncSession, datos: PresupuestoCrear) -> dict:
        presupuesto = Presupuesto(
            auto_id=datos.auto_id, descripcion=datos.descripcion, notas=datos.notas
        )
        for it in datos.items:
            presupuesto.items.append(PresupuestoItem(**it.model_dump()))
        sesion.add(presupuesto)
        await sesion.commit()
        # recargar con ítems
        p = await ServicioPresupuesto.obtener(sesion, presupuesto.id)
        return _armar_respuesta(p)

    @staticmethod
    async def actualizar(
        sesion: AsyncSession, presupuesto: Presupuesto, datos: PresupuestoActualizar
    ) -> dict:
        if datos.descripcion is not None:
            presupuesto.descripcion = datos.descripcion
        if datos.notas is not None:
            presupuesto.notas = datos.notas
        # si mandan items, reemplazan a los actuales
        if datos.items is not None:
            presupuesto.items.clear()
            for it in datos.items:
                presupuesto.items.append(PresupuestoItem(**it.model_dump()))
        await sesion.commit()
        p = await ServicioPresupuesto.obtener(sesion, presupuesto.id)
        return _armar_respuesta(p)

    @staticmethod
    async def borrar(sesion: AsyncSession, presupuesto: Presupuesto) -> None:
        # el presupuesto SÍ se puede borrar (regla del negocio)
        await sesion.delete(presupuesto)
        await sesion.commit()
