"""CONTROLADOR de Comprobante: genera y descarga el PDF de una orden."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.comprobante_servicio import ServicioComprobante

router = APIRouter(prefix="/api/comprobante", tags=["comprobante"])


@router.get("/orden/{orden_id}")
async def comprobante_pdf(orden_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    pdf = await ServicioComprobante.generar_pdf(sesion, orden_id)
    if pdf is None:
        raise HTTPException(404, "Orden no encontrada")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="comprobante-orden-{orden_id}.pdf"'},
    )
