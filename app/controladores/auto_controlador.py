"""
CONTROLADOR de Auto (router de FastAPI).
Los autos cuelgan de un cliente.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.auto_servicio import ServicioAuto
from app.servicios.cliente_servicio import ServicioCliente
from app.esquemas.auto import AutoCrear, AutoActualizar, AutoRespuesta

router = APIRouter(prefix="/api", tags=["autos"])


@router.get("/clientes/{cliente_id}/autos", response_model=list[AutoRespuesta])
async def listar_de_cliente(cliente_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    return await ServicioAuto.listar_de_cliente(sesion, cliente_id)


@router.get("/autos")
async def listar_todos(q: str | None = None, sesion: AsyncSession = Depends(obtener_sesion)):
    """Todos los vehículos del taller (vista general, con búsqueda por patente/cliente)."""
    return await ServicioAuto.listar_todos(sesion, q)


@router.post("/clientes/{cliente_id}/autos", response_model=AutoRespuesta, status_code=201)
async def crear(cliente_id: int, datos: AutoCrear, sesion: AsyncSession = Depends(obtener_sesion)):
    cliente = await ServicioCliente.obtener(sesion, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    return await ServicioAuto.crear(sesion, cliente_id, datos)


@router.get("/autos/{auto_id}", response_model=AutoRespuesta)
async def obtener(auto_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    auto = await ServicioAuto.obtener(sesion, auto_id)
    if not auto:
        raise HTTPException(404, "Auto no encontrado")
    return auto


@router.put("/autos/{auto_id}", response_model=AutoRespuesta)
async def actualizar(
    auto_id: int, datos: AutoActualizar, sesion: AsyncSession = Depends(obtener_sesion)
):
    auto = await ServicioAuto.obtener(sesion, auto_id)
    if not auto:
        raise HTTPException(404, "Auto no encontrado")
    return await ServicioAuto.actualizar(sesion, auto, datos)


@router.delete("/autos/{auto_id}", status_code=204)
async def borrar(auto_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    auto = await ServicioAuto.obtener(sesion, auto_id)
    if not auto:
        raise HTTPException(404, "Auto no encontrado")
    await ServicioAuto.borrar(sesion, auto)
