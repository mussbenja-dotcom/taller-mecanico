"""
SERVICIO de Métricas = resumen simple para el taller.

Nada de gráficos complejos: los números que importan.
- Autos que ingresaron (órdenes creadas) en el período.
- Órdenes finalizadas y cobradas.
- Facturado / Cobrado / Por cobrar del período (ver nota abajo).
- Repuestos con stock bajo (para reponer).

Facturado vs. Cobrado vs. Por cobrar
-------------------------------------
Antes la única métrica de plata era "total facturado", y sumaba solo las
órdenes con estado 'cobrada'. Eso ignoraba señas y pagos parciales: si un
cliente pagaba una seña de $24.000 sobre una orden que seguía 'pendiente' o
'finalizada', ese ingreso real no aparecía en ningún lado.

Ahora se calculan tres cosas separadas:
- "Facturado este mes": el total (importe) de las órdenes finalizadas o
  cobradas cuya fecha de cierre (finalizada_en, o creado_en si no la tiene)
  cae en el período. Es el valor del trabajo emitido en el mes, más allá de
  si ya se cobró o no.
- "Cobrado este mes": la plata que realmente entró a caja en el período,
  sumando TODOS los pagos (Pago.monto) registrados con fecha dentro del mes,
  sin importar el estado de la orden a la que pertenecen, MÁS el total de
  las ventas de mostrador (Venta) del período -- esas se cobran completas
  en el momento. Así, una seña de $24.000 cobrada en el mes cuenta aunque
  la orden esté 'pendiente', y una venta de un repuesto suelto también.
- "Por cobrar": el saldo pendiente total a día de hoy (no es una métrica de
  "del mes", es una foto actual), sumando el saldo abierto (total - pagado)
  de todas las órdenes con saldo positivo. Es cuánto deben los clientes en
  total, más allá de cuándo se generó esa deuda.
"""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos import OrdenTrabajo, Repuesto, Pago, Venta


def _rango_mes(anio: int, mes: int):
    """Devuelve (inicio, fin) del mes pedido, en UTC."""
    inicio = datetime(anio, mes, 1, tzinfo=timezone.utc)
    if mes == 12:
        fin = datetime(anio + 1, 1, 1, tzinfo=timezone.utc)
    else:
        fin = datetime(anio, mes + 1, 1, tzinfo=timezone.utc)
    return inicio, fin


class ServicioMetricas:

    @staticmethod
    async def resumen_mes(sesion: AsyncSession, anio: int, mes: int) -> dict:
        inicio, fin = _rango_mes(anio, mes)

        # traer las órdenes del mes (por fecha de creación) con sus ítems
        # (sirve para "autos ingresados" y los conteos de finalizadas/cobradas)
        res = await sesion.execute(
            select(OrdenTrabajo)
            .options(selectinload(OrdenTrabajo.items))
            .where(OrdenTrabajo.creado_en >= inicio, OrdenTrabajo.creado_en < fin)
        )
        ordenes_del_mes = list(res.scalars().all())

        creadas = len(ordenes_del_mes)
        finalizadas = sum(1 for o in ordenes_del_mes if o.estado in ("finalizada", "cobrada"))
        cobradas = sum(1 for o in ordenes_del_mes if o.estado == "cobrada")

        # --- (a) Facturado este mes: órdenes finalizadas/cobradas CERRADAS en
        # el período (por finalizada_en; si no la tiene, se usa creado_en como
        # respaldo). Es el valor del trabajo emitido, cobrado o no.
        res_cierre = await sesion.execute(
            select(OrdenTrabajo)
            .options(selectinload(OrdenTrabajo.items))
            .where(
                OrdenTrabajo.estado.in_(("finalizada", "cobrada")),
                func.coalesce(OrdenTrabajo.finalizada_en, OrdenTrabajo.creado_en) >= inicio,
                func.coalesce(OrdenTrabajo.finalizada_en, OrdenTrabajo.creado_en) < fin,
            )
        )
        ordenes_cerradas_mes = list(res_cierre.scalars().all())
        # ================================================================
        # PLATA QUE ENTRÓ ESTE MES (dividida en dos)
        # ================================================================
        # (1) COBRADO DE CONTADO = ventas de mostrador PAGADAS del mes
        #     (efectivo/transferencia/tarjeta, NO cuenta corriente).
        res_ventas = await sesion.execute(
            select(Venta).options(selectinload(Venta.items))
            .where(Venta.creado_en >= inicio, Venta.creado_en < fin)
        )
        ventas_del_mes = list(res_ventas.scalars().all())
        cobrado_contado = Decimal(0)
        fiado_mes = Decimal(0)  # ventas a cuenta corriente de este mes (te deben)
        for v in ventas_del_mes:
            tot_v = sum((Decimal(it.cantidad) * Decimal(it.precio_unitario) for it in v.items), Decimal(0))
            if getattr(v, "pagada", True):
                cobrado_contado += tot_v
            else:
                fiado_mes += tot_v

        # (2) COBRADO DE DEUDAS = pagos de cuenta corriente (órdenes) hechos
        #     este mes. Es plata que entró de gente que estaba debiendo.
        res_pagos = await sesion.execute(
            select(Pago).where(Pago.fecha >= inicio.date(), Pago.fecha < fin.date())
        )
        cobrado_deudas = sum((Decimal(p.monto) for p in res_pagos.scalars().all()), Decimal(0))

        # total que entró a caja este mes
        total_cobrado = cobrado_contado + cobrado_deudas

        # facturado del mes (lo mantengo por compatibilidad: órdenes cerradas)
        total_facturado = Decimal(0)
        for o in ordenes_cerradas_mes:
            for it in o.items:
                total_facturado += Decimal(it.cantidad) * Decimal(it.precio_unitario)

        # ================================================================
        # LO QUE TE DEBEN (foto actual, no del mes)
        # ================================================================
        # DEUDA TOTAL = saldos pendientes de órdenes + ventas a cuenta corriente
        res_todas = await sesion.execute(
            select(OrdenTrabajo).options(selectinload(OrdenTrabajo.items))
        )
        todas_las_ordenes = list(res_todas.scalars().all())
        res_pagos_todos = await sesion.execute(select(Pago))
        pagado_por_orden: dict[int, Decimal] = {}
        for p in res_pagos_todos.scalars().all():
            pagado_por_orden[p.orden_id] = pagado_por_orden.get(p.orden_id, Decimal(0)) + Decimal(p.monto)

        deuda_ordenes = Decimal(0)
        for o in todas_las_ordenes:
            total_orden = sum(
                (Decimal(it.cantidad) * Decimal(it.precio_unitario) for it in o.items), Decimal(0)
            )
            saldo = total_orden - pagado_por_orden.get(o.id, Decimal(0))
            if saldo > 0:
                deuda_ordenes += saldo

        # deuda de ventas de mostrador a cuenta corriente (todas, no solo del mes)
        res_ventas_deuda = await sesion.execute(
            select(Venta).options(selectinload(Venta.items)).where(Venta.pagada == False)  # noqa: E712
        )
        deuda_ventas = Decimal(0)
        for v in res_ventas_deuda.scalars().all():
            deuda_ventas += sum((Decimal(it.cantidad) * Decimal(it.precio_unitario) for it in v.items), Decimal(0))

        total_por_cobrar = deuda_ordenes + deuda_ventas


        # repuestos con stock bajo (foto actual, no del mes)
        res2 = await sesion.execute(select(Repuesto))
        repuestos = res2.scalars().all()
        stock_bajo = [
            {"id": r.id, "nombre": r.nombre, "codigo": r.codigo,
             "cantidad": r.cantidad, "reservado": r.reservado,
             "disponible": r.cantidad - r.reservado, "minimo": r.minimo,
             "proveedor_id": r.proveedor_id,
             "faltan": max(0, r.minimo - r.cantidad)}
            for r in repuestos if r.cantidad <= r.minimo
        ]

        # texto resumen en lenguaje natural
        nombre_mes = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
                      "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"][mes]
        texto = (
            f"En {nombre_mes} de {anio} entraron {creadas} auto(s). "
            f"Se finalizaron {finalizadas} orden(es) y se cobraron {cobradas}. "
            f"Entró a caja: ${total_cobrado:,.0f}".replace(",", ".")
            + f" (${cobrado_contado:,.0f} de contado".replace(",", ".")
            + f" + ${cobrado_deudas:,.0f} de cobranzas)".replace(",", ".") + ". "
            + (f"Fiaste ${fiado_mes:,.0f} este mes. ".replace(",", ".") if fiado_mes > 0 else "")
            + f"Te deben en total: ${total_por_cobrar:,.0f}".replace(",", ".") + ". "
        )
        if stock_bajo:
            texto += f"Atención: {len(stock_bajo)} repuesto(s) con stock bajo."
        else:
            texto += "Sin repuestos en stock bajo."

        return {
            "anio": anio, "mes": mes,
            "autos_ingresados": creadas,
            "ordenes_finalizadas": finalizadas,
            "ordenes_cobradas": cobradas,
            "total_facturado": total_facturado,
            "total_cobrado": total_cobrado,
            "cobrado_contado": cobrado_contado,
            "cobrado_deudas": cobrado_deudas,
            "fiado_mes": fiado_mes,
            "total_por_cobrar": total_por_cobrar,
            "deuda_ordenes": deuda_ordenes,
            "deuda_ventas": deuda_ventas,
            "repuestos_stock_bajo": stock_bajo,
            "resumen": texto,
        }


class ServicioMetricasCompras:
    """Métricas basadas en el historial de compras (evolución de precios)."""

    @staticmethod
    async def evolucion_precios(sesion: AsyncSession) -> dict:
        """
        Por cada repuesto con al menos 2 compras, calcula cuánto varió el costo
        entre la primera y la última compra (monto y %). Devuelve la lista
        ordenada por mayor aumento porcentual, y también los más comprados.
        """
        from decimal import Decimal
        from app.modelos import Compra, Repuesto

        res = await sesion.execute(select(Compra).order_by(Compra.fecha, Compra.id))
        compras = list(res.scalars().all())

        # agrupar compras por repuesto
        por_rep: dict[int, list] = {}
        for c in compras:
            por_rep.setdefault(c.repuesto_id, []).append(c)

        # nombres de repuestos
        res2 = await sesion.execute(select(Repuesto))
        nombres = {r.id: (r.codigo, r.nombre) for r in res2.scalars().all()}

        aumentos = []
        mas_comprados = []
        for rep_id, lista in por_rep.items():
            codigo, nombre = nombres.get(rep_id, (None, f"#{rep_id}"))
            total_comprado = sum(int(c.cantidad) for c in lista)
            mas_comprados.append({
                "repuesto_id": rep_id, "codigo": codigo, "nombre": nombre,
                "veces": len(lista), "total_unidades": total_comprado,
            })
            if len(lista) >= 2:
                primero = Decimal(lista[0].costo_unitario)
                ultimo = Decimal(lista[-1].costo_unitario)
                if primero > 0:
                    var_monto = ultimo - primero
                    var_pct = (var_monto / primero) * 100
                    aumentos.append({
                        "repuesto_id": rep_id, "codigo": codigo, "nombre": nombre,
                        "costo_inicial": primero, "costo_actual": ultimo,
                        "variacion_monto": var_monto, "variacion_pct": round(float(var_pct), 1),
                        "compras": len(lista),
                        "fecha_inicial": lista[0].fecha, "fecha_actual": lista[-1].fecha,
                    })

        # ordenar: los que más aumentaron primero
        aumentos.sort(key=lambda a: a["variacion_pct"], reverse=True)
        mas_comprados.sort(key=lambda m: m["total_unidades"], reverse=True)

        return {
            "aumentos": aumentos,
            "mas_comprados": mas_comprados[:10],
            "hay_datos": bool(aumentos or mas_comprados),
        }
