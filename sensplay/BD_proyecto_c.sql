-- Crear base de datos
CREATE DATABASE IF NOT EXISTS proyecto_c CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE proyecto_c;

-- Tabla: area
CREATE TABLE area (
  id_area INT AUTO_INCREMENT PRIMARY KEY,
  nombre_area VARCHAR(50)
);

INSERT INTO area VALUES
(1, 'Desarrollo de Software'),
(3, 'Terapeuta'),
(14, 'Administrativa');

-- Tabla: genero
CREATE TABLE genero (
  id_genero INT AUTO_INCREMENT PRIMARY KEY,
  tipo_genero VARCHAR(45)
);

INSERT INTO genero VALUES
(1, 'Masculino'),
(2, 'Femenino'),
(3, 'Otro');

-- Tabla: estado_civil
CREATE TABLE estado_civil (
  id_estado_civil INT AUTO_INCREMENT PRIMARY KEY,
  registro_civil VARCHAR(45)
);

INSERT INTO estado_civil VALUES
(1, 'Soltero(a)'),
(2, 'Casado(a)'),
(3, 'Divorciado(a)'),
(4, 'Viudo(a)'),
(5, 'Unión Libre');

-- Tabla: rol
CREATE TABLE rol (
  id_rol INT AUTO_INCREMENT PRIMARY KEY,
  nombre_rol VARCHAR(50)
);

INSERT INTO rol VALUES
(1, 'admin'),
(2, 'user');

-- Tabla: usuarios
CREATE TABLE usuarios (
  id_usuario INT AUTO_INCREMENT PRIMARY KEY,
  cedula CHAR(10) NOT NULL UNIQUE,
  nombre_usuario VARCHAR(50),
  apellido_usuario VARCHAR(50),
  password TEXT NOT NULL,
  id_area INT,
  id_rol INT,
  id_genero INT,
  id_estado_civil INT,
  FOREIGN KEY (id_area) REFERENCES area(id_area),
  FOREIGN KEY (id_rol) REFERENCES rol(id_rol),
  FOREIGN KEY (id_genero) REFERENCES genero(id_genero),
  FOREIGN KEY (id_estado_civil) REFERENCES estado_civil(id_estado_civil)
);

INSERT INTO usuarios VALUES
(1, '0123456789', 'Admin', 'Admin', 'scrypt:32768:8:1$iU4IOddLZ0WELUtr$f882a98e51d0eecae0748d2925bbf99b4f8668189d16cbf7b3c2c2efce5cba97b5b43b2f8cd0b8b1a227ddbe73b9210dd261d2a97608c32f14cdf6c6c711fe4b', 1, 1, NULL, NULL),
(9, '0987654321', 'Carlos', 'Perez', 'scrypt:32768:8:1$0YomGZv4SOkE4mSo$89f0e7f40ae01eddfa48dc5b62283586d8448b10fd0f06452e239e3b8cde55555c82420119c4741e60489874957505ad9491214c40b6f98614b002d8cf82c079', 3, 2, 1, 1);

-- Tabla: pacientes
CREATE TABLE pacientes (
  id_paciente INT AUTO_INCREMENT PRIMARY KEY,
  cedula CHAR(10) NOT NULL UNIQUE,
  nombres VARCHAR(100),
  apellidos VARCHAR(100),
  edad INT,
  id_genero INT,
  FOREIGN KEY (id_genero) REFERENCES genero(id_genero)
);

INSERT INTO pacientes VALUES
(1, '0571754879', 'Pepe', 'Perez', 3, 1),
(2, '2705141657', 'Carlos Andres', 'Perez Lopez', 4, 1),
(14, '8415155516', 'Carlos Fernandez', 'Mejia Andrade', 3, 1);

-- Tabla: accesos
CREATE TABLE accesos (
  id_acceso INT AUTO_INCREMENT PRIMARY KEY,
  fecha DATETIME,
  clave VARCHAR(50),
  id_usuario INT,
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
);

INSERT INTO accesos VALUES
(1, '2025-06-24 03:23:11', 'NhcKYV', 1),
(2, '2025-07-02 03:42:12', 'Fjs1fg', 1);

-- Tabla: sesiones
CREATE TABLE sesiones (
  id_sesion INT AUTO_INCREMENT PRIMARY KEY,
  id_paciente INT,
  id_usuario INT,
  fecha_inicio DATETIME,
  fecha_fin DATETIME,
  FOREIGN KEY (id_paciente) REFERENCES pacientes(id_paciente),
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
);

-- Tabla: log_balon
CREATE TABLE log_balon (
  id_log_balon INT AUTO_INCREMENT PRIMARY KEY,
  id_sesion INT,
  sensor VARCHAR(5),
  fecha_registro DATETIME,
  FOREIGN KEY (id_sesion) REFERENCES sesiones(id_sesion)
);

-- Tabla: sensor_balon (resumen por sesión)
CREATE TABLE sensor_balon (
  id_registro INT AUTO_INCREMENT PRIMARY KEY,
  id_sesion INT,
  S1 INT DEFAULT 0,
  S2 INT DEFAULT 0,
  S3 INT DEFAULT 0,
  S4 INT DEFAULT 0,
  S5 INT DEFAULT 0,
  S6 INT DEFAULT 0,
  FOREIGN KEY (id_sesion) REFERENCES sesiones(id_sesion)
);

-- Tabla: log_trampolin
CREATE TABLE log_trampolin (
  id_log_trampolin INT AUTO_INCREMENT PRIMARY KEY,
  id_sesion INT,
  sensor INT DEFAULT 1,
  fecha_registro DATETIME,
  FOREIGN KEY (id_sesion) REFERENCES sesiones(id_sesion)
);

-- Tabla: sensor_trampolin (resumen por sesión)
CREATE TABLE sensor_trampolin (
  id_conteo INT AUTO_INCREMENT PRIMARY KEY,
  id_sesion INT,
  total_saltos INT,
  FOREIGN KEY (id_sesion) REFERENCES sesiones(id_sesion)
);

-- Inserts de ejemplo:
-- Insertar una sesión
INSERT INTO sesiones (id_paciente, id_usuario, fecha_inicio, fecha_fin)
VALUES (1, 9, '2025-07-10 10:00:00', '2025-07-10 10:30:00');

-- Registros de log_balon (toques individuales)
INSERT INTO log_balon (id_sesion, sensor, fecha_registro) VALUES
(1, 'S1', '2025-07-10 10:05:10'),
(1, 'S1', '2025-07-10 10:05:12'),
(1, 'S2', '2025-07-10 10:06:30'),
(1, 'S3', '2025-07-10 10:07:45'),
(1, 'S3', '2025-07-10 10:08:00'),
(1, 'S3', '2025-07-10 10:08:10');

-- Insertar resumen de conteo de sensores de balón para la sesión
INSERT INTO sensor_balon (id_sesion, S1, S2, S3, S4, S5, S6)
VALUES (1, 2, 1, 3, 0, 0, 0);

-- Registros de log_trampolin (saltos individuales)
INSERT INTO log_trampolin (id_sesion, sensor, fecha_registro) VALUES
(1, 1, '2025-07-10 10:10:00'),
(1, 1, '2025-07-10 10:11:12'),
(1, 1, '2025-07-10 10:13:55'),
(1, 1, '2025-07-10 10:15:00');

-- Insertar resumen de conteo de trampolín
INSERT INTO sensor_trampolin (id_sesion, total_saltos)
VALUES (1, 4);

-- Selects de ejemplo para posterior uso en colsulta de graficas
/*
-- Total por sensor balón en sesión 1
SELECT * FROM sensor_balon WHERE id_sesion = 1;

-- Tiempos de toques exactos
SELECT sensor, fecha_registro FROM log_balon WHERE id_sesion = 1;

-- Total de saltos
SELECT total_saltos FROM sensor_trampolin WHERE id_sesion = 1;

-- Detalle de saltos
SELECT fecha_registro FROM log_trampolin WHERE id_sesion = 1;

*/ 
