# core/config.py — Configuración centralizada, variables de entorno y logging
# Creado y diseñado por David Carreres Gómez.

import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- Rutas base ---
BASE_DIR = Path(__file__).resolve().parent.parent
CONTEXTO_PATH = BASE_DIR / "contexto.txt"
MENSAJE_INICIAL_PATH = BASE_DIR / "mensaje_inicial.txt"
LOG_PATH = BASE_DIR / "juanito.log"

# --- Variables de entorno ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OLLAMA_MODEL_CHAT = os.getenv("OLLAMA_MODEL_CHAT", "qwen3.5:cloud")
OLLAMA_MODEL_VISION = os.getenv("OLLAMA_MODEL_VISION", "llava")
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "juanito_bot.db"))
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

# --- HuggingFace (Generación de imágenes) ---
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

# --- Seguridad y Admins ---
_allowed_raw = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = [int(uid.strip()) for uid in _allowed_raw.split(",") if uid.strip()] if _allowed_raw.strip() else []

_admin_raw = os.getenv("ADMIN_USER_IDS", "")
# Separar los admins por ID numérico y por @username
ADMIN_USER_IDS = []
ADMIN_USERNAMES = []
if _admin_raw.strip():
    for admin in _admin_raw.split(","):
        admin = admin.strip()
        if admin.startswith("@"):
            ADMIN_USERNAMES.append(admin[1:].lower())  # Guardamos sin el @ y en minúsculas
        elif admin.isdigit():
            ADMIN_USER_IDS.append(int(admin))

# --- Rate Limiting ---
RATE_LIMIT_MESSAGES = int(os.getenv("RATE_LIMIT_MESSAGES", "20"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # segundos

# --- Lectura segura de archivos de texto ---
def _leer_archivo_seguro(ruta, default=""):
    """Lee un archivo de texto con fallback si no existe."""
    try:
        with open(ruta, "r", encoding="UTF-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"Archivo no encontrado: {ruta}. Usando valor por defecto.")
        return default

# --- Logging ---
def setup_logging():
    """Configura logging con RotatingFileHandler + StreamHandler."""
    root_logger = logging.getLogger("juanito")
    root_logger.setLevel(logging.INFO)

    # Formato
    formatter = logging.Formatter(
        "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Handler de archivo rotativo (5MB, 3 backups)
    file_handler = RotatingFileHandler(
        LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return root_logger


# Inicializar logging al importar config
logger = setup_logging()

# Cargar textos base
CONTEXTO_BASE = _leer_archivo_seguro(
    CONTEXTO_PATH,
    default="Eres Juanito, un asistente de IA peculiar, teatral y con humor cambiante."
)
MENSAJE_INICIAL = _leer_archivo_seguro(
    MENSAJE_INICIAL_PATH,
    default="¡Ey, aquí Juanito al servicio! ¿Qué necesitas?"
)
