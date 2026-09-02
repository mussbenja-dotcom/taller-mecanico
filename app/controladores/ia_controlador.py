"""CONTROLADOR de Diagnóstico IA."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.servicios.ia_servicio import ServicioIA

router = APIRouter(prefix="/api/ia", tags=["ia"])


class DiagnosticoDatos(BaseModel):
    sintomas: str
    datos_auto: str | None = None


@router.get("/estado")
async def estado():
    """Dice si la IA está configurada (si hay API key)."""
    return {"configurada": ServicioIA.hay_clave()}


@router.post("/diagnostico")
async def diagnostico(datos: DiagnosticoDatos):
    return await ServicioIA.diagnosticar(datos.sintomas, datos.datos_auto)
