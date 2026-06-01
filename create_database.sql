-- Script para crear y poblar la base de datos local gyh_local.db
-- Compatible con la aplicación Flask en app.py
-- Fecha: 26 de mayo de 2025

-- Eliminar vistas y tablas si existen (para evitar conflictos)
DROP VIEW IF EXISTS vista_inventario;
DROP TABLE IF EXISTS etapas_productos;
DROP TABLE IF EXISTS etapas_lotes;
DROP TABLE IF EXISTS lotes;
DROP TABLE IF EXISTS movimientos_inventario;
DROP TABLE IF EXISTS productos;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS proveedores;
DROP TABLE IF EXISTS tipos_producto;
DROP TABLE IF EXISTS unidades_medida;
DROP TABLE IF EXISTS procesos_guardados;
DROP TABLE IF EXISTS etapas_prototipos;
DROP TABLE IF EXISTS historial_estados_prototipos;
DROP TABLE IF EXISTS prototipos;

-- Crear tabla unidades_medida
CREATE TABLE unidades_medida (
    id_unidad INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    abreviatura TEXT NOT NULL
);

-- Insertar datos en unidades_medida
INSERT INTO unidades_medida (id_unidad, nombre, abreviatura) VALUES
    (1, 'Gramos', 'g'),
    (2, 'Mililitros', 'ml'),
    (3, 'Kilogramos', 'kg'),
    (4, 'Litros', 'L');

-- Crear tabla tipos_producto
CREATE TABLE tipos_producto (
    id_tipo INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    descripcion TEXT
);

-- Insertar datos en tipos_producto
INSERT INTO tipos_producto (id_tipo, nombre, descripcion) VALUES
    (1, 'Colorantes y Pigmentos', 'Productos para teñir jeans'),
    (2, 'Agentes Auxiliares', 'Químicos para procesos de lavado y teñido'),
    (3, 'Productos para Lavado y Desgaste', 'Materiales para desgastar o lavar jeans'),
    (4, 'Sales', 'Sales químicas para procesos de fijación'),
    (5, 'Desinfectantes', 'Químicos para desinfección'),
    (6, 'Ácidos', 'Ácidos para procesos químicos');

-- Crear tabla proveedores
CREATE TABLE proveedores (
    id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    contacto TEXT,
    telefono TEXT,
    email TEXT
);

-- Insertar datos en proveedores
INSERT INTO proveedores (id_proveedor, nombre, contacto, telefono, email) VALUES
    (1, 'Proveedor ABC', 'Juan Pérez', '123456789', 'contacto@proveedorabc.com'),
    (2, 'Químicos S.A.', 'María López', '987654321', 'ventas@quimicos.com');

-- Crear tabla usuarios (modificada para incluir email y nuevos roles)
CREATE TABLE usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    contrasena TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('Administrador', 'Líder', 'Bodeguero')),
    email TEXT NOT NULL UNIQUE
);

-- Insertar datos en usuarios (ajustados con email y nuevos roles)
INSERT INTO usuarios (id_usuario, nombre, rol, email, contrasena) VALUES
    (1, 'Ana Gómez', 'Administrador', 'ana@tintoreria.com', 'admin123'),
    (2, 'Luis Martínez', 'Líder', 'luis@tintoreria.com', 'lider123'),
    (3, 'Carlos Rodríguez', 'Bodeguero', 'carlos@tintoreria.com', 'bodega123');

-- Crear tabla productos
CREATE TABLE productos (
    id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    id_tipo INTEGER,
    cantidad REAL NOT NULL,
    id_unidad INTEGER,
    stock_minimo REAL NOT NULL,
    stock_maximo REAL NOT NULL,
    fecha_ingreso TEXT DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP,
    lote TEXT,
    precio REAL DEFAULT 0.00,
    estado_verificacion TEXT DEFAULT 'Pendiente',
    id_proveedor INTEGER,
    es_toxico INTEGER DEFAULT 0,
    es_corrosivo INTEGER DEFAULT 0,
    es_inflamable INTEGER DEFAULT 0,
    FOREIGN KEY (id_tipo) REFERENCES tipos_producto(id_tipo) ON DELETE SET NULL,
    FOREIGN KEY (id_unidad) REFERENCES unidades_medida(id_unidad) ON DELETE SET NULL,
    FOREIGN KEY (id_proveedor) REFERENCES proveedores(id_proveedor) ON DELETE SET NULL
);

-- Insertar datos en productos (desde la consola de SQLite Cloud, eliminando duplicado id=24)
INSERT INTO productos (
    id_producto, nombre, id_tipo, cantidad, id_unidad, stock_minimo, stock_maximo,
    fecha_ingreso, fecha_actualizacion, lote, precio, estado_verificacion, id_proveedor,
    es_toxico, es_corrosivo, es_inflamable
) VALUES
    (1, 'Hipoclorito de sodio', 5, 580, 4, 100, 800, '2025-03-10 10:00:00', '2025-05-26 16:59:00', 'LOTE2025-001', 1500, 'Verificado', 1, 0, 1, 0),
    (2, 'Acido Salico', 6, 23, 3, 10, 100, '2025-03-10 10:00:00', '2025-05-23 09:21:05', 'LOTE2025-002', 1, 'Verificado', 2, 0, 1, 0),
    (3, 'Ácido Oxalico', 2, 23, 3, 5, 20, '2025-03-10 10:00:00', '2025-05-23 09:21:54', 'LOTE2025-003', 25, 'Verificado', 1, 0, 0, 0),
    (4, 'Acitex TR', 3, 18, 3, 5, 40, '2025-03-10 10:00:00', '2025-05-23 09:22:26', 'LOTE2025-004', 40, 'Verificado', 2, 0, 0, 0),
    (5, 'Antimigrante ABS', 2, 37, 3, 10, 60, '2025-03-10 10:00:00', '2025-05-23 09:23:32', 'LOTE2025-005', 20, 'Verificado', 1, 0, 0, 0),
    (6, 'Antipilling Luna', 2, 7, 3, 10, 50, '2025-03-10 10:00:00', '2025-05-23 09:24:07', 'LOTE2025-006', 15, 'Verificado', 2, 0, 0, 0),
    (7, 'Metabisulfito de Sodio', 1, 51.8, 3, 1, 100, '2025-05-23 14:24:53', '2025-05-23 14:24:53', '', 1, 'Verificado', 1, 0, 0, 0),
    (8, 'Neutrazyme N600', 1, 1, 3, 1, 100, '2025-05-23 14:26:18', '2025-05-23 14:26:18', '', 1, 'Verificado', 1, 0, 0, 0),
    (9, 'Recolpal', 1, 22, 3, 1, 100, '2025-05-23 14:27:00', '2025-05-23 14:27:00', '', 1, 'Verificado', 1, 0, 0, 0),
    (10, 'Recolsoft AFK', 1, 8, 3, 1, 100, '2025-05-23 14:27:34', '2025-05-23 14:27:34', '', 1, 'Verificado', 1, 0, 0, 0),
    (11, 'Reques 1704', 1, 1, 3, 1, 100, '2025-05-23 14:28:21', '2025-05-23 14:28:21', '', 1, 'Verificado', 1, 0, 0, 0),
    (12, 'Estabilizador AWN', 1, 10, 3, 1, 100, '2025-05-23 14:28:57', '2025-05-23 14:28:57', '', 1, 'Verificado', 1, 0, 0, 0),
    (13, 'Microsiliconado RC.M', 1, 1, 3, 1, 100, '2025-05-23 14:29:36', '2025-05-23 14:29:36', '', 1, 'Verificado', 1, 0, 0, 0),
    (14, 'Recolfix WRF-Eco', 1, 10, 3, 1, 100, '2025-05-23 14:30:21', '2025-05-23 14:30:21', '', 1, 'Verificado', 1, 0, 0, 0),
    (15, 'Amilasa HC 400', 1, 7.6, 3, 1, 100, '2025-05-23 14:31:17', '2025-05-23 14:31:17', '', 1, 'Verificado', 1, 0, 0, 0),
    (16, 'Antimigrante King', 1, 3, 3, 1, 10, '2025-05-23 14:31:57', '2025-05-23 14:31:57', '', 1, 'Verificado', 1, 0, 0, 0),
    (17, 'Neutralizante RC', 1, 8.8, 3, 1, 10, '2025-05-23 14:32:39', '2025-05-23 14:32:39', '', 1, 'Verificado', 1, 0, 0, 0),
    (18, 'Acido Acetico', 1, 8, 3, 1, 10, '2025-05-23 14:33:11', '2025-05-23 14:33:11', '', 1, 'Verificado', 1, 0, 0, 0),
    (19, 'RecolClear TS', 1, 7, 3, 1, 10, '2025-05-23 14:33:50', '2025-05-23 14:33:50', '', 1, 'Verificado', 1, 0, 0, 0),
    (20, 'Lubricol RC CONC', 1, 9, 3, 1, 10, '2025-05-23 14:35:17', '2025-05-23 14:35:17', '', 1, 'Verificado', 1, 0, 0, 0),
    (21, 'Peroxido Hidrogeno', 1, 22, 3, 1, 50, '2025-05-23 14:35:56', '2025-05-23 14:35:56', '', 1, 'Verificado', 1, 0, 0, 0),
    (22, 'Black Magic RC', 1, 22, 3, 1, 50, '2025-05-23 14:37:04', '2025-05-23 14:37:04', '', 1, 'Verificado', 1, 0, 0, 0),
    (23, 'Sal Refinada', 4, 12, 3, 1, 70, '2025-05-23 14:37:46', '2025-05-23 14:37:46', '', 1, 'Verificado', 1, 0, 0, 0),
    (24, 'Antideslizante Prest New', 1, 19.3, 3, 10, 50, '2025-05-23 14:39:48', '2025-05-23 14:39:48', '', 1, 'Verificado', 1, 0, 0, 0),
    (25, 'Pegamanato de Sodio', 1, 1, 3, 1, 10, '2025-05-23 14:40:25', '2025-05-23 14:40:25', '', 1, 'Verificado', 1, 0, 0, 0),
    (26, 'Demicol Clean SMS', 1, 4.9, 3, 1, 10, '2025-05-23 14:41:14', '2025-05-23 14:41:14', '', 1, 'Verificado', 1, 0, 0, 0),
    (27, 'Demicol Clean TFC', 1, 4.4, 3, 1, 10, '2025-05-23 14:41:57', '2025-05-23 14:41:57', '', 1, 'Verificado', 1, 0, 0, 0),
    (28, 'Demicol Clean MPC', 1, 10, 3, 1, 10, '2025-05-23 14:42:40', '2025-05-23 14:42:40', '', 1, 'Verificado', 1, 0, 0, 0),
    (29, 'Demicol BWL CONC', 1, 8, 3, 1, 10, '2025-05-23 14:43:18', '2025-05-23 14:43:18', '', 1, 'Verificado', 1, 0, 0, 0),
    (30, 'Demicol Soft 66', 1, 5, 3, 1, 10, '2025-05-23 14:43:52', '2025-05-23 14:43:52', '', 1, 'Verificado', 1, 0, 0, 0),
    (31, 'Demicol Dis 043', 1, 6.8, 3, 1, 10, '2025-05-23 14:44:32', '2025-05-23 14:44:32', '', 1, 'Verificado', 1, 0, 0, 0),
    (32, 'Beizym Top Plus', 3, 5, 3, 1, 10, '2025-05-23 14:45:21', '2025-05-23 14:45:21', '', 1, 'Verificado', 1, 0, 0, 0),
    (33, 'BEIZIM PUSH-M', 3, 1, 3, 3, 20, '2025-05-23 14:54:39', '2025-05-23 14:54:39', '', 1, 'Verificado', 1, 0, 0, 0);

-- Crear tabla movimientos_inventario
CREATE TABLE movimientos_inventario (
    id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL,
    id_usuario INTEGER,
    tipo_movimiento TEXT NOT NULL CHECK (tipo_movimiento IN ('Ingreso', 'Salida', 'Modificación', 'Verificación')),
    cantidad REAL NOT NULL,
    precio REAL,
    fecha_movimiento TEXT DEFAULT CURRENT_TIMESTAMP,
    descripcion TEXT,
    FOREIGN KEY (id_producto) REFERENCES productos(id_producto) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL
);

-- Insertar datos en movimientos_inventario (ajustados a productos reales)
INSERT INTO movimientos_inventario (id_producto, id_usuario, tipo_movimiento, cantidad, precio, descripcion) VALUES
    (1, 3, 'Ingreso', 580, 1500.00, 'Ingreso inicial de Hipoclorito de sodio'),
    (2, 3, 'Ingreso', 23, 1.00, 'Ingreso inicial de Acido Salico'),
    (3, 3, 'Ingreso', 23, 25.00, 'Ingreso inicial de Ácido Oxalico'),
    (4, 3, 'Ingreso', 18, 40.00, 'Ingreso inicial de Acitex TR'),
    (5, 3, 'Ingreso', 37, 20.00, 'Ingreso inicial de Antimigrante ABS'),
    (6, 3, 'Ingreso', 7, 15.00, 'Ingreso inicial de Antipilling Luna');

-- Crear tabla lotes
CREATE TABLE lotes (
    id_lote INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_lote TEXT NOT NULL UNIQUE,
    fecha_inicio TEXT DEFAULT CURRENT_TIMESTAMP,
    estado_actual TEXT DEFAULT 'Iniciado' CHECK (estado_actual IN ('Iniciado', 'En Progreso', 'Completado')),
    id_usuario INTEGER,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL
);

-- Insertar datos en lotes
INSERT INTO lotes (id_lote, numero_lote, fecha_inicio, estado_actual, id_usuario) VALUES
    (1, 'LOTE #256', '2025-05-23 09:00:00', 'Iniciado', 3),
    (2, 'LOTE #257', '2025-05-23 10:00:00', 'Iniciado', 3);

-- Crear tabla procesos_guardados
CREATE TABLE procesos_guardados (
    id_proceso_guardado INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_proceso TEXT NOT NULL,
    maquina_predeterminada TEXT,
    tiempo_estimado INTEGER,
    descripcion TEXT
);

-- Insertar datos en procesos_guardados
INSERT INTO procesos_guardados (id_proceso_guardado, nombre_proceso, maquina_predeterminada, tiempo_estimado, descripcion) VALUES
    (1, 'Lavado enzimático', 'Lavadora industrial', 135, 'Lavado con enzimas para desgaste suave'),
    (2, 'Teñido', 'Máquina de teñido', 45, 'Proceso de teñido con productos químicos'),
    (3, 'Pre-lavado', 'Lavadora industrial', 30, 'Lavado inicial para preparar la tela'),
    (4, 'Neutralización', 'Máquina de neutralización', 20, 'Neutralización de químicos'),
    (5, 'Aplicación de suavizante', 'Máquina de suavizado', 45, 'Aplicación de suavizante y resina');

-- Crear tabla etapas_lotes
CREATE TABLE etapas_lotes (
    id_etapa_lote INTEGER PRIMARY KEY AUTOINCREMENT,
    id_lote INTEGER NOT NULL,
    numero_etapa INTEGER NOT NULL,
    nombre_etapa TEXT NOT NULL,
    tiempo_estimado INTEGER,
    tiempo_real INTEGER DEFAULT 0,
    maquina_utilizada TEXT,
    tiempo_restante INTEGER,
    estado_etapa TEXT DEFAULT 'Pendiente' CHECK (estado_etapa IN ('Pendiente', 'En Progreso', 'Pausado', 'Completado')),
    fecha_inicio TEXT,
    fecha_fin TEXT,
    FOREIGN KEY (id_lote) REFERENCES lotes(id_lote) ON DELETE CASCADE
);

-- Insertar datos en etapas_lotes
INSERT INTO etapas_lotes (
    id_etapa_lote, id_lote, numero_etapa, nombre_etapa, tiempo_estimado, maquina_utilizada,
    tiempo_restante, estado_etapa, fecha_inicio, fecha_fin
) VALUES
    (1, 1, 1, 'Lavado enzimático', 135, 'Lavadora industrial', 135, 'Completado', '2025-05-23 09:00:00', '2025-05-23 11:15:00'),
    (2, 1, 2, 'Teñido', 45, 'Máquina de teñido', 45, 'Pendiente', NULL, NULL),
    (3, 1, 3, 'Neutralización', 20, 'Máquina de neutralización', 20, 'Pendiente', NULL, NULL),
    (4, 1, 4, 'Secado', 30, 'Secadora industrial', 30, 'Pendiente', NULL, NULL),
    (5, 1, 5, 'Aplicación de suavizante', 45, 'Máquina de suavizado', 45, 'Pendiente', NULL, NULL),
    (6, 1, 6, 'Finalización', 15, 'Máquina de finalización', 15, 'Pendiente', NULL, NULL),
    (7, 2, 1, 'Pre-lavado', 30, 'Lavadora industrial', 30, 'Completado', '2025-05-23 10:00:00', '2025-05-23 10:30:00'),
    (8, 2, 2, 'Lavado enzimático', 135, 'Lavadora industrial', 135, 'Completado', '2025-05-23 10:30:00', '2025-05-23 12:45:00'),
    (9, 2, 3, 'Teñido', 45, 'Máquina de teñido', 45, 'Completado', '2025-05-23 12:45:00', '2025-05-23 13:30:00'),
    (10, 2, 4, 'Secado', 30, 'Secadora industrial', 30, 'Completado', '2025-05-23 13:30:00', '2025-05-23 14:00:00'),
    (11, 2, 5, 'Aplicación de suavizante', 45, 'Máquina de suavizado', 45, 'Pendiente', NULL, NULL),
    (12, 2, 6, 'Finalización', 15, 'Máquina de finalización', 15, 'Pendiente', NULL, NULL);

-- Crear tabla etapas_productos
CREATE TABLE etapas_productos (
    id_etapa_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    id_etapa_lote INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad_usada REAL NOT NULL,
    nombre_producto TEXT,
    FOREIGN KEY (id_etapa_lote) REFERENCES etapas_lotes(id_etapa_lote) ON DELETE CASCADE,
    FOREIGN KEY (id_producto) REFERENCES productos(id_producto) ON DELETE CASCADE
);

-- Insertar datos en etapas_productos (ajustados a productos reales)
INSERT INTO etapas_productos (id_etapa_lote, id_producto, cantidad_usada, nombre_producto) VALUES
    (1, 4, 2.0, 'Acitex TR'),              -- Lote #256, Etapa 1: Lavado enzimático
    (2, 1, 5.0, 'Hipoclorito de sodio'),   -- Lote #256, Etapa 2: Teñido
    (5, 5, 10.0, 'Antimigrante ABS'),      -- Lote #256, Etapa 5: Aplicación de suavizante
    (7, 3, 1.0, 'Ácido Oxalico'),          -- Lote #257, Etapa 1: Pre-lavado
    (8, 4, 2.0, 'Acitex TR'),              -- Lote #257, Etapa 2: Lavado enzimático
    (9, 2, 5.0, 'Acido Salico'),           -- Lote #257, Etapa 3: Teñido
    (11, 5, 10.0, 'Antimigrante ABS');     -- Lote #257, Etapa 5: Aplicación de suavizante

-- Crear tabla prototipos
CREATE TABLE prototipos (
    id_prototipo INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    responsable TEXT,
    notas TEXT,
    estado TEXT DEFAULT 'En espera' CHECK (estado IN ('En espera', 'Aprobado', 'Rechazado')),
    id_usuario INTEGER,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL
);

-- Insertar datos en prototipos
INSERT INTO prototipos (id_prototipo, nombre, responsable, estado, id_usuario) VALUES
    (1, 'Prototipo Jeans', 'Ana Gómez', 'En espera', 1);

-- Crear tabla etapas_prototipos
CREATE TABLE etapas_prototipos (
    id_etapa_prototipo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_prototipo INTEGER NOT NULL,
    id_proceso INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad_requerida REAL NOT NULL,
    tiempo INTEGER NOT NULL,
    nombre_proceso TEXT NOT NULL,
    nombre_producto TEXT NOT NULL,
    FOREIGN KEY (id_prototipo) REFERENCES prototipos(id_prototipo) ON DELETE CASCADE,
    FOREIGN KEY (id_proceso) REFERENCES procesos_guardados(id_proceso_guardado) ON DELETE SET NULL,
    FOREIGN KEY (id_producto) REFERENCES productos(id_producto) ON DELETE SET NULL
);

-- Insertar datos en etapas_prototipos (ajustado a productos reales)
INSERT INTO etapas_prototipos (id_prototipo, id_proceso, id_producto, cantidad_requerida, tiempo, nombre_proceso, nombre_producto) VALUES
    (1, 2, 1, 5.0, 45, 'Teñido', 'Hipoclorito de sodio'),
    (1, 5, 5, 10.0, 45, 'Aplicación de suavizante', 'Antimigrante ABS');

-- Crear tabla historial_estados_prototipos
CREATE TABLE historial_estados_prototipos (
    id_historial INTEGER PRIMARY KEY AUTOINCREMENT,
    id_prototipo INTEGER NOT NULL,
    estado_anterior TEXT,
    estado_nuevo TEXT NOT NULL,
    fecha_cambio TEXT DEFAULT CURRENT_TIMESTAMP,
    usuario_cambio TEXT,
    FOREIGN KEY (id_prototipo) REFERENCES prototipos(id_prototipo) ON DELETE CASCADE
);

-- Crear vista vista_inventario
CREATE VIEW vista_inventario AS
SELECT
    p.id_producto,
    p.nombre AS producto,
    p.cantidad,
    u.abreviatura AS unidad,
    u.id_unidad AS unit_id,
    t.id_tipo AS type_id,
    t.nombre AS tipo,
    p.lote,
    p.precio,
    p.stock_minimo,
    p.stock_maximo,
    p.estado_verificacion,
    p.id_proveedor,
    pr.nombre AS proveedor,
    p.es_toxico,
    p.es_corrosivo,
    p.es_inflamable
FROM
    productos p
    LEFT JOIN unidades_medida u ON p.id_unidad = u.id_unidad
    LEFT JOIN tipos_producto t ON p.id_tipo = t.id_tipo
    LEFT JOIN proveedores pr ON p.id_proveedor = pr.id_proveedor;

-- Crear índices para optimización
CREATE INDEX idx_productos_id_tipo ON productos(id_tipo);
CREATE INDEX idx_productos_id_unidad ON productos(id_unidad);
CREATE INDEX idx_productos_id_proveedor ON productos(id_proveedor);
CREATE INDEX idx_movimientos_id_producto ON movimientos_inventario(id_producto);
CREATE INDEX idx_etapas_lotes_id_lote ON etapas_lotes(id_lote);
CREATE INDEX idx_etapas_lotes_numero_etapa ON etapas_lotes(numero_etapa);
CREATE INDEX idx_etapas_productos_id_etapa_lote ON etapas_productos(id_etapa_lote);
CREATE INDEX idx_prototipos_estado ON prototipos(estado);
CREATE INDEX idx_etapas_prototipos_id_prototipo ON etapas_prototipos(id_prototipo);
CREATE INDEX idx_historial_id_prototipo ON historial_estados_prototipos(id_prototipo);

-- Columna peso de tela para lotes (normalización g/kg)
ALTER TABLE lotes ADD COLUMN peso_tela_kg REAL DEFAULT 0;

-- Coeficientes ambientales configurables por producto
CREATE TABLE factores_ambientales (
    id_factor INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL UNIQUE,
    agua_l_por_kg REAL DEFAULT 0,
    co2_kg_por_kg REAL DEFAULT 0,
    carga_efluente_gdqo_por_kg REAL DEFAULT 0,
    eco_score TEXT DEFAULT 'C',
    fuente TEXT,
    es_estimacion INTEGER DEFAULT 1,
    FOREIGN KEY (id_producto) REFERENCES productos(id_producto) ON DELETE CASCADE
);

-- Dosis óptima de referencia (g de químico por kg de tela)
CREATE TABLE dosis_referencia (
    id_dosis INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_proceso TEXT NOT NULL,
    id_producto INTEGER NOT NULL,
    dosis_g_kg REAL NOT NULL,
    UNIQUE (nombre_proceso, id_producto),
    FOREIGN KEY (id_producto) REFERENCES productos(id_producto) ON DELETE CASCADE
);

-- Verificaciones
SELECT 'Verificando unidades_medida:' AS mensaje, * FROM unidades_medida;
SELECT 'Verificando tipos_producto:' AS mensaje, * FROM tipos_producto;
SELECT 'Verificando proveedores:' AS mensaje, * FROM proveedores;
SELECT 'Verificando usuarios:' AS mensaje, * FROM usuarios;
SELECT 'Verificando productos:' AS mensaje, * FROM productos;
SELECT 'Verificando movimientos_inventario:' AS mensaje, * FROM movimientos_inventario;
SELECT 'Verificando lotes:' AS mensaje, * FROM lotes;
SELECT 'Verificando procesos_guardados:' AS mensaje, * FROM procesos_guardados;
SELECT 'Verificando etapas_lotes:' AS mensaje, * FROM etapas_lotes;
SELECT 'Verificando etapas_productos:' AS mensaje, * FROM etapas_productos;
SELECT 'Verificando prototipos:' AS mensaje, * FROM prototipos;
SELECT 'Verificando etapas_prototipos:' AS mensaje, * FROM etapas_prototipos;
SELECT 'Verificando historial_estados_prototipos:' AS mensaje, * FROM historial_estados_prototipos;
SELECT 'Verificando vista_inventario:' AS mensaje, * FROM vista_inventario;

-- Verificar precio total
SELECT 'Precio total:' AS mensaje, SUM(CAST(COALESCE(cantidad, 0) AS REAL) * CAST(COALESCE(precio, 0) AS REAL)) AS precio_total FROM productos;

-- Verificar historial de movimientos
SELECT 'Historial de movimientos:' AS mensaje, 
       p.nombre AS producto, p.cantidad, p.precio, p.stock_minimo, p.stock_maximo,
       u.nombre AS usuario, m.tipo_movimiento, m.cantidad AS cantidad_movimiento, 
       m.fecha_movimiento, m.descripcion
FROM movimientos_inventario m
LEFT JOIN productos p ON m.id_producto = p.id_producto
LEFT JOIN usuarios u ON m.id_usuario = u.id_usuario;

-- Verificar productos con características especiales
SELECT p.nombre AS producto, p.cantidad, p.precio, p.stock_minimo, p.stock_maximo, 
       p.es_toxico, p.es_corrosivo, p.es_inflamable, pr.nombre AS proveedor
FROM productos p
LEFT JOIN proveedores pr ON p.id_proveedor = pr.id_proveedor;

-- Verificar productos más utilizados
SELECT ep.nombre_producto, SUM(ep.cantidad_usada) AS total_requerido
FROM etapas_productos ep
GROUP BY ep.nombre_producto
ORDER BY total_requerido DESC
LIMIT 5;

-- Verificación adicional para confirmar eliminación de duplicado
SELECT * FROM productos WHERE nombre = 'Hipoclorito de sodio';