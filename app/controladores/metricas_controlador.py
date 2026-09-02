"""CONTROLADOR de Métricas."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.metricas_servicio import ServicioMetricas

router = APIRouter(prefix="/api/metricas", tags=["metricas"])


@router.get("/mes")
async def resumen_mes(
    anio: int | None = None, mes: int | None = None,
    sesion: AsyncSession = Depends(obtener_sesion)
):
    """Resumen del mes. Sin parámetros, usa el mes actual."""
    ahora = datetime.now(timezone.utc)
    return await ServicioMetricas.resumen_mes(
        sesion, anio or ahora.year, mes or ahora.month
    )
