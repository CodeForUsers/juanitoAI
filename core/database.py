# core/database.py — Gestión de Base de Datos con context managers
# Creado y diseñado por David Carreres Gómez.

import sqlite3
import random
import logging

from core.config import DB_PATH

logger = logging.getLogger("juanito.database")

# Lista de humores disponibles
HUMORES = [
    "sarcástico", "eufórico", "vago", "dramático",
    "picante", "mayordomo servicial pero despistado"
]


class DatabaseManager:
    """Gestiona todas las operaciones con la base de datos SQLite."""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.init_db()

    def _connect(self):
        """Crea y devuelve una conexión con context manager."""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Crea las tablas si no existen."""
        with self._connect() as conn:
            cursor = conn.cursor()

            # Tabla para el historial de mensajes
            cursor.execute('''CREATE TABLE IF NOT EXISTS historial
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          id_usuario INTEGER,
                          rol TEXT,
                          contenido TEXT,
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

            # Tabla para el estado de ánimo persistente por usuario
            cursor.execute('''CREATE TABLE IF NOT EXISTS estados
                         (id_usuario INTEGER PRIMARY KEY, humor TEXT)''')

            # Tabla para las notas del usuario
            cursor.execute('''CREATE TABLE IF NOT EXISTS notas
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          id_usuario INTEGER,
                          contenido TEXT,
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

            # Tabla para recordatorios programados
            cursor.execute('''CREATE TABLE IF NOT EXISTS recordatorios
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          id_usuario INTEGER,
                          chat_id INTEGER,
                          mensaje TEXT,
                          fecha_ejecucion DATETIME)''')

            # Tabla para perfiles semánticos de usuario
            cursor.execute('''CREATE TABLE IF NOT EXISTS perfil
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          id_usuario INTEGER UNIQUE,
                          hechos TEXT)''')

            conn.commit()
        logger.info("Base de datos inicializada correctamente.")

    # --- Historial de Conversación ---

    def guardar_mensaje(self, id_usuario, rol, contenido):
        """Guarda un mensaje en el historial."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO historial (id_usuario, rol, contenido) VALUES (?, ?, ?)",
                (id_usuario, rol, contenido)
            )
            conn.commit()

    def obtener_historial(self, id_usuario, limite=10):
        """Obtiene los últimos mensajes del usuario, asegurando alternancia user/assistant."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT rol, contenido FROM historial WHERE id_usuario = ? ORDER BY id DESC LIMIT ?",
                (id_usuario, limite)
            )
            filas = cursor.fetchall()

        # Orden cronológico
        historial_raw = [{"role": rol, "content": contenido} for rol, contenido in reversed(filas)]

        # Asegurar alternancia user/assistant
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

    def contar_mensajes(self, id_usuario, rol="user"):
        """Cuenta cuántos mensajes ha enviado el usuario en total (útil para triggers)."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(id) FROM historial WHERE id_usuario = ? AND rol = ?", (id_usuario, rol))
            fila = cursor.fetchone()
            return fila[0] if fila else 0

    def borrar_historial(self, id_usuario):
        """Borra todo el historial de un usuario."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM historial WHERE id_usuario = ?", (id_usuario,))
            conn.commit()
        logger.info(f"Historial borrado para usuario {id_usuario}.")

    # --- Memoria Semántica ---

    def obtener_perfil(self, id_usuario):
        """Devuelve los hechos conocidos sobre el usuario, o string vacío si no hay."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT hechos FROM perfil WHERE id_usuario = ?", (id_usuario,))
            fila = cursor.fetchone()
            return fila[0] if fila else ""

    def actualizar_perfil(self, id_usuario, nuevos_hechos):
        """Actualiza el perfil de hechos del usuario."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO perfil (id_usuario, hechos) VALUES (?, ?) "
                "ON CONFLICT(id_usuario) DO UPDATE SET hechos=excluded.hechos",
                (id_usuario, nuevos_hechos)
            )
            conn.commit()

    # --- Estado de Ánimo ---

    def obtener_o_crear_humor(self, id_usuario):
        """Obtiene el humor actual del usuario, ocrea uno aleatorio si no existe."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT humor FROM estados WHERE id_usuario = ?", (id_usuario,))
            fila = cursor.fetchone()

            if fila:
                return fila[0]

            # No existe → crear uno nuevo
            humor = random.choice(HUMORES)
            cursor.execute(
                "INSERT INTO estados (id_usuario, humor) VALUES (?, ?)",
                (id_usuario, humor)
            )
            conn.commit()
            logger.info(f"Humor creado para usuario {id_usuario}: {humor}")
            return humor

    def actualizar_humor(self, id_usuario, nuevo_humor):
        """Actualiza el humor de un usuario."""
        # Asegurar que el usuario existe primero
        self.obtener_o_crear_humor(id_usuario)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE estados SET humor = ? WHERE id_usuario = ?",
                (nuevo_humor, id_usuario)
            )
            conn.commit()
        logger.info(f"Humor actualizado para usuario {id_usuario}: {nuevo_humor}")

    def cambio_aleatorio_humor(self, id_usuario, probabilidad=0.2):
        """Cambia el humor aleatoriamente con una probabilidad dada."""
        if random.random() < probabilidad:
            nuevo_humor = random.choice(HUMORES)
            self.actualizar_humor(id_usuario, nuevo_humor)
            return nuevo_humor
        return None

    # --- Sistema de Notas ---

    def guardar_nota(self, id_usuario, contenido):
        """Guarda una nota para el usuario."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notas (id_usuario, contenido) VALUES (?, ?)",
                (id_usuario, contenido)
            )
            conn.commit()
            # Devolver el ID insertado
            return cursor.lastrowid

    def obtener_notas(self, id_usuario):
        """Devuelve todas las notas del usuario como lista de diccionarios."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, contenido, timestamp FROM notas WHERE id_usuario = ? ORDER BY id ASC",
                (id_usuario,)
            )
            filas = cursor.fetchall()
            return [{"id": fila[0], "contenido": fila[1], "fecha": fila[2]} for fila in filas]

    def borrar_nota(self, id_usuario, id_nota):
        """Borra una nota específica de un usuario. Devuelve True si borró algo, False si no."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM notas WHERE id_usuario = ? AND id = ?",
                (id_usuario, id_nota)
            )
            conn.commit()
            return cursor.rowcount > 0

    # --- Sistema de Recordatorios ---

    def guardar_recordatorio(self, id_usuario, chat_id, mensaje, fecha_ejecucion):
        """Guarda un recordatorio programado."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO recordatorios (id_usuario, chat_id, mensaje, fecha_ejecucion) VALUES (?, ?, ?, ?)",
                (id_usuario, chat_id, mensaje, fecha_ejecucion)
            )
            conn.commit()
            return cursor.lastrowid

    def borrar_recordatorio(self, id_recordatorio):
        """Borra un recordatorio ejecutado."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM recordatorios WHERE id = ?", (id_recordatorio,))
            conn.commit()
            return cursor.rowcount > 0

    def obtener_recordatorios_pendientes(self):
        """Devuelve todos los recordatorios que están pendientes."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, id_usuario, chat_id, mensaje, fecha_ejecucion FROM recordatorios WHERE fecha_ejecucion > CURRENT_TIMESTAMP"
            )
            filas = cursor.fetchall()
            return [{"id": fila[0], "id_usuario": fila[1], "chat_id": fila[2], "mensaje": fila[3], "fecha_ejecucion": fila[4]} for fila in filas]
