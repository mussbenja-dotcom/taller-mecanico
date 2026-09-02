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

# modelo gratuito y rápido de Gemini
MODELO = "deep-research-preview-04-2026"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent"

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
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 800},
        }

        try:
            async with httpx.AsyncClient(timeout=30) as cliente:
                r = await cliente.post(
                    URL,
                    headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                    json=cuerpo,
                )
            if r.status_code != 200:
                return {"error": f"Gemini respondió con error ({r.status_code}). Revisá la API key."}
            data = r.json()
            texto = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"diagnostico": texto}
        except Exception as e:
            return {"error": f"No se pudo consultar la IA: {e}"}
