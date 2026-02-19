# Juanito - Tu Bot de Telegram con IA

Juanito es un bot de Telegram avanzado que utiliza modelos de IA locales (Ollama + Whisper) para interactuar contigo de múltiples formas.

## Características 

*   **Chat Inteligente**: Conversa con naturalidad usando modelos como `qwen` o `llama`.
*   **Visión Artificial**: Envíale una foto y te dirá lo que ve (usando `llava`).
*   **Audio a Texto**: Envíale una nota de voz y te responderá por escrito (usando `whisper`).
*   **Personalidad Dinámica**: Juanito tiene estados de ánimo cambiantes (sarcástico, eufórico, vago...).
*   **Memoria**: Recuerda el contexto de la conversación (hasta 10 mensajes).

## Requisitos Previos

1.  **Python 3.8+**
2.  **Ollama**: Debes tener [Ollama](https://ollama.com/) instalado y corriendo.
    *   Modelos sugeridos: `ollama pull qwen2.5:7b` (chat) y `ollama pull llava` (visión).
3.  **FFmpeg**: Necesario para procesar audio.
    *   Linux (Debian/Ubuntu): `sudo apt install ffmpeg`
    *   Windows: Descargar e instalar FFmpeg y añadirlo al PATH.
4.  **Telegram**: Debes tener una cuenta de Telegram y un bot creado con @BotFather.

## Instalación

1.  Clona este repositorio o descarga los archivos.
2.  Instala las dependencias de Python:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configura tus variables de entorno:
    *   Crea un archivo `.env` basado en `.env.example`.
    *   Añade tu `TELEGRAM_TOKEN` (consíguelo con @BotFather).
    *   Ajusta los nombres de tus modelos de Ollama si es necesario.

## Uso

1.  Ejecuta el bot:
    ```bash
    python Telegram_AI_bot.py
    ```
2.  Abre Telegram y busca a tu bot.
3.  Comandos disponibles:
    *   `/start`: Inicia la conversación.
    *   `/mood`: Consulta o cambia el humor de Juanito.
    *   `/clear`: Borra la memoria de la conversación actual.
    *   `/help`: Muestra la ayuda.

## Estructura del Proyecto

*   `Telegram_AI_bot.py`: Código principal del bot.
*   `.env`: Configuración y secretos (¡No compartir!).
*   `requirements.txt`: Lista de librerías necesarias.
*   `juanito_bot.db`: Base de datos SQLite (se crea automáticamente).

## Prueba el bot en Telegram

*   @juanitoAI_el_bot


# Información adicional

*   Creado por David Carreres Gómez.
*   Fecha: 19/02/2026
*   Versión: 1.0
*   Licencia: GPL-3.0
