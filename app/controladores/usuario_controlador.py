"""
CONTROLADOR de Usuarios: el admin gestiona los empleados.
Todos los endpoints requieren rol admin (validado en el backend).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.nucleo.auth import requiere_rol
from app.servicios.usuario_servicio import ServicioUsuario
from app.esquemas.usuario import EmpleadoCrear, EmpleadoActualizar, UsuarioRespuesta

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


@router.get("/empleados", response_model=list[UsuarioRespuesta])
async def listar_empleados(
    _rol: str = Depends(requiere_rol("admin")),
    sesion: AsyncSession = Depends(obtener_sesion),
):
    return await ServicioUsuario.listar_empleados(sesion)


@router.post("/empleados", response_model=UsuarioRespuesta, status_code=201)
async def crear_empleado(
    datos: EmpleadoCrear,
    _rol: str = Depends(requiere_rol("admin")),
    sesion: AsyncSession = Depends(obtener_sesion),
):
    if not datos.nombre.strip() or not datos.password:
        raise HTTPException(400, "Nombre y contraseña son obligatorios")
    # evitar nombres duplicados
    existentes = await ServicioUsuario.listar_empleados(sesion)
    if any(e.usuario.lower() == datos.nombre.strip().lower() for e in existentes):
        raise HTTPException(400, "Ya existe un empleado con ese nombre")
    return await ServicioUsuario.crear_empleado(sesion, datos)


@router.put("/empleados/{usuario_id}", response_model=UsuarioRespuesta)
async def actualizar_empleado(
    usuario_id: int, datos: EmpleadoActualizar,
    _rol: str = Depends(requiere_rol("admin")),
    sesion: AsyncSession = Depends(obtener_sesion),
):
    u = await ServicioUsuario.obtener(sesion, usuario_id)
    if not u or u.rol != "empleado":
        raise HTTPException(404, "Empleado no encontrado")
    return await ServicioUsuario.actualizar_empleado(sesion, u, datos)


@router.delete("/empleados/{usuario_id}", status_code=204)
async def borrar_empleado(
    usuario_id: int,
    _rol: str = Depends(requiere_rol("admin")),
    sesion: AsyncSession = Depends(obtener_sesion),
):
    u = await ServicioUsuario.obtener(sesion, usuario_id)
    if not u or u.rol != "empleado":
        raise HTTPException(404, "Empleado no encontrado")
    await ServicioUsuario.borrar(sesion, u)
