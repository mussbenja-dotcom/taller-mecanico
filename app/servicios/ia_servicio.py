"""
SERVICIO de Diagnóstico con IA (Google Gemini).

Recibe los síntomas que describe el mecánico y devuelve un análisis con
posibles fallas y sugerencias. Usa la API de Gemini (plan gratuito).

Para que funcione hay que poner la API key en el archivo .env:
  GEMINI_API_KEY=tu_clave_aca

Cómo sacar la clave (gratis): https://aistudio.google.com/apikey
"""
import os
import httpx

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Modelos de Gemini a intentar, en orden. Si Google da de baja uno, el sistema
# prueba el siguiente automáticamente. Así no hay que tocar el código cada vez.
MODELOS = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-flash-latest"]
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

INSTRUCCION = (
    "Sos un asistente experto en mecánica automotriz que ayuda a un taller. "
    "El mecánico te describe los síntomas de un vehículo. Respondé en español, "
    "de forma clara y ordenada, con: 1) las posibles causas más probables, "
    "2) qué revisar primero, y 3) una estimación de urgencia. "
    "Sé concreto y práctico, sin relleno. Aclará que es orientativo y que hay "
    "que verificar en el taller."
)


class ServicioIA:

    @staticmethod
    def hay_clave() -> bool:
        return bool(GEMINI_API_KEY)

    @staticmethod
    async def diagnosticar(sintomas: str, datos_auto: str | None = None) -> dict:
        if not GEMINI_API_KEY:
            return {
                "error": "Falta configurar la API key de Gemini.",
                "ayuda": "Poné GEMINI_API_KEY en el archivo .env. La clave es gratis en https://aistudio.google.com/apikey",
            }

        contexto = INSTRUCCION
        if datos_auto:
            contexto += f"\n\nDatos del vehículo: {datos_auto}"

        cuerpo = {
            "system_instruction": {"parts": [{"text": contexto}]},
            "contents": [{"parts": [{"text": sintomas}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2000},
        }

        import asyncio
        ultimo_detalle = ""
        # probar cada modelo hasta que uno funcione
        for modelo in MODELOS:
            url = f"{BASE_URL}/{modelo}:generateContent"
            # por cada modelo, reintentar hasta 3 veces si está sobrecargado (503)
            for intento in range(3):
                try:
                    async with httpx.AsyncClient(timeout=30) as cliente:
                        r = await cliente.post(
                            url,
                            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                            json=cuerpo,
                        )
                    if r.status_code == 200:
                        data = r.json()
                        texto = data["candidates"][0]["content"]["parts"][0]["text"]
                        return {"diagnostico": texto}
                    try:
                        ultimo_detalle = r.json().get("error", {}).get("message", "")
                    except Exception:
                        ultimo_detalle = r.text[:200]
                    # 503 = servidor de Google sobrecargado: esperar y reintentar
                    if r.status_code == 503:
                        await asyncio.sleep(1.5 * (intento + 1))
                        continue
                    # 404 = modelo no existe: pasar al siguiente modelo
                    if r.status_code == 404:
                        break
                    # otro error: cortar y avisar
                    return {"error": "La IA no pudo responder.",
                            "ayuda": ultimo_detalle or "Revisá que la API key sea válida."}
                except Exception as e:
                    ultimo_detalle = str(e)
                    await asyncio.sleep(1)

        # ningún modelo/intento funcionó
        return {"error": "La IA está muy ocupada en este momento.",
                "ayuda": "Los servidores de Gemini están sobrecargados. Probá de nuevo en unos segundos."}
