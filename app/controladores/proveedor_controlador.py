"""CONTROLADOR de Proveedor."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.proveedor_servicio import ServicioProveedor
from app.esquemas.proveedor import (
    ProveedorCrear, ProveedorActualizar, ProveedorRespuesta
)

router = APIRouter(prefix="/api/proveedores", tags=["proveedores"])


@router.get("", response_model=list[ProveedorRespuesta])
async def listar(q: str | None = None, sesion: AsyncSession = Depends(obtener_sesion)):
    return await ServicioProveedor.listar(sesion, q)


@router.get("/{proveedor_id}", response_model=ProveedorRespuesta)
async def obtener(proveedor_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    prov = await ServicioProveedor.obtener(sesion, proveedor_id)
    if not prov:
        raise HTTPException(404, "Proveedor no encontrado")
    return prov


@router.post("", response_model=ProveedorRespuesta, status_code=201)
async def crear(datos: ProveedorCrear, sesion: AsyncSession = Depends(obtener_sesion)):
    return await ServicioProveedor.crear(sesion, datos)


@router.put("/{proveedor_id}", response_model=ProveedorRespuesta)
async def actualizar(
    proveedor_id: int, datos: ProveedorActualizar, sesion: AsyncSession = Depends(obtener_sesion)
):
    prov = await ServicioProveedor.obtener(sesion, proveedor_id)
    if not prov:
        raise HTTPException(404, "Proveedor no encontrado")
    return await ServicioProveedor.actualizar(sesion, prov, datos)


@router.delete("/{proveedor_id}", status_code=204)
async def borrar(proveedor_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    prov = await ServicioProveedor.obtener(sesion, proveedor_id)
    if not prov:
        raise HTTPException(404, "Proveedor no encontrado")
    await ServicioProveedor.borrar(sesion, prov)
