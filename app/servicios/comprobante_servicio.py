"""
SERVICIO de Comprobante PDF.

Genera un comprobante (PDF) de una orden de trabajo con: datos del taller,
cliente, vehículo, detalle de ítems (repuestos + mano de obra), total, y si
hay pagos registrados, lo pagado y el saldo. Es un comprobante PROPIO del
taller (no una factura oficial de AFIP).

Devuelve los bytes del PDF para que el navegador lo descargue.
"""
import io
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos import OrdenTrabajo, Auto, Pago

# nombre del taller (configurable por variable de entorno)
import os
NOMBRE_TALLER = os.getenv("NOMBRE_TALLER", "Dodorico Mecánica")


def _plata(n) -> str:
    return "$ " + f"{Decimal(n):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


class ServicioComprobante:

    @staticmethod
    async def generar_pdf(sesion: AsyncSession, orden_id: int) -> bytes | None:
        # traer la orden con ítems, auto y cliente
        res = await sesion.execute(
            select(OrdenTrabajo)
            .options(selectinload(OrdenTrabajo.items),
                     selectinload(OrdenTrabajo.auto).selectinload(Auto.cliente))
            .where(OrdenTrabajo.id == orden_id)
        )
        orden = res.scalar_one_or_none()
        if not orden:
            return None

        # pagos de la orden
        resp = await sesion.execute(select(Pago).where(Pago.orden_id == orden_id))
        pagos = list(resp.scalars().all())
        pagado = sum((Decimal(p.monto) for p in pagos), Decimal(0))

        auto = orden.auto
        cliente = auto.cliente if auto else None
        total = sum((Decimal(it.cantidad) * Decimal(it.precio_unitario) for it in orden.items), Decimal(0))
        saldo = total - pagado

        # ---- generar el PDF ----
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=18*mm, rightMargin=18*mm,
                                topMargin=18*mm, bottomMargin=18*mm)
        estilos = getSampleStyleSheet()
        h1 = ParagraphStyle("h1", parent=estilos["Heading1"], fontSize=20, textColor=colors.HexColor("#1a2230"))
        normal = estilos["Normal"]
        chico = ParagraphStyle("chico", parent=normal, fontSize=9, textColor=colors.HexColor("#666666"))
        elementos = []

        # encabezado: taller + N° comprobante
        elementos.append(Paragraph(f"<b>{NOMBRE_TALLER}</b>", h1))
        elementos.append(Paragraph("Comprobante de trabajo", chico))
        elementos.append(Spacer(1, 4*mm))

        fecha_str = datetime.now().strftime("%d/%m/%Y")
        entrega_str = orden.entregada_en.strftime("%d/%m/%Y") if orden.entregada_en else "—"
        info = [
            [Paragraph(f"<b>Comprobante N°:</b> {orden.id}", normal),
             Paragraph(f"<b>Fecha:</b> {fecha_str}", normal)],
            [Paragraph(f"<b>Entregado:</b> {entrega_str}", normal),
             Paragraph("", normal)],
        ]
        t_info = Table(info, colWidths=[90*mm, 84*mm])
        t_info.setStyle(TableStyle([("BOTTOMPADDING", (0,0), (-1,-1), 6)]))
        elementos.append(t_info)

        # datos del cliente y vehículo
        cli_nombre = cliente.nombre if cliente else "—"
        cli_tel = cliente.telefono if cliente and cliente.telefono else ""
        veh = " ".join(filter(None, [
            auto.marca if auto else None, auto.modelo if auto else None,
            str(auto.anio) if auto and auto.anio else None])) or "—"
        patente = auto.patente if auto and auto.patente else "—"

        datos = [
            [Paragraph("<b>Cliente</b>", chico), Paragraph("<b>Vehículo</b>", chico)],
            [Paragraph(f"{cli_nombre}<br/>{cli_tel}", normal),
             Paragraph(f"{veh}<br/>Patente: {patente}", normal)],
        ]
        t_datos = Table(datos, colWidths=[87*mm, 87*mm])
        t_datos.setStyle(TableStyle([
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
            ("INNERGRID", (0,0), (-1,-1), 0.5, colors.HexColor("#eeeeee")),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f5f5f5")),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        elementos.append(Spacer(1, 2*mm))
        elementos.append(t_datos)
        elementos.append(Spacer(1, 6*mm))

        if orden.descripcion:
            elementos.append(Paragraph(f"<b>Trabajo:</b> {orden.descripcion}", normal))
            elementos.append(Spacer(1, 4*mm))

        # tabla de ítems
        filas = [["Descripción", "Cant.", "P. Unit.", "Subtotal"]]
        for it in orden.items:
            sub = Decimal(it.cantidad) * Decimal(it.precio_unitario)
            filas.append([
                it.descripcion,
                str(int(it.cantidad)),
                _plata(it.precio_unitario),
                _plata(sub),
            ])
        t_items = Table(filas, colWidths=[95*mm, 20*mm, 30*mm, 29*mm])
        t_items.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a2230")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("ALIGN", (0,0), (0,-1), "LEFT"),
            ("LINEBELOW", (0,0), (-1,-1), 0.4, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ]))
        elementos.append(t_items)
        elementos.append(Spacer(1, 4*mm))

        # totales
        tot_filas = [["", "TOTAL", _plata(total)]]
        if pagos:
            tot_filas.append(["", "Pagado", _plata(pagado)])
            tot_filas.append(["", "Saldo pendiente", _plata(saldo)])
        t_tot = Table(tot_filas, colWidths=[95*mm, 50*mm, 29*mm])
        estilo_tot = [
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("FONTNAME", (1,0), (2,0), "Helvetica-Bold"),
            ("TEXTCOLOR", (1,0), (2,0), colors.HexColor("#1a2230")),
            ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]
        if pagos:
            estilo_tot.append(("TEXTCOLOR", (1,2), (2,2), colors.HexColor("#c0392b")))
            estilo_tot.append(("FONTNAME", (1,2), (2,2), "Helvetica-Bold"))
        t_tot.setStyle(TableStyle(estilo_tot))
        elementos.append(t_tot)

        elementos.append(Spacer(1, 12*mm))
        elementos.append(Paragraph("Gracias por confiar en nosotros.", chico))

        doc.build(elementos)
        buffer.seek(0)
        return buffer.read()
