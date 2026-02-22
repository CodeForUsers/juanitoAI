# core/services/conversation.py — Servicio central de conversación
# Creado y diseñado por David Carreres Gómez.

import logging
import time
import re

from core.config import CONTEXTO_BASE, OLLAMA_MODEL_CHAT, OLLAMA_MODEL_VISION
from core.config import RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW

logger = logging.getLogger("juanito.conversation")


class ConversationService:
    """Orquesta la lógica de un mensaje: rate limit -> STT -> BD -> LLM -> BD -> Humor."""

    def __init__(self, db_manager, llm_manager, semantic_memory_service=None):
        self.db = db_manager
        self.llm = llm_manager
        self.semantic = semantic_memory_service
        # Rate limiting en memoria: {user_id: [timestamps]}
        self._rate_limits = {}

    def check_rate_limit(self, user_id):
        """
        Comprueba si el usuario ha excedido el rate limit.
        Returns:
            True si puede enviar, False si está limitado.
        """
        if RATE_LIMIT_MESSAGES <= 0:
            return True

        ahora = time.time()
        if user_id not in self._rate_limits:
            self._rate_limits[user_id] = []

        # Limpiar timestamps antiguos
        self._rate_limits[user_id] = [
            ts for ts in self._rate_limits[user_id]
            if ahora - ts < RATE_LIMIT_WINDOW
        ]

        if len(self._rate_limits[user_id]) >= RATE_LIMIT_MESSAGES:
            logger.warning(f"Rate limit alcanzado para usuario {user_id}.")
            return False

        self._rate_limits[user_id].append(ahora)
        return True

    async def procesar_mensaje(self, message):
        """
        Procesa un Message del core y devuelve la respuesta del LLM.
        """
        from core.config import CONTEXTO_BASE, OLLAMA_MODEL_CHAT, OLLAMA_MODEL_VISION
        
        user_id = message.user_id

        # 1. Extraer texto principal (texto + capturas + audios)
        texto = ""
        if message.text:
            texto += message.text + "\n"
        if message.caption:
            texto += message.caption + "\n"
        if message.audio_text:
            if len(message.audio_text) > 500:
                texto += f"[AUDIO LARGO DETECTADO] Haz un resumen ejecutivo en viñetas de lo que cuenta el usuario a continuación y respóndele:\n\n{message.audio_text}\n"
            else:
                texto += f"[Audio transcrito]: {message.audio_text}\n"
        
        texto = texto.strip()

        if not texto and message.images:
            texto = "Describe esta imagen."
        if not texto: return None

        # 2. Configurar el System Prompt (Humor + Memoria Semántica)
        humor_actual = self.db.obtener_o_crear_humor(user_id)
        
        perfil = self.db.obtener_perfil(user_id) if hasattr(self.db, 'obtener_perfil') else ""
        if perfil and "<think>" in perfil:
            perfil = re.sub(r'<think>.*?</think>', '', perfil, flags=re.DOTALL).strip()
        
        contexto = CONTEXTO_BASE
        if perfil:
            contexto += f"\n\n[MEMORIA SEMÁNTICA — lo que sabes del usuario, úsalo naturalmente]: \n{perfil}\n"
            logger.info(f"Perfil semántico inyectado para usuario {user_id} ({len(perfil)} chars).")

        prompt_sistema = (
            f"{contexto}\n\n"
            f"TU ESTADO ACTUAL: Estás de humor '{humor_actual}'.\n"
            "IMPORTANTE: Tus respuestas deben ser CORTAS y directas, no te enrolles como una persiana."
        )

        mensajes_para_llm = [{"role": "system", "content": prompt_sistema}]

        # 3. Añadir historial
        historial = self.db.obtener_historial(user_id)
        mensajes_para_llm.extend(historial)

        # 4. Añadir mensaje actual
        msg_contenido = {"role": "user", "content": texto}
        if message.images:
            msg_contenido["images"] = message.images
        mensajes_para_llm.append(msg_contenido)

        # Seleccionar modelo
        modelo_usar = OLLAMA_MODEL_VISION if message.images else OLLAMA_MODEL_CHAT

        try:
            # 5. Llamar al LLM
            respuesta = await self.llm.chat(model=modelo_usar, messages=mensajes_para_llm)

            # 6. Guardar en DB
            self.db.guardar_mensaje(user_id, "user", texto)
            self.db.guardar_mensaje(user_id, "assistant", respuesta)

            # 7. Probabilidad de cambio de humor (5%)
            self.db.cambio_aleatorio_humor(user_id, probabilidad=0.05)
            
            # 8. Extraer perfil semántico cada 15 mensajes
            if self.semantic:
                total_mensajes = self.db.contar_mensajes(user_id, rol="user")
                if total_mensajes > 0 and total_mensajes % 15 == 0:
                    self.semantic.trigger_analisis(user_id)

            logger.info(f"Mensaje procesado para usuario {user_id} (modelo: {modelo_usar}).")
            return respuesta

        except Exception as e:
            logger.error(f"Error procesando mensaje de usuario {user_id}: {e}")
            raise
