"""
analytics/regression_model.py
===============================
Modelo Econométrico OLS + Persistencia + PDF - Pyme Analytics Engine v2.0

Clase principal: AnalistaPyme (NO ModeloRegresionPyme)
Método orquestador: ejecutar_todo()

PDFs nombrados: archivo00001ml.pdf, archivo00002ml.pdf, ...
"""

import os
import logging
import warnings
import joblib
import mysql.connector
import pandas as pd
import numpy as np
import statsmodels.api as sm
from fpdf import FPDF
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

logger = logging.getLogger("pyme_analytics")

# ── Directorios ───────────────────────────────────────────────────────────────
MODELS_DIR  = Path(__file__).parent / "modelos_guardados"
REPORTS_DIR = Path(__file__).parent.parent / "reports" / "output"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

MODELO_PATH = MODELS_DIR / "modelo_ventas_ols.pkl"


def _siguiente_numero(prefijo: str) -> str:
    existentes = list(REPORTS_DIR.glob(f"*{prefijo}.pdf"))
    nums = []
    for f in existentes:
        try:
            nums.append(int(f.stem.replace(prefijo, "").replace("archivo", "")))
        except ValueError:
            pass
    return str(max(nums, default=0) + 1).zfill(5)


def _nombre_pdf_ml() -> Path:
    return REPORTS_DIR / f"archivo{_siguiente_numero('ml')}ml.pdf"


def _conexion_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "pyme_analytics"),
    )


# ── PDF ───────────────────────────────────────────────────────────────────────
class PDFModeloML(FPDF):
    COLOR = (0, 82, 155)

    def header(self):
        self.set_fill_color(*self.COLOR)
        self.rect(0, 0, 210, 18, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 13)
        self.set_xy(0, 3)
        self.cell(0, 10, "Reporte Machine Learning - Pyme Analytics Engine", align="C", ln=True)
        self.set_text_color(0, 0, 0)
        self.set_xy(0, 20)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10,
                  f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
                  f"Pyme Analytics Engine v2.0 | Pág. {self.page_no()}",
                  align="C")

    def kpi_row(self, items: list):
        ancho = 60
        for etiqueta, valor in items[:3]:
            x, y = self.get_x(), self.get_y()
            self.set_fill_color(245, 249, 255)
            self.rect(x, y, ancho, 18, "FD")
            self.set_font("Arial", "I", 7)
            self.set_text_color(100, 100, 100)
            self.set_xy(x + 2, y + 2)
            self.cell(ancho - 4, 5, etiqueta)
            self.set_font("Arial", "B", 11)
            self.set_text_color(*self.COLOR)
            self.set_xy(x + 2, y + 8)
            self.cell(ancho - 4, 7, str(valor))
            self.set_text_color(0, 0, 0)
            self.set_xy(x + ancho + 3, y)
        self.ln(22)


# ── Clase principal ───────────────────────────────────────────────────────────
class AnalistaPyme:
    """
    Pipeline econométrico completo:
      1. extraer_datos()         → MySQL
      2. entrenar_o_cargar()     → OLS (reutiliza modelo si n obs no cambió)
      3. guardar_en_db()         → historico_regresion
      4. generar_pdf()           → archivo000XXml.pdf
      5. ejecutar_todo()         → orquestador
    """

    def __init__(self):
        self.db_config = {
            "host":     os.getenv("DB_HOST", "localhost"),
            "user":     os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "pyme_analytics"),
        }

    def extraer_datos(self) -> pd.DataFrame:
        logger.info("Extrayendo datos para OLS...")
        try:
            conn = mysql.connector.connect(**self.db_config)
            sql = """
                SELECT
                    precio_unitario,
                    costo_unitario_variable,
                    cantidad,
                    (precio_unitario * cantidad)                AS venta_total,
                    (precio_unitario - costo_unitario_variable) AS margen_unitario
                FROM ventas
                WHERE precio_unitario > 0 AND cantidad > 0
            """
            df = pd.read_sql(sql, conn)
            conn.close()
            logger.info(f"Observaciones para modelo: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"❌ Error extrayendo datos OLS: {e}")
            return pd.DataFrame()

    def entrenar_o_cargar(self, df: pd.DataFrame):
        """Carga modelo guardado si aplica, sino entrena nuevo."""
        if MODELO_PATH.exists():
            m = joblib.load(MODELO_PATH)
            if int(getattr(m, "nobs", 0)) == len(df):
                logger.info("♻️  Modelo cargado desde caché")
                return m

        logger.info("🧠 Entrenando nuevo modelo OLS...")
        X = sm.add_constant(df[["precio_unitario", "costo_unitario_variable", "cantidad"]])
        Y = df["venta_total"]
        modelo = sm.OLS(Y, X).fit()
        joblib.dump(modelo, MODELO_PATH)
        logger.info(f"💾 Modelo guardado: {MODELO_PATH}")
        return modelo

    def guardar_en_db(self, modelo) -> None:
        logger.info("Guardando métricas en historico_regresion...")
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historico_regresion (
                    id              INT AUTO_INCREMENT PRIMARY KEY,
                    fecha           DATETIME,
                    r_cuadrado      FLOAT,
                    r_cuadrado_adj  FLOAT,
                    coef_precio     FLOAT,
                    coef_costo      FLOAT,
                    coef_cantidad   FLOAT,
                    p_valor_global  FLOAT,
                    aic             FLOAT,
                    bic             FLOAT,
                    observaciones   INT
                )
            """)
            params = modelo.params
            cursor.execute("""
                INSERT INTO historico_regresion
                    (fecha, r_cuadrado, r_cuadrado_adj, coef_precio,
                     coef_costo, coef_cantidad, p_valor_global, aic, bic, observaciones)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                datetime.now(),
                round(float(modelo.rsquared), 6),
                round(float(modelo.rsquared_adj), 6),
                round(float(params.get("precio_unitario", 0)), 6),
                round(float(params.get("costo_unitario_variable", 0)), 6),
                round(float(params.get("cantidad", 0)), 6),
                round(float(modelo.f_pvalue), 6),
                round(float(modelo.aic), 2),
                round(float(modelo.bic), 2),
                int(modelo.nobs),
            ))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Métricas guardadas en historico_regresion")
        except Exception as e:
            logger.error(f"❌ Error guardando métricas: {e}")

    def generar_pdf(self, modelo, df: pd.DataFrame) -> str:
        pdf = PDFModeloML()
        pdf.add_page()

        pdf.set_font("Arial", "B", 14)
        pdf.set_text_color(0, 82, 155)
        pdf.cell(0, 8, "ANÁLISIS ECONOMÉTRICO - REGRESIÓN OLS", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 5, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Obs: {int(modelo.nobs)}", ln=True)
        pdf.ln(4)

        pdf.kpi_row([
            ("R² (Bondad de ajuste)", f"{modelo.rsquared:.4f}"),
            ("R² Ajustado",           f"{modelo.rsquared_adj:.4f}"),
            ("AIC",                   f"{modelo.aic:.1f}"),
        ])
        pdf.kpi_row([
            ("F-estadístico",    f"{modelo.fvalue:.2f}"),
            ("P-valor (global)", f"{modelo.f_pvalue:.4f}"),
            ("Observaciones",    str(int(modelo.nobs))),
        ])

        # Tabla de coeficientes
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(0, 82, 155)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 7, "  TABLA DE COEFICIENTES", ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        headers = ["Variable", "Coeficiente", "Error Std", "t-stat", "P-valor", "IC95 Inf", "IC95 Sup"]
        anchos  = [50, 25, 25, 22, 20, 26, 27]
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(0, 82, 155)
        pdf.set_text_color(255, 255, 255)
        for h, w in zip(headers, anchos):
            pdf.cell(w, 7, h, border=1, fill=True)
        pdf.ln()

        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(0, 0, 0)
        conf_int = modelo.conf_int()
        for i, (nombre, coef) in enumerate(modelo.params.items()):
            fill = i % 2 == 0
            pdf.set_fill_color(245, 249, 255) if fill else pdf.set_fill_color(255, 255, 255)
            pval = modelo.pvalues[nombre]
            sig = " ***" if pval < 0.001 else " **" if pval < 0.01 else " *" if pval < 0.05 else ""
            vals = [str(nombre) + sig, f"{coef:.4f}", f"{modelo.bse[nombre]:.4f}",
                    f"{modelo.tvalues[nombre]:.3f}", f"{pval:.4f}",
                    f"{conf_int.loc[nombre, 0]:.4f}", f"{conf_int.loc[nombre, 1]:.4f}"]
            for v, w in zip(vals, anchos):
                pdf.cell(w, 6, v, border=1, fill=fill)
            pdf.ln()

        pdf.ln(3)
        pdf.set_font("Arial", "I", 7)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, "*** p<0.001  ** p<0.01  * p<0.05", ln=True)

        # Resumen statsmodels
        pdf.add_page()
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(0, 82, 155)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 7, "  RESUMEN STATSMODELS", ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.set_font("Courier", "", 7)
        for linea in modelo.summary().as_text().split("\n"):
            pdf.cell(0, 4, linea[:120], ln=True)

        ruta = str(_nombre_pdf_ml())
        pdf.output(ruta)
        logger.info(f"✅ PDF ML generado: {ruta}")
        print(f"✅ PDF ML: {ruta}")
        return ruta

    def ejecutar_todo(self) -> None:
        """Orquestador principal: extrae → entrena → guarda → PDF."""
        df = self.extraer_datos()
        if df is None or df.empty:
            logger.warning("⚠️  Sin datos para el modelo OLS")
            return
        modelo = self.entrenar_o_cargar(df)
        print(modelo.summary())
        self.guardar_en_db(modelo)
        self.generar_pdf(modelo, df)

    # Alias para compatibilidad con código que use el nombre anterior
    def ejecutar_pipeline_completo(self) -> None:
        self.ejecutar_todo()
