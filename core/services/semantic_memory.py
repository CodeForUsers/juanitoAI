# core/services/semantic_memory.py — Memoria Semántica (Extracción de Hechos)
# Creado y diseñado por David Carreres Gómez.

import logging
import asyncio
import re

logger = logging.getLogger("juanito.semantic_memory")


class SemanticMemoryService:
    """Extrae hechos en segundo plano para construir un perfil del usuario."""

    def __init__(self, db_manager, llm_manager):
        self.db = db_manager
        self.llm = llm_manager

    def _limpiar_respuesta_llm(self, texto: str) -> str:
        """Elimina bloques <think>...</think> y basura extra del LLM."""
        texto = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL)
        texto = re.sub(r'\n{3,}', '\n\n', texto)
        return texto.strip()

    async def analizar_y_actualizar_perfil(self, id_usuario):
        """
        Lee el historial reciente del usuario y usa el LLM para extraer
        hechos estáticos (gustos, profesión, mascotas, nombre, etc).
        """
        try:
            historial = self.db.obtener_historial(id_usuario, limite=20)
            if len(historial) < 5:
                return

            historial_texto = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial])
            perfil_actual = self.db.obtener_perfil(id_usuario)

            prompt_extraccion = (
                "Eres un analizador de perfiles semánticos.\n"
                "Tu objetivo es leer el historial de chat proporcionado y extraer únicamente AFIRMACIONES FACTUALES "
                "sobre el usuario (el humano, el que tiene role 'user') que sean útiles para recordarle en el futuro.\n"
                "Ejemplos de lo que busco: Su nombre, su profesión, mascotas, gustos fuertes, fobias, ciudad donde vive.\n"
                "NO devuelvas introducciones, ni saludos, ni comentarios, ni bloques de pensamiento.\n"
                "SOLO devuelve una lista con viñetas (- Hecho 1).\n"
                "Si no hay nada nuevo que añadir, devuelve exactamente el perfil anterior sin cambios.\n\n"
                f"Perfil que ya conoces de él hasta ahora:\n{perfil_actual}\n\n"
                f"HISTORIAL RECIENTE:\n{historial_texto}"
            )

            mensajes = [
                {"role": "system", "content": prompt_extraccion},
                {"role": "user", "content": "Extrae los hechos factuales del historial anterior."}
            ]
            
            from core.config import OLLAMA_MODEL_CHAT
            nuevos_hechos = await self.llm.chat(model=OLLAMA_MODEL_CHAT, messages=mensajes)
            
            nuevos_hechos = self._limpiar_respuesta_llm(nuevos_hechos)
            
            if nuevos_hechos:
                self.db.actualizar_perfil(id_usuario, nuevos_hechos)
                logger.info(f"Perfil semántico actualizado para el usuario {id_usuario}.")
                logger.info(f"Contenido del perfil: {nuevos_hechos[:200]}...")

        except Exception as e:
            logger.error(f"Error en extracción de memoria semántica: {e}")

    def trigger_analisis(self, id_usuario):
        """Dispara el análisis en background sin bloquear la ejecución principal."""
        asyncio.create_task(self.analizar_y_actualizar_perfil(id_usuario))
