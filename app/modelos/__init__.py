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
from app.modelos.usuario import Usuario
from app.modelos.pago import Pago
from app.modelos.venta import Venta, VentaItem

__all__ = [
    "Cliente", "Auto",
    "Presupuesto", "PresupuestoItem",
    "OrdenTrabajo", "OrdenItem", "ESTADOS_ORDEN",
    "Repuesto",
    "LogAccion",
    "Proveedor",
    "Compra",
    "Usuario",
    "Pago",
    "Venta", "VentaItem",
]
