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
    disponible = r.cantidad - r.reservado
    return {
        "id": r.id, "nombre": r.nombre, "codigo": r.codigo, "precio": r.precio,
        "cantidad": r.cantidad, "reservado": r.reservado, "disponible": disponible,
        "minimo": r.minimo,
        "marca_compatible": r.marca_compatible, "modelo_compatible": r.modelo_compatible,
        "proveedor_id": r.proveedor_id,
        "stock_bajo": r.cantidad <= r.minimo,
        "creado_en": r.creado_en, "actualizado_en": r.actualizado_en,
    }


class ServicioRepuesto:

    @staticmethod
    async def listar(sesion: AsyncSession, q: str | None = None, solo_bajos: bool = False,
                     marca: str | None = None, modelo: str | None = None) -> list[dict]:
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

        # ¿este repuesto es compatible con el auto (marca/modelo) que se está armando?
        def es_compatible(i):
            if not marca and not modelo:
                return False
            mc = (i["marca_compatible"] or "").strip().lower()
            mo = (i["modelo_compatible"] or "").strip().lower()
            if not mc and not mo:
                return False  # sin datos = sirve para todo, pero no lo priorizamos
            coincide_marca = (not mc) or (marca and mc == marca.strip().lower())
            coincide_modelo = (not mo) or (modelo and mo == modelo.strip().lower())
            return bool(coincide_marca and coincide_modelo)

        for i in items:
            i["compatible"] = es_compatible(i)

        # ordenar: compatibles primero, después con stock, después el resto (por nombre)
        items.sort(key=lambda i: (not i["compatible"], i["cantidad"] <= 0, i["nombre"].lower()))
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
    async def reservar(sesion: AsyncSession, repuesto_id: int, cantidad: int) -> None:
        """
        Reserva unidades de un repuesto (para un presupuesto/orden pendiente).
        Sube 'reservado'. NO hace commit (entra en la transacción del que llama).
        Falla si no hay disponible suficiente (disponible = cantidad - reservado).
        Se relee el repuesto dentro de la transacción para controlar concurrencia:
        dos órdenes no pueden reservar las mismas unidades a la vez.
        """
        rep = await sesion.get(Repuesto, repuesto_id, with_for_update=True)
        if not rep:
            return
        disponible = rep.cantidad - rep.reservado
        if disponible < cantidad:
            raise HTTPException(
                400,
                f"Stock insuficiente de '{rep.nombre}'. Disponible: {disponible}, se pidió: {cantidad}."
            )
        rep.reservado += cantidad

    @staticmethod
    async def liberar(sesion: AsyncSession, repuesto_id: int, cantidad: int) -> None:
        """Libera una reserva (al borrar/editar un presupuesto u orden). NO commitea."""
        rep = await sesion.get(Repuesto, repuesto_id, with_for_update=True)
        if not rep:
            return
        rep.reservado = max(0, rep.reservado - cantidad)

    @staticmethod
    async def descontar(sesion: AsyncSession, repuesto_id: int, cantidad: int,
                        desde_reserva: bool = False) -> None:
        """
        Descuenta stock real de un repuesto. Lo usa la orden al finalizar.
        NO hace commit: lo hace el que lo llama (una sola transacción por orden).
        Si desde_reserva=True, además baja la reserva (la reserva se convierte
        en consumo real: no queda 'reservado' fantasma después de finalizar).
        """
        rep = await sesion.get(Repuesto, repuesto_id, with_for_update=True)
        if not rep:
            return  # si el ítem no está vinculado a un repuesto real, se ignora
        rep.cantidad = max(0, rep.cantidad - cantidad)
        if desde_reserva:
            rep.reservado = max(0, rep.reservado - cantidad)

    @staticmethod
    async def borrar(sesion: AsyncSession, rep: Repuesto) -> None:
        await sesion.delete(rep)
        await sesion.commit()
