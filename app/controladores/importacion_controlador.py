"""CONTROLADOR de importación de stock desde Excel/CSV."""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.nucleo.auth import requiere_rol
from app.servicios.importacion_servicio import ServicioImportacion

router = APIRouter(prefix="/api/importar", tags=["importar"])


@router.post("/stock")
async def importar_stock(
    archivo: UploadFile = File(...),
    _rol: str = Depends(requiere_rol("admin")),   # solo admin puede importar
    sesion: AsyncSession = Depends(obtener_sesion),
):
    nombre = archivo.filename or ""
    if not (nombre.lower().endswith(".xlsx") or nombre.lower().endswith(".csv")):
        raise HTTPException(400, "El archivo debe ser .xlsx o .csv")
    contenido = await archivo.read()
    resultado = await ServicioImportacion.importar_stock(sesion, contenido, nombre)
    if "error" in resultado:
        raise HTTPException(400, resultado["error"])
    return resultado
