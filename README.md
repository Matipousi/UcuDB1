# Sistema de Reservas de Salas de Estudio UCU

Aplicación web para la gestión de reservas de salas de estudio en la UCU.

## Inicio Rápido

### Opción 1: Usando Docker

Si tienes Docker instalado, esta es la forma más simple de ejecutar todo:

```bash
docker-compose up -d
```

La aplicación estará disponible en `http://localhost:5001` y la base de datos se configurará automáticamente.

Para detenerla:
```bash
docker-compose down
```

Para detener y eliminar todos los datos:
```bash
docker-compose down -v
```

### Opción 2: Ejecución Local

#### Configuración

1. **Crear un entorno virtual:**
   ```bash
   python -m venv venv
   ```

2. **Instalar dependencias:**
   ```bash
   # Linux/Mac
   ./venv/bin/pip install -r requirements.txt
   
   # Windows
   venv\Scripts\pip install -r requirements.txt
   ```

3. **Configurar la base de datos:**
   - Asegúrate de que MySQL esté ejecutándose
   - Crea la base de datos: `mysql -u root -p < schema.sql`
   - O configura la conexión en `app.py` si es necesario

#### Ejecutar la Aplicación

**Versión web** (se abre en el navegador en `http://localhost:5000`):

- **Linux/Mac:** `./run_web.sh`
- **Windows:** `run_web.bat`

**Versión consola** (interfaz de línea de comandos):

- **Linux/Mac:** `./run_console.sh`
- **Windows:** `run_console.bat`

Los scripts manejan todo automáticamente.

## Funcionalidades

- Registro e inicio de sesión de usuarios
- Crear y gestionar reservas de salas
- Control de asistencia
- Ver reportes y estadísticas
- Gestionar participantes, salas y sanciones

## Requisitos

- Python 3.8+
- MySQL 5.7+ (o usar Docker)
- Navegador web

## Ayuda

Revisa los logs si algo sale mal o consulta el código.
