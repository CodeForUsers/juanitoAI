# Creado y diseñado por David Carreres Gómez.
# Fecha: 19/02/2026
# Versión: 2.0 — Arquitectura modular
# Licencia: GPL-3.0
#
# ENTRYPOINT: Este archivo se mantiene como único punto de entrada.
# Toda la lógica de negocio está en core/ y los adaptadores en channels/.

import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from core.config import TELEGRAM_TOKEN
from core.database import DatabaseManager
from core.llm import LLMManager
from core.speech_to_text import WhisperManager
from core.web_search import WebSearchManager
from core.services.image_generation import ImageGenerationService
from core.services.scheduler import SchedulerService
from core.services.semantic_memory import SemanticMemoryService
from core.services.conversation import ConversationService
from channels.telegram.handlers import TelegramHandler

logger = logging.getLogger("juanito.main")


def main():
    # --- Inicializar componentes del core ---
    logger.info("Inicializando componentes...")

    db_manager = DatabaseManager()
    llm_manager = LLMManager()
    whisper_manager = WhisperManager()
    web_search_manager = WebSearchManager()
    image_gen_manager = ImageGenerationService(llm_manager)

    semantic_memory_manager = SemanticMemoryService(db_manager, llm_manager)
    conversation_service = ConversationService(db_manager, llm_manager, semantic_memory_service=semantic_memory_manager)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    scheduler_service = SchedulerService(db_manager, app.bot)

    # --- Inicializar canal Telegram ---
    telegram_handler = TelegramHandler(
        db_manager=db_manager,
        llm_manager=llm_manager,
        whisper_manager=whisper_manager,
        conversation_service=conversation_service,
        web_search_manager=web_search_manager,
        image_generation_service=image_gen_manager,
        scheduler_service=scheduler_service,
    )

    # Ejecutar el scheduler de APScheduler una vez que el event loop de Telegram esté listo
    async def post_init(application):
        scheduler_service.start()

    # Registrar el hook de inicio
    app.post_init = post_init

    # Registrar handlers
    app.add_handler(CommandHandler("start", telegram_handler.start))
    app.add_handler(CommandHandler("clear", telegram_handler.clear))
    app.add_handler(CommandHandler("mood", telegram_handler.mood_command))
    app.add_handler(CommandHandler("help", telegram_handler.help_command))
    app.add_handler(CommandHandler("search", telegram_handler.search_command))
    app.add_handler(CommandHandler("deepsearch", telegram_handler.deepsearch_command))
    app.add_handler(CommandHandler("img", telegram_handler.img_command))
    app.add_handler(CommandHandler("remind", telegram_handler.remind_command))
    app.add_handler(CommandHandler("nota", telegram_handler.nota_command))
    app.add_handler(CommandHandler("notas", telegram_handler.notas_command))
    app.add_handler(CommandHandler("vps", telegram_handler.vps_command))
    app.add_handler(CommandHandler("models", telegram_handler.models_command))

    # Escuchar texto, fotos, documentos, voz y audio
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VOICE | filters.AUDIO) & ~filters.COMMAND,
            telegram_handler.chat,
        )
    )

    logger.info("Juanito está online. Creado y diseñado por David Carreres Gómez.")
    app.run_polling()


if __name__ == "__main__":
    main()