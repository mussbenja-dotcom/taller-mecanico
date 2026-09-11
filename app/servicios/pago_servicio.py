"""
SERVICIO de Pago = registrar pagos y calcular saldos (cuenta corriente).

Regla nueva: cuando un pago deja la orden saldada (pagado >= total), la
orden se marca 'cobrada' automáticamente. Si todavía no había pasado por
'finalizada' (y por lo tanto no se había descontado el stock reservado),
se fuerza ese paso primero para no romper el inventario -- se reusa
ServicioOrden.cambiar_estado, que ya sabe hacer ese descuento.
"""
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos import Pago, OrdenTrabajo, Auto
from app.esquemas.pago import PagoCrear


def _total_orden(orden: OrdenTrabajo) -> Decimal:
    return sum((Decimal(it.cantidad) * Decimal(it.precio_unitario) for it in orden.items), Decimal(0))


class ServicioPago:

    @staticmethod
    async def registrar(sesion: AsyncSession, datos: PagoCrear) -> Pago:
        pago = Pago(**datos.model_dump())
        sesion.add(pago)
        await sesion.commit()
        await sesion.refresh(pago)

        # si con este pago la cuenta corriente de la orden queda saldada,
        # se marca como "cobrada" sola (no hace falta ir a cambiarla a mano).
        await ServicioPago._marcar_cobrada_si_saldada(sesion, datos.orden_id)

        return pago

    @staticmethod
    async def _marcar_cobrada_si_saldada(sesion: AsyncSession, orden_id: int) -> None:
        # import acá adentro para evitar import circular (orden_servicio no
        # importa pago_servicio, así que esto es seguro)
        from app.servicios.orden_servicio import ServicioOrden

        res = await sesion.execute(
            select(OrdenTrabajo).options(selectinload(OrdenTrabajo.items))
            .where(OrdenTrabajo.id == orden_id)
        )
        orden = res.scalar_one_or_none()
        if not orden or orden.estado == "cobrada":
            return

        total = _total_orden(orden)
        if total <= 0:
            return  # orden sin ítems / sin importe: no hay nada que saldar

        pagos = await ServicioPago.listar_de_orden(sesion, orden_id)
        pagado = sum((Decimal(p.monto) for p in pagos), Decimal(0))
        if pagado < total:
            return  # todavía queda saldo pendiente

        # si no pasó por "finalizada" todavía, se fuerza ese paso primero
        # (ahí es donde se descuenta el stock reservado; cambiar_estado es
        # idempotente así que no hay riesgo de descontar dos veces).
        if orden.estado != "finalizada":
            await ServicioOrden.cambiar_estado(sesion, orden, "finalizada")
        await ServicioOrden.cambiar_estado(sesion, orden, "cobrada")

    @staticmethod
    async def listar_de_orden(sesion: AsyncSession, orden_id: int) -> list[Pago]:
        res = await sesion.execute(
            select(Pago).where(Pago.orden_id == orden_id).order_by(Pago.fecha, Pago.id)
        )
        return list(res.scalars().all())

    @staticmethod
    async def resumen_orden(sesion: AsyncSession, orden_id: int) -> dict:
        """Total de la orden, lo pagado y el saldo pendiente."""
        res = await sesion.execute(
            select(OrdenTrabajo).options(selectinload(OrdenTrabajo.items))
            .where(OrdenTrabajo.id == orden_id)
        )
        orden = res.scalar_one_or_none()
        if not orden:
            return {"error": "Orden no encontrada"}
        total = _total_orden(orden)
        pagos = await ServicioPago.listar_de_orden(sesion, orden_id)
        pagado = sum((Decimal(p.monto) for p in pagos), Decimal(0))
        saldo = total - pagado
        return {
            "orden_id": orden_id, "total": total, "pagado": pagado, "saldo": saldo,
            "pagos": [{"id": p.id, "fecha": p.fecha, "monto": p.monto, "nota": p.nota} for p in pagos],
        }

    @staticmethod
    async def deudores(sesion: AsyncSession) -> list[dict]:
        """
        Lista las órdenes con saldo pendiente > 0, con cliente y auto.
        Sirve como 'cuenta corriente': quién debe, cuánto y de qué vehículo.
        """
        res = await sesion.execute(
            select(OrdenTrabajo)
            .options(selectinload(OrdenTrabajo.items),
                     selectinload(OrdenTrabajo.auto).selectinload(Auto.cliente))
            .order_by(OrdenTrabajo.creado_en.desc())
        )
        ordenes = list(res.scalars().all())

        # traer todos los pagos de una y agrupar por orden
        res2 = await sesion.execute(select(Pago))
        pagos_por_orden: dict[int, Decimal] = {}
        for p in res2.scalars().all():
            pagos_por_orden[p.orden_id] = pagos_por_orden.get(p.orden_id, Decimal(0)) + Decimal(p.monto)

        salida = []
        for o in ordenes:
            total = _total_orden(o)
            pagado = pagos_por_orden.get(o.id, Decimal(0))
            saldo = total - pagado
            if saldo > 0 and total > 0:  # solo los que deben algo
                auto = o.auto
                salida.append({
                    "orden_id": o.id, "descripcion": o.descripcion, "estado": o.estado,
                    "auto_desc": " ".join(filter(None, [auto.marca, auto.modelo])) if auto else "",
                    "patente": auto.patente if auto else None,
                    "cliente_nombre": auto.cliente.nombre if auto and auto.cliente else None,
                    "cliente_telefono": auto.cliente.telefono if auto and auto.cliente else None,
                    "total": total, "pagado": pagado, "saldo": saldo,
                    "creado_en": o.creado_en,
                })
        return salida
