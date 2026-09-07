"""Prueba Etapa D: proveedores CRUD + reposición por WhatsApp."""
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.nucleo.base_datos import engine, Base
from app import modelos  # noqa

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # crear proveedor
        prov = (await c.post("/api/proveedores", json={"nombre":"Repuestos SA","telefono":"+54 9 3462 111222"})).json()
        print("proveedor creado:", prov["nombre"], "id", prov["id"])
        assert prov["id"]

        # editar proveedor
        prov2 = (await c.put(f"/api/proveedores/{prov['id']}", json={"notas":"Entrega en 24hs"})).json()
        assert prov2["notas"] == "Entrega en 24hs"
        print("proveedor editado OK")

        # repuesto CON proveedor, sin stock
        rep = (await c.post("/api/repuestos", json={"nombre":"Bujia","codigo":"B1","cantidad":0,"minimo":4,"precio":500,"proveedor_id":prov["id"]})).json()
        print("repuesto proveedor_id:", rep["proveedor_id"])
        assert rep["proveedor_id"] == prov["id"]

        # link de reposición: arma mensaje al proveedor
        r = (await c.get(f"/api/whatsapp/reposicion/{rep['id']}")).json()
        print("reposición -> proveedor:", r["proveedor"], "| tel:", r["telefono"])
        assert r["telefono"] == "5493462111222"
        assert "Bujia" in r["mensaje"] and "B1" in r["mensaje"]
        assert r["link"].startswith("https://wa.me/5493462111222")

        # repuesto SIN proveedor -> error claro
        rep2 = (await c.post("/api/repuestos", json={"nombre":"Sin prov","cantidad":0,"minimo":1,"precio":100})).json()
        r2 = await c.get(f"/api/whatsapp/reposicion/{rep2['id']}")
        print("sin proveedor -> status", r2.status_code, "(esperado 404)")
        assert r2.status_code == 404

        # borrar proveedor
        r3 = await c.delete(f"/api/proveedores/{prov['id']}")
        assert r3.status_code == 204
        print("proveedor borrado OK")

    print("\n✅ ETAPA D OK: proveedores CRUD + reposición por WhatsApp")

asyncio.run(main())
