# Dockerfile para Juanito AI Bot
FROM python:3.9-slim

# Evitar que Python escriba archivos .pyc y forzar logs sin buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema, incluyendo FFmpeg para Whisper
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Crear y establecer el directorio de trabajo
WORKDIR /app

# Copiar requirements primero para aprovechar la caché de capas de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# El bot se inicia con este comando
CMD ["python", "Telegram_AI_bot.py"]
