"""CONTROLADOR de Venta de mostrador (venta directa de stock, sin vehículo)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.venta_servicio import ServicioVenta
from app.esquemas.venta import VentaCrear, VentaRespuesta

router = APIRouter(prefix="/api/ventas", tags=["ventas"])


@router.get("")
async def listar_todas(sesion: AsyncSession = Depends(obtener_sesion)):
    """Todas las ventas de mostrador (vista general)."""
    return await ServicioVenta.listar_todos(sesion)


@router.get("/{venta_id}", response_model=VentaRespuesta)
async def obtener(venta_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    v = await ServicioVenta.obtener_respuesta(sesion, venta_id)
    if not v:
        raise HTTPException(404, "Venta no encontrada")
    return v


@router.post("", response_model=VentaRespuesta, status_code=201)
async def crear(datos: VentaCrear, sesion: AsyncSession = Depends(obtener_sesion)):
    return await ServicioVenta.crear(sesion, datos)


@router.patch("/{venta_id}/pagar", response_model=VentaRespuesta)
async def marcar_pagada(venta_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    """Salda una venta de cuenta corriente (la marca como pagada)."""
    v = await ServicioVenta.marcar_pagada(sesion, venta_id)
    if not v:
        raise HTTPException(404, "Venta no encontrada")
    return v
