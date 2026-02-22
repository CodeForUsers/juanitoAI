# core/speech_to_text.py — Transcripción de audio con Whisper
# Creado y diseñado por David Carreres Gómez.

import logging
import whisper

from core.config import WHISPER_MODEL_SIZE

logger = logging.getLogger("juanito.stt")


class WhisperManager:
    """Gestiona la transcripción de audio a texto usando OpenAI Whisper."""

    def __init__(self, model_size=None):
        self.model_size = model_size or WHISPER_MODEL_SIZE
        logger.info(f"Cargando modelo Whisper ({self.model_size})... esto puede tardar un poco.")
        self.model = whisper.load_model(self.model_size)
        logger.info("Modelo Whisper cargado correctamente.")

    def transcribe(self, audio_path):
        """
        Transcribe un archivo de audio a texto.

        Args:
            audio_path: Ruta al archivo de audio.

        Returns:
            str: Texto transcrito.
        """
        try:
            resultado = self.model.transcribe(audio_path)
            texto = resultado["text"]
            logger.info(f"Audio transcrito ({len(texto)} caracteres).")
            return texto
        except Exception as e:
            logger.error(f"Error transcribiendo audio: {e}")
            raise
