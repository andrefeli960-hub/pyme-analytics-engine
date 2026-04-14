"""
data_processing/clean_data.py
==============================
ETL: Limpieza, validación y EDA automático - Pyme Analytics Engine v2.0

Capacidades:
  - Normalización de nombres de columnas
  - Validación de campos obligatorios
  - Limpieza de nulos y casteo de tipos
  - EDA automático: estadísticos, outliers IQR, normalidad Shapiro-Wilk, correlación Pearson
  - Validación de reglas de negocio (precios/cantidades positivos, etc.)

Importación correcta del logger:
  from config.logger_config import obtener_logger
"""

import pandas as pd
import numpy as np
from scipy import stats

# ── IMPORTACIÓN CORRECTA DEL LOGGER ──────────────────────────────────────────
from config.logger_config import obtener_logger

logger = obtener_logger(__name__)

# ── Esquemas de columnas ──────────────────────────────────────────────────────
COLUMNAS_VENTAS = [
    "fecha", "cliente", "producto",
    "cantidad", "precio_unitario", "costo_unitario"
]
COLUMNAS_GASTOS = [
    "fecha", "descripcion",
    "categoria_gasto", "tipo_gasto", "monto"
]
TIPOS_ESPERADOS_VENTAS = {
    "cantidad":        "int64",
    "precio_unitario": "float64",
    "costo_unitario":  "float64",
}
TIPOS_ESPERADOS_GASTOS = {
    "monto": "float64",
}


# ── Pipeline principal ────────────────────────────────────────────────────────
def cargar_y_limpiar_csv(
    ruta_archivo: str,
    columnas_requeridas: list,
    tipos_esperados: dict = None,
    ejecutar_eda: bool = True,
) -> pd.DataFrame | None:
    """
    Pipeline completo de limpieza para un archivo CSV.

    Returns:
        pd.DataFrame limpio o None si hay error fatal.
    """
    logger.info(f"📂 Limpiando: {ruta_archivo}")

    # Lectura con detección de encoding
    try:
        df = pd.read_csv(ruta_archivo, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(ruta_archivo, encoding="latin-1")
            logger.warning("⚠️  latin-1 encoding detectado (recomendado UTF-8)")
        except Exception as e:
            logger.error(f"❌ Error de lectura: {e}")
            return None
    except FileNotFoundError:
        logger.error(f"❌ Archivo no encontrado: {ruta_archivo}")
        return None
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        return None

    logger.info(f"   Filas={len(df):,} | Columnas={len(df.columns)}")

    # 1. Normalizar nombres
    df.columns = (
        df.columns.str.strip().str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )

    # 2. Validar columnas obligatorias
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        logger.error(f"❌ Columnas faltantes: {faltantes}")
        logger.error(f"   Encontradas: {list(df.columns)}")
        return None

    # 3. Seleccionar solo columnas relevantes
    df = df[columnas_requeridas].copy()

    # 4. Limpiar nulos
    nulos = df.isnull().sum()
    if nulos.sum() > 0:
        logger.warning(f"⚠️  Nulos: {nulos[nulos > 0].to_dict()}")
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].fillna("SIN_DATO").str.strip()
        else:
            df[col] = df[col].fillna(0)

    # 5. Casteo de tipos
    if tipos_esperados:
        for col, tipo in tipos_esperados.items():
            if col in df.columns:
                try:
                    df[col] = df[col].astype(tipo)
                except (ValueError, TypeError) as e:
                    logger.error(f"❌ Cast error en '{col}': {e}")
                    return None

    # 6. Reglas de negocio
    df = _validar_negocio(df)
    if df is None:
        return None

    # 7. EDA
    if ejecutar_eda:
        _ejecutar_eda(df, ruta_archivo)

    logger.info(f"✅ Limpieza OK | Filas válidas: {len(df):,}")
    return df


def _validar_negocio(df: pd.DataFrame) -> pd.DataFrame | None:
    filas_0 = len(df)

    if "cantidad" in df.columns:
        mask = df["cantidad"] <= 0
        if mask.sum():
            logger.warning(f"⚠️  {mask.sum()} filas con cantidad<=0 eliminadas")
            df = df[~mask]

    if "precio_unitario" in df.columns:
        mask = df["precio_unitario"] <= 0
        if mask.sum():
            logger.warning(f"⚠️  {mask.sum()} filas con precio<=0 eliminadas")
            df = df[~mask]

    if "costo_unitario" in df.columns:
        mask = df["costo_unitario"] < 0
        if mask.sum():
            logger.warning(f"⚠️  {mask.sum()} filas con costo<0 eliminadas")
            df = df[~mask]

    if "costo_unitario" in df.columns and "precio_unitario" in df.columns:
        sospechosos = df["costo_unitario"] > df["precio_unitario"] * 3
        if sospechosos.sum():
            logger.warning(f"⚠️  {sospechosos.sum()} filas con costo>3×precio (conservadas)")

    if "monto" in df.columns:
        mask = df["monto"] <= 0
        if mask.sum():
            logger.warning(f"⚠️  {mask.sum()} filas con monto<=0 eliminadas")
            df = df[~mask]

    if len(df) == 0:
        logger.error("❌ Sin filas válidas tras validación de negocio")
        return None

    eliminadas = filas_0 - len(df)
    if eliminadas:
        logger.info(f"   Filas eliminadas: {eliminadas}")

    return df.reset_index(drop=True)


def _ejecutar_eda(df: pd.DataFrame, fuente: str) -> None:
    numericas = df.select_dtypes(include=[np.number])
    if numericas.empty:
        return

    sep = "=" * 58
    logger.info(sep)
    logger.info(f"📊 EDA - {fuente}")
    logger.info(sep)

    # Estadísticos descriptivos
    logger.info("📈 ESTADÍSTICOS:")
    desc = numericas.describe().round(2)
    for col in desc.columns:
        logger.info(
            f"   {col:25s} | media={desc[col]['mean']:>12,.2f} | "
            f"std={desc[col]['std']:>12,.2f} | "
            f"min={desc[col]['min']:>12,.2f} | max={desc[col]['max']:>12,.2f}"
        )

    # Outliers IQR
    logger.info("🚨 OUTLIERS (IQR):")
    for col in numericas.columns:
        q1, q3 = numericas[col].quantile(0.25), numericas[col].quantile(0.75)
        iqr = q3 - q1
        li, ls = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = ((numericas[col] < li) | (numericas[col] > ls)).sum()
        pct = n_out / len(df) * 100 if len(df) else 0
        mark = "⚠️ " if pct > 5 else "✅"
        logger.info(f"   {mark} {col:25s} | n={n_out} ({pct:.1f}%) | [{li:,.2f}, {ls:,.2f}]")

    # Normalidad Shapiro-Wilk
    logger.info("🔔 NORMALIDAD (Shapiro-Wilk α=0.05):")
    for col in numericas.columns:
        n = len(numericas[col].dropna())
        if 3 <= n <= 5000:
            stat, p = stats.shapiro(numericas[col].dropna())
            dist = "Normal ✅" if p > 0.05 else "No normal ⚠️"
            logger.info(f"   {col:25s} | W={stat:.4f} | p={p:.4f} | {dist}")
        elif n > 5000:
            stat, p = stats.kstest(
                numericas[col].dropna(), "norm",
                args=(numericas[col].mean(), numericas[col].std())
            )
            dist = "Normal ✅" if p > 0.05 else "No normal ⚠️"
            logger.info(f"   {col:25s} | KS={stat:.4f} | p={p:.4f} | {dist} (n>5000)")
        else:
            logger.info(f"   {col:25s} | n insuficiente (n={n})")

    # Correlación Pearson
    if len(numericas.columns) > 1:
        logger.info("🔗 CORRELACIÓN (Pearson):")
        corr = numericas.corr(method="pearson").round(3)
        cols = list(corr.columns)
        hdr = f"   {'':20s}"
        for c in cols:
            hdr += f" {c[:10]:>12s}"
        logger.info(hdr)
        for r in cols:
            row_str = f"   {r:20s}"
            for c in cols:
                row_str += f" {corr.loc[r, c]:12.3f}"
            logger.info(row_str)
        for i, c1 in enumerate(cols):
            for c2 in cols[i+1:]:
                v = abs(corr.loc[c1, c2])
                if v >= 0.8:
                    logger.warning(f"⚠️  Alta correlación {c1} ↔ {c2}: r={v:.3f}")

    logger.info(sep)


# ── Shortcuts públicos ────────────────────────────────────────────────────────
def limpiar_ventas(ruta: str = "assets/ventas.csv") -> pd.DataFrame | None:
    return cargar_y_limpiar_csv(ruta, COLUMNAS_VENTAS, TIPOS_ESPERADOS_VENTAS)


def limpiar_gastos(ruta: str = "assets/gastos.csv") -> pd.DataFrame | None:
    return cargar_y_limpiar_csv(ruta, COLUMNAS_GASTOS, TIPOS_ESPERADOS_GASTOS)
