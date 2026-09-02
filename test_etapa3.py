"""Prueba de la Etapa 3: stock, descuento al finalizar y alerta de stock bajo."""
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
        cli = (await c.post("/api/clientes", json={"nombre": "Stock Test"})).json()
        auto = (await c.post(f"/api/clientes/{cli['id']}/autos",
                             json={"marca": "Ford", "modelo": "Ranger"})).json()

        rep = (await c.post("/api/repuestos", json={
            "nombre": "Filtro de aceite", "codigo": "FA-001",
            "cantidad": 5, "minimo": 2, "precio": 8000
        })).json()
        print("repuesto creado:", rep["nombre"], "| cantidad:", rep["cantidad"], "| bajo:", rep["stock_bajo"])
        assert rep["cantidad"] == 5 and rep["stock_bajo"] is False

        orden = (await c.post("/api/ordenes", json={
            "auto_id": auto["id"], "descripcion": "Service",
            "items": [
                {"descripcion": "Filtro de aceite", "cantidad": 3, "precio_unitario": 8000,
                 "es_repuesto": True, "repuesto_id": rep["id"]},
                {"descripcion": "Mano de obra", "cantidad": 1, "precio_unitario": 20000,
                 "es_repuesto": False},
            ]
        })).json()
        print("orden creada:", orden["id"], "| total:", orden["total"])

        r = (await c.get(f"/api/repuestos/{rep['id']}")).json()
        print("stock antes de finalizar:", r["cantidad"], "(esperado 5)")
        assert r["cantidad"] == 5

        await c.patch(f"/api/ordenes/{orden['id']}/estado", json={"estado": "finalizada"})
        r = (await c.get(f"/api/repuestos/{rep['id']}")).json()
        print("stock tras finalizar:", r["cantidad"], "| stock_bajo:", r["stock_bajo"], "(esperado 2, True)")
        assert r["cantidad"] == 2 and r["stock_bajo"] is True

        await c.patch(f"/api/ordenes/{orden['id']}/estado", json={"estado": "cobrada"})
        r = (await c.get(f"/api/repuestos/{rep['id']}")).json()
        print("stock tras cobrar:", r["cantidad"], "(esperado 2)")
        assert r["cantidad"] == 2

        bajos = (await c.get("/api/repuestos", params={"solo_bajos": "true"})).json()
        print("repuestos con stock bajo:", len(bajos))
        assert len(bajos) == 1

        r = (await c.patch(f"/api/repuestos/{rep['id']}/ajustar", json={"delta": 10})).json()
        print("tras reponer +10:", r["cantidad"], "| bajo:", r["stock_bajo"], "(esperado 12, False)")
        assert r["cantidad"] == 12 and r["stock_bajo"] is False

    print("\n✅ ETAPA 3 OK: descuento al finalizar, alerta de stock bajo, idempotencia")


asyncio.run(main())
