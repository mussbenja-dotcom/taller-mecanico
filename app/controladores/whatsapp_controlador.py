"""CONTROLADOR de WhatsApp: devuelve el link wa.me listo para abrir."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.whatsapp_servicio import ServicioWhatsApp

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


@router.get("/presupuesto/{presupuesto_id}")
async def link_presupuesto(presupuesto_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    r = await ServicioWhatsApp.link_presupuesto(sesion, presupuesto_id)
    if "error" in r:
        raise HTTPException(404, r["error"])
    return r


@router.get("/orden/{orden_id}")
async def link_orden(orden_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    r = await ServicioWhatsApp.link_orden(sesion, orden_id)
    if "error" in r:
        raise HTTPException(404, r["error"])
    return r
