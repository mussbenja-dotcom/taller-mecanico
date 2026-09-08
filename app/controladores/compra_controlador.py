"""CONTROLADOR de Compra: registrar compras y ver historial."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.compra_servicio import ServicioCompra
from app.servicios.repuesto_servicio import ServicioRepuesto
from app.esquemas.compra import CompraCrear, CompraRespuesta

router = APIRouter(prefix="/api/compras", tags=["compras"])


@router.post("", response_model=CompraRespuesta, status_code=201)
async def registrar(datos: CompraCrear, sesion: AsyncSession = Depends(obtener_sesion)):
    rep = await ServicioRepuesto.obtener(sesion, datos.repuesto_id)
    if not rep:
        raise HTTPException(404, "Repuesto no encontrado")
    return await ServicioCompra.registrar(sesion, datos)


@router.get("/repuesto/{repuesto_id}", response_model=list[CompraRespuesta])
async def historial(repuesto_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    return await ServicioCompra.listar_de_repuesto(sesion, repuesto_id)
