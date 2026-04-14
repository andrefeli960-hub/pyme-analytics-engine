"""
analytics/ebitda.py
====================
Módulo Financiero: KPIs, EBITDA, Pareto, Estacionalidad - v2.0

COLUMNA CORRECTA en la BD: costo_unitario_variable
(confirmado en el schema de la BD)

Importación correcta del logger:
  from config.logger_config import obtener_logger
"""

import pandas as pd
from mysql.connector import Error

from config.db_config import obtener_conexion
from config.logger_config import obtener_logger   # ← CORRECTO

logger = obtener_logger(__name__)


def obtener_kpi_dashboard() -> dict | None:
    """Dashboard consolidado - una consulta, todos los KPIs."""
    logger.info("📊 Calculando KPI Dashboard...")
    sql = """
        WITH base AS (
            SELECT
                COALESCE(SUM(v.cantidad * v.precio_unitario), 0)         AS ingresos,
                COALESCE(SUM(v.cantidad * v.costo_unitario_variable), 0) AS costos,
                COUNT(DISTINCT v.id_cliente)                             AS num_clientes,
                COUNT(DISTINCT v.id_producto)                            AS num_productos,
                COUNT(v.id_factura)                                      AS num_transacciones,
                SUM(v.cantidad)                                          AS unidades_totales
            FROM ventas v
        ),
        gasto_total AS (
            SELECT COALESCE(SUM(monto), 0) AS total FROM gastos
        )
        SELECT
            b.ingresos,
            b.costos                                                             AS costos_variables,
            b.ingresos - b.costos                                                AS utilidad_bruta,
            g.total                                                              AS gastos_operativos,
            (b.ingresos - b.costos) - g.total                                    AS ebitda,
            ROUND(((b.ingresos - b.costos - g.total) / b.ingresos) * 100, 2)   AS margen_ebitda_pct,
            ROUND(b.ingresos / b.num_clientes, 2)                               AS ingreso_por_cliente,
            ROUND(b.ingresos / b.num_transacciones, 2)                          AS ticket_promedio,
            b.num_clientes,
            b.num_productos,
            b.num_transacciones,
            b.unidades_totales
        FROM base b CROSS JOIN gasto_total g
    """
    try:
        conn = obtener_conexion()
        df = pd.read_sql(sql, conn)
        conn.close()
        if df.empty:
            logger.warning("Sin datos para KPIs")
            return None
        kpis = {k: float(v) for k, v in df.iloc[0].items()}
        logger.info(
            f"\n{'='*52}\n"
            f"  Ingresos Totales:    $ {kpis['ingresos']:>15,.2f}\n"
            f"  Costos Variables:    $ {kpis['costos_variables']:>15,.2f}\n"
            f"  Utilidad Bruta:      $ {kpis['utilidad_bruta']:>15,.2f}\n"
            f"  Gastos Operativos:   $ {kpis['gastos_operativos']:>15,.2f}\n"
            f"  EBITDA:              $ {kpis['ebitda']:>15,.2f}\n"
            f"  Margen EBITDA:         {kpis['margen_ebitda_pct']:>14.2f}%\n"
            f"  Ticket Promedio:     $ {kpis['ticket_promedio']:>15,.2f}\n"
            f"{'='*52}"
        )
        return kpis
    except Error as e:
        logger.error(f"❌ Error KPI Dashboard: {e}")
        return None


def calcular_ebitda() -> dict | None:
    """EBITDA con CTEs. Columna correcta: costo_unitario_variable."""
    logger.info("Calculando EBITDA...")
    sql = """
        WITH ic AS (
            SELECT
                COALESCE(SUM(v.cantidad * v.precio_unitario), 0)         AS ingresos_totales,
                COALESCE(SUM(v.cantidad * v.costo_unitario_variable), 0) AS costos_totales
            FROM ventas v
        ),
        go AS (
            SELECT COALESCE(SUM(g.monto), 0) AS total_gastos FROM gastos g
        )
        SELECT
            ic.ingresos_totales                                    AS ingresos,
            ic.costos_totales                                      AS costos_variables,
            ic.ingresos_totales - ic.costos_totales                AS utilidad_bruta,
            go.total_gastos                                        AS gastos,
            (ic.ingresos_totales - ic.costos_totales) - go.total_gastos AS ebitda,
            ROUND(
                (((ic.ingresos_totales - ic.costos_totales) - go.total_gastos)
                 / ic.ingresos_totales) * 100, 2
            ) AS margen_pct
        FROM ic CROSS JOIN go
    """
    try:
        conn = obtener_conexion()
        df = pd.read_sql(sql, conn)
        conn.close()
        resultado = {k: float(v) for k, v in df.iloc[0].items()}
        logger.info(f"EBITDA=${resultado['ebitda']:,.2f} | Margen {resultado['margen_pct']}%")
        return resultado
    except Error as e:
        logger.error(f"❌ Error EBITDA: {e}")
        return None


def rentabilidad_por_cliente() -> pd.DataFrame | None:
    """Margen por cliente con Pareto acumulado."""
    logger.info("Calculando rentabilidad por cliente...")
    sql = """
        SELECT
            c.nombre_cliente,
            ROUND(SUM(v.cantidad * v.precio_unitario), 2)              AS ingresos,
            ROUND(SUM(v.cantidad * v.costo_unitario_variable), 2)      AS costos,
            ROUND(SUM(v.cantidad * v.precio_unitario)
                  - SUM(v.cantidad * v.costo_unitario_variable), 2)    AS margen_bruto
        FROM ventas v
        JOIN clientes c ON v.id_cliente = c.id_cliente
        GROUP BY c.id_cliente, c.nombre_cliente
        ORDER BY margen_bruto DESC
    """
    try:
        conn = obtener_conexion()
        df = pd.read_sql(sql, conn)
        conn.close()
        if df.empty:
            return df
        total = df["margen_bruto"].sum()
        df["margen_pct"] = (df["margen_bruto"] / total * 100).round(2)
        df["pareto_acumulado"] = df["margen_pct"].cumsum().round(2)
        logger.info(f"Clientes: {len(df)}")
        return df
    except Error as e:
        logger.error(f"❌ Error rentabilidad cliente: {e}")
        return None


def rentabilidad_por_producto() -> pd.DataFrame | None:
    """Margen bruto por producto."""
    logger.info("Calculando rentabilidad por producto...")
    sql = """
        SELECT
            p.nombre_producto,
            COUNT(v.id_factura)                                            AS transacciones,
            SUM(v.cantidad)                                                AS unidades,
            ROUND(SUM(v.cantidad * v.precio_unitario), 2)                  AS ingresos,
            ROUND(SUM(v.cantidad * v.costo_unitario_variable), 2)          AS costos,
            ROUND(SUM(v.cantidad * v.precio_unitario)
                  - SUM(v.cantidad * v.costo_unitario_variable), 2)        AS margen_bruto,
            ROUND((SUM(v.cantidad * v.precio_unitario)
                   - SUM(v.cantidad * v.costo_unitario_variable))
                  / SUM(v.cantidad * v.precio_unitario) * 100, 2)          AS margen_pct
        FROM ventas v
        JOIN productos p ON v.id_producto = p.id_producto
        GROUP BY p.id_producto, p.nombre_producto
        ORDER BY margen_bruto DESC
    """
    try:
        conn = obtener_conexion()
        df = pd.read_sql(sql, conn)
        conn.close()
        return df
    except Error as e:
        logger.error(f"❌ Error rentabilidad producto: {e}")
        return None


def estacionalidad_mensual() -> pd.DataFrame | None:
    """Ingresos y márgenes por mes."""
    logger.info("Calculando estacionalidad mensual...")
    sql = """
        SELECT
            YEAR(v.fecha)       AS anio,
            MONTH(v.fecha)      AS mes_num,
            MONTHNAME(v.fecha)  AS mes_nombre,
            COUNT(v.id_factura) AS num_ventas,
            ROUND(SUM(v.cantidad * v.precio_unitario), 2)              AS ingresos,
            ROUND(SUM(v.cantidad * v.costo_unitario_variable), 2)      AS costos,
            ROUND(SUM(v.cantidad * v.precio_unitario)
                  - SUM(v.cantidad * v.costo_unitario_variable), 2)    AS margen
        FROM ventas v
        GROUP BY YEAR(v.fecha), MONTH(v.fecha), MONTHNAME(v.fecha)
        ORDER BY anio ASC, mes_num ASC
    """
    try:
        conn = obtener_conexion()
        df = pd.read_sql(sql, conn)
        conn.close()
        return df
    except Error as e:
        logger.error(f"❌ Error estacionalidad: {e}")
        return None


def estructura_gastos() -> pd.DataFrame | None:
    """Breakdown de gastos por categoría."""
    logger.info("Analizando gastos...")
    sql = """
        SELECT
            g.categoria_gasto,
            g.tipo_gasto,
            COUNT(*)               AS registros,
            ROUND(SUM(g.monto), 2) AS total_monto
        FROM gastos g
        GROUP BY g.categoria_gasto, g.tipo_gasto
        ORDER BY total_monto DESC
    """
    try:
        conn = obtener_conexion()
        df = pd.read_sql(sql, conn)
        conn.close()
        if not df.empty:
            total = df["total_monto"].sum()
            df["pct_total"] = (df["total_monto"] / total * 100).round(2)
        return df
    except Error as e:
        logger.error(f"❌ Error gastos: {e}")
        return None
