# channels/telegram/handlers.py — Handlers específicos de Telegram
# Creado y diseñado por David Carreres Gómez.

import logging
from telegram import Update
from telegram.ext import ContextTypes

from core.config import MENSAJE_INICIAL, ALLOWED_USER_IDS, ADMIN_USER_IDS, ADMIN_USERNAMES
from channels.telegram.mapper import telegram_update_to_message
from core.services.monitoring import SystemMonitoringService
from core.services.image_generation import ImageGenerationService

logger = logging.getLogger("juanito.telegram.handlers")


class TelegramHandler:
    """
    Contiene todos los handlers de Telegram.
    Delega la lógica de negocio al ConversationService y otros managers del core.
    """

    def __init__(self, db_manager, llm_manager, whisper_manager, conversation_service, web_search_manager=None, image_generation_service=None, scheduler_service=None):
        self.db = db_manager
        self.llm = llm_manager
        self.whisper = whisper_manager
        self.conversation = conversation_service
        self.web_search = web_search_manager
        self.image_gen = image_generation_service
        self.scheduler = scheduler_service

    def _is_allowed(self, user_id):
        """Comprueba si un usuario está en la whitelist (si está activa)."""
        if not ALLOWED_USER_IDS:
            return True  # Sin whitelist → todos pueden usar el bot
        return user_id in ALLOWED_USER_IDS

    def _is_admin(self, update: Update):
        """Comprueba si el usuario del mensaje actual es admin por ID o por @username."""
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        if user_id in ADMIN_USER_IDS:
            return True
        if username and username.lower() in ADMIN_USERNAMES:
            return True
        return False

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /start."""
        user_id = update.effective_user.id
        if not self._is_allowed(user_id):
            await update.message.reply_text("Lo siento, no tienes permiso para usar este bot.")
            return
        logger.info(f"/start de usuario {user_id}")
        await update.message.reply_text(MENSAJE_INICIAL)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /help."""
        user_id = update.effective_user.id
        if not self._is_allowed(user_id):
            return

        ayuda = (
            "🤖 *Ayuda de Juanito* 🤖\n\n"
            "Soy Juanito, tu mayordomo digital con personalidad propia.\n"
            "Creado y diseñado por David Carreres Gómez.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *COMANDOS BÁSICOS*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "`/start` — Despierta a Juanito\n"
            "`/help` — Muestra esta ayuda\n"
            "`/clear` — Borra tu historial de chat\n"
            "`/mood` — Ver mi humor actual\n"
            "`/mood <texto>` — Cámbiame el humor\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔍 *BÚSQUEDA E INVESTIGACIÓN*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "`/search <texto>` — Búsqueda rápida en internet\n"
            "`/deepsearch <consulta>` — Investigación profunda: leo webs reales y redacto un informe con fuentes\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎨 *CREACIÓN Y PRODUCTIVIDAD*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "`/img <descripción>` — Genero una imagen con IA a partir de tu texto\n"
            "`/remind <minutos> <tarea>` — Te aviso en X minutos con un recordatorio\n"
            "`/nota <texto>` — Guardo un apunte personal en mi libreta\n"
            "`/notas` — Muestro todos tus apuntes guardados\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛡️ *ADMINISTRACIÓN* _(solo admins)_\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "`/vps` — Estado del servidor (CPU, RAM, disco)\n"
            "`/models` — Modelos de IA disponibles en Ollama\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✨ *CAPACIDADES PASIVAS*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📸 Envíame una *foto* y te diré qué veo\n"
            "🎙️ Envíame un *audio* y lo transcribo\n"
            "📄 Envíame un *documento TXT* y lo leo\n"
            "🧠 Cada 15 mensajes extraigo datos sobre ti para conocerte mejor\n"
            "📝 Los audios largos (+1 min) los resumo automáticamente en viñetas\n"
        )
        await update.message.reply_text(ayuda, parse_mode="Markdown")

    async def mood_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /mood [humor]."""
        user_id = update.effective_user.id
        if not self._is_allowed(user_id):
            return

        args = context.args

        if not args:
            # GET mood
            humor = self.db.obtener_o_crear_humor(user_id)
            await update.message.reply_text(f"Ahora mismo me siento: *{humor}*.", parse_mode="Markdown")
        else:
            # SET mood
            nuevo_humor = " ".join(args)
            self.db.actualizar_humor(user_id, nuevo_humor)
            await update.message.reply_text(
                f"Vale, vale... ahora seré: *{nuevo_humor}*.", parse_mode="Markdown"
            )

    async def vps_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /vps (solo admin)."""
        if not self._is_admin(update):
            await update.message.reply_text("¡Quieto ahí! Ese comando es solo para el amo de la casa.")
            return
        
        # Enviar estado "escribiendo"
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        stats = SystemMonitoringService.get_system_stats()
        await update.message.reply_text(stats, parse_mode="Markdown")

    async def models_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /models (solo admin)."""
        if not self._is_admin(update):
            await update.message.reply_text("¡Quieto ahí! Modificar mi cerebro es solo para mi creador.")
            return
            
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            modelos = await self.llm.list_models()
            if not modelos:
                texto = "No detecto ningún modelo instalado."
            else:
                texto = "🧠 *Modelos disponibles en el servidor* 🧠\n\n"
                for m in modelos:
                    texto += f"- `{m}`\n"
            await update.message.reply_text(texto, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"Error leyendo modelos: {e}")

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /search <consulta>."""
        user_id = update.effective_user.id
        if not self._is_allowed(user_id):
            return

        query = " ".join(context.args)
        if not query:
            await update.message.reply_text("Dime qué buscar, que no leo mentes. Uso: `/search <consulta>`", parse_mode="Markdown")
            return

        if not self.web_search:
            await update.message.reply_text("La búsqueda web está desactivada.")
            return

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await update.message.reply_text("🔍 Buscando en las profundidades de internet...")
        
        resultados = self.web_search.search(query)
        await update.message.reply_text(resultados, parse_mode="Markdown")

    async def deepsearch_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /deepsearch <consulta>."""
        user_id = update.effective_user.id
        if not self._is_allowed(user_id):
            return

        query = " ".join(context.args)
        if not query:
            await update.message.reply_text("Uso: `/deepsearch <consulta compleja>`. Busco, descargo los artículos, los leo y te los resumo.", parse_mode="Markdown")
            return

        if not self.web_search:
            await update.message.reply_text("La búsqueda web está desactivada.")
            return

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        msg = await update.message.reply_text("🔬 Agente Deep Research activado. Descargando artículos y leyendo... Esto tomará un buen rato.")
        
        try:
            resultados = await self.web_search.deep_search(query, self.llm)
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=msg.message_id,
                text=resultados,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error en deepsearch: {e}")
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text="Ups, se fundió el microscopio.")

    async def img_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /img <prompt>."""
        user_id = update.effective_user.id
        if not self._is_allowed(user_id):
            return

        prompt = " ".join(context.args)
        if not prompt:
            await update.message.reply_text("Dime qué quieres que dibuje. Uso: `/img un gato astronauta`", parse_mode="Markdown")
            return

        if not getattr(self, 'image_gen', None):
            await update.message.reply_text("La generación de imágenes está desactivada.")
            return

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
        msg_espere = await update.message.reply_text("🎨 Pintando... Dame unos segundos (y un poco de imaginación).")
        
        try:
            foto_bytes = await self.image_gen.generate_image(prompt)
            await update.message.reply_photo(photo=foto_bytes, caption=f"🖼️ *Prompt:* {prompt}", parse_mode="Markdown")
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_espere.message_id)
        except Exception as e:
            logger.error(f"Error generando imagen: {e}")
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=msg_espere.message_id,
                text="Se me cayeron las acuarelas. No pude generar la imagen."
            )

    async def remind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /remind <minutos> <mensaje>."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if not self._is_allowed(user_id):
            return

        if not getattr(self, 'scheduler', None):
            await update.message.reply_text("La memoria a largo plazo está desactivada bro. No puedo programar nada.")
            return

        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Uso: `/remind <minutos> <mensaje>`\nEjemplo: `/remind 60 sacar el pastel`", parse_mode="Markdown")
            return

        try:
            minutos = int(args[0])
            if minutos <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("El primer argumento debe ser el número de minutos (positivo).")
            return

        mensaje = " ".join(args[1:])
        run_date = self.scheduler.schedule_reminder(user_id, chat_id, mensaje, delay_minutes=minutos)
        
        hora_bonita = run_date.strftime("%H:%M:%S")
        await update.message.reply_text(f"✅ ¡Entendido jefe! Te avisaré a las {hora_bonita}.")

    async def nota_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /nota <texto>."""
        user_id = update.effective_user.id
        if not self._is_allowed(user_id):
            return

        contenido = " ".join(context.args)
        if not contenido:
            await update.message.reply_text("¿Una nota vacía? Muy poético. Uso: `/nota <texto>`", parse_mode="Markdown")
            return

        self.db.guardar_nota(user_id, contenido)
        await update.message.reply_text("✅ Nota guardada en mi desordenada memoria.")

    async def notas_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /notas."""
        user_id = update.effective_user.id
        if not self._is_allowed(user_id):
            return

        notas = self.db.obtener_notas(user_id)
        if not notas:
            await update.message.reply_text("Tienes menos notas que yo ganas de trabajar. ¡Está vacío!")
            return

        texto = "📝 *Tus notas:* 📝\n\n"
        for nota in notas:
            texto += f"🔹 **{nota['id']}**: {nota['contenido']}\n"
            
        await update.message.reply_text(texto, parse_mode="Markdown")

    async def clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /clear."""
        user_id = update.effective_user.id
        if not self._is_allowed(user_id):
            return

        self.db.borrar_historial(user_id)
        await update.message.reply_text(
            "He tirado toda nuestra conversación a la trituradora. ¡Empezamos de cero, jefe!"
        )
        logger.info(f"/clear de usuario {user_id}")

    async def chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler principal para mensajes (texto, fotos, audio).
        Convierte el Update de Telegram a core.Message y delega al ConversationService.
        """
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not self._is_allowed(user_id):
            return

        # Rate limit
        if not self.conversation.check_rate_limit(user_id):
            await update.message.reply_text(
                "¡Para el carro, campeón! Me estás fundiendo los circuitos. Espera un momento."
            )
            return

        # Convertir Update de Telegram → core.Message
        try:
            message = await telegram_update_to_message(update, context, self.whisper)
        except Exception as e:
            logger.error(f"Error procesando entrada de usuario {user_id}: {e}")
            await update.message.reply_text("Me he quedado sordo... no he podido escuchar ese audio.")
            return

        if message is None:
            return

        # Feedback de audio transcrito
        if message.audio_text:
            await update.message.reply_text(
                f"🎤 *Escuchado:* _{message.audio_text}_", parse_mode="Markdown"
            )

        # Lógica de grupos: solo responder si mencionan a Juanito
        if message.is_group and not message.bot_mentioned:
            # Excepción: foto con caption que mencione a Juanito ya se detecta en mapper
            if not message.images:
                return
            # Foto sin mención → ignorar
            return

        # Mostrar estado "escribiendo..." o "subiendo foto..."
        action = "upload_photo" if message.images else "typing"
        await context.bot.send_chat_action(chat_id=chat_id, action=action)

        try:
            # Delegar al ConversationService
            respuesta = await self.conversation.procesar_mensaje(message)

            if respuesta:
                await update.message.reply_text(respuesta)

        except Exception as e:
            error_msg = f"¡Ay! ¡Se me han caído los cables! Error: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(f"Error en chat de usuario {user_id}: {e}")
