# Dockerfile para producción
FROM python:3.11-slim

# Metadatos
LABEL maintainer="estra"
LABEL description="Backend del Sistema de Indicadores - Alcaldía"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Crear directorio para archivos media
RUN mkdir -p /app/media /app/staticfiles

# Crear usuario no-root
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Recopilar archivos estáticos
RUN python manage.py collectstatic --noinput

# Exponer puerto
EXPOSE 8000

# Comando por defecto
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]