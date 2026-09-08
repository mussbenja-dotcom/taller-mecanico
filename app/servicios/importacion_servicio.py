"""
SERVICIO de importación de stock desde Excel (.xlsx) o CSV.

Lee una planilla con columnas (no importa el orden, se detectan por nombre):
  nombre*    -> obligatorio
  codigo     -> si ya existe un repuesto con ese código, se ACTUALIZA; si no, se crea
  cantidad   -> stock (número, default 0)
  precio     -> precio de venta (número, default 0)
  minimo     -> mínimo para alerta (número, default 1)
  marca      -> marca compatible (opcional)
  modelo     -> modelo compatible (opcional)

Devuelve un resumen: cuántos se crearon, cuántos se actualizaron y los errores
por fila (para que el usuario sepa qué corregir).
"""
import io
import csv
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos import Repuesto


# nombres de columna aceptados (normalizados) -> campo interno
_ALIAS = {
    "nombre": "nombre", "descripcion": "nombre", "repuesto": "nombre",
    "codigo": "codigo", "código": "codigo", "sku": "codigo",
    "cantidad": "cantidad", "stock": "cantidad", "cant": "cantidad",
    "precio": "precio", "precio_venta": "precio", "valor": "precio",
    "minimo": "minimo", "mínimo": "minimo", "min": "minimo",
    "marca": "marca_compatible", "marca_compatible": "marca_compatible",
    "modelo": "modelo_compatible", "modelo_compatible": "modelo_compatible",
}


def _norm(s: str) -> str:
    return (s or "").strip().lower().replace(" ", "_")


def _a_entero(v, default=0) -> int:
    try:
        if v is None or str(v).strip() == "":
            return default
        return int(float(str(v).replace(",", ".")))
    except (ValueError, TypeError):
        return default


def _a_decimal(v, default=Decimal(0)) -> Decimal:
    try:
        if v is None or str(v).strip() == "":
            return default
        return Decimal(str(v).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _leer_filas(contenido: bytes, nombre_archivo: str) -> list[dict]:
    """Devuelve una lista de dicts {columna_normalizada: valor} por fila."""
    filas = []
    if nombre_archivo.lower().endswith(".csv"):
        texto = contenido.decode("utf-8-sig", errors="replace")
        lector = csv.reader(io.StringIO(texto))
        datos = list(lector)
        if not datos:
            return []
        encabezados = [_norm(h) for h in datos[0]]
        for fila in datos[1:]:
            filas.append({encabezados[i]: (fila[i] if i < len(fila) else "")
                          for i in range(len(encabezados))})
    else:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
        ws = wb.active
        filas_iter = list(ws.iter_rows(values_only=True))
        if not filas_iter:
            return []
        encabezados = [_norm(str(h)) if h is not None else "" for h in filas_iter[0]]
        for fila in filas_iter[1:]:
            filas.append({encabezados[i]: (fila[i] if i < len(fila) else "")
                          for i in range(len(encabezados))})
    return filas


class ServicioImportacion:

    @staticmethod
    async def importar_stock(sesion: AsyncSession, contenido: bytes, nombre_archivo: str) -> dict:
        filas = _leer_filas(contenido, nombre_archivo)
        if not filas:
            return {"error": "El archivo está vacío o no se pudo leer."}

        creados = 0
        actualizados = 0
        errores = []

        for n, fila in enumerate(filas, start=2):  # fila 2 = primera de datos
            # mapear columnas por alias
            datos = {}
            for col, valor in fila.items():
                campo = _ALIAS.get(col)
                if campo:
                    datos[campo] = valor

            nombre = str(datos.get("nombre", "") or "").strip()
            if not nombre:
                # fila sin nombre: se ignora si está totalmente vacía, si no, error
                if any(str(v).strip() for v in fila.values()):
                    errores.append(f"Fila {n}: falta el nombre del repuesto.")
                continue

            codigo = str(datos.get("codigo", "") or "").strip() or None
            cantidad = _a_entero(datos.get("cantidad"), 0)
            precio = _a_decimal(datos.get("precio"), Decimal(0))
            minimo = _a_entero(datos.get("minimo"), 1)
            marca = str(datos.get("marca_compatible", "") or "").strip() or None
            modelo = str(datos.get("modelo_compatible", "") or "").strip() or None

            # si hay código, buscar si ya existe para actualizar
            existente = None
            if codigo:
                res = await sesion.execute(select(Repuesto).where(Repuesto.codigo == codigo))
                existente = res.scalar_one_or_none()

            if existente:
                existente.nombre = nombre
                existente.cantidad = cantidad
                existente.precio = precio
                existente.minimo = minimo
                if marca is not None:
                    existente.marca_compatible = marca
                if modelo is not None:
                    existente.modelo_compatible = modelo
                actualizados += 1
            else:
                sesion.add(Repuesto(
                    nombre=nombre, codigo=codigo, cantidad=cantidad,
                    precio=precio, minimo=minimo,
                    marca_compatible=marca, modelo_compatible=modelo,
                ))
                creados += 1

        await sesion.commit()
        return {
            "creados": creados, "actualizados": actualizados,
            "errores": errores, "total_filas": len(filas),
        }
