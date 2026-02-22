# core/services/scheduler.py — Programador de Tareas (APScheduler)
# Creado y diseñado por David Carreres Gómez.

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("juanito.scheduler")


class SchedulerService:
    """Gestiona tareas programadas y recordatorios."""

    def __init__(self, db_manager, bot_instance):
        self.db = db_manager
        self.bot = bot_instance  # Instancia del bot de telegram para poder enviar mensajes
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Inicia el planificador y carga los recordatorios pendientes."""
        self.scheduler.start()
        logger.info("Scheduler iniciado.")
        self._cargar_recordatorios_pendientes()

    def _cargar_recordatorios_pendientes(self):
        """Lee de la BD los recordatorios que aún no han vencido y los programa."""
        pendientes = self.db.obtener_recordatorios_pendientes()
        for r in pendientes:
            try:
                # Convertir string ISO de SQLite a datetime
                run_date = datetime.fromisoformat(r["fecha_ejecucion"])
                if run_date > datetime.now():
                    self._programar_job(r["id"], r["id_usuario"], r["chat_id"], r["mensaje"], run_date)
            except Exception as e:
                logger.error(f"Error cargando recordatorio {r['id']}: {e}")
                
        logger.info(f"Se han cargado {len(pendientes)} recordatorios pendientes.")

    def _programar_job(self, id_recordatorio, id_usuario, chat_id, mensaje, run_date):
        """Programa internamente el job en APScheduler."""
        self.scheduler.add_job(
            self._ejecutar_recordatorio,
            'date',
            run_date=run_date,
            args=[id_recordatorio, id_usuario, chat_id, mensaje],
            id=f"remind_{id_recordatorio}",
            replace_existing=True
        )

    def schedule_reminder(self, id_usuario, chat_id, mensaje, delay_minutes: int):
        """
        Crea un nuevo recordatorio en la BD y lo programa.
        Devuelve la fecha calculada de ejecución.
        """
        run_date = datetime.now() + timedelta(minutes=delay_minutes)
        # Formato ISO para SQLite guardando hasta milisegundos
        fecha_iso = run_date.isoformat()
        
        # Guardar en DB
        id_recordatorio = self.db.guardar_recordatorio(id_usuario, chat_id, mensaje, fecha_iso)
        
        # Programar en memoria
        self._programar_job(id_recordatorio, id_usuario, chat_id, mensaje, run_date)
        
        logger.info(f"Recordatorio {id_recordatorio} programado para {run_date} (User: {id_usuario})")
        return run_date

    async def _ejecutar_recordatorio(self, id_recordatorio, id_usuario, chat_id, mensaje):
        """Función callback que se ejecuta cuando salta la alarma."""
        try:
            texto = f"⏰ *¡Bip Bip! Recordatorio para ti:*\n\n{mensaje}"
            await self.bot.send_message(chat_id=chat_id, text=texto, parse_mode="Markdown")
            logger.info(f"Recordatorio {id_recordatorio} enviado con éxito al chat {chat_id}.")
            
            # Borrar de la BD para que no se repita al reiniciar
            self.db.borrar_recordatorio(id_recordatorio)
        except Exception as e:
            logger.error(f"Error enviando recordatorio {id_recordatorio}: {e}")
