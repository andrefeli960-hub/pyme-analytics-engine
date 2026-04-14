"""
config/db_config.py
====================
Gestión de conexiones MySQL - Pyme Analytics Engine v2.0

Patrón: Pool de conexiones (reutilizable, eficiente).
Seguridad: Credenciales SOLO desde .env, nunca hardcodeadas.
Fallback: Si el pool falla, usa conexión directa (no interrumpe el flujo).
"""

import os
import logging
import mysql.connector
from mysql.connector import pooling, Error
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("pyme_analytics")

# ── Config desde .env ─────────────────────────────────────────────────────────
_DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "pyme_analytics"),
}

_pool = None  # Singleton


def _inicializar_pool() -> None:
    global _pool
    if _pool is not None:
        return
    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name="pyme_pool",
            pool_size=5,
            pool_reset_session=True,
            **_DB_CONFIG,
        )
        logger.info("✅ Pool MySQL inicializado (size=5)")
    except Error as e:
        logger.warning(f"⚠️  Pool no disponible, se usará conexión directa: {e}")
        _pool = None


def obtener_conexion() -> mysql.connector.MySQLConnection | None:
    """
    Retorna una conexión del pool, o conexión directa como fallback.
    Retorna None si no hay conectividad.
    """
    _inicializar_pool()

    if _pool:
        try:
            return _pool.get_connection()
        except Error as e:
            logger.warning(f"⚠️  Pool agotado, conexión directa: {e}")

    try:
        return mysql.connector.connect(**_DB_CONFIG)
    except Error as e:
        logger.error(f"❌ Sin conexión MySQL: {e}")
        return None


def probar_conexion() -> bool:
    """Verifica conectividad. Retorna True si OK."""
    try:
        conn = obtener_conexion()
        if conn is None:
            return False
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        logger.info(f"✅ Conexión a '{_DB_CONFIG['database']}' verificada")
        return True
    except Error as e:
        logger.error(f"❌ Prueba de conexión fallida: {e}")
        return False


def get_sqlalchemy_engine():
    """Engine SQLAlchemy para pandas.read_sql() (opcional)."""
    try:
        from sqlalchemy import create_engine
        h = _DB_CONFIG["host"]
        p = _DB_CONFIG["port"]
        u = _DB_CONFIG["user"]
        pw = _DB_CONFIG["password"]
        db = _DB_CONFIG["database"]
        return create_engine(f"mysql+pymysql://{u}:{pw}@{h}:{p}/{db}", pool_size=5)
    except ImportError:
        logger.warning("SQLAlchemy no instalado. pip install sqlalchemy pymysql")
        return None
    except Exception as e:
        logger.error(f"❌ Error SQLAlchemy engine: {e}")
        return None
