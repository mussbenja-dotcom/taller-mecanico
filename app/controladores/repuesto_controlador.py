"""CONTROLADOR de Repuesto (stock)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.repuesto_servicio import ServicioRepuesto
from app.esquemas.repuesto import (
    RepuestoCrear, RepuestoActualizar, RepuestoAjustarStock, RepuestoRespuesta
)

router = APIRouter(prefix="/api/repuestos", tags=["repuestos"])


@router.get("", response_model=list[RepuestoRespuesta])
async def listar(
    q: str | None = None, solo_bajos: bool = False,
    sesion: AsyncSession = Depends(obtener_sesion)
):
    """Lista repuestos. ?q= busca; ?solo_bajos=true trae solo los de stock bajo."""
    return await ServicioRepuesto.listar(sesion, q, solo_bajos)


@router.get("/{repuesto_id}", response_model=RepuestoRespuesta)
async def obtener(repuesto_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    rep = await ServicioRepuesto.obtener(sesion, repuesto_id)
    if not rep:
        raise HTTPException(404, "Repuesto no encontrado")
    from app.servicios.repuesto_servicio import _armar
    return _armar(rep)


@router.post("", response_model=RepuestoRespuesta, status_code=201)
async def crear(datos: RepuestoCrear, sesion: AsyncSession = Depends(obtener_sesion)):
    return await ServicioRepuesto.crear(sesion, datos)


@router.put("/{repuesto_id}", response_model=RepuestoRespuesta)
async def actualizar(
    repuesto_id: int, datos: RepuestoActualizar,
    sesion: AsyncSession = Depends(obtener_sesion)
):
    rep = await ServicioRepuesto.obtener(sesion, repuesto_id)
    if not rep:
        raise HTTPException(404, "Repuesto no encontrado")
    return await ServicioRepuesto.actualizar(sesion, rep, datos)


@router.patch("/{repuesto_id}/ajustar", response_model=RepuestoRespuesta)
async def ajustar_stock(
    repuesto_id: int, datos: RepuestoAjustarStock,
    sesion: AsyncSession = Depends(obtener_sesion)
):
    """Suma o resta unidades (ej: entrada de mercadería con delta positivo)."""
    rep = await ServicioRepuesto.obtener(sesion, repuesto_id)
    if not rep:
        raise HTTPException(404, "Repuesto no encontrado")
    return await ServicioRepuesto.ajustar(sesion, rep, datos.delta)


@router.delete("/{repuesto_id}", status_code=204)
async def borrar(repuesto_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    rep = await ServicioRepuesto.obtener(sesion, repuesto_id)
    if not rep:
        raise HTTPException(404, "Repuesto no encontrado")
    await ServicioRepuesto.borrar(sesion, rep)
