# Creado y diseñado por David Carreres Gómez.
# Fecha: 19/02/2026
# Versión: 1.0
# Licencia: GPL-3.0

import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import ollama
import sqlite3
import random
import whisper
import tempfile
from dotenv import load_dotenv


# Cargar variables de entorno
load_dotenv()

# Variables de configuración
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OLLAMA_MODEL_CHAT = os.getenv("OLLAMA_MODEL_CHAT")
OLLAMA_MODEL_VISION = os.getenv("OLLAMA_MODEL_VISION")
DB_PATH = os.getenv("DB_PATH", "juanito_bot.db")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

# Cargar modelo Whisper (Global para no recargar en cada mensaje)
print(f"Cargando modelo Whisper ({WHISPER_MODEL_SIZE})... esto puede tardar un poco.")
whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
print("Modelo Whisper cargado.")

# Lectura de archivo de contexto y mensaje inicial
with open("contexto.txt", "r", encoding="UTF-8") as f:
    contexto_base = f.read()

with open("mensaje_inicial.txt", "r", encoding="UTF-8") as f:
    mensaje_inicial = f.read()

# --- Gestión de Base de Datos ---

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Tabla para el historial de mensajes
    c.execute('''CREATE TABLE IF NOT EXISTS historial
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  id_usuario INTEGER, 
                  rol TEXT, 
                  contenido TEXT, 
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabla para el estado de ánimo persistente por usuario
    c.execute('''CREATE TABLE IF NOT EXISTS estados
                 (id_usuario INTEGER PRIMARY KEY, humor TEXT)''')
    conn.commit()
    conn.close()

def guardar_mensaje(id_usuario, rol, contenido):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO historial (id_usuario, rol, contenido) VALUES (?, ?, ?)", (id_usuario, rol, contenido))
    conn.commit()
    conn.close()

def obtener_historial(id_usuario, limite=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Obtener últimos mensajes ordenados cronológicamente
    c.execute("SELECT rol, contenido FROM historial WHERE id_usuario = ? ORDER BY id DESC LIMIT ?", (id_usuario, limite))
    filas = c.fetchall()
    conn.close()
    
    # Asegurar alternancia user/assistant
    historial_raw = [{"role": r, "content": c} for r, c in reversed(filas)]
    historial_limpio = []
    ultimo_rol = None
    
    for msg in historial_raw:
        rol_actual = msg["role"]
        if rol_actual == ultimo_rol:
            continue
        historial_limpio.append(msg)
        ultimo_rol = rol_actual
        
    # El historial debe terminar en 'assistant' para que el siguiente sea 'user'
    if historial_limpio and historial_limpio[-1]["role"] == "user":
        historial_limpio.pop()
        
    return historial_limpio

def borrar_historial_db(id_usuario):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM historial WHERE id_usuario = ?", (id_usuario,))
    conn.commit()
    conn.close()

def obtener_o_crear_humor(id_usuario):
    humores = ["sarcástico", "eufórico", "vago", "dramático", "picante", "mayordomo servicial pero despistado"]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT humor FROM estados WHERE id_usuario = ?", (id_usuario,))
    fila = c.fetchone()
    if fila:
        humor = fila[0]
    else:
        humor = random.choice(humores)
        c.execute("INSERT INTO estados (id_usuario, humor) VALUES (?, ?)", (id_usuario, humor))
        conn.commit()
    conn.close()
    return humor

# --- Lógica del Bot ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id_usuario = update.effective_user.id
    init_db() # Asegurar que existe la DB
    await update.message.reply_text(mensaje_inicial)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ayuda = (
        "🤖 *Ayuda de Juanito* 🤖\n\n"
        "Soy Juanito, tu asistente con múltiples personalidades.\n"
        "Comandos disponibles:\n"
        "/start - Despiértame.\n"
        "/mood - Consulta o cambia mi humor actual.\n"
        "/clear - Borra nuestra memoria.\n"
        "/help - Muestra este mensaje.\n\n"
        "📸 *Ojos Digitales*: ¡Envíame una foto y te diré qué veo! (Usando mi modelo de visión).\n"
    )
    await update.message.reply_text(ayuda, parse_mode="Markdown")

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id_usuario = update.effective_user.id
    args = context.args
    
    if not args:
        # GET mood
        humor = obtener_o_crear_humor(id_usuario)
        await update.message.reply_text(f"Ahora mismo me siento: *{humor}*.", parse_mode="Markdown")
    else:
        # SET mood
        nuevo_humor = " ".join(args)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Verificar si usuario existe en tabla estados, si no crear
        obtener_o_crear_humor(id_usuario) 
        c.execute("UPDATE estados SET humor = ? WHERE id_usuario = ?", (nuevo_humor, id_usuario))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Vale, vale... ahora seré: *{nuevo_humor}*.", parse_mode="Markdown")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id_usuario = update.effective_user.id
    id_chat = update.effective_chat.id
    
    # --- Procesamiento de Entrada (Texto, Foto, Audio) ---
    mensaje_usuario = update.message.text
    es_audio = False
    
    # 1. Foto
    if not mensaje_usuario and update.message.caption:
        mensaje_usuario = update.message.caption
    elif not mensaje_usuario and update.message.photo:
        mensaje_usuario = "Describe esta imagen." 

    # 2. Audio/Voz
    if update.message.voice or update.message.audio:
        es_audio = True
        await context.bot.send_chat_action(chat_id=id_chat, action="typing") # o "record_voice" pero typing está bien para "pensando"
        
        try:
            # Seleccionar archivo
            archivo_voz = update.message.voice if update.message.voice else update.message.audio
            file_id = archivo_voz.file_id
            new_file = await context.bot.get_file(file_id)
            
            # Descargar a temporal
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
                await new_file.download_to_drive(custom_path=temp_audio.name)
                temp_path = temp_audio.name
            
            # Transcribir audio con Whisper
            loop = asyncio.get_running_loop()
            resultado = await loop.run_in_executor(None, lambda: whisper_model.transcribe(temp_path))
            texto_transcrito = resultado["text"]
            
            # Borrar temporal
            os.remove(temp_path)
            
            mensaje_usuario = texto_transcrito
            
            # Feedback al usuario de qué entendió (Opcional, pero útil)
            await update.message.reply_text(f"🎤 *Escuchado:* _{mensaje_usuario}_", parse_mode="Markdown")
            
        except Exception as e:
            print(f"Error transcribiendo audio: {e}")
            await update.message.reply_text("Me he quedado sordo... no he podido escuchar ese audio.")
            return

    if not mensaje_usuario:
        return # Si tras todo no hay texto, salir
    
    tipo_chat = update.effective_chat.type

    # Lógica de grupos: solo responder si mencionan a Juanito
    if tipo_chat in ["group", "supergroup"]:
        bot_username = (await context.bot.get_me()).username
        mencion = f"@{bot_username}"
        match_keywords = (mencion in mensaje_usuario or "Juanito" in mensaje_usuario or "juanito" in mensaje_usuario)
        
        if es_audio and not match_keywords:
            return
            
        if not es_audio and not match_keywords:
             if update.message.photo and update.message.caption and (mencion in update.message.caption or "Juanito" in update.message.caption):
                 pass
             elif not update.message.photo:
                 return
             elif update.message.photo and not update.message.caption:
                 return

    # Mostrar estado "escribiendo..." o "subiendo foto..." 
    # (Si era audio ya mostramos typing, pero repetimos por si acaso tardó el whisper)
    action = "upload_photo" if update.message.photo else "typing"
    await context.bot.send_chat_action(chat_id=id_chat, action=action)

    # Obtener humor y construir contexto dinámico
    humor_actual = obtener_o_crear_humor(id_usuario)
    contexto_personalizado = (
        f"{contexto_base}\n\n"
        f"TU ESTADO ACTUAL: Estás de humor {humor_actual}. "
        "IMPORTANTE: Tus respuestas deben ser CORTAS y directas, no te enrolles como una persiana."
    )

    # Procesar Imagen si existe
    imagenes_bytes = []
    modelo_a_usar = OLLAMA_MODEL_CHAT
    
    if update.message.photo:
        modelo_a_usar = OLLAMA_MODEL_VISION
        # Obtener la foto más grande
        foto = await update.message.photo[-1].get_file()
        foto_bytes = await foto.download_as_bytearray()
        imagenes_bytes.append(bytes(foto_bytes))
    
    # Recuperar historial de la DB y añadir mensaje actual
    mensajes = [{"role": "system", "content": contexto_personalizado}]
    
    # Solo añadimos historial si ES chat de texto puro (o audio transcrito).
    historial = obtener_historial(id_usuario)
    mensajes.extend(historial)
    
    msg_contenido = {"role": "user", "content": mensaje_usuario}
    if imagenes_bytes:
        msg_contenido["images"] = imagenes_bytes
    
    mensajes.append(msg_contenido)

    try:
        # Llamada asíncrona a Ollama
        client = ollama.AsyncClient()
        response = await client.chat(model=modelo_a_usar, messages=mensajes)
        mensaje_ia = response['message']['content']

        # Guardar en DB (Solo guardamos texto para no llenar DB de bytes)
        guardar_mensaje(id_usuario, "user", mensaje_usuario)
        guardar_mensaje(id_usuario, "assistant", mensaje_ia)

        await update.message.reply_text(mensaje_ia)

        # Probabilidad de cambio de humor tras la interacción
        if random.random() < 0.2:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            nuevo_humor = random.choice(["sarcástico", "eufórico", "vago", "dramático", "picante", "mayordomo servicial"])
            c.execute("UPDATE estados SET humor = ? WHERE id_usuario = ?", (nuevo_humor, id_usuario))
            conn.commit()
            conn.close()

    except Exception as e:
        error_msg = f"¡Ay! ¡Se me han caído los cables! Error: {str(e)}"
        await update.message.reply_text(error_msg)
        print(f"Error en chat: {e}")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id_usuario = update.effective_user.id
    borrar_historial_db(id_usuario)
    await update.message.reply_text("He tirado toda nuestra conversación a la trituradora. ¡Empezamos de cero, jefe!")

def main():
    # Inicializar DB al arrancar
    init_db()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("mood", mood_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Escuchar texto Y fotos Y voz Y audio
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VOICE | filters.AUDIO) & ~filters.COMMAND, chat))

    print("Juanito está online. Creado y diseñado por David Carreres Gómez.")
    app.run_polling()

if __name__ == "__main__":
    main()