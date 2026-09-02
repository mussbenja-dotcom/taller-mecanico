"""Prueba de la Etapa 2: presupuestos y órdenes de trabajo."""
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
        # preparar cliente + auto
        cli = (await c.post("/api/clientes", json={"nombre": "Taller Test"})).json()
        auto = (await c.post(f"/api/clientes/{cli['id']}/autos",
                             json={"marca": "Ford", "modelo": "Ranger"})).json()
        print("auto:", auto["id"])

        # crear presupuesto con items
        presu = (await c.post("/api/presupuestos", json={
            "auto_id": auto["id"],
            "descripcion": "Service completo",
            "items": [
                {"descripcion": "Filtro de aceite", "cantidad": 1, "precio_unitario": 8000, "es_repuesto": True},
                {"descripcion": "Aceite 10W40 x4L", "cantidad": 4, "precio_unitario": 6000, "es_repuesto": True},
                {"descripcion": "Mano de obra", "cantidad": 1, "precio_unitario": 25000, "es_repuesto": False},
            ]
        })).json()
        print("presupuesto creado. total =", presu["total"], "(esperado 57000)")
        assert str(presu["total"]) == "57000.00" or float(presu["total"]) == 57000, presu["total"]

        # editar presupuesto (agregar un item)
        presu2 = (await c.put(f"/api/presupuestos/{presu['id']}", json={
            "items": [
                {"descripcion": "Filtro de aire", "cantidad": 1, "precio_unitario": 5000, "es_repuesto": True},
            ]
        })).json()
        print("presupuesto editado. total =", presu2["total"], "(esperado 5000)")

        # crear orden desde el presupuesto
        orden = (await c.post("/api/ordenes/desde-presupuesto",
                              json={"presupuesto_id": presu["id"]})).json()
        print("orden creada desde presupuesto:", orden["id"], "| estado:", orden["estado"], "| items:", len(orden["items"]))
        assert orden["estado"] == "pendiente"

        # cambiar estado a finalizada
        orden = (await c.patch(f"/api/ordenes/{orden['id']}/estado",
                               json={"estado": "finalizada"})).json()
        print("orden finalizada. finalizada_en:", orden["finalizada_en"] is not None)
        assert orden["finalizada_en"] is not None

        # cambiar a cobrada
        orden = (await c.patch(f"/api/ordenes/{orden['id']}/estado",
                               json={"estado": "cobrada"})).json()
        print("orden cobrada. estado:", orden["estado"])

        # verificar que NO se puede borrar (no existe el endpoint)
        r = await c.delete(f"/api/ordenes/{orden['id']}")
        print("intento de borrar orden -> status:", r.status_code, "(esperado 405, no existe)")
        assert r.status_code == 405

        # borrar el presupuesto SÍ se puede, y la orden sigue viva
        r = await c.delete(f"/api/presupuestos/{presu['id']}")
        assert r.status_code == 204
        r = await c.get(f"/api/ordenes/{orden['id']}")
        assert r.status_code == 200
        print("presupuesto borrado, la orden sigue grabada OK")

    print("\n✅ ETAPA 2 OK: presupuestos editables/borrables, órdenes permanentes")


asyncio.run(main())
