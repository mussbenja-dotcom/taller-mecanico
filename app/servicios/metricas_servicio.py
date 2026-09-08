"""
SERVICIO de Métricas = resumen simple para el taller.

Nada de gráficos complejos: los números que importan.
- Autos que ingresaron (órdenes creadas) en el período.
- Órdenes finalizadas y cobradas.
- Total facturado (suma de órdenes cobradas del período).
- Repuestos con stock bajo (para reponer).
"""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos import OrdenTrabajo, Repuesto


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
        res = await sesion.execute(
            select(OrdenTrabajo)
            .options(selectinload(OrdenTrabajo.items))
            .where(OrdenTrabajo.creado_en >= inicio, OrdenTrabajo.creado_en < fin)
        )
        ordenes = list(res.scalars().all())

        creadas = len(ordenes)
        finalizadas = sum(1 for o in ordenes if o.estado in ("finalizada", "cobrada"))
        cobradas = sum(1 for o in ordenes if o.estado == "cobrada")

        # total facturado = suma de las órdenes cobradas del mes
        total_facturado = Decimal(0)
        for o in ordenes:
            if o.estado == "cobrada":
                for it in o.items:
                    total_facturado += Decimal(it.cantidad) * Decimal(it.precio_unitario)

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
            f"Facturación cobrada del mes: ${total_facturado:,.0f}".replace(",", ".") + ". "
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
