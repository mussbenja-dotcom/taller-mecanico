"""
SERVICIO de Historial por QR.

Cada auto tiene un qr_token único (creado en la Etapa 1). Con ese token:
- Se arma la URL pública del historial: /historial/<qr_token>
- Se genera la imagen del QR que apunta a esa URL.
- Se consulta el historial completo de órdenes del vehículo.

El QR se imprime y se pega en el auto. Al escanearlo, muestra el historial.
"""
import io
import base64
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos import Auto, OrdenTrabajo


class ServicioHistorial:

    @staticmethod
    async def por_token(sesion: AsyncSession, qr_token: str) -> dict | None:
        """Devuelve los datos del auto + todas sus órdenes, por token público."""
        res = await sesion.execute(
            select(Auto).options(selectinload(Auto.cliente)).where(Auto.qr_token == qr_token)
        )
        auto = res.scalar_one_or_none()
        if not auto:
            return None

        res2 = await sesion.execute(
            select(OrdenTrabajo)
            .options(selectinload(OrdenTrabajo.items))
            .where(OrdenTrabajo.auto_id == auto.id)
            .order_by(OrdenTrabajo.creado_en.desc())
        )
        ordenes = []
        for o in res2.scalars().all():
            total = sum(Decimal(it.cantidad) * Decimal(it.precio_unitario) for it in o.items)
            ordenes.append({
                "id": o.id, "descripcion": o.descripcion, "estado": o.estado,
                "creado_en": o.creado_en, "finalizada_en": o.finalizada_en,
                "total": total,
                "items": [{"descripcion": it.descripcion, "cantidad": it.cantidad}
                          for it in o.items],
            })

        return {
            "auto": {
                "marca": auto.marca, "modelo": auto.modelo, "anio": auto.anio,
                "patente": auto.patente, "kilometraje": auto.kilometraje,
                "cliente": auto.cliente.nombre if auto.cliente else None,
                "nota_qr": auto.nota_qr,
            },
            "ordenes": ordenes,
            "total_ordenes": len(ordenes),
        }

    @staticmethod
    async def obtener_auto_por_id(sesion: AsyncSession, auto_id: int) -> Auto | None:
        return await sesion.get(Auto, auto_id)

    @staticmethod
    def generar_qr_base64(url: str) -> str:
        """Genera el QR de la URL y lo devuelve como imagen PNG en base64."""
        import qrcode
        img = qrcode.make(url)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
