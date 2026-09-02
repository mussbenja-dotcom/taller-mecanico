"""
PUNTO DE ENTRADA de la aplicación.
Arma la app, conecta los controladores y sirve la vista.

Flujo de una petición (así funciona el MVC acá):

  Navegador (VISTA)
      │  fetch /api/clientes
      ▼
  CONTROLADOR (app/controladores/)   ← recibe el pedido HTTP
      │  llama a
      ▼
  SERVICIO (app/servicios/)          ← lógica de negocio: decide qué hacer
      │  usa
      ▼
  MODELO (app/modelos/) + base       ← guarda / trae datos
      │  vuelve
      ▲
  ESQUEMA (app/esquemas/)            ← valida y da forma a la respuesta
      │
      ▼
  Navegador (VISTA)                  ← muestra el resultado
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.nucleo.base_datos import engine, Base
from app.nucleo.config import config
from app import modelos  # noqa: F401  (registra los modelos)
from app.controladores import (
    cliente_controlador, auto_controlador,
    presupuesto_controlador, orden_controlador,
    repuesto_controlador, whatsapp_controlador,
    metricas_controlador, historial_controlador,
    auth_controlador, ia_controlador,
)


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    if config.CREAR_TABLAS_AL_INICIAR:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Taller — API (MVC)", version="0.2.0", lifespan=ciclo_vida)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONTROLADORES ---
app.include_router(cliente_controlador.router)
app.include_router(auto_controlador.router)
app.include_router(presupuesto_controlador.router)
app.include_router(orden_controlador.router)
app.include_router(repuesto_controlador.router)
app.include_router(whatsapp_controlador.router)
app.include_router(metricas_controlador.router)
app.include_router(historial_controlador.router)
app.include_router(auth_controlador.router)
app.include_router(ia_controlador.router)


@app.get("/api/salud")
async def salud():
    return {"estado": "ok"}


# --- VISTA (front estático) ---
DIR_STATIC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


@app.get("/")
async def raiz():
    return FileResponse(os.path.join(DIR_STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=DIR_STATIC), name="static")
@app.api_route("/ping", methods=["GET", "HEAD"])
def ping():
    return {"status": "ok"}
