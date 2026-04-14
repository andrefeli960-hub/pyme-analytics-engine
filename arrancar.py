"""
arrancar.py - Lanzador principal - Pyme Analytics Engine v2.0
==============================================================
Reemplaza el .bat para evitar problemas de permisos en PowerShell.

Uso:
    python arrancar.py              → ETL + análisis + dashboard
    python arrancar.py --solo-etl   → Solo carga datos
    python arrancar.py --solo-dash  → Solo dashboard Streamlit
    python arrancar.py --analisis   → Análisis + PDFs
"""

import subprocess
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).parent


def verificar_entorno() -> bool:
    try:
        import pandas
        import mysql.connector
        import streamlit
        import dotenv
        import fpdf
        import statsmodels
        import joblib
        print("✅ Entorno verificado correctamente.")
        return True
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        print("💡 Ejecuta: pip install -r requirements.txt")
        return False


def ejecutar_etl() -> bool:
    print("\n🔄 INICIANDO PIPELINE ETL...")
    res = subprocess.run([sys.executable, str(ROOT / "run.py")], capture_output=False)
    if res.returncode == 0:
        print("✅ ETL finalizado correctamente.\n")
    else:
        print("❌ ETL terminó con errores. Revisa logs/app.log\n")
    return res.returncode == 0


def ejecutar_analisis() -> None:
    print("\n📊 GENERANDO ANÁLISIS Y REPORTES PDF...")
    scripts = [
        ROOT / "analytics" / "regression_model.py",
        ROOT / "reports"   / "financial_report.py",
    ]
    for script in scripts:
        if script.exists():
            res = subprocess.run([sys.executable, str(script)])
            if res.returncode != 0:
                print(f"⚠️  {script.name} terminó con advertencias.")
        else:
            print(f"⚠️  No encontrado: {script.name}")


def abrir_dashboard() -> None:
    dashboard = ROOT / "dashboard" / "app.py"
    if not dashboard.exists():
        dashboard = ROOT / "app.py"

    if dashboard.exists():
        print("\n🚀 ABRIENDO DASHBOARD en http://localhost:8501 ...")
        print("   Presiona Ctrl+C para detener.\n")
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(dashboard),
            "--server.headless", "false",
            "--browser.gatherUsageStats", "false",
        ])
    else:
        print("❌ Dashboard no encontrado (dashboard/app.py)")


def main():
    parser = argparse.ArgumentParser(description="Pyme Analytics Engine - Lanzador")
    parser.add_argument("--solo-etl",  action="store_true")
    parser.add_argument("--solo-dash", action="store_true")
    parser.add_argument("--analisis",  action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("   PYME ANALYTICS ENGINE v2.0")
    print("   Sistema de Inteligencia de Negocios para Pymes")
    print("=" * 60)

    if not verificar_entorno():
        sys.exit(1)

    if args.solo_etl:
        ejecutar_etl()
    elif args.solo_dash:
        abrir_dashboard()
    elif args.analisis:
        ejecutar_analisis()
    else:
        etl_ok = ejecutar_etl()
        if etl_ok:
            ejecutar_analisis()
        abrir_dashboard()


if __name__ == "__main__":
    main()
