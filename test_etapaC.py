"""Prueba Etapa C: repuesto_id en presupuestos, compatibilidad marca/modelo, conversión."""
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
        cli = (await c.post("/api/clientes", json={"nombre":"T"})).json()
        auto = (await c.post(f"/api/clientes/{cli['id']}/autos", json={"marca":"Ford","modelo":"Fiesta"})).json()

        # repuestos: uno genérico, uno compatible Ford Fiesta
        await c.post("/api/repuestos", json={"nombre":"Filtro generico","cantidad":5,"minimo":1,"precio":100})
        await c.post("/api/repuestos", json={"nombre":"Filtro Ford","cantidad":5,"minimo":1,"precio":150,"marca_compatible":"Ford","modelo_compatible":"Fiesta"})

        # compatibilidad: con marca/modelo, el compatible va primero y marcado
        lista = (await c.get("/api/repuestos?q=Filtro&marca=Ford&modelo=Fiesta")).json()
        print("primer resultado:", lista[0]["nombre"], "| compatible:", lista[0]["compatible"])
        assert lista[0]["compatible"] is True

        # presupuesto con repuesto_id
        presu = (await c.post("/api/presupuestos", json={"auto_id":auto["id"],"descripcion":"S",
            "items":[{"descripcion":"Filtro Ford","cantidad":2,"precio_unitario":150,"es_repuesto":True,"repuesto_id":2}]})).json()
        print("presupuesto item repuesto_id:", presu["items"][0]["repuesto_id"], "(esperado 2)")
        assert presu["items"][0]["repuesto_id"] == 2

        # convertir a orden: copia repuesto_id Y reserva stock
        orden = (await c.post("/api/ordenes/desde-presupuesto", json={"presupuesto_id":presu["id"]})).json()
        print("orden item repuesto_id:", orden["items"][0]["repuesto_id"], "(esperado 2)")
        assert orden["items"][0]["repuesto_id"] == 2
        rep = (await c.get("/api/repuestos/2")).json()
        print("stock repuesto 2: reservado", rep["reservado"], "disponible", rep["disponible"], "(esperado 2, 3)")
        assert rep["reservado"] == 2 and rep["disponible"] == 3

    print("\n✅ ETAPA C OK: buscador+compatibilidad en presupuestos, conversión copia vínculo y reserva")

asyncio.run(main())
