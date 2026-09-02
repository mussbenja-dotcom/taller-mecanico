"""
CONTROLADOR de Cliente (router de FastAPI).

Fijate lo finito que quedó: solo recibe el pedido HTTP, llama al SERVICIO
y devuelve la respuesta. La lógica NO está acá, está en el servicio.
Así se ve MVC bien separado.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.cliente_servicio import ServicioCliente
from app.esquemas.cliente import (
    ClienteCrear, ClienteActualizar, ClienteRespuesta, ClienteConAutos
)

router = APIRouter(prefix="/api/clientes", tags=["clientes"])


@router.get("", response_model=list[ClienteRespuesta])
async def listar(q: str | None = None, sesion: AsyncSession = Depends(obtener_sesion)):
    return await ServicioCliente.listar(sesion, q)


@router.get("/{cliente_id}", response_model=ClienteConAutos)
async def obtener(cliente_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    cliente = await ServicioCliente.obtener(sesion, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    return cliente


@router.post("", response_model=ClienteRespuesta, status_code=201)
async def crear(datos: ClienteCrear, sesion: AsyncSession = Depends(obtener_sesion)):
    return await ServicioCliente.crear(sesion, datos)


@router.put("/{cliente_id}", response_model=ClienteRespuesta)
async def actualizar(
    cliente_id: int, datos: ClienteActualizar, sesion: AsyncSession = Depends(obtener_sesion)
):
    cliente = await ServicioCliente.obtener(sesion, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    return await ServicioCliente.actualizar(sesion, cliente, datos)


@router.delete("/{cliente_id}", status_code=204)
async def borrar(cliente_id: int, sesion: AsyncSession = Depends(obtener_sesion)):
    cliente = await ServicioCliente.obtener(sesion, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    await ServicioCliente.borrar(sesion, cliente)
