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
    async def listar_todos(sesion: AsyncSession, estado: str | None = None) -> list[dict]:
        """Todas las órdenes del taller, con datos del auto y cliente. Filtra por estado opcional."""
        from app.modelos import Auto, Cliente
        consulta = (
            select(OrdenTrabajo)
            .options(selectinload(OrdenTrabajo.items),
                     selectinload(OrdenTrabajo.auto).selectinload(Auto.cliente))
            .order_by(OrdenTrabajo.creado_en.desc())
        )
        if estado:
            consulta = consulta.where(OrdenTrabajo.estado == estado)
        res = await sesion.execute(consulta)
        salida = []
        for o in res.scalars().all():
            d = _armar_respuesta(o)
            auto = o.auto
            d["auto_desc"] = " ".join(filter(None, [auto.marca, auto.modelo])) if auto else ""
            d["patente"] = auto.patente if auto else None
            d["cliente_nombre"] = auto.cliente.nombre if auto and auto.cliente else None
            salida.append(d)
        return salida

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
            item = OrdenItem(**it.model_dump())
            # si el ítem está vinculado a un repuesto, reservar su stock
            if item.es_repuesto and item.repuesto_id:
                try:
                    await ServicioRepuesto.reservar(sesion, item.repuesto_id, int(item.cantidad))
                    item.reservado = True
                except HTTPException:
                    # sin stock disponible: se agrega igual pero sin reserva
                    # (el usuario ya confirmó agregarlo sin stock en el frontend)
                    item.reservado = False
            orden.items.append(item)
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
            item = OrdenItem(
                descripcion=it.descripcion, cantidad=it.cantidad,
                precio_unitario=it.precio_unitario, es_repuesto=it.es_repuesto,
                repuesto_id=it.repuesto_id,
            )
            # reservar stock igual que en crear (si no hay, se agrega sin reserva)
            if item.es_repuesto and item.repuesto_id:
                try:
                    await ServicioRepuesto.reservar(sesion, item.repuesto_id, int(item.cantidad))
                    item.reservado = True
                except HTTPException:
                    item.reservado = False
            orden.items.append(item)
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

        # Al pasar a "en_proceso": el vehículo entra al taller y empieza el trabajo.
        # Se valida que haya stock suficiente de cada repuesto. Si un ítem NO tenía
        # reserva previa (orden vieja o ítem agregado suelto), se comprueba y reserva
        # el stock en el momento. Si no alcanza, se corta con 400 y el detalle.
        if nuevo_estado == "en_proceso" and orden.estado == "pendiente":
            for it in orden.items:
                if it.es_repuesto and it.repuesto_id and not it.reservado:
                    # el ítem no tenía reserva previa: reservar ahora (valida stock)
                    await ServicioRepuesto.reservar(
                        sesion, it.repuesto_id, int(it.cantidad)
                    )
                    it.reservado = True

        # Al finalizar por primera vez: se registra el momento Y se consume el stock
        # (se descuenta de cantidad y de reservado a la vez). Idempotente.
        if nuevo_estado == "finalizada" and orden.finalizada_en is None:
            orden.finalizada_en = datetime.now(timezone.utc)
            for it in orden.items:
                if it.es_repuesto and it.repuesto_id:
                    await ServicioRepuesto.descontar(
                        sesion, it.repuesto_id, int(it.cantidad),
                        desde_reserva=bool(it.reservado),
                    )

        orden.estado = nuevo_estado
        await sesion.commit()
        o = await ServicioOrden.obtener(sesion, orden.id)
        return _armar_respuesta(o)

    @staticmethod
    async def borrar(sesion: AsyncSession, orden: OrdenTrabajo, usuario: str | None) -> None:
        """
        Borra una orden SOLO si está pendiente. Libera las reservas de sus ítems
        y registra la baja en el log de auditoría. El control de rol (solo admin)
        se hace en el controlador con la dependencia requiere_rol.
        """
        from app.servicios.log_servicio import ServicioLog
        if orden.estado != "pendiente":
            raise HTTPException(400, "Solo se pueden eliminar órdenes en estado pendiente.")
        # liberar reservas de los ítems antes de borrar
        for it in orden.items:
            if it.es_repuesto and it.repuesto_id and it.reservado:
                await ServicioRepuesto.liberar(sesion, it.repuesto_id, int(it.cantidad))
        await ServicioLog.registrar(
            sesion, usuario, "borrar_orden", f"Orden #{orden.id} ({orden.descripcion or 's/desc'})"
        )
        await sesion.delete(orden)
        await sesion.commit()
