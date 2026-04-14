"""
reports/financial_report.py
=============================
Generador de Reportes Financieros PDF - Pyme Analytics Engine v2.0

FIX: pd.read_sql con mysql.connector genera UserWarning en pandas >= 2.0
     porque requiere SQLAlchemy. Solución: usar cursor.fetchall() + pd.DataFrame()
     que funciona con cualquier versión de pandas y sin dependencias extra.

Nomenclatura: archivo00001fr.pdf, archivo00002fr.pdf, ...
Clase: ReporteFinanciero  →  método: generar()
"""

import os
import mysql.connector
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger("pyme_analytics")

REPORTES_DIR = Path(__file__).parent / "output"
REPORTES_DIR.mkdir(parents=True, exist_ok=True)


def _siguiente_num(prefijo: str) -> str:
    existentes = list(REPORTES_DIR.glob(f"*{prefijo}.pdf"))
    nums = []
    for f in existentes:
        try:
            nums.append(int(f.stem.replace(prefijo, "").replace("archivo", "")))
        except ValueError:
            pass
    return str(max(nums, default=0) + 1).zfill(5)


def _nombre_pdf(prefijo: str) -> Path:
    return REPORTES_DIR / f"archivo{_siguiente_num(prefijo)}{prefijo}.pdf"


def _conectar():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "pyme_analytics"),
        )
    except Exception as e:
        logger.error(f"❌ Conexión financial_report: {e}")
        return None


def _query_df(conn, sql: str) -> pd.DataFrame:
    """
    Ejecuta SQL y retorna DataFrame SIN usar pd.read_sql directamente.
    Compatible con pandas >= 2.0 sin necesitar SQLAlchemy.
    """
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as e:
        logger.error(f"❌ Query error: {e}")
        return pd.DataFrame()


# ── Clases PDF ────────────────────────────────────────────────────────────────

class PDFBase(FPDF):
    TITULO_REPORTE = "Pyme Analytics Engine"
    COLOR    = (0, 82, 155)
    COLOR_BG = (240, 240, 240)

    def header(self):
        self.set_fill_color(*self.COLOR)
        self.rect(0, 0, 210, 18, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 13)
        self.set_xy(0, 3)
        self.cell(0, 10, self.TITULO_REPORTE, align="C", ln=True)
        self.set_text_color(0, 0, 0)
        self.set_xy(0, 20)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0, 10,
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
            f"Pyme Analytics Engine v2.0 | Pág. {self.page_no()}",
            align="C",
        )

    def seccion_titulo(self, texto: str):
        self.set_fill_color(*self.COLOR_BG)
        self.set_font("Arial", "B", 11)
        self.set_text_color(*self.COLOR)
        self.cell(0, 8, f"  {texto}", ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def kpi_card(self, etiqueta: str, valor: str, variacion: str = ""):
        x, y, ancho, alto = self.get_x(), self.get_y(), 60, 18
        self.set_fill_color(245, 249, 255)
        self.rect(x, y, ancho, alto, "FD")
        self.set_font("Arial", "I", 7)
        self.set_text_color(100, 100, 100)
        self.set_xy(x + 2, y + 2)
        self.cell(ancho - 4, 5, etiqueta)
        self.set_font("Arial", "B", 12)
        self.set_text_color(*self.COLOR)
        self.set_xy(x + 2, y + 7)
        self.cell(ancho - 4, 7, valor)
        if variacion:
            color = (0, 150, 0) if "+" in variacion or "%" in variacion else (200, 0, 0)
            self.set_font("Arial", "", 7)
            self.set_text_color(*color)
            self.set_xy(x + 2, y + 13)
            self.cell(ancho - 4, 4, variacion)
        self.set_text_color(0, 0, 0)
        self.set_xy(x + ancho + 3, y)


# ── Clase principal ───────────────────────────────────────────────────────────

class ReporteFinanciero:
    """
    Genera reporte PDF financiero completo.
    Uso: ReporteFinanciero().generar()  →  retorna ruta del PDF generado.
    """

    def __init__(self):
        self.conn = _conectar()

    def _ebitda(self) -> dict:
        if not self.conn:
            return {}
        df = _query_df(self.conn, """
            SELECT
                COALESCE(SUM(v.cantidad * v.precio_unitario), 0)         AS ingresos,
                COALESCE(SUM(v.cantidad * v.costo_unitario_variable), 0) AS costos_variables,
                (SELECT COALESCE(SUM(monto), 0) FROM gastos)             AS gastos_operativos
            FROM ventas v
        """)
        if df.empty:
            return {}
        r = df.iloc[0]
        ing  = float(r["ingresos"])
        cos  = float(r["costos_variables"])
        gas  = float(r["gastos_operativos"])
        ebit = ing - cos - gas
        return {
            "ingresos":          ing,
            "costos_variables":  cos,
            "gastos_operativos": gas,
            "margen_bruto":      ing - cos,
            "ebitda":            ebit,
            "margen_bruto_pct":  ((ing - cos) / ing * 100) if ing else 0,
            "margen_ebitda_pct": (ebit / ing * 100) if ing else 0,
        }

    def _clientes(self) -> pd.DataFrame:
        if not self.conn:
            return pd.DataFrame()
        return _query_df(self.conn, """
            SELECT
                c.nombre_cliente,
                ROUND(SUM(v.cantidad * v.precio_unitario), 2)            AS ingresos,
                ROUND(SUM(v.cantidad * v.costo_unitario_variable), 2)    AS costos,
                ROUND(SUM(v.cantidad * v.precio_unitario)
                      - SUM(v.cantidad * v.costo_unitario_variable), 2)  AS margen,
                ROUND((SUM(v.cantidad * v.precio_unitario)
                       - SUM(v.cantidad * v.costo_unitario_variable))
                      / NULLIF(SUM(v.cantidad * v.precio_unitario), 0) * 100, 1)  AS margen_pct
            FROM ventas v
            JOIN clientes c ON v.id_cliente = c.id_cliente
            GROUP BY c.nombre_cliente
            ORDER BY margen DESC
            LIMIT 20
        """)

    def _productos(self) -> pd.DataFrame:
        if not self.conn:
            return pd.DataFrame()
        return _query_df(self.conn, """
            SELECT
                p.nombre_producto,
                ROUND(SUM(v.cantidad * v.precio_unitario), 2)            AS ingresos,
                ROUND(SUM(v.cantidad * v.costo_unitario_variable), 2)    AS costos,
                ROUND(SUM(v.cantidad * v.precio_unitario)
                      - SUM(v.cantidad * v.costo_unitario_variable), 2)  AS margen,
                ROUND((SUM(v.cantidad * v.precio_unitario)
                       - SUM(v.cantidad * v.costo_unitario_variable))
                      / NULLIF(SUM(v.cantidad * v.precio_unitario), 0) * 100, 1)  AS margen_pct
            FROM ventas v
            JOIN productos p ON v.id_producto = p.id_producto
            GROUP BY p.nombre_producto
            ORDER BY margen DESC
            LIMIT 20
        """)

    def _mensual(self) -> pd.DataFrame:
        if not self.conn:
            return pd.DataFrame()
        return _query_df(self.conn, """
            SELECT
                DATE_FORMAT(fecha, '%Y-%m')                             AS mes,
                ROUND(SUM(cantidad * precio_unitario), 2)               AS ingresos,
                ROUND(SUM(cantidad * costo_unitario_variable), 2)       AS costos
            FROM ventas
            GROUP BY mes
            ORDER BY mes DESC
            LIMIT 12
        """)

    def generar(self) -> str:
        """Genera el PDF y retorna su ruta absoluta."""
        kpis   = self._ebitda()
        df_c   = self._clientes()
        df_p   = self._productos()
        df_m   = self._mensual()

        pdf = PDFBase()
        pdf.TITULO_REPORTE = "Reporte Financiero - Pyme Analytics Engine"
        pdf.add_page()

        # ── Encabezado ──
        pdf.set_font("Arial", "B", 14)
        pdf.set_text_color(0, 82, 155)
        pdf.cell(0, 8, "INDICADORES DE RENTABILIDAD Y MÁRGENES", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 5, f"Período de análisis: {datetime.now().strftime('%B %Y')}", ln=True)
        pdf.ln(5)

        def fmt(v): return f"$ {v:,.0f}"
        def pct(v): return f"{v:.1f}%"

        # ── KPIs ──
        if kpis:
            pdf.kpi_card("INGRESOS TOTALES",  fmt(kpis["ingresos"]))
            pdf.kpi_card("COSTOS VARIABLES",  fmt(kpis["costos_variables"]))
            pdf.kpi_card("GASTOS OPERATIVOS", fmt(kpis["gastos_operativos"]))
            pdf.ln(22)
            pdf.kpi_card("MARGEN BRUTO", fmt(kpis["margen_bruto"]),
                         pct(kpis["margen_bruto_pct"]))
            pdf.kpi_card("EBITDA",       fmt(kpis["ebitda"]),
                         pct(kpis["margen_ebitda_pct"]))
            pdf.ln(22)

        # ── Función auxiliar para tablas PDF ──
        def _tabla(df_t, titulo, col_nombre, col_label):
            pdf.add_page()
            pdf.seccion_titulo(titulo)
            if df_t.empty:
                pdf.cell(0, 6, "Sin datos disponibles", ln=True)
                return
            cabeceras = [(col_label, 60), ("Ingresos", 35),
                         ("Costos", 35), ("Margen", 35), ("Margen%", 20)]
            pdf.set_font("Arial", "B", 8)
            pdf.set_fill_color(0, 82, 155)
            pdf.set_text_color(255, 255, 255)
            for h, w in cabeceras:
                pdf.cell(w, 7, h, border=1, fill=True)
            pdf.ln()
            pdf.set_font("Arial", "", 8)
            pdf.set_text_color(0, 0, 0)
            for i, (_, row) in enumerate(df_t.iterrows()):
                fill = (i % 2 == 0)
                pdf.set_fill_color(245, 249, 255) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(60, 6, str(row[col_nombre])[:28],           border=1, fill=fill)
                pdf.cell(35, 6, f"${float(row['ingresos']):,.0f}",   border=1, fill=fill, align="R")
                pdf.cell(35, 6, f"${float(row['costos']):,.0f}",     border=1, fill=fill, align="R")
                pdf.cell(35, 6, f"${float(row['margen']):,.0f}",     border=1, fill=fill, align="R")
                pdf.cell(20, 6, f"{float(row['margen_pct']):.1f}%",  border=1, fill=fill, align="R")
                pdf.ln()

        _tabla(df_c, "RENTABILIDAD POR CLIENTE (TOP 20)", "nombre_cliente", "Cliente")
        _tabla(df_p, "RENTABILIDAD POR PRODUCTO (TOP 20)", "nombre_producto", "Producto")

        # ── Tendencia mensual ──
        if not df_m.empty:
            pdf.add_page()
            pdf.seccion_titulo("TENDENCIA MENSUAL (ÚLTIMOS 12 MESES)")
            pdf.set_font("Arial", "B", 8)
            pdf.set_fill_color(0, 82, 155)
            pdf.set_text_color(255, 255, 255)
            for h, w in [("Mes", 40), ("Ingresos", 50), ("Costos Var.", 50), ("Margen Bruto", 50)]:
                pdf.cell(w, 7, h, border=1, fill=True)
            pdf.ln()
            pdf.set_font("Arial", "", 8)
            pdf.set_text_color(0, 0, 0)
            for i, (_, row) in enumerate(df_m.iterrows()):
                fill = (i % 2 == 0)
                pdf.set_fill_color(245, 249, 255) if fill else pdf.set_fill_color(255, 255, 255)
                ing = float(row["ingresos"])
                cos = float(row["costos"])
                mb  = ing - cos
                pdf.cell(40, 6, str(row["mes"]),    border=1, fill=fill)
                pdf.cell(50, 6, f"${ing:,.0f}",     border=1, fill=fill, align="R")
                pdf.cell(50, 6, f"${cos:,.0f}",     border=1, fill=fill, align="R")
                pdf.cell(50, 6, f"${mb:,.0f}",      border=1, fill=fill, align="R")
                pdf.ln()

        if self.conn:
            self.conn.close()

        ruta = str(_nombre_pdf("fr"))
        pdf.output(ruta)
        logger.info(f"✅ Reporte financiero: {ruta}")
        print(f"✅ PDF Financiero: {ruta}")
        return ruta


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    logging.basicConfig(level=logging.INFO)
    ruta = ReporteFinanciero().generar()
    print(f"PDF generado: {ruta}")
