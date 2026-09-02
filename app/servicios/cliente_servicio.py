"""
SERVICIO de Cliente = LÓGICA DE NEGOCIO.

Esta capa es el corazón del MVC bien separado:
- El CONTROLADOR (router) solo recibe el pedido y llama al servicio.
- El SERVICIO decide QUÉ hacer y habla con el MODELO (base de datos).
- El MODELO solo guarda/trae datos.

Ventaja: si mañana cambia la lógica (ej: validar que el teléfono tenga
código de país antes de guardar), se toca ACÁ y no en el controlador ni en la vista.
"""
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos import Cliente
from app.esquemas.cliente import ClienteCrear, ClienteActualizar


class ServicioCliente:

    @staticmethod
    async def listar(sesion: AsyncSession, q: str | None = None) -> list[Cliente]:
        """Lista clientes. Si viene 'q', busca por nombre o teléfono."""
        consulta = select(Cliente).order_by(Cliente.nombre)
        if q:
            patron = f"%{q}%"
            consulta = consulta.where(
                or_(Cliente.nombre.ilike(patron), Cliente.telefono.ilike(patron))
            )
        resultado = await sesion.execute(consulta)
        return list(resultado.scalars().all())

    @staticmethod
    async def obtener(sesion: AsyncSession, cliente_id: int) -> Cliente | None:
        """Trae un cliente CON sus autos cargados."""
        consulta = (
            select(Cliente)
            .options(selectinload(Cliente.autos))
            .where(Cliente.id == cliente_id)
        )
        resultado = await sesion.execute(consulta)
        return resultado.scalar_one_or_none()

    @staticmethod
    async def crear(sesion: AsyncSession, datos: ClienteCrear) -> Cliente:
        cliente = Cliente(**datos.model_dump())
        sesion.add(cliente)
        await sesion.commit()
        await sesion.refresh(cliente)
        return cliente

    @staticmethod
    async def actualizar(
        sesion: AsyncSession, cliente: Cliente, datos: ClienteActualizar
    ) -> Cliente:
        # exclude_unset=True: solo toca los campos que realmente mandaron
        for campo, valor in datos.model_dump(exclude_unset=True).items():
            setattr(cliente, campo, valor)
        await sesion.commit()
        await sesion.refresh(cliente)
        return cliente

    @staticmethod
    async def borrar(sesion: AsyncSession, cliente: Cliente) -> None:
        await sesion.delete(cliente)  # borra en cascada sus autos
        await sesion.commit()
