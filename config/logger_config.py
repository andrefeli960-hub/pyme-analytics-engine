"""
config/logger_config.py
========================
Sistema centralizado de logging - Pyme Analytics Engine v2.0

REGLA FUNDAMENTAL (lo que causó el caos):
  - Este es EL ÚNICO archivo de logging del proyecto.
  - Exporta DOS funciones públicas:
      configurar_logger()  → llamar UNA SOLA VEZ desde run.py o arrancar.py
      obtener_logger(name) → usar en TODOS los módulos individuales
  - NUNCA crear otro archivo logger.py, log.py o similar.

Salidas:
  logs/app.log      → Todo (rotativo 10MB × 5 backups)
  logs/errores.log  → Solo ERROR y CRITICAL
  logs/ingesta.log  → Trazabilidad ETL
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# ── Constantes ────────────────────────────────────────────────────────────────
LOGS_DIR  = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

NIVEL_LOG     = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
FORMATO       = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
FORMATO_CORTO = "%(asctime)s | %(levelname)s | %(message)s"


# ── configurar_logger ─────────────────────────────────────────────────────────
def configurar_logger(nombre: str = "pyme_analytics") -> logging.Logger:
    """
    Configura el logger raíz del sistema.
    Llamar UNA sola vez al inicio (run.py / arrancar.py).

    Args:
        nombre: Nombre del logger. Default 'pyme_analytics'.
    """
    logger = logging.getLogger(nombre)
    if logger.handlers:
        return logger   # Ya configurado, evitar duplicados

    logger.setLevel(NIVEL_LOG)

    fmt_full  = logging.Formatter(FORMATO)
    fmt_short = logging.Formatter(FORMATO_CORTO)

    # Consola
    ch = logging.StreamHandler()
    ch.setLevel(NIVEL_LOG)
    ch.setFormatter(fmt_short)
    logger.addHandler(ch)

    # app.log (rotativo)
    ah = RotatingFileHandler(LOGS_DIR / "app.log",
                             maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
    ah.setLevel(NIVEL_LOG)
    ah.setFormatter(fmt_full)
    logger.addHandler(ah)

    # errores.log
    eh = RotatingFileHandler(LOGS_DIR / "errores.log",
                             maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    eh.setLevel(logging.ERROR)
    eh.setFormatter(fmt_full)
    logger.addHandler(eh)

    # ingesta.log
    ih = RotatingFileHandler(LOGS_DIR / "ingesta.log",
                             maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    ih.setLevel(logging.INFO)
    ih.setFormatter(fmt_full)
    logger.addHandler(ih)

    logger.info("=" * 58)
    logger.info("  Pyme Analytics Engine v2.0 - Logger iniciado")
    logger.info(f"  {datetime.now().isoformat()}")
    logger.info(f"  Nivel: {logging.getLevelName(NIVEL_LOG)}")
    logger.info("=" * 58)
    return logger


# ── obtener_logger ────────────────────────────────────────────────────────────
def obtener_logger(nombre_modulo: str) -> logging.Logger:
    """
    Retorna un logger para módulos individuales.
    Los mensajes se propagan al logger raíz 'pyme_analytics'.

    Args:
        nombre_modulo: Usar siempre __name__ del módulo.

    Ejemplo:
        from config.logger_config import obtener_logger
        logger = obtener_logger(__name__)
    """
    logger = logging.getLogger(nombre_modulo)
    if logger.handlers:
        return logger

    logger.setLevel(NIVEL_LOG)

    # Si el logger raíz no está listo, agregar handler mínimo de consola
    if not logging.getLogger("pyme_analytics").handlers:
        ch = logging.StreamHandler()
        ch.setLevel(NIVEL_LOG)
        ch.setFormatter(logging.Formatter(FORMATO_CORTO))
        logger.addHandler(ch)

    return logger


# ── Helpers de trazabilidad ───────────────────────────────────────────────────
def registrar_inicio_proceso(nombre: str) -> None:
    logging.getLogger("pyme_analytics").info(f"▶ INICIO | {nombre}")


def registrar_fin_proceso(nombre: str, filas: int = 0, errores: int = 0) -> None:
    estado = "OK" if errores == 0 else f"CON {errores} ERRORES"
    logging.getLogger("pyme_analytics").info(
        f"■ FIN   | {nombre} | filas={filas} | {estado}"
    )
