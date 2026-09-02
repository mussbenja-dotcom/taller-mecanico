"""CONTROLADOR de Presupuesto."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.presupuesto_servicio import ServicioPresupuesto
from app.servicios.auto_servicio import ServicioAuto
from app.esquemas.presupuesto import (
    PresupuestoCrear, PresupuestoActualizar, PresupuestoRespuesta
)

router = APIRouter(prefix="/api", tags=["presupuestos"])


@router.get("/autos/{auto_id}/presupuestos", response_model=list[PresupuestoRespuesta])
async def listar_de_auto(auto_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    return await ServicioPresupuesto.listar_de_auto(sesion, auto_id)


@router.get("/presupuestos/{presupuesto_id}", response_model=PresupuestoRespuesta)
async def obtener(presupuesto_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    p = await ServicioPresupuesto.obtener_respuesta(sesion, presupuesto_id)
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")
    return p


@router.post("/presupuestos", response_model=PresupuestoRespuesta, status_code=201)
async def crear(datos: PresupuestoCrear, sesion: AsyncSession = Depends(obtener_sesion)):
    auto = await ServicioAuto.obtener(sesion, datos.auto_id)
    if not auto:
        raise HTTPException(404, "Auto no encontrado")
    return await ServicioPresupuesto.crear(sesion, datos)


@router.put("/presupuestos/{presupuesto_id}", response_model=PresupuestoRespuesta)
async def actualizar(
    presupuesto_id: int, datos: PresupuestoActualizar,
    sesion: AsyncSession = Depends(obtener_sesion)
):
    p = await ServicioPresupuesto.obtener(sesion, presupuesto_id)
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")
    return await ServicioPresupuesto.actualizar(sesion, p, datos)


@router.delete("/presupuestos/{presupuesto_id}", status_code=204)
async def borrar(presupuesto_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    p = await ServicioPresupuesto.obtener(sesion, presupuesto_id)
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")
    await ServicioPresupuesto.borrar(sesion, p)
