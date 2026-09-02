"""Prueba de Etapas 4, 5 y 6: WhatsApp, métricas y QR/historial."""
import asyncio
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.nucleo.base_datos import engine, Base
from app import modelos  # noqa: F401


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        cli = (await c.post("/api/clientes", json={"nombre": "Maria Lopez", "telefono": "+54 9 3462 12-3456"})).json()
        auto = (await c.post(f"/api/clientes/{cli['id']}/autos",
                             json={"marca": "Ford", "modelo": "Ranger", "anio": 2020, "patente": "AD145JF"})).json()

        # presupuesto
        presu = (await c.post("/api/presupuestos", json={
            "auto_id": auto["id"], "descripcion": "Service completo",
            "items": [
                {"descripcion": "Filtro aceite", "cantidad": 1, "precio_unitario": 8000},
                {"descripcion": "Mano de obra", "cantidad": 1, "precio_unitario": 25000, "es_repuesto": False},
            ]
        })).json()

        # ---- ETAPA 4: WhatsApp ----
        wa = (await c.get(f"/api/whatsapp/presupuesto/{presu['id']}")).json()
        print("=== ETAPA 4: WhatsApp ===")
        print("teléfono limpio:", wa["telefono"], "(esperado 5493462123456)")
        assert wa["telefono"] == "5493462123456", wa["telefono"]
        assert wa["link"].startswith("https://wa.me/5493462123456?text=")
        print("link OK, empieza con wa.me/<tel>?text=")
        print("tiene_telefono:", wa["tiene_telefono"])

        # orden + finalizar/cobrar para métricas
        orden = (await c.post("/api/ordenes/desde-presupuesto", json={"presupuesto_id": presu["id"]})).json()
        await c.patch(f"/api/ordenes/{orden['id']}/estado", json={"estado": "finalizada"})
        await c.patch(f"/api/ordenes/{orden['id']}/estado", json={"estado": "cobrada"})

        wa2 = (await c.get(f"/api/whatsapp/orden/{orden['id']}")).json()
        assert "ORDEN DE TRABAJO" in wa2["mensaje"]
        print("mensaje de orden generado OK")

        # ---- ETAPA 5: métricas ----
        ahora = datetime.now(timezone.utc)
        met = (await c.get("/api/metricas/mes", params={"anio": ahora.year, "mes": ahora.month})).json()
        print("\n=== ETAPA 5: Métricas ===")
        print("autos ingresados:", met["autos_ingresados"])
        print("órdenes finalizadas:", met["ordenes_finalizadas"])
        print("órdenes cobradas:", met["ordenes_cobradas"])
        print("total facturado:", met["total_facturado"])
        print("resumen:", met["resumen"])
        assert met["autos_ingresados"] == 1
        assert met["ordenes_cobradas"] == 1

        # ---- ETAPA 6: QR / historial ----
        print("\n=== ETAPA 6: QR / Historial ===")
        qr = (await c.get(f"/api/autos/{auto['id']}/qr")).json()
        print("URL pública del QR:", qr["url"][:50], "...")
        print("QR generado (base64):", len(qr["qr_base64"]), "chars")
        assert qr["qr_base64"] and len(qr["qr_base64"]) > 100

        token = qr["qr_token"]
        hist = (await c.get(f"/api/historial/{token}")).json()
        print("historial: vehículo", hist["auto"]["marca"], hist["auto"]["modelo"],
              "| órdenes:", hist["total_ordenes"])
        assert hist["total_ordenes"] == 1

        # página pública HTML
        r = await c.get(f"/historial/{token}")
        assert r.status_code == 200 and "Ranger" in r.text
        print("página pública del historial carga OK")

    print("\n✅ ETAPAS 4, 5 y 6 OK")


asyncio.run(main())
