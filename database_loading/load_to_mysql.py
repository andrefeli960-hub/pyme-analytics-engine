"""
database_loading/load_to_mysql.py
===================================
Carga de datos a MySQL - Pyme Analytics Engine v2.0

Estrategia anti-duplicados:
  - clientes/productos: SELECT → INSERT solo si nuevo
  - ventas: REPLACE INTO con ID determinístico (fecha+cliente+producto)
  - gastos: TRUNCATE + INSERT (período completo)
"""

import uuid
import logging
from config.db_config import obtener_conexion

logger = logging.getLogger("pyme_analytics")


def _generar_id(prefijo: str) -> str:
    return prefijo + str(uuid.uuid4())[:8].upper()


def cargar_ventas_a_mysql(df) -> int:
    """
    Carga ventas con deduplicación completa.
    Returns: número de filas procesadas.
    """
    conn = obtener_conexion()
    if not conn:
        logger.error("❌ Sin conexión. Abortando carga de ventas.")
        return 0

    cursor = conn.cursor(buffered=True)
    ok, err = 0, 0
    logger.info(f"👥 Procesando {len(df)} ventas...")

    for _, row in df.iterrows():
        try:
            cliente  = str(row["cliente"]).strip()
            producto = str(row["producto"]).strip()

            # Cliente
            cursor.execute(
                "SELECT id_cliente FROM clientes WHERE nombre_cliente = %s", (cliente,)
            )
            res = cursor.fetchone()
            id_cliente = res[0] if res else _generar_id("CLI")
            if not res:
                cursor.execute(
                    "INSERT INTO clientes (id_cliente, nombre_cliente) VALUES (%s,%s)",
                    (id_cliente, cliente)
                )

            # Producto
            cursor.execute(
                "SELECT id_producto FROM productos WHERE nombre_producto = %s", (producto,)
            )
            res = cursor.fetchone()
            id_producto = res[0] if res else _generar_id("PROD")
            if not res:
                cursor.execute(
                    "INSERT INTO productos (id_producto, nombre_producto) VALUES (%s,%s)",
                    (id_producto, producto)
                )

            # Venta - ID determinístico garantiza idempotencia
            id_factura = (
                f"FAC-{row['fecha']}-{id_cliente[:5]}-{id_producto[:5]}"
            ).replace("/", "-")

            cursor.execute("""
                REPLACE INTO ventas
                    (id_factura, fecha, id_cliente, id_producto,
                     cantidad, precio_unitario, costo_unitario_variable)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                id_factura,
                str(row["fecha"]),
                id_cliente,
                id_producto,
                int(float(row["cantidad"])),
                float(row["precio_unitario"]),
                float(row["costo_unitario"]),   # CSV: costo_unitario → BD: costo_unitario_variable
            ))
            ok += 1

        except Exception as e:
            logger.warning(f"⚠️  Fila omitida: {e}")
            err += 1

    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"✅ Ventas cargadas | ok={ok} | errores={err}")
    return ok


def cargar_gastos_a_mysql(df) -> int:
    """
    Carga gastos con TRUNCATE + INSERT (datos de período completo).
    Returns: número de filas insertadas.
    """
    conn = obtener_conexion()
    if not conn:
        logger.error("❌ Sin conexión. Abortando carga de gastos.")
        return 0

    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE gastos")
    logger.info("🧹 Tabla gastos truncada")

    ok, err = 0, 0
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO gastos
                    (fecha, descripcion, categoria_gasto, tipo_gasto, monto)
                VALUES (%s,%s,%s,%s,%s)
            """, (
                str(row["fecha"]),
                str(row["descripcion"]),
                str(row["categoria_gasto"]),
                str(row["tipo_gasto"]),
                float(row["monto"]),
            ))
            ok += 1
        except Exception as e:
            logger.warning(f"⚠️  Gasto omitido: {e}")
            err += 1

    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"✅ Gastos cargados | ok={ok} | errores={err}")
    return ok
