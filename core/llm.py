# core/llm.py — Gestión del modelo de lenguaje (Ollama)
# Creado y diseñado por David Carreres Gómez.

import logging
import ollama

logger = logging.getLogger("juanito.llm")


class LLMManager:
    """Encapsula el cliente de Ollama con una instancia única de AsyncClient."""

    def __init__(self):
        self.client = ollama.AsyncClient()
        logger.info("Cliente Ollama (AsyncClient) inicializado.")

    async def chat(self, model, messages):
        """
        Envía mensajes al modelo y devuelve la respuesta.

        Args:
            model: Nombre del modelo a usar (chat o visión).
            messages: Lista de mensajes con formato Ollama.

        Returns:
            str: Texto de la respuesta del modelo.
        """
        try:
            response = await self.client.chat(model=model, messages=messages)
            return response['message']['content']
        except Exception as e:
            logger.error(f"Error en llamada a Ollama (modelo: {model}): {e}")
            raise

    async def list_models(self):
        """Lista los modelos disponibles en Ollama."""
        try:
            response = await self.client.list()
            modelos = [m.model for m in response.models]
            logger.info(f"Modelos disponibles: {modelos}")
            return modelos
        except Exception as e:
            logger.error(f"Error listando modelos: {e}")
            raise
