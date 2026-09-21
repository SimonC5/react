-- Esquema MySQL de SimonC.
-- El backend lo ejecuta solo al arrancar con DB_ENGINE=mysql; también se
-- puede importar desde phpMyAdmin. Las tablas van en orden de dependencia,
-- primero las que otras referencian, para que el Diseñador de phpMyAdmin
-- dibuje las relaciones sin cruces innecesarios.

CREATE DATABASE IF NOT EXISTS simonsc CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE simonsc;

-- ---------------------------------------------------------------------------
-- Seguridad: roles, permisos y usuarios.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS roles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(40) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS permisos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(60) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS role_permisos (
  role_id INT NOT NULL,
  permiso_id INT NOT NULL,
  PRIMARY KEY (role_id, permiso_id),
  CONSTRAINT fk_role_permisos_rol FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
  CONSTRAINT fk_role_permisos_permiso FOREIGN KEY (permiso_id) REFERENCES permisos (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  last_name VARCHAR(80) NOT NULL,
  document_type VARCHAR(20) NOT NULL,
  document_number VARCHAR(12) NOT NULL UNIQUE,
  address VARCHAR(150) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  active TINYINT(1) NOT NULL DEFAULT 1,
  role_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_usuarios_rol FOREIGN KEY (role_id) REFERENCES roles (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Catálogo. No dependen de nadie: en el diagrama van sueltas a un lado.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS productos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  description VARCHAR(255) NOT NULL DEFAULT '',
  price DECIMAL(12,2) NOT NULL DEFAULT 0,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS servicios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  description VARCHAR(255) NOT NULL DEFAULT '',
  price DECIMAL(12,2) NOT NULL DEFAULT 0,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Ventas y facturación.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ventas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  numero VARCHAR(20) NOT NULL UNIQUE,
  cliente_id INT NULL,
  cliente_nombre VARCHAR(160) NOT NULL,
  cliente_documento VARCHAR(20) NOT NULL DEFAULT '',
  usuario_id INT NULL,
  usuario_nombre VARCHAR(160) NOT NULL DEFAULT '',
  subtotal DECIMAL(12,2) NOT NULL DEFAULT 0,
  descuento DECIMAL(12,2) NOT NULL DEFAULT 0,
  impuestos DECIMAL(12,2) NOT NULL DEFAULT 0,
  total DECIMAL(12,2) NOT NULL DEFAULT 0,
  estado VARCHAR(20) NOT NULL DEFAULT 'Registrada',
  observaciones VARCHAR(255) NOT NULL DEFAULT '',
  fecha DATETIME NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ventas_fecha (fecha),
  CONSTRAINT fk_ventas_cliente FOREIGN KEY (cliente_id) REFERENCES usuarios (id) ON DELETE SET NULL,
  CONSTRAINT fk_ventas_vendedor FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- item_id apunta a productos o a servicios según item_tipo, así que no puede
-- llevar clave foránea: es la única relación que el Diseñador no dibuja.
CREATE TABLE IF NOT EXISTS detalle_ventas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  venta_id INT NOT NULL,
  item_tipo VARCHAR(20) NOT NULL,
  item_id INT NULL,
  nombre VARCHAR(160) NOT NULL,
  cantidad DECIMAL(12,2) NOT NULL DEFAULT 1,
  precio_unitario DECIMAL(12,2) NOT NULL DEFAULT 0,
  descuento DECIMAL(12,2) NOT NULL DEFAULT 0,
  impuesto DECIMAL(12,2) NOT NULL DEFAULT 0,
  subtotal DECIMAL(12,2) NOT NULL DEFAULT 0,
  total DECIMAL(12,2) NOT NULL DEFAULT 0,
  CONSTRAINT fk_detalle_ventas_venta FOREIGN KEY (venta_id) REFERENCES ventas (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS facturas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  numero VARCHAR(20) NOT NULL UNIQUE,
  venta_id INT NOT NULL UNIQUE,
  cliente_nombre VARCHAR(160) NOT NULL,
  cliente_documento VARCHAR(20) NOT NULL DEFAULT '',
  subtotal DECIMAL(12,2) NOT NULL DEFAULT 0,
  descuento DECIMAL(12,2) NOT NULL DEFAULT 0,
  impuestos DECIMAL(12,2) NOT NULL DEFAULT 0,
  total DECIMAL(12,2) NOT NULL DEFAULT 0,
  estado VARCHAR(20) NOT NULL DEFAULT 'Emitida',
  fecha DATETIME NOT NULL,
  INDEX idx_facturas_fecha (fecha),
  CONSTRAINT fk_facturas_venta FOREIGN KEY (venta_id) REFERENCES ventas (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS detalle_facturas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  factura_id INT NOT NULL,
  item_tipo VARCHAR(20) NOT NULL,
  nombre VARCHAR(160) NOT NULL,
  cantidad DECIMAL(12,2) NOT NULL DEFAULT 1,
  precio_unitario DECIMAL(12,2) NOT NULL DEFAULT 0,
  descuento DECIMAL(12,2) NOT NULL DEFAULT 0,
  impuesto DECIMAL(12,2) NOT NULL DEFAULT 0,
  subtotal DECIMAL(12,2) NOT NULL DEFAULT 0,
  total DECIMAL(12,2) NOT NULL DEFAULT 0,
  CONSTRAINT fk_detalle_facturas_factura FOREIGN KEY (factura_id) REFERENCES facturas (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Atención al cliente: PQR, chatbot y recuperación de contraseña.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pqr (
  id INT AUTO_INCREMENT PRIMARY KEY,
  radicado VARCHAR(20) NOT NULL UNIQUE,
  tipo VARCHAR(20) NOT NULL DEFAULT 'Petición',
  asunto VARCHAR(160) NOT NULL,
  descripcion TEXT NOT NULL,
  estado VARCHAR(20) NOT NULL DEFAULT 'Pendiente',
  respuesta TEXT NULL,
  cliente_id INT NULL,
  cliente_nombre VARCHAR(160) NOT NULL,
  cliente_email VARCHAR(120) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  INDEX idx_pqr_estado (estado),
  CONSTRAINT fk_pqr_cliente FOREIGN KEY (cliente_id) REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS conversaciones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NULL,
  titulo VARCHAR(120) NOT NULL DEFAULT 'Conversación',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  CONSTRAINT fk_conversaciones_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mensajes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  conversacion_id INT NOT NULL,
  rol VARCHAR(20) NOT NULL,
  contenido TEXT NOT NULL,
  created_at DATETIME NOT NULL,
  INDEX idx_mensajes_conversacion (conversacion_id),
  CONSTRAINT fk_mensajes_conversacion FOREIGN KEY (conversacion_id) REFERENCES conversaciones (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recuperaciones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  token_hash CHAR(64) NOT NULL UNIQUE,
  expira_en DATETIME NOT NULL,
  usado TINYINT(1) NOT NULL DEFAULT 0,
  creado_en DATETIME NOT NULL,
  INDEX idx_recuperaciones_usuario (usuario_id),
  CONSTRAINT fk_recuperaciones_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
