"""
CONTROLADOR de Orden de Trabajo.

Fijate que NO hay endpoint DELETE: la orden queda grabada de forma permanente,
tal como pidió el cliente. Solo se puede crear, ver, editar (si no está cobrada)
y cambiar de estado.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.orden_servicio import ServicioOrden
from app.servicios.auto_servicio import ServicioAuto
from app.esquemas.orden import (
    OrdenCrear, OrdenActualizar, OrdenCambiarEstado,
    OrdenDesdePresupuesto, OrdenRespuesta
)

router = APIRouter(prefix="/api", tags=["ordenes"])


@router.get("/autos/{auto_id}/ordenes", response_model=list[OrdenRespuesta])
async def listar_de_auto(auto_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    return await ServicioOrden.listar_de_auto(sesion, auto_id)


@router.get("/ordenes/{orden_id}", response_model=OrdenRespuesta)
async def obtener(orden_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    o = await ServicioOrden.obtener_respuesta(sesion, orden_id)
    if not o:
        raise HTTPException(404, "Orden no encontrada")
    return o


@router.post("/ordenes", response_model=OrdenRespuesta, status_code=201)
async def crear(datos: OrdenCrear, sesion: AsyncSession = Depends(obtener_sesion)):
    auto = await ServicioAuto.obtener(sesion, datos.auto_id)
    if not auto:
        raise HTTPException(404, "Auto no encontrado")
    return await ServicioOrden.crear(sesion, datos)


@router.post("/ordenes/desde-presupuesto", response_model=OrdenRespuesta, status_code=201)
async def crear_desde_presupuesto(
    datos: OrdenDesdePresupuesto, sesion: AsyncSession = Depends(obtener_sesion)
):
    return await ServicioOrden.crear_desde_presupuesto(sesion, datos.presupuesto_id)


@router.put("/ordenes/{orden_id}", response_model=OrdenRespuesta)
async def actualizar(
    orden_id: int, datos: OrdenActualizar, sesion: AsyncSession = Depends(obtener_sesion)
):
    o = await ServicioOrden.obtener(sesion, orden_id)
    if not o:
        raise HTTPException(404, "Orden no encontrada")
    return await ServicioOrden.actualizar(sesion, o, datos)


@router.patch("/ordenes/{orden_id}/estado", response_model=OrdenRespuesta)
async def cambiar_estado(
    orden_id: int, datos: OrdenCambiarEstado,
    sesion: AsyncSession = Depends(obtener_sesion)
):
    o = await ServicioOrden.obtener(sesion, orden_id)
    if not o:
        raise HTTPException(404, "Orden no encontrada")
    return await ServicioOrden.cambiar_estado(sesion, o, datos.estado)
