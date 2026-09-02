"""
Capa MODELO. Expone todos los modelos para que SQLAlchemy los registre.
"""
from app.modelos.cliente import Cliente
from app.modelos.auto import Auto
from app.modelos.presupuesto import Presupuesto, PresupuestoItem
from app.modelos.orden import OrdenTrabajo, OrdenItem, ESTADOS_ORDEN
from app.modelos.repuesto import Repuesto

__all__ = [
    "Cliente", "Auto",
    "Presupuesto", "PresupuestoItem",
    "OrdenTrabajo", "OrdenItem", "ESTADOS_ORDEN",
    "Repuesto",
]
