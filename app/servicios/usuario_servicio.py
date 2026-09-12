"""
SERVICIO de Usuario = login + gestión de empleados + admin inicial.
"""
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos import Usuario
from app.nucleo import auth
from app.esquemas.usuario import EmpleadoCrear, EmpleadoActualizar


class ServicioUsuario:

    @staticmethod
    async def autenticar(sesion: AsyncSession, usuario: str, password: str) -> Usuario | None:
        """Devuelve el Usuario si las credenciales son válidas y está activo."""
        res = await sesion.execute(select(Usuario).where(Usuario.usuario == usuario))
        u = res.scalar_one_or_none()
        if not u or not u.activo:
            return None
        if not auth.verificar_password(password, u.password_hash):
            return None
        return u

    @staticmethod
    async def listar_empleados(sesion: AsyncSession) -> list[Usuario]:
        res = await sesion.execute(
            select(Usuario).where(Usuario.rol == "empleado").order_by(Usuario.nombre)
        )
        return list(res.scalars().all())

    @staticmethod
    async def obtener(sesion: AsyncSession, usuario_id: int) -> Usuario | None:
        return await sesion.get(Usuario, usuario_id)

    @staticmethod
    async def crear_empleado(sesion: AsyncSession, datos: EmpleadoCrear) -> Usuario:
        # el "usuario" (identificador de login) del empleado es su nombre
        u = Usuario(
            usuario=datos.nombre.strip(),
            nombre=datos.nombre.strip(),
            password_hash=auth.hashear_password(datos.password),
            rol="empleado",
            activo=True,
        )
        sesion.add(u)
        await sesion.commit()
        await sesion.refresh(u)
        return u

    @staticmethod
    async def actualizar_empleado(
        sesion: AsyncSession, u: Usuario, datos: EmpleadoActualizar
    ) -> Usuario:
        if datos.nombre is not None:
            u.nombre = datos.nombre.strip()
            u.usuario = datos.nombre.strip()  # el login del empleado sigue su nombre
        if datos.password:
            u.password_hash = auth.hashear_password(datos.password)
        if datos.activo is not None:
            u.activo = datos.activo
        await sesion.commit()
        await sesion.refresh(u)
        return u

    @staticmethod
    async def borrar(sesion: AsyncSession, u: Usuario) -> None:
        await sesion.delete(u)
        await sesion.commit()

    @staticmethod
    async def cambiar_password_propia(
        sesion: AsyncSession, usuario_login: str, actual: str, nueva: str
    ) -> bool:
        """
        Cambia la contraseña del usuario logueado, verificando la actual.
        Devuelve True si se cambió, False si la contraseña actual no coincide.
        """
        res = await sesion.execute(select(Usuario).where(Usuario.usuario == usuario_login))
        u = res.scalar_one_or_none()
        if not u or not auth.verificar_password(actual, u.password_hash):
            return False
        u.password_hash = auth.hashear_password(nueva)
        await sesion.commit()
        return True

    @staticmethod
    async def asegurar_admin_inicial(sesion: AsyncSession) -> None:
        """
        Crea la cuenta admin inicial si no existe ningún admin. Los valores salen
        de variables de entorno (o usa unos por defecto para el primer arranque).
        Cambialos en el .env / Render:  ADMIN_EMAIL, ADMIN_PASSWORD
        """
        res = await sesion.execute(select(Usuario).where(Usuario.rol == "admin"))
        if res.scalar_one_or_none():
            return  # ya hay un admin, no hacer nada
        email = os.getenv("ADMIN_EMAIL", "Info@dodoricoenergy.com.ar")
        password = os.getenv("ADMIN_PASSWORD", "dodorico2026")
        admin = Usuario(
            usuario=email, nombre="Administrador",
            password_hash=auth.hashear_password(password),
            rol="admin", activo=True,
        )
        sesion.add(admin)
        await sesion.commit()
