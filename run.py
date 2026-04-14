"""
run.py - Orquestador Principal - Pyme Analytics Engine v2.0
============================================================
PUNTO DE VERDAD: Este es el run.py correcto y definitivo.

Errores que estaba cometiendo y que NUNCA debes repetir:
  1. Cambiar nombres de clases sin actualizar todos los import
  2. Mezclar versiones de archivos (v1 en una carpeta, v2 en otra)
  3. Usar "import *" - siempre import explícito
  4. Copiar código sin leer los nombres de funciones/clases primero
  5. Tener dos archivos de logging con nombres distintos

Flujo correcto:
  python run.py                   → Pipeline completo
  python run.py --solo-etl        → Solo carga datos
  python run.py --solo-analisis   → Solo KPIs + OLS
  python run.py --test-conexion   → Verifica MySQL
============================================================
"""

import sys
import time
import argparse
from pathlib import Path

# ── Seguridad de rutas ────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ── Logger (configurar UNA SOLA VEZ aquí) ────────────────────────────────────
from config.logger_config import (
    configurar_logger,
    registrar_inicio_proceso,
    registrar_fin_proceso,
)
logger = configurar_logger()   # sin argumento = usa "pyme_analytics"

# ── Verificación de conexión ──────────────────────────────────────────────────
from config.db_config import probar_conexion

# ── ETL ───────────────────────────────────────────────────────────────────────
from data_processing.ingestor_universal import IngestorUniversal
from database_loading.load_to_mysql import cargar_ventas_a_mysql, cargar_gastos_a_mysql

# ── Análisis financiero ───────────────────────────────────────────────────────
from analytics.ebitda import (
    obtener_kpi_dashboard,
    calcular_ebitda,
    rentabilidad_por_cliente,
    rentabilidad_por_producto,
    estacionalidad_mensual,
    estructura_gastos,
)

# ── Modelo OLS ────────────────────────────────────────────────────────────────
# CORRECCIÓN CRÍTICA: la clase se llama AnalistaPyme, NO ModeloRegresionPyme
from analytics.regression_model import AnalistaPyme

# ── Reporte PDF ───────────────────────────────────────────────────────────────
# CORRECCIÓN CRÍTICA: usar ReporteFinanciero().generar(), NO generar_reporte_pyme()
from reports.financial_report import ReporteFinanciero


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          PYME ANALYTICS ENGINE  v2.0                         ║
║          Sistema de Inteligencia de Negocios para Pymes      ║
╚══════════════════════════════════════════════════════════════╝
"""


# ════════════════════════════════════════════════════════════════════════════
# ETAPAS
# ════════════════════════════════════════════════════════════════════════════

def etapa_verificacion() -> bool:
    logger.info("🔌 Verificando conexión MySQL/XAMPP...")
    ok = probar_conexion()
    if not ok:
        logger.critical(
            "❌ Sin conexión MySQL.\n"
            "   Verifique:\n"
            "   1. XAMPP iniciado y MySQL en estado RUNNING\n"
            "   2. Credenciales correctas en .env\n"
            "   3. BD 'pyme_analytics' existe en Workbench"
        )
    return ok


def etapa_etl() -> bool:
    logger.info("─" * 55)
    logger.info("📦 ETAPA 1: ETL - Carga de Datos")
    logger.info("─" * 55)

    registrar_inicio_proceso("ETL")
    filas = 0
    ok = True

    ruta_v = ROOT / "assets" / "ventas.csv"
    if ruta_v.exists():
        try:
            df_v = IngestorUniversal(tipo_tabla="ventas").ingestar(str(ruta_v))
            if df_v is not None:
                n = cargar_ventas_a_mysql(df_v)
                filas += n
                logger.info(f"   ✅ Ventas: {n} registros cargados")
            else:
                logger.error("   ❌ Fallo en ingesta de ventas")
                ok = False
        except Exception as e:
            logger.error(f"   ❌ ETL ventas: {e}")
            ok = False
    else:
        logger.warning(f"   ⚠️  {ruta_v} no encontrado")

    ruta_g = ROOT / "assets" / "gastos.csv"
    if ruta_g.exists():
        try:
            df_g = IngestorUniversal(tipo_tabla="gastos").ingestar(str(ruta_g))
            if df_g is not None:
                n = cargar_gastos_a_mysql(df_g)
                filas += n
                logger.info(f"   ✅ Gastos: {n} registros cargados")
            else:
                logger.error("   ❌ Fallo en ingesta de gastos")
                ok = False
        except Exception as e:
            logger.error(f"   ❌ ETL gastos: {e}")
            ok = False
    else:
        logger.warning(f"   ⚠️  {ruta_g} no encontrado")

    registrar_fin_proceso("ETL", filas=filas, errores=0 if ok else 1)
    return ok


def etapa_analisis() -> None:
    logger.info("─" * 55)
    logger.info("📊 ETAPA 2: ANÁLISIS FINANCIERO")
    logger.info("─" * 55)

    registrar_inicio_proceso("ANALISIS")
    try:
        obtener_kpi_dashboard()
        rentabilidad_por_cliente()
        rentabilidad_por_producto()
        estacionalidad_mensual()
        estructura_gastos()
        registrar_fin_proceso("ANALISIS")
    except Exception as e:
        logger.error(f"❌ Error en análisis: {e}")
        registrar_fin_proceso("ANALISIS", errores=1)


def etapa_regresion() -> None:
    logger.info("─" * 55)
    logger.info("🔬 ETAPA 3: MODELO ECONOMÉTRICO OLS")
    logger.info("─" * 55)

    registrar_inicio_proceso("OLS")
    try:
        # CORRECTO: AnalistaPyme con método ejecutar_todo()
        AnalistaPyme().ejecutar_todo()
        registrar_fin_proceso("OLS")
    except Exception as e:
        logger.error(f"❌ Error en OLS: {e}")
        registrar_fin_proceso("OLS", errores=1)


def etapa_reporte_pdf() -> None:
    logger.info("─" * 55)
    logger.info("📄 ETAPA 4: REPORTE PDF FINANCIERO")
    logger.info("─" * 55)

    registrar_inicio_proceso("PDF")
    try:
        # CORRECTO: ReporteFinanciero().generar()
        ruta = ReporteFinanciero().generar()
        logger.info(f"   ✅ PDF en: {ruta}")
        registrar_fin_proceso("PDF")
    except Exception as e:
        logger.error(f"❌ Error generando PDF: {e}")
        registrar_fin_proceso("PDF", errores=1)


# ════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ════════════════════════════════════════════════════════════════════════════
def main():
    print(BANNER)

    parser = argparse.ArgumentParser(description="Pyme Analytics Engine v2.0")
    parser.add_argument("--solo-etl",       action="store_true", help="Solo ETL")
    parser.add_argument("--solo-analisis",  action="store_true", help="Solo análisis")
    parser.add_argument("--test-conexion",  action="store_true", help="Test MySQL")
    args = parser.parse_args()

    inicio = time.time()

    if not etapa_verificacion():
        sys.exit(1)

    if args.test_conexion:
        logger.info("✅ Conexión OK")
        sys.exit(0)

    elif args.solo_etl:
        etapa_etl()

    elif args.solo_analisis:
        etapa_analisis()
        etapa_regresion()
        etapa_reporte_pdf()

    else:
        # Pipeline completo
        etapa_etl()
        etapa_analisis()
        etapa_regresion()
        etapa_reporte_pdf()

    logger.info("=" * 55)
    logger.info(f"🏁 Pipeline finalizado en {time.time() - inicio:.2f}s")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
