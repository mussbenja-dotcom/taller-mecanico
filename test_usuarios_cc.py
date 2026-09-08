"""Prueba: sistema de usuarios (bcrypt, roles) + cuenta corriente (pagos/saldos)."""
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.nucleo.base_datos import engine, Base, SesionLocal
from app.servicios.usuario_servicio import ServicioUsuario
from app import modelos  # noqa

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SesionLocal() as s:
        await ServicioUsuario.asegurar_admin_inicial(s)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # --- USUARIOS ---
        tok = (await c.post("/api/auth/login", json={"usuario":"admin@dodorico.com","password":"dodorico2025"})).json()["token"]
        H = {"Authorization": f"Bearer {tok}"}
        # crear empleado
        emp = (await c.post("/api/usuarios/empleados", json={"nombre":"Pedro","password":"pedro123"}, headers=H)).json()
        print("empleado creado:", emp["nombre"], "| rol:", emp["rol"])
        assert emp["rol"] == "empleado"
        # empleado se loguea
        tokE = (await c.post("/api/auth/login", json={"usuario":"Pedro","password":"pedro123"})).json()["token"]
        print("empleado login OK")
        # empleado NO puede listar empleados (403)
        r = await c.get("/api/usuarios/empleados", headers={"Authorization":f"Bearer {tokE}"})
        assert r.status_code == 403
        print("empleado no puede gestionar usuarios (403) OK")
        # editar empleado (cambiar contraseña)
        await c.put(f"/api/usuarios/empleados/{emp['id']}", json={"password":"nueva456"}, headers=H)
        tokE2 = await c.post("/api/auth/login", json={"usuario":"Pedro","password":"nueva456"})
        assert tokE2.status_code == 200
        print("cambio de contraseña OK")

        # --- CUENTA CORRIENTE ---
        cli = (await c.post("/api/clientes", json={"nombre":"Ana","telefono":"5493462222"})).json()
        auto = (await c.post(f"/api/clientes/{cli['id']}/autos", json={"marca":"VW","modelo":"Gol","patente":"XY999ZZ"})).json()
        orden = (await c.post("/api/ordenes", json={"auto_id":auto["id"],"descripcion":"Chapa",
            "items":[{"descripcion":"Trabajo","cantidad":1,"precio_unitario":50000,"es_repuesto":False}]})).json()
        # seña de 20000
        await c.post("/api/pagos", json={"orden_id":orden["id"],"fecha":"2026-06-01","monto":20000,"nota":"seña"})
        res = (await c.get(f"/api/pagos/orden/{orden['id']}")).json()
        print("orden: total", res["total"], "pagado", res["pagado"], "saldo", res["saldo"])
        assert float(res["saldo"]) == 30000
        # deudores
        deu = (await c.get("/api/pagos/deudores")).json()
        print("deudores:", deu[0]["cliente_nombre"], "debe", deu[0]["saldo"], "auto", deu[0]["auto_desc"])
        assert float(deu[0]["saldo"]) == 30000
        # pagar el resto
        await c.post("/api/pagos", json={"orden_id":orden["id"],"fecha":"2026-06-10","monto":30000})
        deu2 = (await c.get("/api/pagos/deudores")).json()
        assert len(deu2) == 0
        print("saldo cancelado, ya no aparece en deudores OK")

    print("\n✅ USUARIOS + CUENTA CORRIENTE OK")

asyncio.run(main())
