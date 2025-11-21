# Dockerfile para Sistema de Gestión de Reservas de Salas de Estudio - UCU
FROM python:3.13-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear directorio para logs (si es necesario)
RUN mkdir -p /app/logs

# Exponer puerto de Flask
EXPOSE 5000

# Variables de entorno por defecto
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Comando por defecto (se puede sobrescribir en docker-compose)
CMD ["python", "app.py"]

