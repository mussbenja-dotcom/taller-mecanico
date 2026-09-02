"""
SERVICIO de Auto = LÓGICA DE NEGOCIO de vehículos.
"""
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos import Auto, Cliente
from app.esquemas.auto import AutoCrear, AutoActualizar


class ServicioAuto:

    @staticmethod
    async def listar_de_cliente(sesion: AsyncSession, cliente_id: int) -> list[Auto]:
        resultado = await sesion.execute(
            select(Auto).where(Auto.cliente_id == cliente_id)
        )
        return list(resultado.scalars().all())

    @staticmethod
    async def listar_todos(sesion: AsyncSession, q: str | None = None) -> list[dict]:
        """Todos los vehículos del taller, con el nombre del cliente. Busca por
        patente, marca, modelo o nombre del cliente."""
        consulta = select(Auto).options(selectinload(Auto.cliente))
        if q:
            patron = f"%{q}%"
            consulta = consulta.join(Cliente).where(or_(
                Auto.patente.ilike(patron), Auto.marca.ilike(patron),
                Auto.modelo.ilike(patron), Cliente.nombre.ilike(patron),
            ))
        consulta = consulta.order_by(Auto.marca, Auto.modelo)
        res = await sesion.execute(consulta)
        autos = res.scalars().all()
        return [{
            "id": a.id, "cliente_id": a.cliente_id,
            "cliente_nombre": a.cliente.nombre if a.cliente else None,
            "marca": a.marca, "modelo": a.modelo, "anio": a.anio,
            "patente": a.patente, "kilometraje": a.kilometraje, "color": a.color,
        } for a in autos]

    @staticmethod
    async def obtener(sesion: AsyncSession, auto_id: int) -> Auto | None:
        return await sesion.get(Auto, auto_id)

    @staticmethod
    async def crear(sesion: AsyncSession, cliente_id: int, datos: AutoCrear) -> Auto:
        auto = Auto(cliente_id=cliente_id, **datos.model_dump())
        sesion.add(auto)
        await sesion.commit()
        await sesion.refresh(auto)
        return auto

    @staticmethod
    async def actualizar(sesion: AsyncSession, auto: Auto, datos: AutoActualizar) -> Auto:
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(auto, campo, valor)
        await sesion.commit()
        await sesion.refresh(auto)
        return auto

    @staticmethod
    async def borrar(sesion: AsyncSession, auto: Auto) -> None:
        await sesion.delete(auto)
        await sesion.commit()
