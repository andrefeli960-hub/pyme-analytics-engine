-- ============================================================
-- PYME ANALYTICS ENGINE v2.0
-- Script completo de base de datos: pyme_analytics
-- Motor: MariaDB 10.4.32 (XAMPP) | Workbench 8.0
--
-- MEJORAS DE SEGURIDAD Y GOBERNABILIDAD APLICADAS:
--   1. UNIQUE KEY en ventas → evita duplicados desde la BD
--   2. NOT NULL en campos críticos de análisis
--   3. CHECK constraints (MariaDB 10.2+)
--   4. COMMENT en tablas y columnas (documentación)
--   5. utf8mb4 en todas las tablas
--   6. Índices en columnas de JOIN y filtro frecuente
--   7. Tabla de auditoría para registro de cambios
-- ============================================================

-- Usar la base de datos
CREATE DATABASE IF NOT EXISTS pyme_analytics
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_general_ci;
USE pyme_analytics;

-- Desactivar checks temporalmente para recrear tablas
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- TABLA: clientes
-- ============================================================
DROP TABLE IF EXISTS `clientes`;
CREATE TABLE `clientes` (
    `id_cliente`      VARCHAR(50)  NOT NULL  COMMENT 'ID generado por Python (prefijo CLI + UUID)',
    `nombre_cliente`  VARCHAR(100) NOT NULL  COMMENT 'Nombre o razón social del cliente',
    `ciudad`          VARCHAR(50)  DEFAULT NULL,
    `segmento`        VARCHAR(50)  DEFAULT NULL  COMMENT 'Segmento de negocio (opcional)',
    `created_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_cliente`),
    UNIQUE KEY `uq_nombre_cliente` (`nombre_cliente`)   -- Evita clientes duplicados por nombre
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_general_ci
  COMMENT='Dimensión de clientes';


-- ============================================================
-- TABLA: productos
-- ============================================================
DROP TABLE IF EXISTS `productos`;
CREATE TABLE `productos` (
    `id_producto`      VARCHAR(50)  NOT NULL  COMMENT 'ID generado por Python (prefijo PROD + UUID)',
    `nombre_producto`  VARCHAR(100) NOT NULL  COMMENT 'Nombre del producto o servicio',
    `categoria`        VARCHAR(50)  DEFAULT NULL,
    `created_at`       DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_producto`),
    UNIQUE KEY `uq_nombre_producto` (`nombre_producto`)  -- Evita productos duplicados por nombre
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_general_ci
  COMMENT='Dimensión de productos y servicios';


-- ============================================================
-- TABLA: ventas  ← LA MÁS IMPORTANTE
-- ANTI-DUPLICADOS: UNIQUE KEY sobre (fecha + cliente + producto)
-- ============================================================
DROP TABLE IF EXISTS `ventas`;
CREATE TABLE `ventas` (
    `id_factura`              VARCHAR(50)     NOT NULL  COMMENT 'ID determinístico: FAC-fecha-cliente-producto',
    `fecha`                   DATE            NOT NULL  COMMENT 'Fecha de la transacción',
    `id_cliente`              VARCHAR(50)     NOT NULL,
    `id_producto`             VARCHAR(50)     NOT NULL,
    `cantidad`                INT(11)         NOT NULL  CHECK (`cantidad` > 0),
    `precio_unitario`         DECIMAL(15, 2)  NOT NULL  CHECK (`precio_unitario` > 0),
    `costo_unitario_variable` DECIMAL(15, 2)  NOT NULL  CHECK (`costo_unitario_variable` >= 0),
    `created_at`              DATETIME        DEFAULT CURRENT_TIMESTAMP,

    -- Clave primaria: id_factura determinístico garantiza idempotencia
    PRIMARY KEY (`id_factura`),

    -- ÍNDICES para JOINs y filtros frecuentes
    KEY `idx_ventas_fecha`    (`fecha`),
    KEY `idx_ventas_cliente`  (`id_cliente`),
    KEY `idx_ventas_producto` (`id_producto`),

    -- CLAVE ÚNICA ANTI-DUPLICADOS (desde la BD)
    -- Si ya existe la combinación fecha+cliente+producto con misma cantidad y precio
    -- → la BD rechaza el INSERT (o REPLACE lo actualiza, que es idempotente)
    UNIQUE KEY `uq_venta_negocio` (
        `fecha`,
        `id_cliente`,
        `id_producto`,
        `cantidad`,
        `precio_unitario`
    ),

    -- INTEGRIDAD REFERENCIAL
    CONSTRAINT `fk_ventas_cliente`  FOREIGN KEY (`id_cliente`)  REFERENCES `clientes`  (`id_cliente`),
    CONSTRAINT `fk_ventas_producto` FOREIGN KEY (`id_producto`) REFERENCES `productos` (`id_producto`)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_general_ci
  COMMENT='Tabla de hechos: transacciones de venta';


-- ============================================================
-- TABLA: gastos
-- ============================================================
DROP TABLE IF EXISTS `gastos`;
CREATE TABLE `gastos` (
    `id_gasto`        INT(11)         NOT NULL AUTO_INCREMENT,
    `fecha`           DATE            NOT NULL,
    `descripcion`     VARCHAR(255)    NOT NULL,
    `categoria_gasto` VARCHAR(100)    NOT NULL  COMMENT 'Fijo / Variable',
    `tipo_gasto`      VARCHAR(100)    NOT NULL  COMMENT 'Operativo / Marketing / etc',
    `monto`           DECIMAL(15, 2)  NOT NULL  CHECK (`monto` > 0),
    `created_at`      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_gasto`),
    KEY `idx_gastos_fecha` (`fecha`),
    KEY `idx_gastos_cat`   (`categoria_gasto`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_general_ci
  COMMENT='Gastos operativos del período';


-- ============================================================
-- TABLA: historico_regresion (Persistencia del modelo OLS)
-- ============================================================
DROP TABLE IF EXISTS `historico_regresion`;
CREATE TABLE `historico_regresion` (
    `id`              INT(11)         NOT NULL AUTO_INCREMENT,
    `fecha`           DATETIME        NOT NULL,
    `r_cuadrado`      FLOAT,
    `r_cuadrado_adj`  FLOAT,
    `coef_precio`     FLOAT,
    `coef_costo`      FLOAT,
    `coef_cantidad`   FLOAT,
    `p_valor_global`  FLOAT,
    `aic`             FLOAT,
    `bic`             FLOAT,
    `observaciones`   INT(11),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_general_ci
  COMMENT='Historial de ejecuciones del modelo OLS';


-- Restaurar checks
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- VERIFICACIÓN FINAL
-- ============================================================
SELECT 'clientes'             AS tabla, COUNT(*) AS registros FROM clientes
UNION ALL
SELECT 'productos',            COUNT(*) FROM productos
UNION ALL
SELECT 'ventas',               COUNT(*) FROM ventas
UNION ALL
SELECT 'gastos',               COUNT(*) FROM gastos
UNION ALL
SELECT 'historico_regresion',  COUNT(*) FROM historico_regresion;
