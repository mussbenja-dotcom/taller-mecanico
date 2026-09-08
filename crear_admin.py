import asyncio
from app.nucleo.base_datos import SesionLocal
from app.servicios.usuario_servicio import ServicioUsuario

async def main():
    async with SesionLocal() as sesion:
        # Esto lee tu .env local y guarda el usuario en Neon con la clave encriptada
        await ServicioUsuario.asegurar_admin_inicial(sesion)
    print("Éxito: Usuario administrador creado en la base de datos remota.")

asyncio.run(main())
