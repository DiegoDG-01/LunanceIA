# Docker Setup Guide

Esta guía te ayudará a configurar y gestionar los servicios de Docker para el proyecto Lunance IA.

## 📋 Tabla de Contenidos

- [Configuración con Docker Compose](#configuración-con-docker-compose)
- [Configuración de MySQL con Docker](#configuración-de-mysql-con-docker)
- [Correo en local con Mailpit](#-correo-en-local-con-mailpit)
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

# Autenticación: la API firma sus propios tokens (EdDSA/Ed25519).
# Genera estas tres con los comandos de openssl del README
JWT_PRIVATE_KEY='-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----'
JWT_PUBLIC_KEY='-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----'
REFRESH_ROTATION_KEY=una_clave_larga_y_aleatoria_de_al_menos_32_caracteres
ACCESS_TOKEN_EXPIRE_MINUTES=10

# AI Settings (agentes de imagen y asesoría de gastos)
AI_PROVIDER=google-gla
AI_MODEL_ID=gemini-2.5-flash
AI_API_KEY=tu_clave_api

# Correo (verificación de correo y recuperación de contraseña)
# PROD: Resend, obligatorio (la API no arranca sin RESEND_API_KEY y un enlace https).
EMAIL_FROM="Lunance <no-reply@tu-dominio>"   # dominio verificado en Resend
RESEND_API_KEY=re_xxxxxxxx
EMAIL_LINK_BASE_URL=https://tu-frontend      # la web que abre /verify-email y /reset-password
# DEV: sin EMAIL_BACKEND se usa SMTP; docker-compose apunta SMTP_HOST al servicio `mailpit`.
```

**Configuración de ENVIRONMENT:**
- **PROD**: Para producción - CORS con lista cerrada de dominios, logging optimizado
- **DEV**: Para desarrollo - CORS con `FRONTEND_URL` (un solo origen), logging detallado

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
- **Mailpit** (solo con `--profile dev`): http://localhost:8025

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

## 📬 Correo en local con Mailpit

En desarrollo (`ENVIRONMENT=DEV`) la API manda los correos (verificación de registro, recuperación y cambio de contraseña) por SMTP a [Mailpit](https://mailpit.axllent.org/), un buzón falso: nada sale a Internet y todo se ve en su interfaz web.

**Con Docker Compose**, Mailpit es el servicio `mailpit` del perfil `dev` (no arranca en producción):

```bash
docker compose --profile dev up --build -d
```

- UI: http://localhost:8025 (publicada solo en `127.0.0.1`)
- SMTP: `mailpit:1025`, solo dentro de la red de Docker; el servicio `api` ya tiene `SMTP_HOST=mailpit` y `SMTP_PORT=1025`

**Con la API fuera de Docker** (`uvicorn` en tu máquina), levanta Mailpit publicando también el SMTP en local; los valores por defecto (`SMTP_HOST=localhost`, `SMTP_PORT=1025`) ya apuntan ahí:

```bash
docker run -d --name lunance-mailpit -p 127.0.0.1:8025:8025 -p 127.0.0.1:1025:1025 axllent/mailpit:v1.33.1
```

Los enlaces de los correos apuntan a `EMAIL_LINK_BASE_URL` (o, si está vacío, a `FRONTEND_URL`). En producción se usa Resend (`EMAIL_BACKEND=resend`); falta verificar el dominio del remitente en Resend (SPF, DKIM y DMARC).

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
