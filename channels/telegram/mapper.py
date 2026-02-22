# channels/telegram/mapper.py — Conversión de objetos Telegram a core.Message
# Creado y diseñado por David Carreres Gómez.

import os
import asyncio
import tempfile
import logging

from core.models import Message

logger = logging.getLogger("juanito.telegram.mapper")


async def telegram_update_to_message(update, context, whisper_manager=None):
    """
    Convierte un telegram.Update en un core.models.Message.
    Procesa texto, fotos, audio/voz y captions.

    Args:
        update: telegram.Update entrante.
        context: telegram.ext.ContextTypes.DEFAULT_TYPE.
        whisper_manager: WhisperManager para transcribir audios (opcional).

    Returns:
        core.models.Message o None si no hay contenido procesable.
    """
    tg_message = update.message
    if not tg_message:
        return None

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    tipo_chat = update.effective_chat.type
    is_group = tipo_chat in ["group", "supergroup"]

    texto = tg_message.text or ""
    caption = tg_message.caption or ""
    images = []
    audio_text = ""
    bot_mentioned = False

    # --- Procesar mención en grupos ---
    if is_group:
        bot_username = (await context.bot.get_me()).username
        mencion = f"@{bot_username}"
        contenido_total = f"{texto} {caption}"
        bot_mentioned = (
            mencion in contenido_total
            or "Juanito" in contenido_total
            or "juanito" in contenido_total
        )

    # --- Procesar Audio/Voz ---
    if (tg_message.voice or tg_message.audio) and whisper_manager:
        try:
            archivo_voz = tg_message.voice if tg_message.voice else tg_message.audio
            file_id = archivo_voz.file_id
            new_file = await context.bot.get_file(file_id)

            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
                await new_file.download_to_drive(custom_path=temp_audio.name)
                temp_path = temp_audio.name

            # Transcribir en executor para no bloquear el event loop
            loop = asyncio.get_running_loop()
            audio_text = await loop.run_in_executor(
                None, lambda: whisper_manager.transcribe(temp_path)
            )

            # Borrar archivo temporal
            os.remove(temp_path)
            logger.info(f"Audio transcrito para usuario {user_id}: {len(audio_text)} chars")

        except Exception as e:
            logger.error(f"Error transcribiendo audio de usuario {user_id}: {e}")
            raise

    # --- Procesar Documentos ---
    if tg_message.document:
        doc = tg_message.document
        if doc.file_name and doc.file_name.endswith(('.txt', '.md', '.csv', '.log')):
            try:
                file_id = doc.file_id
                new_file = await context.bot.get_file(file_id)
                
                with tempfile.NamedTemporaryFile(delete=False) as temp_doc:
                    await new_file.download_to_drive(custom_path=temp_doc.name)
                    temp_path = temp_doc.name
                    
                with open(temp_path, "r", encoding="utf-8") as f:
                    doc_content = f.read()
                    
                os.remove(temp_path)
                
                texto_doc = f"\n[Contenido del documento '{doc.file_name}']:\n{doc_content}\n"
                texto = texto + texto_doc if texto else texto_doc
                logger.info(f"Documento de texto procesado ({len(doc_content)} chars)")
            except Exception as e:
                logger.error(f"Error procesando documento: {e}")

    # --- Procesar Fotos ---
    if tg_message.photo:
        foto = await tg_message.photo[-1].get_file()
        foto_bytes = await foto.download_as_bytearray()
        images.append(bytes(foto_bytes))

    # --- Determinar texto final ---
    if audio_text:
        texto_final = audio_text
    elif texto:
        texto_final = texto
    elif caption:
        texto_final = caption
    elif images:
        texto_final = ""
    else:
        return None

    return Message(
        user_id=user_id,
        chat_id=chat_id,
        text=texto_final,
        images=images,
        audio_text=audio_text,
        is_group=is_group,
        channel="telegram",
        bot_mentioned=bot_mentioned,
        caption=caption,
    )
