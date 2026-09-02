"""
SERVICIO de Orden de Trabajo = lógica de negocio.

Reglas clave que viven ACÁ:
- La orden NO se borra (no hay método borrar).
- Al pasar a 'finalizada' se registra finalizada_en (y en la Etapa 3, acá mismo
  se descontará el stock de los ítems que sean repuesto).
- Se puede crear directa o copiando un presupuesto.
"""
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos import OrdenTrabajo, OrdenItem, ESTADOS_ORDEN
from app.modelos import Presupuesto
from app.servicios.repuesto_servicio import ServicioRepuesto
from app.esquemas.orden import OrdenCrear, OrdenActualizar


def _armar_respuesta(o: OrdenTrabajo) -> dict:
    items = []
    total = Decimal(0)
    for it in o.items:
        subtotal = Decimal(it.cantidad) * Decimal(it.precio_unitario)
        total += subtotal
        items.append({
            "id": it.id, "descripcion": it.descripcion, "cantidad": it.cantidad,
            "precio_unitario": it.precio_unitario, "es_repuesto": it.es_repuesto,
            "repuesto_id": it.repuesto_id, "subtotal": subtotal,
        })
    return {
        "id": o.id, "auto_id": o.auto_id, "presupuesto_id": o.presupuesto_id,
        "descripcion": o.descripcion, "estado": o.estado, "notas": o.notas,
        "creado_en": o.creado_en, "actualizado_en": o.actualizado_en,
        "finalizada_en": o.finalizada_en, "items": items, "total": total,
    }


class ServicioOrden:

    @staticmethod
    async def listar_de_auto(sesion: AsyncSession, auto_id: int) -> list[dict]:
        consulta = (
            select(OrdenTrabajo)
            .options(selectinload(OrdenTrabajo.items))
            .where(OrdenTrabajo.auto_id == auto_id)
            .order_by(OrdenTrabajo.creado_en.desc())
        )
        res = await sesion.execute(consulta)
        return [_armar_respuesta(o) for o in res.scalars().all()]

    @staticmethod
    async def obtener(sesion: AsyncSession, orden_id: int) -> OrdenTrabajo | None:
        consulta = (
            select(OrdenTrabajo)
            .options(selectinload(OrdenTrabajo.items))
            .where(OrdenTrabajo.id == orden_id)
        )
        res = await sesion.execute(consulta)
        return res.scalar_one_or_none()

    @staticmethod
    async def obtener_respuesta(sesion: AsyncSession, orden_id: int) -> dict | None:
        o = await ServicioOrden.obtener(sesion, orden_id)
        return _armar_respuesta(o) if o else None

    @staticmethod
    async def crear(sesion: AsyncSession, datos: OrdenCrear) -> dict:
        orden = OrdenTrabajo(
            auto_id=datos.auto_id, descripcion=datos.descripcion, notas=datos.notas
        )
        for it in datos.items:
            orden.items.append(OrdenItem(**it.model_dump()))
        sesion.add(orden)
        await sesion.commit()
        o = await ServicioOrden.obtener(sesion, orden.id)
        return _armar_respuesta(o)

    @staticmethod
    async def crear_desde_presupuesto(sesion: AsyncSession, presupuesto_id: int) -> dict:
        # traer el presupuesto con sus ítems
        consulta = (
            select(Presupuesto)
            .options(selectinload(Presupuesto.items))
            .where(Presupuesto.id == presupuesto_id)
        )
        res = await sesion.execute(consulta)
        presu = res.scalar_one_or_none()
        if not presu:
            raise HTTPException(404, "Presupuesto no encontrado")

        orden = OrdenTrabajo(
            auto_id=presu.auto_id,
            presupuesto_id=presu.id,
            descripcion=presu.descripcion,
            notas=presu.notas,
        )
        for it in presu.items:
            orden.items.append(OrdenItem(
                descripcion=it.descripcion, cantidad=it.cantidad,
                precio_unitario=it.precio_unitario, es_repuesto=it.es_repuesto,
            ))
        sesion.add(orden)
        await sesion.commit()
        o = await ServicioOrden.obtener(sesion, orden.id)
        return _armar_respuesta(o)

    @staticmethod
    async def actualizar(
        sesion: AsyncSession, orden: OrdenTrabajo, datos: OrdenActualizar
    ) -> dict:
        # no se permite editar una orden ya cobrada (queda cerrada)
        if orden.estado == "cobrada":
            raise HTTPException(400, "No se puede editar una orden cobrada")
        if datos.descripcion is not None:
            orden.descripcion = datos.descripcion
        if datos.notas is not None:
            orden.notas = datos.notas
        if datos.items is not None:
            orden.items.clear()
            for it in datos.items:
                orden.items.append(OrdenItem(**it.model_dump()))
        await sesion.commit()
        o = await ServicioOrden.obtener(sesion, orden.id)
        return _armar_respuesta(o)

    @staticmethod
    async def cambiar_estado(
        sesion: AsyncSession, orden: OrdenTrabajo, nuevo_estado: str
    ) -> dict:
        if nuevo_estado not in ESTADOS_ORDEN:
            raise HTTPException(400, f"Estado inválido. Válidos: {', '.join(ESTADOS_ORDEN)}")

        # Al finalizar por primera vez: se registra el momento Y se descuenta
        # el stock de cada ítem que sea repuesto y esté vinculado (repuesto_id).
        # Es idempotente: solo entra cuando finalizada_en estaba vacío, así que
        # nunca se descuenta dos veces la misma orden.
        if nuevo_estado == "finalizada" and orden.finalizada_en is None:
            orden.finalizada_en = datetime.now(timezone.utc)
            for it in orden.items:
                if it.es_repuesto and it.repuesto_id:
                    await ServicioRepuesto.descontar(
                        sesion, it.repuesto_id, int(it.cantidad)
                    )

        orden.estado = nuevo_estado
        await sesion.commit()
        o = await ServicioOrden.obtener(sesion, orden.id)
        return _armar_respuesta(o)

    # OJO: no hay método 'borrar'. La orden queda grabada de forma permanente.
