"""Prueba de humo del sistema MVC: verifica que las capas conversan bien."""
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.nucleo.base_datos import engine, Base
from app import modelos  # noqa: F401


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/salud")
        assert r.status_code == 200, r.text
        print("salud:", r.json())

        r = await c.post("/api/clientes", json={
            "nombre": "Juan Perez", "telefono": "5493462123456"
        })
        assert r.status_code == 201, r.text
        cli = r.json()
        print("cliente creado:", cli["id"], cli["nombre"])

        r = await c.post(f"/api/clientes/{cli['id']}/autos", json={
            "marca": "Ford", "modelo": "Ranger", "anio": 2019, "kilometraje": 85000
        })
        assert r.status_code == 201, r.text
        auto = r.json()
        print("auto creado:", auto["marca"], auto["modelo"], "| qr:", auto["qr_token"][:8], "...")

        r = await c.get(f"/api/clientes/{cli['id']}")
        assert r.status_code == 200, r.text
        print("cliente con autos:", len(r.json()["autos"]))

        r = await c.get("/api/clientes", params={"q": "Perez"})
        print("busqueda:", len(r.json()), "resultado(s)")

        r = await c.put(f"/api/autos/{auto['id']}", json={"kilometraje": 90000})
        assert r.status_code == 200, r.text
        print("km actualizado:", r.json()["kilometraje"])

        r = await c.delete(f"/api/clientes/{cli['id']}")
        assert r.status_code == 204, r.text
        r = await c.get(f"/api/autos/{auto['id']}")
        assert r.status_code == 404
        print("borrado en cascada OK")

    print("\n✅ MVC funcionando: vista → controlador → servicio → modelo")


asyncio.run(main())
