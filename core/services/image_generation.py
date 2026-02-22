# core/services/image_generation.py — Generación de Imágenes (HuggingFace Inference API)
# Creado y diseñado por David Carreres Gómez.

import logging
import asyncio
import re
import aiohttp

logger = logging.getLogger("juanito.image_generation")

# Modelos gratuitos de HuggingFace ordenados por velocidad/calidad
HF_MODELS = [
    "black-forest-labs/FLUX.1-schnell",       # Rápido y bueno
    "stabilityai/sdxl-turbo",                  # Fallback
]

HF_API_URL = "https://router.huggingface.co/hf-inference/models/{model}"


class ImageGenerationService:
    """
    Servicio para generar imágenes usando la API de Inferencia de HuggingFace.
    Requiere un token gratuito (HF_API_TOKEN en .env).
    """

    def __init__(self, llm_manager):
        self.llm = llm_manager
        from core.config import HF_API_TOKEN
        self.hf_token = HF_API_TOKEN

    async def _traducir_prompt(self, prompt: str) -> str:
        """Traduce de forma oculta el prompt al inglés para mejores resultados gráficos."""
        try:
            mensajes = [
                {
                    "role": "system",
                    "content": "Translate the following text to English. Reply ONLY with the translation, nothing else. No explanations, no quotes, no thinking."
                },
                {"role": "user", "content": prompt}
            ]
            from core.config import OLLAMA_MODEL_CHAT
            respuesta_ingles = await self.llm.chat(model=OLLAMA_MODEL_CHAT, messages=mensajes)
            texto_limpio = respuesta_ingles.strip()
            # Quitar bloques <think> si el modelo los mete
            if "<think>" in texto_limpio:
                texto_limpio = re.sub(r'<think>.*?</think>', '', texto_limpio, flags=re.DOTALL).strip()
            texto_limpio = texto_limpio.strip('"').strip("'")
            return texto_limpio
        except Exception as e:
            logger.error(f"Error traduciendo prompt de imagen: {e}")
            return prompt

    async def generate_image(self, prompt: str) -> bytes:
        """
        Genera una imagen con HuggingFace Inference API.
        Intenta varios modelos hasta que uno funcione.
        """
        if not self.hf_token:
            raise Exception("No se ha configurado HF_API_TOKEN en el archivo .env. Regístrate gratis en huggingface.co y genera un token.")

        logger.info(f"Petición de imagen original: '{prompt}'")
        prompt_ingles = await self._traducir_prompt(prompt)
        logger.info(f"Petición de imagen traducida: '{prompt_ingles}'")

        headers = {"Authorization": f"Bearer {self.hf_token}"}
        payload = {"inputs": prompt_ingles}
        timeout = aiohttp.ClientTimeout(total=120)
        errores = []

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for modelo in HF_MODELS:
                url = HF_API_URL.format(model=modelo)
                nombre_corto = modelo.split("/")[-1]
                logger.info(f"Intentando modelo HF: {nombre_corto}")

                for intento in range(2):
                    try:
                        async with session.post(url, json=payload) as response:
                            content_type = response.headers.get("content-type", "")

                            if response.status == 200 and "image" in content_type:
                                data = await response.read()
                                logger.info(f"✅ Imagen generada con {nombre_corto} ({len(data)} bytes).")
                                return data

                            elif response.status == 503:
                                # Modelo se está cargando (cold start)
                                body = await response.json()
                                wait_time = body.get("estimated_time", 20)
                                logger.warning(f"{nombre_corto} cargando, espera ~{wait_time:.0f}s...")
                                await asyncio.sleep(min(wait_time, 30))
                                continue

                            elif response.status == 429:
                                logger.warning(f"Rate limit en {nombre_corto}")
                                errores.append(f"{nombre_corto}: rate limited")
                                break

                            else:
                                body_text = await response.text()
                                logger.warning(f"{nombre_corto} devolvió {response.status}: {body_text[:120]}")
                                errores.append(f"{nombre_corto}: HTTP {response.status}")
                                break

                    except asyncio.TimeoutError:
                        errores.append(f"{nombre_corto}: timeout")
                        logger.warning(f"Timeout con {nombre_corto}")
                        break
                    except Exception as e:
                        errores.append(f"{nombre_corto}: {str(e)[:60]}")
                        logger.warning(f"Error con {nombre_corto}: {e}")
                        break

        resumen = "; ".join(errores)
        raise Exception(f"Ningún modelo de HuggingFace respondió: {resumen}")
