"""
Capa MODELO. Expone todos los modelos para que SQLAlchemy los registre.
"""
from app.modelos.cliente import Cliente
from app.modelos.auto import Auto
from app.modelos.presupuesto import Presupuesto, PresupuestoItem
from app.modelos.orden import OrdenTrabajo, OrdenItem, ESTADOS_ORDEN
from app.modelos.repuesto import Repuesto
from app.modelos.log_accion import LogAccion
from app.modelos.proveedor import Proveedor
from app.modelos.compra import Compra

__all__ = [
    "Cliente", "Auto",
    "Presupuesto", "PresupuestoItem",
    "OrdenTrabajo", "OrdenItem", "ESTADOS_ORDEN",
    "Repuesto",
    "LogAccion",
    "Proveedor",
    "Compra",
]
