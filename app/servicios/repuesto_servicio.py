"""
SERVICIO de Repuesto = lógica de stock.

Reglas que viven acá:
- El stock nunca puede quedar negativo.
- 'stock_bajo' se calcula: cantidad <= minimo.
- El descuento por orden finalizada lo hace ServicioOrden llamando a
  'descontar' de acá (una sola fuente de verdad para tocar stock).
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos import Repuesto
from app.esquemas.repuesto import RepuestoCrear, RepuestoActualizar


def _armar(r: Repuesto) -> dict:
    return {
        "id": r.id, "nombre": r.nombre, "codigo": r.codigo, "precio": r.precio,
        "cantidad": r.cantidad, "minimo": r.minimo,
        "stock_bajo": r.cantidad <= r.minimo,
        "creado_en": r.creado_en, "actualizado_en": r.actualizado_en,
    }


class ServicioRepuesto:

    @staticmethod
    async def listar(sesion: AsyncSession, q: str | None = None, solo_bajos: bool = False) -> list[dict]:
        consulta = select(Repuesto).order_by(Repuesto.nombre)
        if q:
            patron = f"%{q}%"
            consulta = consulta.where(
                (Repuesto.nombre.ilike(patron)) | (Repuesto.codigo.ilike(patron))
            )
        res = await sesion.execute(consulta)
        items = [_armar(r) for r in res.scalars().all()]
        if solo_bajos:
            items = [i for i in items if i["stock_bajo"]]
        return items

    @staticmethod
    async def obtener(sesion: AsyncSession, repuesto_id: int) -> Repuesto | None:
        return await sesion.get(Repuesto, repuesto_id)

    @staticmethod
    async def crear(sesion: AsyncSession, datos: RepuestoCrear) -> dict:
        rep = Repuesto(**datos.model_dump())
        if rep.cantidad < 0:
            raise HTTPException(400, "La cantidad no puede ser negativa")
        sesion.add(rep)
        await sesion.commit()
        await sesion.refresh(rep)
        return _armar(rep)

    @staticmethod
    async def actualizar(sesion: AsyncSession, rep: Repuesto, datos: RepuestoActualizar) -> dict:
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(rep, campo, valor)
        if rep.cantidad < 0:
            raise HTTPException(400, "La cantidad no puede ser negativa")
        await sesion.commit()
        await sesion.refresh(rep)
        return _armar(rep)

    @staticmethod
    async def ajustar(sesion: AsyncSession, rep: Repuesto, delta: int) -> dict:
        """Suma o resta unidades (entrada de mercadería, corrección, etc.)."""
        nueva = rep.cantidad + delta
        if nueva < 0:
            raise HTTPException(400, f"No hay stock suficiente. Actual: {rep.cantidad}")
        rep.cantidad = nueva
        await sesion.commit()
        await sesion.refresh(rep)
        return _armar(rep)

    @staticmethod
    async def descontar(sesion: AsyncSession, repuesto_id: int, cantidad: int) -> None:
        """
        Descuenta stock de un repuesto. Lo usa la orden al finalizar.
        NO hace commit: lo hace el que lo llama, para que todo el descuento
        de la orden entre en una sola transacción.
        """
        rep = await sesion.get(Repuesto, repuesto_id)
        if not rep:
            return  # si el ítem no está vinculado a un repuesto real, se ignora
        nueva = rep.cantidad - cantidad
        # no se permite negativo: se deja en 0 y listo (el trabajo ya se hizo)
        rep.cantidad = max(0, nueva)

    @staticmethod
    async def borrar(sesion: AsyncSession, rep: Repuesto) -> None:
        await sesion.delete(rep)
        await sesion.commit()
