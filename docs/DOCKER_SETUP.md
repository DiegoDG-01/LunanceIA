# Docker Setup Guide

Esta guía te ayudará a configurar y gestionar los servicios de Docker para el proyecto Lunance IA.

## 📋 Tabla de Contenidos

- [Configuración con Docker Compose](#configuración-con-docker-compose)
- [Configuración de MySQL con Docker](#configuración-de-mysql-con-docker)
- [Gestión de Contenedores](#gestión-de-contenedores)
- [Troubleshooting](#troubleshooting)

## 🐳 Configuración con Docker Compose

### Configuración Completa (API + Base de Datos)

Docker Compose levanta toda la infraestructura necesaria:

```bash
# Clonar el repositorio
git clone <repository-url>
cd Lunance

# Configurar variables de entorno
cp .env.example .env
```

Editar `.env` para Docker Compose:
```env
# API Configuration
ENVIRONMENT=PROD  # PROD para producción, DEV para desarrollo

# Database Connection Details
DB_HOST=db  # Usar "db" para Docker Compose
DB_PORT=3306
DB_NAME=lunance
DB_USER=luna
DB_PASSWORD=luna_root

# JWT Configuration (la API firma sus propios tokens)
SECRET_KEY=una_clave_larga_y_aleatoria
SECRET_KEY_REFRESH=otra_clave_distinta_y_aleatoria
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI Settings (agentes de imagen y asesoría de gastos)
AI_PROVIDER=google-gla
AI_MODEL_ID=gemini-2.5-flash
AI_API_KEY=tu_clave_api

# Auth0 (legado: el flujo activo es el JWT propio, pero settings.py
# sigue exigiendo estas dos variables para arrancar)
AUTH0_DOMAIN=placeholder.auth0.com
AUTH0_AUDIENCE=placeholder
```

**Configuración de ENVIRONMENT:**
- **PROD**: Para producción - CORS restrictivo, logging optimizado
- **DEV**: Para desarrollo - CORS abierto, logging detallado

```bash
# Construir y ejecutar todos los servicios
docker-compose up --build

# O en modo daemon (segundo plano)
docker-compose up --build -d
```

### Verificación
- **API**: http://localhost:8000
- **Documentación**: http://localhost:8000/docs
- **Base de datos**: localhost:3306

> ✅ **Las migraciones se ejecutan automáticamente al iniciar el contenedor.**

## 🗄️ Configuración de MySQL con Docker

### Para Desarrollo Local

Si solo necesitas la base de datos para desarrollo local:

```bash
# Ejecutar contenedor MySQL
docker run --name lunance-mysql \
  -e MYSQL_ROOT_PASSWORD=luna_root \
  -e MYSQL_DATABASE=lunance \
  -e MYSQL_USER=luna \
  -e MYSQL_PASSWORD=luna_root \
  -p 3306:3306 \
  -d mysql:8.0

# Verificar que el contenedor esté funcionando
docker ps
```

### Configuración de Variables de Entorno

Para desarrollo local con MySQL en Docker:
```env
# API Configuration
ENVIRONMENT=DEV  # DEV para desarrollo local

# Database Connection Details
DB_HOST=localhost  # Usar "localhost" para desarrollo local
DB_PORT=3306
DB_NAME=lunance
DB_USER=luna
DB_PASSWORD=luna_root
```

## 🛠️ Gestión de Contenedores

### Comandos Básicos

```bash
# Ver contenedores en ejecución
docker ps

# Ver todos los contenedores (incluyendo detenidos)
docker ps -a

# Detener un contenedor
docker stop lunance-mysql

# Iniciar un contenedor detenido
docker start lunance-mysql

# Reiniciar un contenedor
docker restart lunance-mysql

# Eliminar un contenedor
docker rm lunance-mysql

# Eliminar contenedor y volumen
docker rm -v lunance-mysql
```

### Docker Compose - Gestión

```bash
# Ver logs de todos los servicios
docker-compose logs

# Ver logs de un servicio específico
docker-compose logs api
docker-compose logs db

# Detener todos los servicios
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v

# Reconstruir servicios
docker-compose build

# Reconstruir sin cache
docker-compose build --no-cache
```

### Acceso a la Base de Datos

```bash
# Conectar a MySQL desde el contenedor
docker exec -it lunance-mysql mysql -u luna -p

# O con Docker Compose
docker-compose exec db mysql -u luna -p

# Ejecutar comandos SQL directamente
docker exec -it lunance-mysql mysql -u luna -p -e "SHOW DATABASES;"
```

## 🔧 Troubleshooting

### Problemas Comunes

#### Puerto 3306 ya está en uso
```bash
# Verificar qué está usando el puerto
lsof -i :3306

# Cambiar puerto en el comando Docker
docker run --name lunance-mysql \
  -e MYSQL_ROOT_PASSWORD=luna_root \
  -e MYSQL_DATABASE=lunance \
  -e MYSQL_USER=luna \
  -e MYSQL_PASSWORD=luna_root \
  -p 3307:3306 \
  -d mysql:8.0
```

#### Contenedor no inicia
```bash
# Ver logs del contenedor
docker logs lunance-mysql

# Verificar si el contenedor existe
docker ps -a | grep lunance-mysql

# Eliminar contenedor problemático
docker rm lunance-mysql
```

#### Problemas de conexión
```bash
# Verificar que el contenedor esté corriendo
docker ps

# Verificar conectividad
telnet localhost 3306

# Verificar configuración de red
docker network ls
```

#### Resetear la base de datos
```bash
# Detener y eliminar contenedor con volumen
docker stop lunance-mysql
docker rm -v lunance-mysql

# Crear nuevo contenedor
docker run --name lunance-mysql \
  -e MYSQL_ROOT_PASSWORD=luna_root \
  -e MYSQL_DATABASE=lunance \
  -e MYSQL_USER=luna \
  -e MYSQL_PASSWORD=luna_root \
  -p 3306:3306 \
  -d mysql:8.0

# Ejecutar migraciones
alembic upgrade head
```

### Limpieza del Sistema

```bash
# Eliminar contenedores detenidos
docker container prune

# Eliminar imágenes no utilizadas
docker image prune

# Eliminar volúmenes no utilizados
docker volume prune

# Limpieza completa del sistema
docker system prune -a
```

## 📚 Recursos Adicionales

- [Docker Official Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [MySQL Docker Hub](https://hub.docker.com/_/mysql)
- [FastAPI with Docker](https://fastapi.tiangolo.com/deployment/docker/)

## 🔄 Flujo de Desarrollo Recomendado

### Con Docker Compose (Recomendado)
1. Usar Docker Compose para toda la infraestructura
2. Desarrollar con hot reload activado
3. Usar volúmenes para persistencia de datos

### Con MySQL Docker + API Local
1. Levantar solo MySQL con Docker
2. Ejecutar la API localmente con `uvicorn`
3. Permite debugging más fácil de la API

### Para Producción
1. Usar Docker Compose con configuración optimizada
2. Configurar variables de entorno específicas de producción
3. Usar volúmenes nombrados para persistencia
4. Configurar redes personalizadas para seguridad
