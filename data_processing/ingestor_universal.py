"""
data_processing/ingestor_universal.py
=======================================
Ingesta de datos multi-formato - Pyme Analytics Engine v2.0

Soporta: CSV, Excel (.xlsx/.xls), JSON, TXT-ERP
Incluye: anonimización SHA-256 (Habeas Data / Ley 1581 Colombia / GDPR)
"""

import pandas as pd
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger("pyme_analytics")

COLUMNAS_VENTAS = ["fecha", "cliente", "producto", "cantidad", "precio_unitario", "costo_unitario"]
COLUMNAS_GASTOS = ["fecha", "descripcion", "categoria_gasto", "tipo_gasto", "monto"]

SINONIMOS_VENTAS = {
    "date": "fecha", "sale_date": "fecha", "fecha_venta": "fecha",
    "customer": "cliente", "client": "cliente", "nombre_cliente": "cliente",
    "item": "producto", "product": "producto", "articulo": "producto",
    "qty": "cantidad", "quantity": "cantidad", "units": "cantidad",
    "unit_price": "precio_unitario", "price": "precio_unitario", "valor": "precio_unitario",
    "cost": "costo_unitario", "unit_cost": "costo_unitario", "costo": "costo_unitario",
}
SINONIMOS_GASTOS = {
    "date": "fecha", "expense_date": "fecha",
    "description": "descripcion", "concepto": "descripcion",
    "category": "categoria_gasto", "type": "tipo_gasto",
    "amount": "monto", "valor": "monto", "value": "monto",
}


class IngestorUniversal:
    def __init__(self, tipo_tabla: str = "ventas", anonimizar: bool = False):
        self.tipo_tabla = tipo_tabla
        self.anonimizar = anonimizar
        self.columnas = COLUMNAS_VENTAS if tipo_tabla == "ventas" else COLUMNAS_GASTOS
        self.sinonimos = SINONIMOS_VENTAS if tipo_tabla == "ventas" else SINONIMOS_GASTOS

    def ingestar(self, ruta: str) -> Optional[pd.DataFrame]:
        ruta_p = Path(ruta)
        if not ruta_p.exists():
            logger.error(f"❌ Archivo no encontrado: {ruta}")
            return None

        ext = ruta_p.suffix.lower()
        logger.info(f"📂 Ingesta | {ruta_p.name} | tabla={self.tipo_tabla}")

        try:
            df_raw = self._leer(ruta_p, ext)
        except Exception as e:
            logger.error(f"❌ Error leyendo archivo: {e}")
            return None

        if df_raw is None or df_raw.empty:
            logger.warning("⚠️  Archivo vacío")
            return None

        df = self._normalizar(df_raw, ruta_p.name)
        if df is not None and self.anonimizar:
            df = self._anonimizar(df)
        if df is not None:
            logger.info(f"✅ Ingesta OK | {len(df)} filas | {ruta_p.name}")
        return df

    def _leer(self, ruta: Path, ext: str) -> Optional[pd.DataFrame]:
        if ext == ".csv":
            return self._leer_csv(ruta)
        elif ext in (".xlsx", ".xls"):
            return self._leer_excel(ruta)
        elif ext == ".json":
            return self._leer_json(ruta)
        elif ext == ".txt":
            return self._leer_txt_erp(ruta)
        else:
            logger.error(f"❌ Extensión no soportada: {ext}")
            return None

    def _leer_csv(self, ruta: Path) -> pd.DataFrame:
        for enc in ["utf-8", "latin-1", "cp1252", "utf-8-sig"]:
            for sep in [",", ";", "\t", "|"]:
                try:
                    df = pd.read_csv(ruta, encoding=enc, sep=sep, engine="python")
                    if len(df.columns) > 1:
                        return df
                except Exception:
                    continue
        raise ValueError("No se pudo leer el CSV con ningún encoding/separador")

    def _leer_excel(self, ruta: Path) -> pd.DataFrame:
        xls = pd.ExcelFile(ruta)
        mejor, score = xls.sheet_names[0], 0
        for h in xls.sheet_names:
            tmp = pd.read_excel(xls, sheet_name=h, nrows=5)
            cols = [c.lower().strip() for c in tmp.columns]
            s = sum(1 for c in self.columnas if c in cols)
            if s > score:
                mejor, score = h, s
        return pd.read_excel(xls, sheet_name=mejor)

    def _leer_json(self, ruta: Path) -> pd.DataFrame:
        with open(ruta, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return pd.DataFrame(data)
            for v in data.values():
                if isinstance(v, list):
                    return pd.DataFrame(v)
            return pd.DataFrame([data])
        except json.JSONDecodeError:
            lineas = [json.loads(l) for l in raw.splitlines() if l.strip()]
            return pd.DataFrame(lineas)

    def _leer_txt_erp(self, ruta: Path) -> pd.DataFrame:
        for sep in ["\t", ";", "|", ","]:
            try:
                df = pd.read_csv(ruta, sep=sep, encoding="latin-1", engine="python")
                if len(df.columns) > 1:
                    return df
            except Exception:
                continue
        raise ValueError("No se pudo leer TXT-ERP")

    def _normalizar(self, df: pd.DataFrame, nombre: str) -> Optional[pd.DataFrame]:
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        df.rename(columns=self.sinonimos, inplace=True)

        faltantes = [c for c in self.columnas if c not in df.columns]
        if faltantes:
            logger.error(f"❌ Columnas faltantes en '{nombre}': {faltantes}")
            return None

        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].fillna("SIN_DATO").str.strip()
            else:
                df[col] = df[col].fillna(0)

        df = self._coercionar_tipos(df)
        df = df[df["fecha"] != "SIN_DATO"]
        df = df[df["fecha"] != "0"]

        df["_origen_archivo"] = nombre
        df["_fecha_ingesta"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"   Normalización OK | {len(df)} filas")
        return df

    def _coercionar_tipos(self, df: pd.DataFrame) -> pd.DataFrame:
        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(
                df["fecha"], dayfirst=True, errors="coerce"
            ).dt.strftime("%Y-%m-%d")
        for col in ["cantidad", "precio_unitario", "costo_unitario"]:
            if col in df.columns:
                df[col] = (
                    df[col].astype(str)
                    .str.replace(",", ".", regex=False)
                    .str.replace(r"[^0-9.]", "", regex=True)
                )
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        if "monto" in df.columns:
            df["monto"] = (
                df["monto"].astype(str)
                .str.replace(",", ".", regex=False)
                .str.replace(r"[^0-9.]", "", regex=True)
            )
            df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
        return df

    def _anonimizar(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in ["cliente", "nombre_cliente", "email", "telefono", "nit"]:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:12]
                    if x not in ("SIN_DATO", "", None) else x
                )
                logger.info(f"   🔐 Columna anonimizada: {col}")
        return df
