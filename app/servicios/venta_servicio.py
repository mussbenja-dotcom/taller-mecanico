"""
SERVICIO de Venta de mostrador = lógica de negocio.

A diferencia de la orden de trabajo:
- No hace falta auto ni presupuesto. El cliente es opcional.
- Se descuenta el stock real AL MOMENTO de crear la venta (no hay reserva
  previa ni un paso de "finalizada": se cobra y se lleva en el momento).
- No maneja cuenta corriente: se asume que la venta de mostrador se cobra
  completa ahí mismo (por eso entra directo a "Cobrado" en las métricas).
"""
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos import Venta, VentaItem, Repuesto, Cliente
from app.servicios.repuesto_servicio import ServicioRepuesto
from app.esquemas.venta import VentaCrear


def _armar_respuesta(v: Venta) -> dict:
    items = []
    total = Decimal(0)
    for it in v.items:
        subtotal = Decimal(it.cantidad) * Decimal(it.precio_unitario)
        total += subtotal
        items.append({
            "id": it.id, "repuesto_id": it.repuesto_id, "descripcion": it.descripcion,
            "cantidad": it.cantidad, "precio_unitario": it.precio_unitario, "subtotal": subtotal,
        })
    return {
        "id": v.id, "cliente_id": v.cliente_id, "forma_pago": v.forma_pago,
        "notas": v.notas, "creado_en": v.creado_en,
        "items": items, "total": total,
    }


class ServicioVenta:

    @staticmethod
    async def listar_todos(sesion: AsyncSession) -> list[dict]:
        """Todas las ventas de mostrador, más recientes primero, con nombre del cliente si tiene."""
        consulta = (
            select(Venta)
            .options(selectinload(Venta.items), selectinload(Venta.cliente))
            .order_by(Venta.creado_en.desc())
        )
        res = await sesion.execute(consulta)
        salida = []
        for v in res.scalars().all():
            d = _armar_respuesta(v)
            d["cliente_nombre"] = v.cliente.nombre if v.cliente else None
            salida.append(d)
        return salida

    @staticmethod
    async def obtener(sesion: AsyncSession, venta_id: int) -> Venta | None:
        consulta = (
            select(Venta).options(selectinload(Venta.items)).where(Venta.id == venta_id)
        )
        res = await sesion.execute(consulta)
        return res.scalar_one_or_none()

    @staticmethod
    async def obtener_respuesta(sesion: AsyncSession, venta_id: int) -> dict | None:
        v = await ServicioVenta.obtener(sesion, venta_id)
        return _armar_respuesta(v) if v else None

    @staticmethod
    async def crear(sesion: AsyncSession, datos: VentaCrear) -> dict:
        if not datos.items:
            raise HTTPException(400, "La venta necesita al menos un ítem.")

        # si viene un cliente, validar que exista (si no, es venta anónima)
        if datos.cliente_id is not None:
            cliente = await sesion.get(Cliente, datos.cliente_id)
            if not cliente:
                raise HTTPException(404, "Cliente no encontrado")

        venta = Venta(cliente_id=datos.cliente_id, forma_pago=datos.forma_pago, notas=datos.notas)

        for it in datos.items:
            rep = await sesion.get(Repuesto, it.repuesto_id, with_for_update=True)
            if not rep:
                raise HTTPException(404, f"Repuesto #{it.repuesto_id} no encontrado")

            cantidad = it.cantidad
            disponible = rep.cantidad - rep.reservado
            if disponible < cantidad:
                raise HTTPException(
                    400,
                    f"Stock insuficiente de '{rep.nombre}'. Disponible: {disponible}, se pidió: {cantidad}."
                )

            # precio: si no lo mandan, se usa el precio de lista actual del repuesto
            precio = it.precio_unitario if it.precio_unitario is not None else Decimal(rep.precio or 0)
            venta.items.append(VentaItem(
                repuesto_id=rep.id,
                descripcion=it.descripcion or rep.nombre,
                cantidad=cantidad,
                precio_unitario=precio,
            ))
            # se descuenta stock real de una: no es una reserva, se cobra en el momento
            await ServicioRepuesto.descontar(sesion, rep.id, int(cantidad), desde_reserva=False)

        sesion.add(venta)
        await sesion.commit()
        v = await ServicioVenta.obtener(sesion, venta.id)
        return _armar_respuesta(v)
