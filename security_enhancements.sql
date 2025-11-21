-- ============================================================
-- Mejoras de Seguridad y Restricciones Adicionales
-- Sistema de Gestión de Reservas de Salas de Estudio - UCU
-- ============================================================

USE `UCU_SalasDeEstudio`;

-- ============================================================
-- 1. VALIDACIONES ADICIONALES (CHECK CONSTRAINTS)
-- ============================================================

-- Validación de email con formato básico
ALTER TABLE `participante`
ADD CONSTRAINT `chk_email_format` 
CHECK (`email` REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$');

-- Validación de capacidad mínima de salas (mínimo 1 persona)
ALTER TABLE `sala`
ADD CONSTRAINT `chk_capacidad_minima` 
CHECK (`capacidad` >= 1);

-- Validación de capacidad máxima razonable (máximo 200 personas)
ALTER TABLE `sala`
ADD CONSTRAINT `chk_capacidad_maxima` 
CHECK (`capacidad` <= 200);

-- Validación de fecha de reserva (no puede ser en el pasado)
-- Nota: Esta validación se maneja mejor en la aplicación, pero se puede agregar un trigger

-- Validación de CI (debe tener al menos 7 caracteres)
ALTER TABLE `participante`
ADD CONSTRAINT `chk_ci_length` 
CHECK (CHAR_LENGTH(`ci`) >= 7);

-- ============================================================
-- 2. VISTAS (VIEWS) PARA SEGURIDAD Y ACCESO CONTROLADO
-- ============================================================

-- Vista para participantes sin información sensible de login
CREATE OR REPLACE VIEW `v_participantes_publicos` AS
SELECT 
    `ci`,
    `nombre`,
    `apellido`,
    `email`
FROM `participante`;

-- Vista para reservas activas con información básica
CREATE OR REPLACE VIEW `v_reservas_activas` AS
SELECT 
    r.`id_reserva`,
    r.`nombre_sala`,
    r.`edificio`,
    r.`fecha`,
    t.`hora_inicio`,
    t.`hora_fin`,
    r.`estado`,
    COUNT(rp.`ci_participante`) AS `num_participantes`
FROM `reserva` r
JOIN `turno` t ON r.`id_turno` = t.`id_turno`
LEFT JOIN `reserva_participante` rp ON r.`id_reserva` = rp.`id_reserva`
WHERE r.`estado` = 'activa'
GROUP BY r.`id_reserva`, r.`nombre_sala`, r.`edificio`, r.`fecha`, t.`hora_inicio`, t.`hora_fin`, r.`estado`;

-- Vista para estadísticas de uso sin información personal
CREATE OR REPLACE VIEW `v_estadisticas_uso` AS
SELECT 
    s.`nombre_sala`,
    s.`edificio`,
    s.`tipo_sala`,
    COUNT(DISTINCT r.`id_reserva`) AS `total_reservas`,
    COUNT(DISTINCT CASE WHEN r.`estado` = 'finalizada' THEN r.`id_reserva` END) AS `reservas_completadas`,
    AVG((SELECT COUNT(*) FROM `reserva_participante` rp2 WHERE rp2.`id_reserva` = r.`id_reserva`)) AS `promedio_participantes`
FROM `sala` s
LEFT JOIN `reserva` r ON s.`nombre_sala` = r.`nombre_sala` AND s.`edificio` = r.`edificio`
GROUP BY s.`nombre_sala`, s.`edificio`, s.`tipo_sala`;

-- ============================================================
-- 3. PROCEDIMIENTOS ALMACENADOS (STORED PROCEDURES)
-- ============================================================

DELIMITER //

-- Procedimiento para crear reserva con validaciones
CREATE PROCEDURE `sp_crear_reserva`(
    IN p_nombre_sala VARCHAR(50),
    IN p_edificio VARCHAR(50),
    IN p_fecha DATE,
    IN p_id_turno INT,
    IN p_ci_solicitante VARCHAR(15),
    OUT p_id_reserva INT,
    OUT p_resultado VARCHAR(255)
)
BEGIN
    DECLARE v_capacidad INT;
    DECLARE v_num_participantes INT;
    DECLARE v_existe_reserva INT;
    
    -- Verificar que la sala existe y obtener capacidad
    SELECT `capacidad` INTO v_capacidad
    FROM `sala`
    WHERE `nombre_sala` = p_nombre_sala AND `edificio` = p_edificio;
    
    IF v_capacidad IS NULL THEN
        SET p_resultado = 'Error: Sala no encontrada';
        SET p_id_reserva = NULL;
    ELSE
        -- Verificar que no existe otra reserva activa para el mismo turno
        SELECT COUNT(*) INTO v_existe_reserva
        FROM `reserva`
        WHERE `nombre_sala` = p_nombre_sala 
          AND `edificio` = p_edificio
          AND `fecha` = p_fecha
          AND `id_turno` = p_id_turno
          AND `estado` = 'activa';
        
        IF v_existe_reserva > 0 THEN
            SET p_resultado = 'Error: Sala ya reservada para este turno';
            SET p_id_reserva = NULL;
        ELSE
            -- Crear la reserva
            INSERT INTO `reserva` (`nombre_sala`, `edificio`, `fecha`, `id_turno`, `estado`)
            VALUES (p_nombre_sala, p_edificio, p_fecha, p_id_turno, 'activa');
            
            SET p_id_reserva = LAST_INSERT_ID();
            SET p_resultado = 'Reserva creada exitosamente';
        END IF;
    END IF;
END //

-- Procedimiento para actualizar estado de reserva
CREATE PROCEDURE `sp_actualizar_estado_reserva`(
    IN p_id_reserva INT,
    IN p_nuevo_estado ENUM('activa', 'cancelada', 'sin asistencia', 'finalizada'),
    OUT p_resultado VARCHAR(255)
)
BEGIN
    DECLARE v_existe INT;
    
    -- Verificar que la reserva existe
    SELECT COUNT(*) INTO v_existe
    FROM `reserva`
    WHERE `id_reserva` = p_id_reserva;
    
    IF v_existe = 0 THEN
        SET p_resultado = 'Error: Reserva no encontrada';
    ELSE
        UPDATE `reserva`
        SET `estado` = p_nuevo_estado
        WHERE `id_reserva` = p_id_reserva;
        
        SET p_resultado = CONCAT('Estado actualizado a: ', p_nuevo_estado);
    END IF;
END //

-- Procedimiento para limpiar tokens expirados
CREATE PROCEDURE `sp_limpiar_tokens_expirados`()
BEGIN
    DELETE FROM `access_token`
    WHERE `fecha_expiracion` < NOW();
    
    SELECT ROW_COUNT() AS `tokens_eliminados`;
END //

DELIMITER ;

-- ============================================================
-- 4. TRIGGERS PARA AUDITORÍA Y VALIDACIÓN
-- ============================================================

DELIMITER //

-- Trigger para validar que las reservas no sean en el pasado
CREATE TRIGGER `trg_validar_fecha_reserva`
BEFORE INSERT ON `reserva`
FOR EACH ROW
BEGIN
    IF NEW.`fecha` < CURDATE() THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'No se pueden crear reservas en fechas pasadas';
    END IF;
END //

-- Trigger para actualizar último acceso de token
CREATE TRIGGER `trg_actualizar_ultimo_acceso_token`
BEFORE UPDATE ON `access_token`
FOR EACH ROW
BEGIN
    SET NEW.`ultimo_acceso` = NOW();
END //

-- Trigger para registrar creación de reserva (auditoría)
CREATE TRIGGER `trg_auditoria_reserva_insert`
AFTER INSERT ON `reserva`
FOR EACH ROW
BEGIN
    -- En una implementación completa, esto insertaría en una tabla de auditoría
    -- Por ahora, solo validamos
    IF NEW.`fecha` < CURDATE() THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error de auditoría: Fecha inválida';
    END IF;
END //

DELIMITER ;

-- ============================================================
-- 5. USUARIOS Y PERMISOS (GRANT/REVOKE)
-- ============================================================

-- Crear usuario para la aplicación (solo lectura/escritura en tablas necesarias)
-- NOTA: En producción, usar contraseñas seguras y diferentes usuarios para diferentes roles

-- Usuario de aplicación (lectura/escritura completa)
-- CREATE USER 'ucu_app_user'@'localhost' IDENTIFIED BY 'password_segura_aqui';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON `UCU_SalasDeEstudio`.* TO 'ucu_app_user'@'localhost';

-- Usuario de solo lectura para reportes
-- CREATE USER 'ucu_readonly_user'@'localhost' IDENTIFIED BY 'password_segura_aqui';
-- GRANT SELECT ON `UCU_SalasDeEstudio`.* TO 'ucu_readonly_user'@'localhost';
-- GRANT SELECT ON `UCU_SalasDeEstudio`.`v_reservas_activas` TO 'ucu_readonly_user'@'localhost';
-- GRANT SELECT ON `UCU_SalasDeEstudio`.`v_estadisticas_uso` TO 'ucu_readonly_user'@'localhost';

-- Usuario administrativo (acceso completo)
-- CREATE USER 'ucu_admin_user'@'localhost' IDENTIFIED BY 'password_segura_aqui';
-- GRANT ALL PRIVILEGES ON `UCU_SalasDeEstudio`.* TO 'ucu_admin_user'@'localhost';

-- Aplicar cambios
-- FLUSH PRIVILEGES;

-- ============================================================
-- 6. ÍNDICES ADICIONALES PARA OPTIMIZACIÓN
-- ============================================================

-- Índice para búsquedas frecuentes de reservas por fecha
CREATE INDEX `idx_reserva_fecha` ON `reserva` (`fecha`);

-- Índice para búsquedas de reservas por estado
CREATE INDEX `idx_reserva_estado` ON `reserva` (`estado`);

-- Índice compuesto para búsquedas de salas por edificio y tipo
CREATE INDEX `idx_sala_edificio_tipo` ON `sala` (`edificio`, `tipo_sala`);

-- Índice para búsquedas de participantes por email (ya existe UNIQUE, pero útil para JOINs)
-- El UNIQUE ya crea un índice, pero podemos verificar que existe

-- Índice para búsquedas de sanciones activas
CREATE INDEX `idx_sancion_fecha_fin` ON `sancion_participante` (`fecha_fin`);

-- Índice para búsquedas de reservas por participante
CREATE INDEX `idx_reserva_participante_ci` ON `reserva_participante` (`ci_participante`);

-- ============================================================
-- FIN DE MEJORAS DE SEGURIDAD
-- ============================================================

