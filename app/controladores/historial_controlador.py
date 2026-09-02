"""
CONTROLADOR de Historial/QR.

- /api/autos/{auto_id}/qr  -> devuelve el QR (base64) y la URL pública.
- /api/historial/{qr_token} -> datos del historial (JSON, público).
- /historial/{qr_token}    -> página pública que se ve al escanear el QR.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.nucleo.base_datos import obtener_sesion
from app.servicios.historial_servicio import ServicioHistorial

router = APIRouter(tags=["historial-qr"])


@router.get("/api/autos/{auto_id}/qr")
async def qr_de_auto(auto_id: int, request: Request, sesion: AsyncSession = Depends(obtener_sesion)):
    auto = await ServicioHistorial.obtener_auto_por_id(sesion, auto_id)
    if not auto:
        raise HTTPException(404, "Auto no encontrado")
    # URL pública que va a codificar el QR
    base = str(request.base_url).rstrip("/")
    url_publica = f"{base}/historial/{auto.qr_token}"
    qr_b64 = ServicioHistorial.generar_qr_base64(url_publica)
    return {"url": url_publica, "qr_base64": qr_b64, "qr_token": auto.qr_token}


@router.get("/api/historial/{qr_token}")
async def historial_json(qr_token: str, sesion: AsyncSession = Depends(obtener_sesion)):
    datos = await ServicioHistorial.por_token(sesion, qr_token)
    if not datos:
        raise HTTPException(404, "Vehículo no encontrado")
    return datos


@router.get("/historial/{qr_token}", response_class=HTMLResponse)
async def historial_pagina(qr_token: str, sesion: AsyncSession = Depends(obtener_sesion)):
    """Página pública que se muestra al escanear el QR del auto."""
    datos = await ServicioHistorial.por_token(sesion, qr_token)
    if not datos:
        return HTMLResponse("<h1>Vehículo no encontrado</h1>", status_code=404)

    a = datos["auto"]
    titulo = " ".join(filter(None, [a["marca"], a["modelo"], str(a["anio"] or "")]))
    filas = ""
    for o in datos["ordenes"]:
        items = "".join(f"<li>{it['descripcion']} (x{int(it['cantidad'])})</li>" for it in o["items"])
        fecha = o["creado_en"].strftime("%d/%m/%Y") if o["creado_en"] else ""
        filas += f"""
        <div class="orden">
          <div class="cab"><b>#{o['id']} · {o['descripcion'] or 'Orden'}</b>
            <span class="estado {o['estado']}">{o['estado']}</span></div>
          <div class="fecha">{fecha}</div>
          <ul>{items}</ul>
          <div class="total">Total: ${o['total']:,.0f}</div>
        </div>""".replace(",", ".")

    nota = a.get("nota_qr")
    nota_html = ('<div class="nota"><b>Observación:</b><br>' + nota.replace(chr(10), "<br>") + '</div>') if nota else ""
    html = f"""<!DOCTYPE html><html lang="es"><head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Historial — {titulo}</title>
    <style>
      body {{ font-family: system-ui, sans-serif; background:#0f1419; color:#e6edf3; margin:0; padding:16px; }}
      .cabecera {{ background:#1a2230; border:1px solid #2f3b4f; border-radius:10px; padding:16px; margin-bottom:16px; }}
      h1 {{ color:#ff6b35; font-size:20px; margin:0 0 8px; }}
      .dato {{ color:#8b98a9; font-size:14px; }}
      .orden {{ background:#1a2230; border:1px solid #2f3b4f; border-radius:8px; padding:12px; margin-bottom:10px; }}
      .cab {{ display:flex; justify-content:space-between; align-items:center; }}
      .fecha {{ color:#8b98a9; font-size:12px; margin:4px 0; }}
      ul {{ margin:8px 0; padding-left:20px; font-size:14px; }}
      .total {{ color:#2ea043; font-weight:700; text-align:right; }}
      .estado {{ font-size:11px; padding:2px 8px; border-radius:20px; }}
      .estado.finalizada {{ background:#14532d; color:#bbf7d0; }}
      .estado.cobrada {{ background:#1e3a8a; color:#bfdbfe; }}
      .estado.pendiente {{ background:#78350f; color:#fde68a; }}
      .nota {{ background:#2a2418; border:1px solid #6b5720; color:#fde68a; border-radius:8px; padding:12px; margin-bottom:16px; font-size:14px; }}
    </style></head><body>
    <div class="cabecera">
      <h1>🔧 {titulo or 'Vehículo'}</h1>
      <div class="dato">Patente: {a['patente'] or '—'}</div>
      <div class="dato">Titular: {a['cliente'] or '—'}</div>
      <div class="dato">{datos['total_ordenes']} trabajo(s) registrado(s)</div>
    </div>
    {nota_html}
    {filas or '<p class="dato">Sin trabajos registrados todavía.</p>'}
    </body></html>"""
    return HTMLResponse(html)
