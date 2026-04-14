"""
dashboard/app.py - Dashboard Streamlit Profesional
=====================================================
Pyme Analytics Engine v2.0

Módulos:
  🏠 Inicio      → KPIs ejecutivos + alertas
  💰 Financiero  → EBITDA mensual con gastos
  👥 Clientes    → Pareto 80/20 con paginación
  📦 Productos   → Treemap + scatter precio/margen
  📈 Tendencias  → Estacionalidad mensual
  📄 Reportes    → Generar PDFs con un clic
  🔄 Ingesta     → Subir CSV y cargar a MySQL

Ejecutar: streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import mysql.connector
import os
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

# ── Rutas y configuración ─────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Pyme Analytics Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS corporativo ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .metric-card {
        background: #f0f4ff;
        border-left: 4px solid #00529B;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .alerta-verde {
        background: #e8f5e9; border-left: 4px solid #43A047;
        border-radius: 6px; padding: 10px 16px; color: #1b5e20;
        font-weight: 600; margin: 8px 0;
    }
    .alerta-roja {
        background: #ffebee; border-left: 4px solid #E53935;
        border-radius: 6px; padding: 10px 16px; color: #b71c1c;
        font-weight: 600; margin: 8px 0;
    }
    .alerta-amarilla {
        background: #fff8e1; border-left: 4px solid #FFA000;
        border-radius: 6px; padding: 10px 16px; color: #e65100;
        font-weight: 600; margin: 8px 0;
    }
    .seccion-titulo {
        font-size: 18px; font-weight: 700;
        color: #00529B; border-bottom: 2px solid #00529B;
        padding-bottom: 6px; margin: 16px 0 12px 0;
    }
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# CAPA DE DATOS
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def get_connection():
    """Conexión MySQL cacheada (singleton en la sesión)."""
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "pyme_analytics"),
        )
    except Exception:
        return None


def conexion_ok() -> bool:
    conn = get_connection()
    if conn is None:
        return False
    try:
        conn.ping(reconnect=True)
        return True
    except Exception:
        return False


def consultar(sql: str) -> pd.DataFrame:
    """Ejecuta SQL y retorna DataFrame. Reconnect automático."""
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        conn.ping(reconnect=True)
        return pd.read_sql(sql, conn)
    except Exception as e:
        st.error(f"❌ Error de consulta: {e}")
        return pd.DataFrame()


# ── Filtros globales de fecha ─────────────────────────────────────────────────
hoy = date.today()
primer_dia_anio = date(hoy.year, 1, 1)

with st.sidebar:
    st.image("https://img.icons8.com/color/96/combo-chart.png", width=60)
    st.markdown("## 📊 Pyme Analytics")
    st.markdown("---")

    st.markdown("### 📅 Filtro de período")
    fecha_desde = st.date_input("Desde", value=primer_dia_anio, key="f_desde")
    fecha_hasta = st.date_input("Hasta", value=hoy, key="f_hasta")

    st.markdown("---")

    # Estado conexión
    if conexion_ok():
        st.success("✅ MySQL Conectado")
    else:
        st.error("❌ MySQL Desconectado")
        st.info("Verifique que XAMPP esté activo")

    st.markdown("---")

    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    modulo = st.radio(
        "Módulo",
        ["🏠 Inicio", "💰 Financiero", "👥 Clientes",
         "📦 Productos", "📈 Tendencias", "📄 Reportes", "🔄 Ingesta"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("**Pyme Analytics Engine v2.0**")
    st.caption("© 2026 - Andrés | Todos los derechos reservados")
    st.caption("Registro DNDA Colombia - Pendiente")

registros_pagina = 15
f_desde = str(fecha_desde)
f_hasta = str(fecha_hasta)


# ── Consultas reutilizables ───────────────────────────────────────────────────
@st.cache_data(ttl=300)
def kpi_resumen(fd: str, fh: str) -> dict:
    df = consultar(f"""
        WITH base AS (
            SELECT
                COALESCE(SUM(v.cantidad * v.precio_unitario), 0)         AS ingresos,
                COALESCE(SUM(v.cantidad * v.costo_unitario_variable), 0) AS costos,
                COUNT(DISTINCT v.id_cliente)   AS clientes,
                COUNT(DISTINCT v.id_producto)  AS productos,
                COUNT(v.id_factura)            AS transacciones
            FROM ventas v
            WHERE v.fecha BETWEEN '{fd}' AND '{fh}'
        ),
        g AS (SELECT COALESCE(SUM(monto),0) AS total FROM gastos
              WHERE fecha BETWEEN '{fd}' AND '{fh}')
        SELECT b.ingresos, b.costos,
               b.ingresos - b.costos AS utilidad_bruta,
               g.total AS gastos,
               (b.ingresos - b.costos) - g.total AS ebitda,
               ROUND(((b.ingresos-b.costos-g.total)/b.ingresos)*100,2) AS margen_ebitda,
               ROUND((b.ingresos-b.costos)/b.ingresos*100,2) AS margen_bruto,
               ROUND(b.ingresos/b.transacciones,2) AS ticket,
               b.clientes, b.productos, b.transacciones
        FROM base b CROSS JOIN g
    """)
    if df.empty:
        return {}
    return {k: float(v) for k, v in df.iloc[0].items()}


@st.cache_data(ttl=300)
def ventas_por_mes(fd: str, fh: str) -> pd.DataFrame:
    return consultar(f"""
        SELECT DATE_FORMAT(fecha,'%Y-%m') AS mes,
               ROUND(SUM(cantidad*precio_unitario),0)          AS ingresos,
               ROUND(SUM(cantidad*costo_unitario_variable),0)  AS costos
        FROM ventas
        WHERE fecha BETWEEN '{fd}' AND '{fh}'
        GROUP BY mes ORDER BY mes
    """)


@st.cache_data(ttl=300)
def top_clientes(fd: str, fh: str, lim: int = 50) -> pd.DataFrame:
    return consultar(f"""
        SELECT c.nombre_cliente,
               ROUND(SUM(v.cantidad*v.precio_unitario),0)          AS ingresos,
               ROUND(SUM(v.cantidad*v.costo_unitario_variable),0)  AS costos,
               ROUND(SUM(v.cantidad*v.precio_unitario)
                     -SUM(v.cantidad*v.costo_unitario_variable),0) AS margen,
               ROUND((SUM(v.cantidad*v.precio_unitario)
                      -SUM(v.cantidad*v.costo_unitario_variable))
                     /NULLIF(SUM(v.cantidad*v.precio_unitario),0)*100,1) AS margen_pct
        FROM ventas v JOIN clientes c ON v.id_cliente=c.id_cliente
        WHERE v.fecha BETWEEN '{fd}' AND '{fh}'
        GROUP BY c.nombre_cliente ORDER BY margen DESC LIMIT {lim}
    """)


@st.cache_data(ttl=300)
def top_productos(fd: str, fh: str, lim: int = 50) -> pd.DataFrame:
    return consultar(f"""
        SELECT p.nombre_producto,
               SUM(v.cantidad) AS unidades,
               ROUND(SUM(v.cantidad*v.precio_unitario),0)          AS ingresos,
               ROUND(SUM(v.cantidad*v.costo_unitario_variable),0)  AS costos,
               ROUND(SUM(v.cantidad*v.precio_unitario)
                     -SUM(v.cantidad*v.costo_unitario_variable),0) AS margen,
               ROUND((SUM(v.cantidad*v.precio_unitario)
                      -SUM(v.cantidad*v.costo_unitario_variable))
                     /NULLIF(SUM(v.cantidad*v.precio_unitario),0)*100,1) AS margen_pct
        FROM ventas v JOIN productos p ON v.id_producto=p.id_producto
        WHERE v.fecha BETWEEN '{fd}' AND '{fh}'
        GROUP BY p.nombre_producto ORDER BY margen DESC LIMIT {lim}
    """)


def fmt_cop(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:.1f}K"
    return f"${v:,.0f}"


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULOS
# ═════════════════════════════════════════════════════════════════════════════

def modulo_inicio():
    st.markdown('<p class="seccion-titulo">🏠 Panel Ejecutivo - KPIs</p>', unsafe_allow_html=True)
    st.caption(f"Período: {f_desde} → {f_hasta}")

    if not conexion_ok():
        st.error("Sin conexión a MySQL. Inicie XAMPP.")
        return

    kpis = kpi_resumen(f_desde, f_hasta)
    if not kpis:
        st.info("Sin datos para el período seleccionado.")
        return

    ingresos = kpis.get("ingresos", 0)
    costos   = kpis.get("costos", 0)
    gastos   = kpis.get("gastos", 0)
    ebitda   = kpis.get("ebitda", 0)
    margen_e = kpis.get("margen_ebitda", 0)
    margen_b = kpis.get("margen_bruto", 0)
    ticket   = kpis.get("ticket", 0)
    clientes = int(kpis.get("clientes", 0))
    txns     = int(kpis.get("transacciones", 0))

    # Fila 1
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Ingresos Totales",  fmt_cop(ingresos))
    c2.metric("📉 Costos Variables",  fmt_cop(costos))
    c3.metric("💸 Gastos Operativos", fmt_cop(gastos))
    c4.metric("💰 EBITDA",           fmt_cop(ebitda),
              delta=f"{margen_e:.1f}% margen")

    # Fila 2
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📊 Margen Bruto",    fmt_cop(ingresos - costos),
              delta=f"{margen_b:.1f}%")
    c2.metric("👥 Clientes Activos", f"{clientes:,}")
    c3.metric("🔢 Transacciones",    f"{txns:,}")
    c4.metric("🎫 Ticket Promedio",  fmt_cop(ticket))

    # Alerta de salud financiera
    st.markdown("---")
    if margen_e >= 30:
        st.markdown(
            f'<div class="alerta-verde">✅ Negocio saludable  Margen EBITDA: {margen_e:.1f}%</div>',
            unsafe_allow_html=True)
    elif margen_e >= 10:
        st.markdown(
            f'<div class="alerta-amarilla">⚠️ Margen EBITDA aceptable: {margen_e:.1f}% - '
            f'Revisar estructura de costos</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="alerta-roja">🔴 Margen EBITDA crítico: {margen_e:.1f}% - '
            f'Acción inmediata requerida</div>', unsafe_allow_html=True)

    # Gráfico de evolución mensual
    df_mes = ventas_por_mes(f_desde, f_hasta)
    if not df_mes.empty:
        st.markdown('<p class="seccion-titulo">📈 Evolución Mensual</p>', unsafe_allow_html=True)
        df_mes["margen"] = df_mes["ingresos"] - df_mes["costos"]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_mes["mes"], y=df_mes["ingresos"],
                             name="Ingresos", marker_color="#00529B"))
        fig.add_trace(go.Bar(x=df_mes["mes"], y=df_mes["costos"],
                             name="Costos", marker_color="#E53935"))
        fig.add_trace(go.Scatter(x=df_mes["mes"], y=df_mes["margen"],
                                 name="Margen Bruto", mode="lines+markers",
                                 line=dict(color="#43A047", width=2.5)))
        fig.update_layout(barmode="group", height=360,
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)

    # Composición de ingresos (donut)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<p class="seccion-titulo">🍩 Estructura del Ingreso</p>', unsafe_allow_html=True)
        labels = ["Costos Variables", "Gastos Operativos", "EBITDA"]
        values = [costos, gastos, max(ebitda, 0)]
        colors = ["#E53935", "#FFA000", "#43A047"]
        fig2 = go.Figure(go.Pie(labels=labels, values=values, hole=0.5,
                                marker_colors=colors, textinfo="label+percent"))
        fig2.update_layout(height=320, showlegend=True,
                           legend=dict(orientation="h"))
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.markdown('<p class="seccion-titulo">📌 Resumen Ejecutivo</p>', unsafe_allow_html=True)
        resumen = pd.DataFrame({
            "Indicador": ["Ingresos", "Costos Variables", "Utilidad Bruta",
                          "Gastos Operativos", "EBITDA", "Margen EBITDA %",
                          "Ticket Promedio", "Clientes", "Transacciones"],
            "Valor": [
                fmt_cop(ingresos), fmt_cop(costos),
                fmt_cop(ingresos - costos), fmt_cop(gastos),
                fmt_cop(ebitda), f"{margen_e:.2f}%",
                fmt_cop(ticket), f"{clientes:,}", f"{txns:,}",
            ]
        })
        st.dataframe(resumen, hide_index=True, use_container_width=True)


def modulo_financiero():
    st.markdown('<p class="seccion-titulo">💰 Análisis Financiero - EBITDA</p>', unsafe_allow_html=True)
    st.caption(f"Período: {f_desde} → {f_hasta}")

    df_mes = ventas_por_mes(f_desde, f_hasta)
    df_gas = consultar(f"""
        SELECT DATE_FORMAT(fecha,'%Y-%m') AS mes,
               ROUND(SUM(monto),0) AS gastos
        FROM gastos
        WHERE fecha BETWEEN '{f_desde}' AND '{f_hasta}'
        GROUP BY mes ORDER BY mes
    """)

    if df_mes.empty:
        st.info("Sin datos para el período.")
        return

    df = df_mes.merge(df_gas, on="mes", how="left").fillna(0) if not df_gas.empty else df_mes.copy()
    if "gastos" not in df.columns:
        df["gastos"] = 0

    df["ebitda"]          = df["ingresos"] - df["costos"] - df["gastos"]
    df["margen_ebitda"]   = (df["ebitda"] / df["ingresos"].replace(0, 1) * 100).round(1)
    df["margen_bruto"]    = ((df["ingresos"] - df["costos"]) / df["ingresos"].replace(0, 1) * 100).round(1)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["mes"], y=df["ingresos"],  name="Ingresos",   marker_color="#00529B"))
    fig.add_trace(go.Bar(x=df["mes"], y=df["costos"],    name="Costos Var", marker_color="#FFA000"))
    fig.add_trace(go.Bar(x=df["mes"], y=df["gastos"],    name="Gastos Op",  marker_color="#E53935"))
    fig.add_trace(go.Scatter(x=df["mes"], y=df["ebitda"], name="EBITDA",
                             mode="lines+markers", line=dict(color="#43A047", width=3)))
    fig.update_layout(barmode="stack", height=420,
                      title="Composición mensual: Ingresos, Costos y EBITDA",
                      legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df[["mes", "ingresos", "costos", "gastos", "ebitda", "margen_ebitda", "margen_bruto"]]
          .rename(columns={
              "mes": "Mes", "ingresos": "Ingresos ($)", "costos": "Costos Var ($)",
              "gastos": "Gastos Op ($)", "ebitda": "EBITDA ($)",
              "margen_ebitda": "Margen EBITDA %", "margen_bruto": "Margen Bruto %",
          }),
        use_container_width=True, hide_index=True,
    )


def modulo_clientes():
    st.markdown('<p class="seccion-titulo">👥 Análisis de Clientes - Pareto 80/20</p>', unsafe_allow_html=True)
    df = top_clientes(f_desde, f_hasta)
    if df.empty:
        st.info("Sin datos de clientes.")
        return

    df["margen_acum"]     = df["margen"].cumsum()
    df["margen_acum_pct"] = (df["margen_acum"] / df["margen"].sum() * 100).round(1)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df.head(20), x="nombre_cliente", y="margen",
                     title="Top 20 - Margen Bruto por Cliente",
                     color="margen_pct", color_continuous_scale="Blues",
                     labels={"nombre_cliente": "Cliente", "margen": "Margen ($)"})
        fig.update_layout(xaxis_tickangle=-35, height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df.head(20)["nombre_cliente"], y=df.head(20)["ingresos"],
            name="Ingresos", marker_color="#00529B"))
        fig2.add_trace(go.Scatter(
            x=df.head(20)["nombre_cliente"],
            y=df.head(20)["margen_acum_pct"],
            name="% Acumulado", mode="lines+markers",
            yaxis="y2", line=dict(color="#E53935")))
        fig2.update_layout(
            title="Curva de Pareto",
            yaxis2=dict(title="%", overlaying="y", side="right", range=[0, 110]),
            height=380, xaxis_tickangle=-35,
            shapes=[dict(type="line", y0=80, y1=80, x0=-0.5,
                         x1=len(df.head(20))-0.5, yref="y2",
                         line=dict(color="#FFA000", dash="dash", width=2))])
        st.plotly_chart(fig2, use_container_width=True)

    # Insight pareto
    pareto_80 = df[df["margen_acum_pct"] <= 80.0]
    st.info(f"🎯 **Regla 80/20:** {len(pareto_80)} de {len(df)} clientes generan el 80% del margen.")

    # Tabla paginada
    st.markdown("### Detalle de clientes")
    pag = st.number_input("Página", min_value=1, value=1, step=1, key="pag_cli")
    ini, fin = (pag - 1) * registros_pagina, pag * registros_pagina
    st.dataframe(df.iloc[ini:fin], use_container_width=True, hide_index=True)
    st.caption(f"Mostrando {ini+1}–{min(fin, len(df))} de {len(df)} clientes")


def modulo_productos():
    st.markdown('<p class="seccion-titulo">📦 Análisis de Productos</p>', unsafe_allow_html=True)
    df = top_productos(f_desde, f_hasta)
    if df.empty:
        st.info("Sin datos de productos.")
        return

    col1, col2 = st.columns(2)
    with col1:
        fig = px.treemap(
            df.head(20), path=["nombre_producto"], values="ingresos",
            color="margen_pct", color_continuous_scale="Blues",
            title="Mapa de calor - Ingresos por Producto")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.scatter(
            df, x="ingresos", y="margen_pct", size="margen",
            hover_name="nombre_producto", title="Precio vs Margen",
            color="margen_pct", color_continuous_scale="RdYlGn",
            labels={"ingresos": "Ingresos ($)", "margen_pct": "Margen %"})
        st.plotly_chart(fig2, use_container_width=True)

    pag = st.number_input("Página", min_value=1, value=1, step=1, key="pag_prod")
    ini, fin = (pag - 1) * registros_pagina, pag * registros_pagina
    st.dataframe(df.iloc[ini:fin], use_container_width=True, hide_index=True)


def modulo_tendencias():
    st.markdown('<p class="seccion-titulo">📈 Tendencias y Estacionalidad</p>', unsafe_allow_html=True)
    df = ventas_por_mes(f_desde, f_hasta)
    if df.empty:
        st.info("Sin datos.")
        return

    df["margen"] = df["ingresos"] - df["costos"]
    df["margen_pct"] = (df["margen"] / df["ingresos"].replace(0, 1) * 100).round(1)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(df, x="mes", y=["ingresos", "costos", "margen"],
                      title="Evolución mensual",
                      labels={"value": "$", "variable": "Métrica", "mes": "Mes"})
        fig.update_layout(height=360)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = go.Figure(go.Bar(
            x=df["mes"], y=df["margen_pct"],
            marker_color=["#43A047" if v >= 20 else "#FFA000" if v >= 10 else "#E53935"
                          for v in df["margen_pct"]],
            text=[f"{v:.1f}%" for v in df["margen_pct"]],
            textposition="outside"))
        fig2.add_hline(y=20, line_dash="dash", line_color="#43A047",
                       annotation_text="Meta 20%")
        fig2.update_layout(title="Margen Bruto % por mes", height=360)
        st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(df, use_container_width=True, hide_index=True)


def _boton_descarga_pdf(ruta_pdf: Path, label: str = "⬇️ Descargar PDF") -> None:
    """Renderiza un botón de descarga inline para un PDF ya generado."""
    with open(ruta_pdf, "rb") as f:
        st.download_button(
            label=label,
            data=f,
            file_name=ruta_pdf.name,
            mime="application/pdf",
            use_container_width=True,
        )


def modulo_reportes():
    st.markdown('<p class="seccion-titulo">📄 Generación de Reportes PDF</p>', unsafe_allow_html=True)
    st.markdown("Genera los reportes y descárgalos directamente desde aquí.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💰 Reporte Financiero")
        st.markdown("Incluye EBITDA, clientes, productos y tendencia mensual.")
        if st.button("📄 Generar Reporte Financiero", use_container_width=True,
                     key="btn_fr"):
            with st.spinner("Generando PDF financiero..."):
                res = subprocess.run(
                    [sys.executable, str(ROOT / "reports" / "financial_report.py")],
                    capture_output=True, text=True, cwd=str(ROOT)
                )
            if res.returncode == 0:
                st.success("✅ Reporte financiero generado")
                output_dir = ROOT / "reports" / "output"
                pdfs = sorted(output_dir.glob("*fr.pdf"),
                              key=lambda x: x.stat().st_mtime)
                if pdfs:
                    ultimo = pdfs[-1]
                    st.info(f"📁 {ultimo.name}")
                    _boton_descarga_pdf(ultimo, "⬇️ Descargar Reporte Financiero")
            else:
                # Mostrar solo las últimas líneas del error para no llenar la pantalla
                stderr = res.stderr.strip()
                lineas_error = stderr.split("\n")
                mensaje = "\n".join(lineas_error[-5:]) if len(lineas_error) > 5 else stderr
                st.error(f"❌ Error generando PDF:\n```\n{mensaje}\n```")

    with col2:
        st.subheader("🤖 Reporte Machine Learning")
        st.markdown("Incluye modelo OLS, coeficientes y estadísticos.")
        if st.button("🤖 Generar Reporte ML", use_container_width=True,
                     key="btn_ml"):
            with st.spinner("Entrenando modelo y generando PDF..."):
                res = subprocess.run(
                    [sys.executable, str(ROOT / "analytics" / "regression_model.py")],
                    capture_output=True, text=True, cwd=str(ROOT)
                )
            if res.returncode == 0:
                st.success("✅ Reporte ML generado")
                output_dir = ROOT / "reports" / "output"
                pdfs = sorted(output_dir.glob("*ml.pdf"),
                              key=lambda x: x.stat().st_mtime)
                if pdfs:
                    ultimo = pdfs[-1]
                    st.info(f"📁 {ultimo.name}")
                    _boton_descarga_pdf(ultimo, "⬇️ Descargar Reporte ML")
            else:
                stderr = res.stderr.strip()
                lineas_error = stderr.split("\n")
                mensaje = "\n".join(lineas_error[-5:]) if len(lineas_error) > 5 else stderr
                st.error(f"❌ Error generando PDF:\n```\n{mensaje}\n```")

    # ── Listado descargable de todos los reportes existentes ──
    output_dir = ROOT / "reports" / "output"
    pdfs = sorted(output_dir.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True)
    if pdfs:
        st.markdown("---")
        st.markdown("### 📂 Reportes generados - Descarga directa")
        for p in pdfs[:10]:
            ts   = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            tipo = "📊 Financiero" if "fr" in p.name else "🤖 ML"
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.markdown(f"**{tipo}** &nbsp; `{p.name}` &nbsp; - &nbsp; {ts}")
            with col_btn:
                with open(p, "rb") as f:
                    st.download_button(
                        label="⬇️ Descargar",
                        data=f,
                        file_name=p.name,
                        mime="application/pdf",
                        key=f"dl_{p.name}",
                        use_container_width=True,
                    )


def modulo_ingesta():
    st.markdown('<p class="seccion-titulo">🔄 Ingesta de Datos</p>', unsafe_allow_html=True)
    st.markdown("Sube tus archivos CSV para cargar datos en MySQL.")

    tab_v, tab_g = st.tabs(["📈 Ventas", "💸 Gastos"])

    with tab_v:
        st.markdown("**Columnas requeridas:** fecha, cliente, producto, cantidad, precio_unitario, costo_unitario")
        archivo_v = st.file_uploader("Subir ventas.csv", type=["csv", "xlsx"], key="up_v")
        if archivo_v and st.button("🚀 Cargar ventas", use_container_width=True):
            ruta_tmp = ROOT / "assets" / "ventas_upload.csv"
            with open(ruta_tmp, "wb") as f:
                f.write(archivo_v.getvalue())
            with st.spinner("Procesando..."):
                res = subprocess.run(
                    [sys.executable, "-c",
                     f"import sys; sys.path.insert(0,'{ROOT}'); "
                     "from data_processing.ingestor_universal import IngestorUniversal; "
                     "from database_loading.load_to_mysql import cargar_ventas_a_mysql; "
                     f"df=IngestorUniversal('ventas').ingestar('{ruta_tmp}'); "
                     "print(cargar_ventas_a_mysql(df) if df is not None else 0)"],
                    capture_output=True, text=True, cwd=str(ROOT)
                )
            if res.returncode == 0:
                st.success(f"✅ Ventas cargadas. Filas: {res.stdout.strip()}")
                st.cache_data.clear()
            else:
                st.error(f"❌ {res.stderr[:400]}")

    with tab_g:
        st.markdown("**Columnas requeridas:** fecha, descripcion, categoria_gasto, tipo_gasto, monto")
        archivo_g = st.file_uploader("Subir gastos.csv", type=["csv", "xlsx"], key="up_g")
        if archivo_g and st.button("🚀 Cargar gastos", use_container_width=True):
            ruta_tmp = ROOT / "assets" / "gastos_upload.csv"
            with open(ruta_tmp, "wb") as f:
                f.write(archivo_g.getvalue())
            with st.spinner("Procesando..."):
                res = subprocess.run(
                    [sys.executable, "-c",
                     f"import sys; sys.path.insert(0,'{ROOT}'); "
                     "from data_processing.ingestor_universal import IngestorUniversal; "
                     "from database_loading.load_to_mysql import cargar_gastos_a_mysql; "
                     f"df=IngestorUniversal('gastos').ingestar('{ruta_tmp}'); "
                     "print(cargar_gastos_a_mysql(df) if df is not None else 0)"],
                    capture_output=True, text=True, cwd=str(ROOT)
                )
            if res.returncode == 0:
                st.success(f"✅ Gastos cargados. Filas: {res.stdout.strip()}")
                st.cache_data.clear()
            else:
                st.error(f"❌ {res.stderr[:400]}")

    # Plantillas de descarga
    st.markdown("---")
    st.markdown("### 📋 Plantillas de ejemplo")
    col1, col2 = st.columns(2)
    with col1:
        plantilla_v = "fecha,cliente,producto,cantidad,precio_unitario,costo_unitario,estado\n2026-01-15,Empresa ABC,Servicio X,2,1500000,300000,Cobrado\n"
        st.download_button("⬇️ Plantilla ventas.csv", plantilla_v, "plantilla_ventas.csv", "text/csv")
    with col2:
        plantilla_g = "fecha,descripcion,categoria_gasto,tipo_gasto,monto\n2026-01-01,Arriendo oficina,Fijo,Operativo,1200000\n"
        st.download_button("⬇️ Plantilla gastos.csv", plantilla_g, "plantilla_gastos.csv", "text/csv")


# ═════════════════════════════════════════════════════════════════════════════
# ROUTER DE MÓDULOS
# ═════════════════════════════════════════════════════════════════════════════

if not conexion_ok() and modulo not in ["📄 Reportes"]:
    st.error("⚠️ No hay conexión a MySQL. Inicie XAMPP y verifique el archivo `.env`.")
    st.stop()

if modulo == "🏠 Inicio":
    modulo_inicio()
elif modulo == "💰 Financiero":
    modulo_financiero()
elif modulo == "👥 Clientes":
    modulo_clientes()
elif modulo == "📦 Productos":
    modulo_productos()
elif modulo == "📈 Tendencias":
    modulo_tendencias()
elif modulo == "📄 Reportes":
    modulo_reportes()
elif modulo == "🔄 Ingesta":
    modulo_ingesta()
