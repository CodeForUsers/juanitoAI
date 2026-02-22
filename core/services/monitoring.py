# core/services/monitoring.py — Monitorización del servidor
# Creado y diseñado por David Carreres Gómez.

import logging
import psutil

logger = logging.getLogger("juanito.monitoring")


class SystemMonitoringService:
    """Servicio para leer el uso de recursos del sistema."""

    @staticmethod
    def get_system_stats():
        """Devuelve un string formateado con el uso de CPU, RAM y Disco."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.5)
            
            # RAM
            mem = psutil.virtual_memory()
            mem_total_gb = mem.total / (1024 ** 3)
            mem_used_gb = mem.used / (1024 ** 3)
            mem_percent = mem.percent
            
            # Disco
            disk = psutil.disk_usage('/')
            disk_total_gb = disk.total / (1024 ** 3)
            disk_used_gb = disk.used / (1024 ** 3)
            disk_percent = disk.percent
            
            stats = (
                "🖥️ *Estadísticas del Servidor (VPS)* 🖥️\n\n"
                f"🧠 *CPU:* {cpu_percent}%\n"
                f"💾 *RAM:* {mem_used_gb:.1f}GB / {mem_total_gb:.1f}GB ({mem_percent}%)\n"
                f"💽 *Disco:* {disk_used_gb:.1f}GB / {disk_total_gb:.1f}GB ({disk_percent}%)\n"
            )
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del VPS: {e}")
            return "No he podido leer las estadísticas del servidor. Me pesan los bits."
