"""CONTROLADOR de Pagos / cuenta corriente."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.pago_servicio import ServicioPago
from app.servicios.orden_servicio import ServicioOrden
from app.esquemas.pago import PagoCrear, PagoRespuesta

router = APIRouter(prefix="/api/pagos", tags=["pagos"])


@router.post("", response_model=PagoRespuesta, status_code=201)
async def registrar(datos: PagoCrear, sesion: AsyncSession = Depends(obtener_sesion)):
    orden = await ServicioOrden.obtener(sesion, datos.orden_id)
    if not orden:
        raise HTTPException(404, "Orden no encontrada")
    return await ServicioPago.registrar(sesion, datos)


@router.get("/orden/{orden_id}")
async def resumen_orden(orden_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    """Total, pagado y saldo de una orden, con el detalle de pagos."""
    r = await ServicioPago.resumen_orden(sesion, orden_id)
    if "error" in r:
        raise HTTPException(404, r["error"])
    return r


@router.get("/deudores")
async def deudores(sesion: AsyncSession = Depends(obtener_sesion)):
    """Cuenta corriente: órdenes con saldo pendiente (quién debe y cuánto)."""
    return await ServicioPago.deudores(sesion)
