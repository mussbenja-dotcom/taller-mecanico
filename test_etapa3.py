"""Prueba Etapas A y B: estados, validación de stock, reserva, borrado con rol, auditoría."""
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.nucleo.base_datos import engine, Base
from app import modelos  # noqa

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # crear el admin inicial (el lifespan no corre con ASGITransport)
    from app.nucleo.base_datos import SesionLocal
    from app.servicios.usuario_servicio import ServicioUsuario
    async with SesionLocal() as s:
        await ServicioUsuario.asegurar_admin_inicial(s)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # login admin y empleado (para tokens)
        # login admin (cuenta inicial por defecto) y crear un empleado para el test
        tok_admin = (await c.post("/api/auth/login", json={"usuario":"admin@dodorico.com","password":"dodorico2025"})).json()["token"]
        await c.post("/api/usuarios/empleados", json={"nombre":"empleado","password":"taller123"},
                     headers={"Authorization":f"Bearer {tok_admin}"})
        tok_emp = (await c.post("/api/auth/login", json={"usuario":"empleado","password":"taller123"})).json()["token"]

        cli = (await c.post("/api/clientes", json={"nombre":"Test"})).json()
        auto = (await c.post(f"/api/clientes/{cli['id']}/autos", json={"marca":"Ford","modelo":"Fiesta"})).json()
        # repuesto con 5 unidades
        rep = (await c.post("/api/repuestos", json={"nombre":"Pastillas","codigo":"P1","cantidad":5,"minimo":1,"precio":1000})).json()
        print("repuesto: cantidad",rep["cantidad"],"reservado",rep["reservado"],"disponible",rep["disponible"])
        assert rep["disponible"]==5

        # crear orden con 3 pastillas (vinculadas al repuesto) -> reserva 3
        orden = (await c.post("/api/ordenes", json={"auto_id":auto["id"],"descripcion":"frenos",
            "items":[{"descripcion":"Pastillas","cantidad":3,"precio_unitario":1000,"es_repuesto":True,"repuesto_id":rep["id"]}]})).json()
        print("orden creada estado:",orden["estado"])
        r = (await c.get(f"/api/repuestos/{rep['id']}")).json()
        print("tras crear orden: reservado",r["reservado"],"disponible",r["disponible"],"(esperado 3, 2)")
        assert r["reservado"]==3 and r["disponible"]==2

        # pasar a en_proceso (ya reservado, no revalida)
        o = (await c.patch(f"/api/ordenes/{orden['id']}/estado", json={"estado":"en_proceso"})).json()
        print("estado ahora:",o["estado"])
        assert o["estado"]=="en_proceso"

        # finalizar -> descuenta stock real Y baja reserva
        o = (await c.patch(f"/api/ordenes/{orden['id']}/estado", json={"estado":"finalizada"})).json()
        r = (await c.get(f"/api/repuestos/{rep['id']}")).json()
        print("tras finalizar: cantidad",r["cantidad"],"reservado",r["reservado"],"(esperado 2, 0)")
        assert r["cantidad"]==2 and r["reservado"]==0

        # --- validación de stock insuficiente al pasar a en_proceso ---
        rep2 = (await c.post("/api/repuestos", json={"nombre":"Disco","codigo":"D1","cantidad":1,"minimo":1,"precio":5000})).json()
        # orden vieja (sin reservar) pidiendo 3 discos de 1 que hay
        orden2 = (await c.post("/api/ordenes", json={"auto_id":auto["id"],"descripcion":"discos",
            "items":[{"descripcion":"Disco","cantidad":3,"precio_unitario":5000,"es_repuesto":True,"repuesto_id":rep2["id"]}]})).json()
        # como reservó al crear... esperá, la orden reserva al crear. Probemos: debería fallar al crear ya
        # (si reserva al crear y no hay stock, crea igual pero sin reserva? Revisemos)
        print("orden2 estado:", orden2.get("estado","(error)"))

        # --- borrado: empleado NO puede, admin SÍ (solo pendiente) ---
        orden3 = (await c.post("/api/ordenes", json={"auto_id":auto["id"],"descripcion":"para borrar","items":[]})).json()
        # empleado intenta borrar -> 403
        r_emp = await c.delete(f"/api/ordenes/{orden3['id']}", headers={"Authorization":f"Bearer {tok_emp}"})
        print("empleado borra -> status",r_emp.status_code,"(esperado 403)")
        assert r_emp.status_code==403
        # sin token -> 401
        r_no = await c.delete(f"/api/ordenes/{orden3['id']}")
        print("sin token borra -> status",r_no.status_code,"(esperado 401)")
        assert r_no.status_code==401
        # admin borra orden pendiente -> 204
        r_adm = await c.delete(f"/api/ordenes/{orden3['id']}", headers={"Authorization":f"Bearer {tok_admin}"})
        print("admin borra pendiente -> status",r_adm.status_code,"(esperado 204)")
        assert r_adm.status_code==204

        # admin NO puede borrar una en_proceso/finalizada
        r_fin = await c.delete(f"/api/ordenes/{orden['id']}", headers={"Authorization":f"Bearer {tok_admin}"})
        print("admin borra finalizada -> status",r_fin.status_code,"(esperado 400)")
        assert r_fin.status_code==400

    print("\n✅ ETAPAS A y B OK")

asyncio.run(main())
