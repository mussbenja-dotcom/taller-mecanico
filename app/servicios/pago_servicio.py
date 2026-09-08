"""
SERVICIO de Pago = registrar pagos y calcular saldos (cuenta corriente).
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
        return pago

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
