# PYME ANALYTICS ENGINE - Módulo BI v2.0

> **Sistema de Automatización de Inteligencia de Negocios para Pymes y Contadores**
> Autor: Andrés - Economista & Analytics Engineer
> País: Colombia
> Año de creación: 2026
> Estado del registro: **Pendiente ante DNDA** (Dirección Nacional de Derecho de Autor)

---

## 1. DESCRIPCIÓN GENERAL

**Pyme Analytics Engine** es una aplicación *Plug & Play* de analítica financiera y comercial diseñada para pequeñas y medianas empresas (Pymes) y contadores en Colombia. El sistema transforma archivos planos de ventas y gastos en métricas financieras accionables, sin que el usuario final requiera conocimientos de programación o bases de datos.

### Problema que resuelve

La mayoría de las Pymes colombianas no tienen acceso a herramientas de Business Intelligence porque son costosas, técnicamente complejas o requieren infraestructura de nube. Esta aplicación democratiza el análisis financiero entregando en segundos indicadores como EBITDA, Pareto de clientes y estacionalidad, a partir de un archivo CSV.

### Propuesta de valor

- **Plug & Play**: el usuario sube su archivo CSV y recibe sus KPIs automáticamente
- **Sin dependencias de nube**: corre localmente sobre XAMPP
- **Transparente**: todo el código es auditable y documentado
- **Ético**: cumple con la Ley 1581 de 2012 (Habeas Data Colombia)

---

## 2. ARQUITECTURA DEL SISTEMA

```
┌─────────────────────────────────────────────────────────────┐
│                  PYME ANALYTICS ENGINE v2.0                 │
├─────────────────────────────────────────────────────────────┤
│  CAPA 1: INGESTA                                            │
│  CSV / Excel / JSON / TXT-ERP  →  IngestorUniversal        │
│  Anonimización SHA-256 (Habeas Data)                        │
├─────────────────────────────────────────────────────────────┤
│  CAPA 2: ETL Y CALIDAD DE DATOS                             │
│  clean_data.py → EDA automático (normalidad, outliers,      │
│  correlación Pearson, estadísticos descriptivos)            │
├─────────────────────────────────────────────────────────────┤
│  CAPA 3: ALMACENAMIENTO                                     │
│  MySQL / MariaDB (XAMPP) → pyme_analytics                   │
│  Tablas: clientes, productos, ventas, gastos,               │
│  historico_regresion                                        │
├─────────────────────────────────────────────────────────────┤
│  CAPA 4: ANALÍTICA FINANCIERA                               │
│  EBITDA · Pareto 80/20 · Estacionalidad · Tickets          │
│  Modelo OLS (statsmodels) + persistencia (joblib)          │
├─────────────────────────────────────────────────────────────┤
│  CAPA 5: VISUALIZACIÓN Y REPORTES                           │
│  Dashboard Streamlit (7 módulos)                            │
│  PDFs automáticos: financiero (fr) + ML (ml)               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. ESTRUCTURA DEL PROYECTO

```
pyme_final/
│
├── run.py                          # Orquestador principal CLI
├── arrancar.py                     # Lanzador interactivo (reemplaza .bat)
├── requirements.txt                # Dependencias Python
├── .env.example                    # Plantilla de variables de entorno
├── .gitignore                      # Exclusiones de repositorio
│
├── config/                         # Configuración centralizada
│   ├── __init__.py
│   ├── logger_config.py            # Sistema de logging (ÚNICO)
│   └── db_config.py                # Pool de conexiones MySQL
│
├── data_processing/                # Capa ETL
│   ├── __init__.py
│   ├── clean_data.py               # Limpieza + EDA automático
│   └── ingestor_universal.py       # Multi-formato + anonimización
│
├── database_loading/               # Carga a MySQL
│   ├── __init__.py
│   └── load_to_mysql.py            # REPLACE INTO anti-duplicados
│
├── analytics/                      # Módulos analíticos
│   ├── __init__.py
│   ├── ebitda.py                   # KPIs financieros completos
│   ├── regression_model.py         # Modelo OLS econométrico
│   └── modelos_guardados/          # Modelos serializados (.pkl)
│
├── reports/                        # Generación de reportes PDF
│   ├── __init__.py
│   ├── financial_report.py         # PDF financiero (archiv0XXXXXfr.pdf)
│   └── output/                     # PDFs generados
│
├── dashboard/                      # Interfaz web Streamlit
│   ├── __init__.py
│   └── app.py                      # Dashboard completo (7 módulos)
│
├── assets/                         # Datos y scripts SQL
│   ├── ventas.csv                  # Ejemplo de datos de ventas
│   ├── gastos.csv                  # Ejemplo de datos de gastos
│   └── pyme_analytics_schema.sql   # Esquema BD con constraints
│
└── logs/                           # Logs de operaciones
    ├── app.log                     # Log principal (rotativo)
    ├── errores.log                 # Solo errores
    └── ingesta.log                 # Trazabilidad ETL
```

---

## 4. TECNOLOGÍAS UTILIZADAS

| Componente | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.10+ |
| Base de datos | MySQL / MariaDB (XAMPP) | 10.4+ |
| Administración BD | MySQL Workbench | 8.0 |
| Dashboard web | Streamlit | 1.30+ |
| Procesamiento datos | Pandas | 2.0+ |
| Estadística | SciPy / Statsmodels | 1.10+ / 0.14+ |
| ML / Persistencia | Joblib | 1.3+ |
| Visualización | Plotly | 5.15+ |
| Reportes PDF | fpdf2 | 2.7+ |
| Seguridad | python-dotenv | 1.0+ |

---

## 5. MÓDULOS IMPLEMENTADOS (ESTADO ACTUAL)

### 5.1 ETL - Extracción, Transformación y Carga ✅ COMPLETO

| Sub-módulo | Estado | Descripción |
|---|---|---|
| Lectura CSV | ✅ Completo | Auto-detección encoding (UTF-8 / Latin-1 / CP1252) |
| Lectura Excel | ✅ Completo | Selección automática de hoja más relevante |
| Lectura JSON | ✅ Completo | Arrays y NDJSON |
| Lectura TXT-ERP | ✅ Completo | Separadores variables (TAB, ;, \|) |
| Mapa de sinónimos | ✅ Completo | Compatibilidad ERP/SAP (60+ sinónimos) |
| Anonimización | ✅ Completo | SHA-256, Ley 1581/2012 y GDPR |
| Validación columnas | ✅ Completo | Falla explícita si faltan columnas obligatorias |
| Reglas de negocio | ✅ Completo | Precios > 0, cantidades > 0, costos >= 0 |
| Anti-duplicados BD | ✅ Completo | UNIQUE KEY en ventas + REPLACE INTO |

### 5.2 Análisis Exploratorio (EDA) ✅ COMPLETO

| Análisis | Estado | Método |
|---|---|---|
| Estadísticos descriptivos | ✅ Completo | mean, std, min, max, quartiles |
| Detección de outliers | ✅ Completo | Método IQR (Q1 - 1.5×IQR, Q3 + 1.5×IQR) |
| Test de normalidad | ✅ Completo | Shapiro-Wilk (n≤5000) / Kolmogorov-Smirnov (n>5000) |
| Correlación | ✅ Completo | Pearson con alerta de multicolinealidad (r≥0.8) |

### 5.3 Módulo Financiero ✅ COMPLETO

| KPI | Fórmula | Estado |
|---|---|---|
| EBITDA | Ingresos - Costos Variables - Gastos Operativos | ✅ |
| Margen EBITDA % | EBITDA / Ingresos × 100 | ✅ |
| Utilidad Bruta | Ingresos - Costos Variables | ✅ |
| Margen Bruto % | Utilidad Bruta / Ingresos × 100 | ✅ |
| Rentabilidad por cliente | Margen bruto agrupado + Pareto acumulado | ✅ |
| Rentabilidad por producto | Margen bruto + % por producto | ✅ |
| Estacionalidad mensual | Ingresos y margen por mes/año | ✅ |
| Ticket promedio | Ingresos totales / Nº transacciones | ✅ |
| Análisis Pareto 80/20 | Participación acumulada de margen | ✅ |

### 5.4 Modelo Econométrico OLS ✅ COMPLETO

| Componente | Estado | Descripción |
|---|---|---|
| Regresión OLS | ✅ Completo | statsmodels: Y=venta_total, X=precio, costo, cantidad |
| Diagnósticos | ✅ Completo | R², R² ajustado, F-statistic, p-valores, AIC, BIC |
| Tabla de coeficientes | ✅ Completo | Con IC 95% y nivel de significancia (*, **, ***) |
| Persistencia del modelo | ✅ Completo | joblib (.pkl) - no re-entrena si n obs no cambia |
| Historial en BD | ✅ Completo | Tabla historico_regresion en MySQL |
| Reporte PDF ML | ✅ Completo | archivo00001ml.pdf, archivo00002ml.pdf, ... |

### 5.5 Reportes PDF ✅ COMPLETO

| Reporte | Estado | Nomenclatura |
|---|---|---|
| Reporte Financiero | ✅ Completo | archivo00001fr.pdf |
| Reporte ML | ✅ Completo | archivo00001ml.pdf |
| Descarga desde dashboard | ✅ Completo | Botón inline en Streamlit |

### 5.6 Dashboard Streamlit ✅ COMPLETO

| Módulo | Estado | Contenido |
|---|---|---|
| 🏠 Inicio | ✅ Completo | KPIs ejecutivos, alerta EBITDA, evolución mensual, donut |
| 💰 Financiero | ✅ Completo | EBITDA mensual con gastos, gráfico apilado |
| 👥 Clientes | ✅ Completo | Pareto 80/20, tabla paginada |
| 📦 Productos | ✅ Completo | Treemap de ingresos, scatter precio/margen |
| 📈 Tendencias | ✅ Completo | Evolución mensual, semáforo de márgenes |
| 📄 Reportes | ✅ Completo | Generación + descarga directa de PDFs |
| 🔄 Ingesta | ✅ Completo | Upload CSV/Excel + plantillas descargables |

### 5.7 Infraestructura y Seguridad ✅ COMPLETO

| Componente | Estado |
|---|---|
| Variables de entorno (.env) | ✅ Completo |
| Pool de conexiones MySQL | ✅ Completo |
| Logging rotativo (app.log, errores.log, ingesta.log) | ✅ Completo |
| .gitignore (protección de credenciales) | ✅ Completo |
| UNIQUE KEY anti-duplicados en BD | ✅ Completo |
| Validación de integridad económica | ✅ Completo |

---

## 6. PORCENTAJE DE AVANCE GLOBAL

```
Módulo                          Avance
──────────────────────────────────────────
ETL Multi-formato               ████████████ 100%
EDA Automático                  ████████████ 100%
Módulo Financiero (KPIs)        ████████████ 100%
Modelo OLS Econométrico         ████████████ 100%
Reportes PDF                    ████████████ 100%
Dashboard Streamlit             ████████████ 100%
Infraestructura/Seguridad       ████████████ 100%
Pruebas Unitarias               ███████░░░░░  60%
Integración Power BI            ██░░░░░░░░░░  20%
Pruebas de usuario (UAT)        ░░░░░░░░░░░░   0% ← SIGUIENTE FASE
Documentación técnica (DNDA)    █████████░░░  85%
Registro DNDA                   ░░░░░░░░░░░░   0% ← PENDIENTE

AVANCE GLOBAL ESTIMADO:  ████████████  ~87%
```

---

## 7. PENDIENTE - PRÓXIMAS FASES

### Fase de pruebas (inmediata)

- [ ] Pruebas unitarias completas con `pytest` (actualmente ~60%)
- [ ] Pruebas de carga con datasets de +1,000 filas
- [ ] Prueba de integración end-to-end (CSV → BD → Dashboard)
- [ ] Pruebas de usuario con contadores reales (UAT)

### Integraciones futuras

- [ ] Conexión Power BI (actualmente 20%)
- [ ] API REST con FastAPI para consumo externo
- [ ] Soporte multi-empresa (multitenancy)
- [ ] Exportación a Google Sheets

### Registro DNDA

- [ ] Consolidar código fuente en ZIP firmado
- [ ] Preparar formulario de registro ante DNDA Colombia
- [ ] Registro como obra literaria (software) - Ley 23/1982

---

## 8. INSTALACIÓN Y USO

### Prerrequisitos

- Python 3.10 o superior
- XAMPP con MySQL en estado RUNNING
- MySQL Workbench 8.0
- Base de datos `pyme_analytics` creada

### Pasos de instalación

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar credenciales
copy .env.example .env
# Editar .env con sus datos de MySQL

# 3. Crear la base de datos
# En MySQL Workbench ejecutar: assets/pyme_analytics_schema.sql

# 4. Verificar conexión
python run.py --test-conexion
```

### Uso diario

```bash
# Pipeline completo (ETL + análisis + PDFs)
python run.py

# Solo cargar datos
python run.py --solo-etl

# Solo análisis y reportes
python run.py --solo-analisis

# Abrir dashboard web
python arrancar.py --solo-dash
# → http://localhost:8501
```

### Formato de archivos de entrada

**ventas.csv** - columnas obligatorias:

| Columna | Tipo | Ejemplo |
|---|---|---|
| fecha | YYYY-MM-DD | 2026-03-25 |
| cliente | texto | Empresa ABC |
| producto | texto | Consultoría BI |
| cantidad | entero | 1 |
| precio_unitario | decimal | 3500000 |
| costo_unitario | decimal | 500000 |

**gastos.csv** - columnas obligatorias:

| Columna | Tipo | Ejemplo |
|---|---|---|
| fecha | YYYY-MM-DD | 2026-03-25 |
| descripcion | texto | Arriendo oficina |
| categoria_gasto | texto | Fijo |
| tipo_gasto | texto | Operativo |
| monto | decimal | 1200000 |

---

## 9. FÓRMULAS Y METODOLOGÍA

### EBITDA
```
EBITDA = Σ(cantidad × precio_unitario)
       - Σ(cantidad × costo_unitario_variable)
       - Σ(gastos operativos)
```

### Margen EBITDA %
```
Margen EBITDA % = (EBITDA / Ingresos Totales) × 100
```

### Análisis Pareto 80/20
```
Margen_i % = Margen_i / Σ(Margen) × 100
Pareto_acumulado_i = Σ(Margen_j %) para j ≤ i
```

### Modelo OLS (Regresión por Mínimos Cuadrados)
```
venta_total = β₀ + β₁×precio_unitario
                 + β₂×costo_unitario_variable
                 + β₃×cantidad
                 + ε
```
*Estimado con statsmodels.OLS. Métricas: R², F-statistic, p-values, AIC, BIC.*

### Test de normalidad
- **Shapiro-Wilk** para n ≤ 5,000 observaciones (α = 0.05)
- **Kolmogorov-Smirnov** para n > 5,000 observaciones

### Detección de outliers (IQR)
```
Límite inferior = Q1 - 1.5 × IQR
Límite superior = Q3 + 1.5 × IQR
IQR = Q3 - Q1
```

---

## 10. SEGURIDAD Y ÉTICA DE DATOS

| Principio | Implementación |
|---|---|
| **Confidencialidad** | Credenciales en `.env`, nunca en código fuente |
| **Anonimización** | Hash SHA-256 en columnas sensibles (Ley 1581/2012) |
| **Integridad** | UNIQUE KEY en BD + validación de reglas de negocio |
| **Trazabilidad** | Logs rotativos con timestamp de cada operación |
| **Idempotencia** | El mismo CSV produce siempre el mismo resultado |
| **No manipulación** | Los datos no se alteran durante el análisis |
| **Principio de mínimo privilegio** | El pool de conexiones utiliza un usuario de bases de datos con permisos limitados
| (solo DML), evitando el uso de la cuenta root en producción |
---

## 11. HISTORIAL DE VERSIONES

| Versión | Fecha | Descripción |
|---|---|---|
| v0.1 | Mar 2026 | ETL básico CSV → MySQL |
| v0.5 | Mar 2026 | Control de duplicados + EDA básico |
| v1.0 | Mar 2026 | EBITDA + Pareto + OLS + PDF básico |
| v2.0 | Abr 2026 | Dashboard Streamlit completo + Ingestor Universal + PDFs descargables |

---

## 12. PROPIEDAD INTELECTUAL

Este software es una obra original de su autor. Todos los derechos reservados.

- **Autor**: Andrés (Colombia)
- **Tipo de obra**: Obra literaria - Programa de ordenador (software)
- **Marco legal**: Ley 23 de 1982 (Derecho de Autor Colombia), modificada por la Ley 44 de 1993
- **Registro**: Pendiente ante la **DNDA** (Dirección Nacional de Derecho de Autor)
- **Prohibición**: Queda prohibida la reproducción total o parcial, distribución, modificación o uso comercial sin autorización expresa del autor.

---

*Documento actualizado: Abril 2026*
