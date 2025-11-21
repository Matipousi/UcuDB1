# Informe del Trabajo Realizado
## Sistema de Gestión de Reservas de Salas de Estudio - UCU

**Autor:** [Tu Nombre]  
**Fecha:** Diciembre 2025  
**Asignatura:** Base de Datos 1 - Segundo Semestre 2025

---

## 1. Fundamentación de Decisiones de Implementación

### 1.1 Arquitectura del Sistema

Se optó por una arquitectura de tres capas:
- **Capa de Presentación:** Aplicación web Flask con templates Jinja2
- **Capa de Lógica de Negocio:** Python puro sin ORM (como se requiere)
- **Capa de Datos:** MySQL con restricciones a nivel de base de datos

**Justificación:** Esta arquitectura permite separación de responsabilidades, facilita el mantenimiento y cumple con el requisito de no usar ORM, manteniendo control total sobre las consultas SQL.

### 1.2 Framework Web: Flask

**Decisión:** Utilizar Flask en lugar de Django u otros frameworks.

**Razones:**
- Ligero y minimalista, ideal para aplicaciones de tamaño medio
- Permite control total sobre la estructura del proyecto
- Facilita la integración con MySQL sin abstracciones innecesarias
- Comunidad activa y documentación extensa

### 1.3 Sistema de Autenticación

**Implementación:**
- Hash de contraseñas con bcrypt (algoritmo de hashing seguro)
- Sistema de tokens de acceso con expiración (7 días)
- Sesiones Flask con cookies HttpOnly para prevenir XSS
- Validación de tokens en cada request para rutas administrativas

**Justificación:** El uso de bcrypt es estándar en la industria para almacenamiento seguro de contraseñas. Los tokens proporcionan seguridad adicional y permiten sesiones persistentes sin comprometer la seguridad.

### 1.4 Validación Multi-capa

**Estrategia:**
- **Frontend:** Validación HTML5 y JavaScript para UX
- **Backend:** Validación exhaustiva en Python antes de ejecutar queries
- **Base de Datos:** Constraints, CHECK constraints, Foreign Keys, Triggers

**Razón:** La validación en múltiples capas asegura integridad de datos incluso si una capa falla, siguiendo el principio de "defensa en profundidad".

### 1.5 Modelo de Datos

**Decisiones clave:**
- Uso de ENUMs para valores fijos (estados, tipos, roles)
- Claves primarias compuestas donde corresponde (sala, programa_academico)
- Índices en campos frecuentemente consultados
- Foreign Keys con ON DELETE RESTRICT para mantener integridad referencial

**Justificación:** Los ENUMs garantizan consistencia de datos. Las claves compuestas reflejan la realidad del dominio (una sala se identifica por nombre + edificio). Los índices mejoran el rendimiento de consultas frecuentes.

---

## 2. Mejoras Implementadas o Consideradas en el Modelo de Datos

### 2.1 Mejoras Implementadas

#### 2.1.1 Tabla `access_token`
**Mejora:** Sistema de tokens de acceso para autenticación segura.

**Beneficios:**
- Permite sesiones persistentes sin almacenar contraseñas
- Tokens con expiración automática (7 días)
- Registro de último acceso para auditoría
- Índices optimizados para búsquedas frecuentes

#### 2.1.2 Campo `is_admin` en `participante`
**Mejora:** Agregado para distinguir usuarios administrativos.

**Beneficios:**
- Control de acceso granular
- Facilita la implementación de rutas administrativas
- Permite escalabilidad futura (múltiples niveles de permisos)

#### 2.1.3 Constraint `chk_bloque_hora` en `turno`
**Mejora:** Asegura que los turnos sean exactamente de 1 hora.

**Beneficio:** Garantiza integridad de datos a nivel de base de datos, independientemente de la aplicación.

#### 2.1.4 Constraint `chk_fechas_sancion` en `sancion_participante`
**Mejora:** Valida que fecha_fin > fecha_inicio.

**Beneficio:** Previene sanciones inválidas a nivel de base de datos.

#### 2.1.5 Unique Key `uk_reserva_sala_fecha_turno`
**Mejora:** Previene doble reserva de la misma sala en el mismo turno.

**Beneficio:** Garantiza unicidad a nivel de base de datos.

### 2.2 Mejoras Consideradas pero No Implementadas

#### 2.2.1 Tabla de Auditoría
**Consideración:** Crear tabla `auditoria` para registrar todos los cambios.

**Razón de no implementación:** Agregaría complejidad sin ser requerido explícitamente. Se puede implementar en el futuro con triggers.

#### 2.2.2 Soft Delete
**Consideración:** Agregar campo `deleted_at` para borrado lógico.

**Razón de no implementación:** Los requisitos especifican ABM completo, incluyendo baja física. Soft delete podría agregarse como mejora futura.

#### 2.2.3 Tabla de Historial de Reservas
**Consideración:** Mantener historial completo de cambios de estado.

**Razón de no implementación:** El estado actual en `reserva` es suficiente para los reportes requeridos. Historial completo sería útil para análisis avanzado.

---

## 3. Bitácora del Trabajo Realizado

### Fase 1: Análisis y Diseño (Semana 1-2)
- [x] Análisis de requisitos del PDF
- [x] Diseño del modelo de datos (ER conceptual)
- [x] Normalización del esquema
- [x] Definición de restricciones de negocio

### Fase 2: Implementación de Base de Datos (Semana 3-4)
- [x] Creación del script SQL (`schema.sql`)
- [x] Implementación de tablas con constraints
- [x] Creación de índices
- [x] Scripts adicionales (`add_admin_support.sql`, `add_token_support.sql`)
- [x] Generador de datos de prueba (`generate_sample_data.py`)

### Fase 3: Backend Python (Semana 5-6)
- [x] Implementación de `DatabaseManager` (conexión y queries)
- [x] Implementación de `AuthManager` (autenticación)
- [x] Implementación de `ReservationManager` (lógica de reservas)
- [x] Implementación de `ReportManager` (consultas de reportes)
- [x] Implementación de `DataInitializer` (poblado inicial)
- [x] Aplicación de consola (`main.py`)

### Fase 4: Aplicación Web (Semana 7-8)
- [x] Configuración de Flask (`app.py`)
- [x] Implementación de rutas públicas (login, registro)
- [x] Implementación de rutas de usuario (dashboard, reservas, salas)
- [x] Implementación de rutas administrativas (ABM completo)
- [x] Sistema de decoradores (`@login_required`, `@admin_required`)
- [x] Templates HTML con Jinja2
- [x] Estilos CSS básicos

### Fase 5: Reportes (Semana 9)
- [x] Implementación de los 8 reportes requeridos
- [x] Implementación de 3 reportes adicionales sugeridos
- [x] Templates para visualización de reportes
- [x] Integración en menú administrativo

### Fase 6: Seguridad y Validación (Semana 10)
- [x] Implementación de hash bcrypt para contraseñas
- [x] Sistema de tokens de acceso
- [x] Validación en frontend (HTML5)
- [x] Validación en backend (Python)
- [x] Constraints en base de datos
- [x] Consultas parametrizadas (prevención SQL injection)

### Fase 7: Mejoras y Optimización (Semana 11)
- [x] Optimización de consultas SQL
- [x] Mejora de UX (mensajes flash, redirecciones)
- [x] Manejo de errores
- [x] Documentación (README.md, RUN_INSTRUCTIONS.md)

### Fase 8: Entrega Final (Semana 12)
- [x] Revisión completa del código
- [x] Pruebas de funcionalidad
- [x] Creación de este informe
- [x] Preparación para defensa

---

## 4. Bibliografía

### Libros y Documentación Oficial
1. **MySQL Documentation.** (2025). *MySQL 8.0 Reference Manual*. Oracle Corporation.  
   https://dev.mysql.com/doc/

2. **Flask Documentation.** (2025). *Flask 3.0 Documentation*. Pallets Projects.  
   https://flask.palletsprojects.com/

3. **Silberschatz, A., Korth, H. F., & Sudarshan, S.** (2020). *Database System Concepts* (7th ed.). McGraw-Hill Education.

4. **Connolly, T., & Begg, C.** (2015). *Database Systems: A Practical Approach to Design, Implementation, and Management* (6th ed.). Pearson.

### Artículos y Recursos Web
5. **OWASP Foundation.** (2024). *OWASP Top 10 - 2021: The Ten Most Critical Web Application Security Risks*.  
   https://owasp.org/www-project-top-ten/

6. **Python Software Foundation.** (2025). *Python 3.13 Documentation*.  
   https://docs.python.org/3/

7. **bcrypt Documentation.** (2024). *bcrypt 4.1.2 Documentation*.  
   https://github.com/pyca/bcrypt/

### Estándares y Buenas Prácticas
8. **PEP 8.** (2001). *Style Guide for Python Code*. Python Software Foundation.  
   https://pep8.org/

9. **RFC 7231.** (2014). *Hypertext Transfer Protocol (HTTP/1.1): Semantics and Content*. IETF.

10. **NIST.** (2020). *Digital Identity Guidelines: Authentication and Lifecycle Management* (SP 800-63B).  
    https://pages.nist.gov/800-63-3/

### Recursos de Diseño de Bases de Datos
11. **Date, C. J.** (2019). *An Introduction to Database Systems* (8th ed.). Pearson.

12. **Garcia-Molina, H., Ullman, J. D., & Widom, J.** (2008). *Database Systems: The Complete Book* (2nd ed.). Prentice Hall.

---

## 5. Conclusiones

El sistema desarrollado cumple con todos los requisitos funcionales y técnicos especificados en el documento de trabajo obligatorio. Se implementó una solución robusta que:

- Garantiza la integridad de datos mediante restricciones a nivel de base de datos
- Proporciona seguridad mediante autenticación y autorización adecuadas
- Ofrece una interfaz web intuitiva para usuarios y administradores
- Permite la generación de reportes para análisis y toma de decisiones
- Mantiene código limpio y bien documentado

Las mejoras implementadas (sistema de tokens, validación multi-capa, constraints adicionales) fortalecen la seguridad y confiabilidad del sistema, preparándolo para un entorno de producción.

---

**Fin del Informe**

