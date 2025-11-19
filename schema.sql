-- -----------------------------------------------------
-- Esquema de la Base de Datos: UCU_SalasDeEstudio
-- -----------------------------------------------------
CREATE DATABASE IF NOT EXISTS `UCU_SalasDeEstudio` DEFAULT CHARACTER SET utf8mb4;
USE `UCU_SalasDeEstudio`;

-- -----------------------------------------------------
-- Tabla `facultad`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `facultad` (
  `id_facultad` INT NOT NULL AUTO_INCREMENT, -- Clave primaria.
  `nombre` VARCHAR(100) NOT NULL UNIQUE,
  PRIMARY KEY (`id_facultad`)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Tabla `programa_academico`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `programa_academico` (
  `nombre_programa` VARCHAR(100) NOT NULL, -- Clave primaria compuesta 1/2.
  `id_facultad` INT NOT NULL, -- Clave primaria compuesta 2/2 y Clave Foránea.
  `tipo` ENUM('grado', 'posgrado') NOT NULL, -- Valores fijos.
  PRIMARY KEY (`nombre_programa`, `id_facultad`),
  FOREIGN KEY (`id_facultad`)
    REFERENCES `facultad` (`id_facultad`)
    ON DELETE RESTRICT -- No permitir borrar una facultad si tiene programas asociados.
    ON UPDATE CASCADE -- Actualizar id_facultad en cascada.
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Tabla `participante`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `participante` (
  `ci` VARCHAR(15) NOT NULL, -- Clave primaria. Se usa VARCHAR para permitir formato con guion o puntos si se desea, y se ajusta a lo solicitado (ci).
  `nombre` VARCHAR(50) NOT NULL,
  `apellido` VARCHAR(50) NOT NULL,
  `email` VARCHAR(100) NOT NULL UNIQUE,
  PRIMARY KEY (`ci`)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Tabla `participante_programa_academico`
-- Esta tabla maneja la relación N:M entre participantes y programas, y define el rol.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `participante_programa_academico` (
  `ci_participante` VARCHAR(15) NOT NULL, -- Clave Foránea 1/3 y Clave primaria compuesta 1/3.
  `nombre_programa` VARCHAR(100) NOT NULL, -- Clave Foránea 2/3 y Clave primaria compuesta 2/3.
  `id_facultad` INT NOT NULL, -- Clave Foránea 3/3 y Clave primaria compuesta 3/3.
  `rol` ENUM('alumno', 'docente') NOT NULL, -- Rol del participante en el programa.
  PRIMARY KEY (`ci_participante`, `nombre_programa`, `id_facultad`),
  FOREIGN KEY (`ci_participante`)
    REFERENCES `participante` (`ci`)
    ON DELETE CASCADE -- Si se borra un participante, se elimina su relación.
    ON UPDATE CASCADE,
  FOREIGN KEY (`nombre_programa`, `id_facultad`)
    REFERENCES `programa_academico` (`nombre_programa`, `id_facultad`)
    ON DELETE RESTRICT -- No eliminar el programa si hay participantes asociados.
    ON UPDATE CASCADE
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Tabla `login`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `login` (
  `correo` VARCHAR(100) NOT NULL, -- Clave primaria. Se usa como enlace al email del participante.
  `password` VARCHAR(255) NOT NULL, -- Se recomienda usar un hash de la contraseña.
  PRIMARY KEY (`correo`),
  FOREIGN KEY (`correo`)
    REFERENCES `participante` (`email`)
    ON DELETE CASCADE -- Si se elimina el participante, se elimina el login.
    ON UPDATE CASCADE
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Tabla `edificio`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `edificio` (
  `nombre_edificio` VARCHAR(50) NOT NULL, -- Clave primaria. Se ajusta el nombre del campo a lo que va a ser PK para mayor claridad.
  `direccion` VARCHAR(150) NOT NULL,
  `departamento` VARCHAR(50) NOT NULL,
  PRIMARY KEY (`nombre_edificio`)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Tabla `sala`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sala` (
  `nombre_sala` VARCHAR(50) NOT NULL, -- Clave primaria compuesta 1/2.
  `edificio` VARCHAR(50) NOT NULL, -- Clave primaria compuesta 2/2 y Clave Foránea.
  `capacidad` INT NOT NULL,
  `tipo_sala` ENUM('libre', 'posgrado', 'docente') NOT NULL, -- Tipos de salas.
  PRIMARY KEY (`nombre_sala`, `edificio`),
  FOREIGN KEY (`edificio`)
    REFERENCES `edificio` (`nombre_edificio`)
    ON DELETE RESTRICT -- No permitir borrar un edificio si tiene salas.
    ON UPDATE CASCADE
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Tabla `turno`
-- Bloques de hora (de 8:00 AM a 11:00 PM).
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `turno` (
  `id_turno` INT NOT NULL AUTO_INCREMENT, -- Clave primaria.
  `hora_inicio` TIME NOT NULL,
  `hora_fin` TIME NOT NULL,
  PRIMARY KEY (`id_turno`),
  CONSTRAINT `chk_bloque_hora` CHECK (TIME_TO_SEC(`hora_fin`) - TIME_TO_SEC(`hora_inicio`) = 3600) -- Restricción de 1 hora de duración (3600 segundos).
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Tabla `reserva`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `reserva` (
  `id_reserva` INT NOT NULL AUTO_INCREMENT, -- Clave primaria.
  `nombre_sala` VARCHAR(50) NOT NULL, -- Clave Foránea 1/3.
  `edificio` VARCHAR(50) NOT NULL, -- Clave Foránea 2/3.
  `fecha` DATE NOT NULL,
  `id_turno` INT NOT NULL, -- Clave Foránea 3/3.
  `estado` ENUM('activa', 'cancelada', 'sin asistencia', 'finalizada') NOT NULL,
  PRIMARY KEY (`id_reserva`),
  UNIQUE KEY `uk_reserva_sala_fecha_turno` (`nombre_sala`, `edificio`, `fecha`, `id_turno`), -- Una sala solo se puede reservar una vez por turno en un día.
  FOREIGN KEY (`nombre_sala`, `edificio`)
    REFERENCES `sala` (`nombre_sala`, `edificio`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  FOREIGN KEY (`id_turno`)
    REFERENCES `turno` (`id_turno`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Tabla `reserva_participante`
-- Asocia participantes a reservas y registra la asistencia.
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `reserva_participante` (
  `ci_participante` VARCHAR(15) NOT NULL, -- Clave Foránea 1/2 y Clave primaria compuesta 1/2.
  `id_reserva` INT NOT NULL, -- Clave Foránea 2/2 y Clave primaria compuesta 2/2.
  `fecha_solicitud_reserva` DATETIME NOT NULL,
  `asistencia` BOOLEAN DEFAULT FALSE, -- Registra si asistió al momento del control.
  PRIMARY KEY (`ci_participante`, `id_reserva`),
  FOREIGN KEY (`ci_participante`)
    REFERENCES `participante` (`ci`)
    ON DELETE RESTRICT -- Mantener registro de reservas aunque el participante se dé de baja.
    ON UPDATE CASCADE,
  FOREIGN KEY (`id_reserva`)
    REFERENCES `reserva` (`id_reserva`)
    ON DELETE CASCADE -- Si se cancela o elimina la reserva, se elimina la asociación.
    ON UPDATE CASCADE
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Tabla `sancion_participante`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `sancion_participante` (
  `id_sancion` INT NOT NULL AUTO_INCREMENT,
  `ci_participante` VARCHAR(15) NOT NULL, -- Clave Foránea.
  `fecha_inicio` DATE NOT NULL,
  `fecha_fin` DATE NOT NULL,
  PRIMARY KEY (`id_sancion`),
  FOREIGN KEY (`ci_participante`)
    REFERENCES `participante` (`ci`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  -- Restricción para asegurar que la fecha de fin sea posterior a la de inicio.
  CONSTRAINT `chk_fechas_sancion` CHECK (`fecha_fin` > `fecha_inicio`)
) ENGINE = InnoDB;

-- -----------------------------------------------------
-- Tabla `access_token`
-- Sistema de tokens de acceso para seguridad de rutas administrativas
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `access_token` (
  `token` VARCHAR(64) NOT NULL, -- Token único (hash SHA-256)
  `ci_participante` VARCHAR(15) NOT NULL, -- Clave Foránea al participante
  `is_admin` BOOLEAN NOT NULL DEFAULT FALSE, -- Indica si el token tiene privilegios de admin
  `fecha_creacion` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `fecha_expiracion` DATETIME NOT NULL, -- Expiración: 1 semana desde creación
  `ultimo_acceso` DATETIME DEFAULT NULL, -- Última vez que se usó el token
  PRIMARY KEY (`token`),
  FOREIGN KEY (`ci_participante`)
    REFERENCES `participante` (`ci`)
    ON DELETE CASCADE -- Si se elimina el participante, se eliminan sus tokens
    ON UPDATE CASCADE,
  INDEX `idx_expiracion` (`fecha_expiracion`), -- Índice para limpieza eficiente
  INDEX `idx_participante` (`ci_participante`) -- Índice para búsquedas por participante
) ENGINE = InnoDB;






