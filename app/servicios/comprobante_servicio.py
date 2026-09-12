"""
SERVICIO de Comprobante PDF.

Genera comprobantes en PDF con datos del taller, cliente, vehículo, detalle
de ítems (repuestos + mano de obra) y totales. Son comprobantes PROPIOS del
taller (no una factura oficial de AFIP).

Hay tres generadores, mismo patrón:
- generar_pdf(orden_id): comprobante de una ORDEN de trabajo. Si hay pagos
  registrados, muestra lo pagado y el saldo pendiente.
- generar_pdf_presupuesto(presupuesto_id): comprobante de un PRESUPUESTO.
  No tiene pagos (todavía no es un trabajo confirmado), así que en su lugar
  muestra las condiciones habituales de un presupuesto (validez, que los
  precios pueden variar, etc).
- generar_pdf_venta(venta_id): comprobante de una VENTA DE MOSTRADOR. Se
  cobra completa en el momento (no hay saldo ni condiciones de validez),
  así que muestra directamente el total y la forma de pago.

Los tres devuelven los bytes del PDF para que el navegador lo descargue.
"""
import io
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos import OrdenTrabajo, Presupuesto, Auto, Pago, Venta

# nombre del taller (configurable por variable de entorno)
import os
NOMBRE_TALLER = os.getenv("NOMBRE_TALLER", "Dodorico Mecánica")
# días de validez de un presupuesto (configurable por variable de entorno)
DIAS_VALIDEZ_PRESUPUESTO = int(os.getenv("DIAS_VALIDEZ_PRESUPUESTO", "15"))


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

    @staticmethod
    async def generar_pdf_presupuesto(sesion: AsyncSession, presupuesto_id: int) -> bytes | None:
        # traer el presupuesto con ítems, auto y cliente (mismo patrón que la orden)
        res = await sesion.execute(
            select(Presupuesto)
            .options(selectinload(Presupuesto.items),
                     selectinload(Presupuesto.auto).selectinload(Auto.cliente))
            .where(Presupuesto.id == presupuesto_id)
        )
        presupuesto = res.scalar_one_or_none()
        if not presupuesto:
            return None

        auto = presupuesto.auto
        cliente = auto.cliente if auto else None
        total = sum(
            (Decimal(it.cantidad) * Decimal(it.precio_unitario) for it in presupuesto.items),
            Decimal(0),
        )

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

        # encabezado: taller + N° de presupuesto
        elementos.append(Paragraph(f"<b>{NOMBRE_TALLER}</b>", h1))
        elementos.append(Paragraph("Presupuesto", chico))
        elementos.append(Spacer(1, 4*mm))

        fecha_emision = presupuesto.creado_en or datetime.now()
        fecha_str = fecha_emision.strftime("%d/%m/%Y")
        vencimiento = fecha_emision + timedelta(days=DIAS_VALIDEZ_PRESUPUESTO)
        info = [
            [Paragraph(f"<b>Presupuesto N°:</b> {presupuesto.id}", normal),
             Paragraph(f"<b>Fecha:</b> {fecha_str}", normal)],
            [Paragraph(f"<b>Válido hasta:</b> {vencimiento.strftime('%d/%m/%Y')}", normal),
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

        if presupuesto.descripcion:
            elementos.append(Paragraph(f"<b>Trabajo:</b> {presupuesto.descripcion}", normal))
            elementos.append(Spacer(1, 4*mm))

        # tabla de ítems
        filas = [["Descripción", "Cant.", "P. Unit.", "Subtotal"]]
        for it in presupuesto.items:
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

        # total
        t_tot = Table([["", "TOTAL", _plata(total)]], colWidths=[95*mm, 50*mm, 29*mm])
        t_tot.setStyle(TableStyle([
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("FONTNAME", (1,0), (2,0), "Helvetica-Bold"),
            ("TEXTCOLOR", (1,0), (2,0), colors.HexColor("#1a2230")),
            ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        elementos.append(t_tot)
        elementos.append(Spacer(1, 8*mm))

        # condiciones (en vez de pagos/saldo, que no aplican a un presupuesto)
        condiciones = (
            f"Presupuesto válido por {DIAS_VALIDEZ_PRESUPUESTO} días desde la fecha de emisión. "
            "Los precios pueden variar sin previo aviso, sujeto a disponibilidad de repuestos. "
            "No incluye trabajos o repuestos no detallados arriba."
        )
        elementos.append(Paragraph(f"<b>Condiciones:</b> {condiciones}", chico))
        elementos.append(Spacer(1, 8*mm))
        elementos.append(Paragraph("Gracias por confiar en nosotros.", chico))

        doc.build(elementos)
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    async def generar_pdf_venta(sesion: AsyncSession, venta_id: int) -> bytes | None:
        # traer la venta con ítems y cliente (si tiene)
        res = await sesion.execute(
            select(Venta)
            .options(selectinload(Venta.items), selectinload(Venta.cliente))
            .where(Venta.id == venta_id)
        )
        venta = res.scalar_one_or_none()
        if not venta:
            return None

        cliente = venta.cliente
        total = sum(
            (Decimal(it.cantidad) * Decimal(it.precio_unitario) for it in venta.items),
            Decimal(0),
        )

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

        # encabezado: taller + N° de venta
        elementos.append(Paragraph(f"<b>{NOMBRE_TALLER}</b>", h1))
        elementos.append(Paragraph("Comprobante de venta (mostrador)", chico))
        elementos.append(Spacer(1, 4*mm))

        fecha_emision = venta.creado_en or datetime.now()
        fecha_str = fecha_emision.strftime("%d/%m/%Y %H:%M")
        info = [
            [Paragraph(f"<b>Venta N°:</b> {venta.id}", normal),
             Paragraph(f"<b>Fecha:</b> {fecha_str}", normal)],
        ]
        t_info = Table(info, colWidths=[90*mm, 84*mm])
        t_info.setStyle(TableStyle([("BOTTOMPADDING", (0,0), (-1,-1), 6)]))
        elementos.append(t_info)

        # cliente (si la venta no tiene, es "consumidor final")
        cli_nombre = cliente.nombre if cliente else "Consumidor final"
        cli_tel = cliente.telefono if cliente and cliente.telefono else ""
        elementos.append(Paragraph(f"<b>Cliente:</b> {cli_nombre}" + (f" · {cli_tel}" if cli_tel else ""), normal))
        elementos.append(Spacer(1, 6*mm))

        # tabla de ítems
        filas = [["Descripción", "Cant.", "P. Unit.", "Subtotal"]]
        for it in venta.items:
            sub = Decimal(it.cantidad) * Decimal(it.precio_unitario)
            filas.append([
                it.descripcion,
                str(int(it.cantidad)) if float(it.cantidad) == int(it.cantidad) else str(it.cantidad),
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

        # total
        t_tot = Table([["", "TOTAL", _plata(total)]], colWidths=[95*mm, 50*mm, 29*mm])
        t_tot.setStyle(TableStyle([
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("FONTNAME", (1,0), (2,0), "Helvetica-Bold"),
            ("TEXTCOLOR", (1,0), (2,0), colors.HexColor("#1a2230")),
            ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        elementos.append(t_tot)
        elementos.append(Spacer(1, 6*mm))

        # forma de pago (la venta se cobra completa en el momento, sin saldo)
        pago_str = f"<b>Forma de pago:</b> {venta.forma_pago}" if venta.forma_pago else "<b>Pagado en el momento.</b>"
        elementos.append(Paragraph(pago_str, normal))
        if venta.notas:
            elementos.append(Spacer(1, 2*mm))
            elementos.append(Paragraph(f"<b>Notas:</b> {venta.notas}", chico))

        elementos.append(Spacer(1, 8*mm))
        elementos.append(Paragraph("Gracias por su compra.", chico))

        doc.build(elementos)
        buffer.seek(0)
        return buffer.read()
