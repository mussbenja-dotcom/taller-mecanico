"""
SERVICIO de LogAccion = registrar acciones para auditoría.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos import LogAccion


class ServicioLog:

    @staticmethod
    async def registrar(
        sesion: AsyncSession, usuario: str | None, accion: str, detalle: str | None = None
    ) -> None:
        """
        Guarda un registro de auditoría. NO hace commit propio: lo hace quien
        lo llama, para que entre en la misma transacción que la acción auditada.
        """
        log = LogAccion(usuario=usuario, accion=accion, detalle=detalle)
        sesion.add(log)
