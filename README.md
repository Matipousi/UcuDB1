# UCU Study Room Reservation System

Sistema web para la gestión de reservas de salas de estudio en la UCU.

## Características

- **Autenticación**: Registro e inicio de sesión con hash de contraseñas bcrypt
- **Gestión de Reservas**: Crear reservas con validación exhaustiva
- **Control de Asistencia**: Actualizar asistencia y sistema automático de sanciones
- **Reportes**: Ver reservas activas, estadísticas de uso y usuarios sancionados
- **ABM Completo**: Gestión de participantes, salas, reservas y sanciones
- **Seguridad**: Consultas parametrizadas para prevenir inyección SQL

## Requisitos

- Python 3.8+
- MySQL 5.7+ o MariaDB 10.3+
- Navegador web moderno

## Instalación

### 1. Crear Entorno Virtual (Recomendado)

En sistemas como Arch Linux/CachyOS que tienen entornos gestionados externamente, es necesario usar un entorno virtual:

```bash
python -m venv venv
```

### 2. Instalar Dependencias

**Opción A: Usando el pip del entorno virtual directamente:**
```bash
./venv/bin/pip install -r requirements.txt
```

**Opción B: Activando el entorno virtual (bash/zsh):**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Opción C: Activando el entorno virtual (fish shell):**
```bash
source venv/bin/activate.fish
pip install -r requirements.txt
```

### 3. Configurar Base de Datos

Asegúrate de que MySQL esté ejecutándose y crea la base de datos usando el esquema SQL:

```bash
mysql -u root -p < schema.sql
```

O crea manualmente la base de datos y ejecuta los comandos SQL desde `schema.sql`.

### 4. Configurar Variables de Entorno (Opcional)

Puedes configurar la conexión a la base de datos usando variables de entorno:

```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=tu_contraseña
export DB_NAME=UCU_SalasDeEstudio
export SECRET_KEY=tu_clave_secreta
```

O modifica directamente las variables en `app.py`:

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'tu_contraseña',
    'database': 'UCU_SalasDeEstudio'
}
```

### 5. Ejecutar la Aplicación Web

**Opción A: Usando scripts de ejecución (Recomendado)**

**En Linux/macOS:**
```bash
chmod +x run_web.sh
./run_web.sh
```

**En Windows:**
```batch
run_web.bat
```

**Opción B: Usando el Python del entorno virtual directamente**

**En Linux/macOS:**
```bash
./venv/bin/python app.py
```

**En Windows:**
```batch
venv\Scripts\python.exe app.py
```

**Opción C: Activando el entorno virtual primero**

**En Linux/macOS (bash/zsh):**
```bash
source venv/bin/activate
python app.py
```

**En Linux/macOS (fish shell):**
```bash
source venv/bin/activate.fish
python app.py
```

**En Windows:**
```batch
venv\Scripts\activate.bat
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Uso

### Inicio de Sesión

1. Accede a `http://localhost:5000`
2. Si no tienes cuenta, regístrate primero
3. Inicia sesión con tu email y contraseña

### Funcionalidades Principales

#### ABM de Participantes
- **Listar**: Ver todos los participantes registrados
- **Crear**: Registrar nuevos participantes (estudiantes o docentes)
- **Editar**: Modificar información de participantes
- **Eliminar**: Eliminar participantes del sistema

#### ABM de Salas
- **Listar**: Ver todas las salas disponibles
- **Crear**: Agregar nuevas salas (libre, posgrado, docente)
- **Editar**: Modificar capacidad y tipo de sala
- **Eliminar**: Eliminar salas del sistema

#### ABM de Reservas
- **Listar**: Ver todas las reservas (activas, canceladas, finalizadas)
- **Crear**: Hacer una nueva reserva
  - Seleccionar sala, fecha y turno
  - Agregar participantes (CIs separados por coma)
  - El sistema valida automáticamente:
    - Máximo 2 horas por día por edificio
    - Máximo 3 reservas activas por semana
    - Capacidad de la sala
    - Acceso según tipo de sala (libre/posgrado/docente)
    - Sanciones activas
- **Editar**: Cambiar estado de la reserva
- **Control de Asistencia**: Marcar asistencia de participantes
  - Si ningún participante asiste, se aplican sanciones automáticas de 2 meses
- **Eliminar**: Eliminar reservas

#### ABM de Sanciones
- **Listar**: Ver todas las sanciones (activas y finalizadas)
- **Crear**: Crear sanciones manualmente
- **Editar**: Modificar fechas de sanciones
- **Eliminar**: Eliminar sanciones

### Reportes y Consultas

El sistema incluye los siguientes reportes:

#### Reportes Requeridos
1. **Salas Más Reservadas**: Ranking de salas por cantidad de reservas
2. **Turnos Más Demandados**: Ranking de turnos por cantidad de reservas
3. **Promedio de Participantes por Sala**: Análisis del promedio de participantes
4. **Reservas por Carrera y Facultad**: Reservas agrupadas por programa académico
5. **Porcentaje de Ocupación por Edificio**: Análisis de ocupación por edificio
6. **Reservas y Asistencias de Profesores y Alumnos**: Estadísticas por rol y tipo
7. **Sanciones para Profesores y Alumnos**: Cantidad de sanciones por categoría
8. **Porcentaje de Reservas Utilizadas**: Análisis de reservas efectivamente usadas vs. canceladas/no asistidas

#### Reportes Adicionales Sugeridos
1. **Reservas por Mes**: Análisis mensual de reservas
2. **Participantes Más Activos**: Top 20 participantes con más reservas
3. **Eficiencia de Uso de Salas**: Análisis de eficiencia y tasa de uso

## Datos de Ejemplo

Al ejecutar la aplicación por primera vez, se poblarán automáticamente las tablas vacías con datos de ejemplo:

- **Turnos**: Bloques horarios de 8:00 AM a 11:00 PM
- **Facultades**: Ingeniería, Ciencias Empresariales, Humanidades
- **Edificios**: Edificio Central, Edificio Norte
- **Salas**: 
  - Sala A, Sala B (libre)
  - Sala C (posgrado)
  - Sala E (docente)
- **Programas Académicos**: 
  - Ingeniería en Sistemas (grado)
  - Maestría en Informática (posgrado)
  - Administración (grado)

## Estructura del Proyecto

```
ObligatorioDB/
├── app.py                 # Aplicación Flask principal
├── main.py               # Lógica de negocio (reutilizada)
├── schema.sql            # Esquema de base de datos
├── requirements.txt      # Dependencias Python
├── README.md             # Este archivo
├── templates/            # Plantillas HTML
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── participantes/
│   ├── salas/
│   ├── reservas/
│   ├── sanciones/
│   └── reportes/
└── static/               # Archivos estáticos (CSS, JS)
    ├── css/
    └── js/
```

## Seguridad

- **Hash de Contraseñas**: Usa bcrypt para almacenamiento seguro de contraseñas
- **Consultas Parametrizadas**: Todas las consultas a la base de datos usan parámetros para prevenir inyección SQL
- **Validación de Entrada**: Validación exhaustiva antes de crear reservas
- **Sesiones**: Uso de sesiones Flask para autenticación

## Restricciones de Reserva

El sistema implementa las siguientes reglas:

1. **Bloques horarios**: Solo se pueden reservar bloques de 1 hora (8:00-9:00, 9:00-10:00, etc.)
2. **Límite diario**: Máximo 2 horas por día por edificio (excepto para docentes y posgrado en salas exclusivas)
3. **Límite semanal**: Máximo 3 reservas activas por semana (excepto para docentes y posgrado en salas exclusivas)
4. **Capacidad**: El número de participantes no puede exceder la capacidad de la sala
5. **Tipo de sala**: 
   - Salas "libre": Profesores, estudiantes de grado o posgrado
   - Salas "posgrado": Solo estudiantes de posgrado
   - Salas "docente": Solo profesores
6. **Sanciones**: Usuarios con sanciones activas no pueden hacer reservas

## Notas

- La aplicación original de consola (`main.py`) sigue disponible para uso en terminal
- La aplicación web (`app.py`) reutiliza toda la lógica de negocio de `main.py`
- Todos los reportes están disponibles desde el menú de navegación

## Dockerización

El proyecto incluye soporte completo para Docker y Docker Compose para facilitar el despliegue.

### Requisitos
- Docker
- Docker Compose

### Ejecutar con Docker Compose

1. **Construir y levantar los servicios:**
```bash
docker-compose up -d
```

2. **Ver logs:**
```bash
docker-compose logs -f
```

3. **Detener servicios:**
```bash
docker-compose down
```

4. **Detener y eliminar volúmenes (incluyendo datos de BD):**
```bash
docker-compose down -v
```

### Estructura Docker

- **Dockerfile**: Imagen de la aplicación Flask
- **docker-compose.yml**: Orquestación de servicios (app + MySQL)
- **.dockerignore**: Archivos excluidos de la imagen

Los scripts SQL se ejecutan automáticamente al inicializar el contenedor de MySQL.

### Variables de Entorno en Docker

Las variables de entorno se configuran en `docker-compose.yml`. Para producción, modifica:
- `MYSQL_ROOT_PASSWORD`
- `SECRET_KEY`
- Credenciales de base de datos

## Soporte

Para problemas o consultas, revisa los logs de la aplicación o contacta al equipo de desarrollo.

## Repositorio

Este proyecto está disponible en GitHub: https://github.com/Matipousi/UcuDB1

**Nota:** Asegúrate de que el repositorio esté configurado como público si es un requisito del proyecto.
