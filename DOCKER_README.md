# Guía de Dockerización
## Sistema de Gestión de Reservas de Salas de Estudio - UCU

## Requisitos Previos

- Docker Engine 20.10+
- Docker Compose 2.0+

## Inicio Rápido

### 1. Construir y Levantar Servicios

```bash
docker-compose up -d
```

Esto creará y levantará:
- Contenedor MySQL con la base de datos
- Contenedor Flask con la aplicación web

### 2. Acceder a la Aplicación

Una vez que los contenedores estén corriendo, accede a:
```
http://localhost:5000
```

### 3. Verificar Estado

```bash
docker-compose ps
```

### 4. Ver Logs

```bash
# Todos los servicios
docker-compose logs -f

# Solo la aplicación web
docker-compose logs -f web

# Solo la base de datos
docker-compose logs -f db
```

## Comandos Útiles

### Detener Servicios
```bash
docker-compose stop
```

### Reiniciar Servicios
```bash
docker-compose restart
```

### Detener y Eliminar Contenedores
```bash
docker-compose down
```

### Detener, Eliminar Contenedores y Volúmenes
```bash
docker-compose down -v
```
⚠️ **Advertencia:** Esto eliminará todos los datos de la base de datos.

### Reconstruir Imágenes
```bash
docker-compose build --no-cache
```

### Ejecutar Comandos en Contenedores

**En el contenedor de la aplicación:**
```bash
docker-compose exec web bash
```

**En el contenedor de MySQL:**
```bash
docker-compose exec db mysql -u root -prootpassword UCU_SalasDeEstudio
```

## Configuración

### Variables de Entorno

Edita `docker-compose.yml` para cambiar:
- `MYSQL_ROOT_PASSWORD`: Contraseña del root de MySQL
- `MYSQL_USER` / `MYSQL_PASSWORD`: Usuario y contraseña de la aplicación
- `SECRET_KEY`: Clave secreta de Flask (¡cambiar en producción!)

### Puertos

- **5000**: Aplicación web Flask
- **3306**: MySQL (accesible desde el host)

### Volúmenes

- `mysql_data`: Datos persistentes de MySQL
- `./logs`: Logs de la aplicación (si se implementa)

## Scripts SQL Automáticos

Los siguientes scripts se ejecutan automáticamente al inicializar MySQL:
1. `schema.sql` - Esquema base
2. `add_admin_support.sql` - Soporte de administradores
3. `add_token_support.sql` - Sistema de tokens
4. `security_enhancements.sql` - Mejoras de seguridad

## Solución de Problemas

### La aplicación no se conecta a la base de datos

1. Verifica que MySQL esté listo:
```bash
docker-compose exec db mysqladmin ping -h localhost -u root -prootpassword
```

2. Revisa los logs:
```bash
docker-compose logs db
docker-compose logs web
```

### Error al construir la imagen

```bash
docker-compose build --no-cache
```

### Reiniciar desde cero

```bash
docker-compose down -v
docker-compose up -d --build
```

## Producción

Para producción, considera:

1. **Cambiar todas las contraseñas** en `docker-compose.yml`
2. **Usar variables de entorno** para secretos (no hardcodear)
3. **Configurar HTTPS** con un reverse proxy (nginx)
4. **Backups regulares** del volumen `mysql_data`
5. **Monitoreo** y logging apropiados
6. **Límites de recursos** en `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 512M
```

## Estructura de Archivos Docker

```
.
├── Dockerfile              # Imagen de la aplicación
├── docker-compose.yml      # Orquestación de servicios
├── .dockerignore          # Archivos excluidos
└── DOCKER_README.md       # Esta guía
```

