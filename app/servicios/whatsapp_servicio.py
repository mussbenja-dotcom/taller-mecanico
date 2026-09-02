"""
SERVICIO de WhatsApp = arma el mensaje y el link wa.me.

No usa la API de Meta (que cuesta y requiere aprobación). Usa el link
público wa.me, que abre WhatsApp Web/App con el chat del cliente y el
mensaje ya cargado. El usuario solo aprieta Enter.

Formato del link: https://wa.me/<telefono>?text=<mensaje url-encodeado>
El teléfono debe ir solo con dígitos y código de país (ej: 5493462123456).
"""
import re
from urllib.parse import quote
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modelos import Presupuesto, OrdenTrabajo, Auto, Cliente


def _solo_digitos(telefono: str | None) -> str:
    """Deja solo números. Ej: '+54 9 3462 12-3456' -> '5493462123456'."""
    return re.sub(r"\D", "", telefono or "")


def _plata(n) -> str:
    return "$" + f"{Decimal(n):,.0f}".replace(",", ".")


def _linea_item(it) -> str:
    subtotal = Decimal(it.cantidad) * Decimal(it.precio_unitario)
    return f"• {it.descripcion}: {int(it.cantidad)} x {_plata(it.precio_unitario)} = {_plata(subtotal)}"


async def _datos_auto_cliente(sesion: AsyncSession, auto_id: int):
    """Trae el auto y su cliente para armar el encabezado y el teléfono."""
    res = await sesion.execute(
        select(Auto).options(selectinload(Auto.cliente)).where(Auto.id == auto_id)
    )
    auto = res.scalar_one_or_none()
    cliente = auto.cliente if auto else None
    return auto, cliente


class ServicioWhatsApp:

    @staticmethod
    async def link_presupuesto(sesion: AsyncSession, presupuesto_id: int) -> dict:
        res = await sesion.execute(
            select(Presupuesto).options(selectinload(Presupuesto.items))
            .where(Presupuesto.id == presupuesto_id)
        )
        p = res.scalar_one_or_none()
        if not p:
            return {"error": "Presupuesto no encontrado"}

        auto, cliente = await _datos_auto_cliente(sesion, p.auto_id)
        return ServicioWhatsApp._armar_link(
            titulo="PRESUPUESTO",
            descripcion=p.descripcion,
            items=p.items,
            auto=auto,
            cliente=cliente,
        )

    @staticmethod
    async def link_orden(sesion: AsyncSession, orden_id: int) -> dict:
        res = await sesion.execute(
            select(OrdenTrabajo).options(selectinload(OrdenTrabajo.items))
            .where(OrdenTrabajo.id == orden_id)
        )
        o = res.scalar_one_or_none()
        if not o:
            return {"error": "Orden no encontrada"}

        auto, cliente = await _datos_auto_cliente(sesion, o.auto_id)
        return ServicioWhatsApp._armar_link(
            titulo="ORDEN DE TRABAJO",
            descripcion=o.descripcion,
            items=o.items,
            auto=auto,
            cliente=cliente,
        )

    @staticmethod
    def _armar_link(titulo, descripcion, items, auto, cliente) -> dict:
        # encabezado
        lineas = [f"*{titulo}*"]
        if cliente:
            lineas.append(f"Cliente: {cliente.nombre}")
        if auto:
            desc_auto = " ".join(filter(None, [auto.marca, auto.modelo,
                                               str(auto.anio) if auto.anio else None]))
            if desc_auto:
                lineas.append(f"Vehículo: {desc_auto}")
            if auto.patente:
                lineas.append(f"Patente: {auto.patente}")
        if descripcion:
            lineas.append(f"\n{descripcion}")

        # ítems + total
        lineas.append("")
        total = Decimal(0)
        for it in items:
            lineas.append(_linea_item(it))
            total += Decimal(it.cantidad) * Decimal(it.precio_unitario)
        lineas.append(f"\n*TOTAL: {_plata(total)}*")
        lineas.append("\n¡Gracias!")

        mensaje = "\n".join(lineas)
        telefono = _solo_digitos(cliente.telefono if cliente else None)

        # si hay teléfono, arma el link directo al chat; si no, link genérico
        if telefono:
            link = f"https://wa.me/{telefono}?text={quote(mensaje)}"
        else:
            link = f"https://wa.me/?text={quote(mensaje)}"

        return {
            "link": link,
            "mensaje": mensaje,
            "telefono": telefono or None,
            "tiene_telefono": bool(telefono),
        }
