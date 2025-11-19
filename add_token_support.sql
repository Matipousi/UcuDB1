-- Migration script to add access_token table for existing databases
-- Run this if you already have a database set up

USE UCU_SalasDeEstudio;

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

