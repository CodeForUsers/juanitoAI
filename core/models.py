# core/models.py — Clases de dominio (agnósticas de canal)
# Creado y diseñado por David Carreres Gómez.

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    """
    Representa un mensaje entrante de cualquier canal.
    El canal convierte su formato nativo a este objeto antes de pasarlo al core.
    """
    user_id: int
    chat_id: int
    text: str = ""
    images: list = field(default_factory=list)       # Lista de bytes de imágenes
    audio_text: str = ""                              # Texto ya transcrito del audio
    is_group: bool = False
    channel: str = "telegram"                         # telegram, whatsapp, signal…
    bot_mentioned: bool = False                       # Si mencionaron al bot en grupo
    caption: str = ""                                 # Caption de foto/documento


@dataclass
class UserContext:
    """Contexto persistente de un usuario."""
    humor: str = "sarcástico"
    idioma: Optional[str] = None
