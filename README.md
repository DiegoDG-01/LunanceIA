# Lunance IA - Personal Finance Management API

Lunance IA es una API REST completa para la gestión de finanzas personales construida con **Clean Architecture + Domain-Driven Design** usando FastAPI y Python. Implementa un backend empresarial robusto con separación clara de responsabilidades, patrones CQRS, y arquitectura hexagonal para el seguimiento de ingresos, gastos, presupuestos, suscripciones, metas de ahorro y recordatorios financieros.

## 🚀 Características Principales

### 💰 Gestión Financiera Completa
- **Seguimiento de Transacciones**: Registro detallado de ingresos y gastos
- **Gestión de Cuentas**: Soporte para múltiples tipos de cuenta (efectivo, débito, crédito, ahorros, inversión)
- **Presupuestos Inteligentes**: Configuración de límites de gasto por categoría con alertas automáticas
- **Metas de Ahorro**: Establecimiento y seguimiento de objetivos financieros
- **Suscripciones**: Control de pagos recurrentes con generación automática de cargos

### 🔐 Seguridad y Autenticación
- **Autenticación JWT**: Sistema seguro basen tokens
- **Encriptación de Contraseñas**: Usando Passlib para máxima seguridad
- **Autenticación OAuth2**: Estándar de la industria para APIs

### 🎯 Organización y Personalización
- **Sistema de Categorías**: Clasificación flexible de transacciones
- **Etiquetas Personalizadas**: Organización custom con colores
- **Recordatorios**: Sistema de notificaciones para pagos y revisiones
- **Soporte Multi-moneda**: Configuración por defecto en MXN

## 🛠️ Stack Tecnológico

### Core Technologies
- **Framework**: FastAPI 0.115.12
- **Base de Datos**: MySQL con SQLAlchemy 2.0.41 ORM
- **Migraciones**: Alembic 1.16.1
- **Autenticación**: JWT + OAuth2 (python-jose 3.5.0)
- **Validación**: Pydantic 2.11.5 con soporte de email
- **Seguridad**: Passlib 1.7.4 + bcrypt 4.3.0
- **IA**: Google Gemini API 1.22.0

### Development Tools
- **Package Manager**: uv (gestor moderno de paquetes Python)
- **Code Quality**: Ruff 0.11.13 (linting & formatting)
- **Testing**: pytest 8.4.1 + pytest-asyncio + httpx
- **Pre-commit**: Hooks automáticos de calidad de código

## 📁 Estructura del Proyecto

```
src/
├── main.py                 # Aplicación principal FastAPI
├── domain/                 # Lógica de negocio central
├── application/            # Casos de uso y comandos
├── infrastructure/         # Base de datos y servicios externos
├── presentation/           # API REST y endpoints
├── shared/                 # Utilidades y recursos compartidos
└── tests/                  # Pruebas unitarias e integración
```

> 📖 **Documentación Técnica**: Para más detalles sobre la arquitectura, patrones de diseño y estructura interna, consulta [ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 🚀 Instalación y Configuración

Tienes dos opciones para ejecutar Lunance IA:

### 🐳 Opción 1: Docker Compose (Recomendado para uso rápido)

**Prerrequisitos:**
- Docker y Docker Compose instalados

**Pasos:**

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd Lunance
```

2. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env y cambiar los valores CHANGE_ME
# IMPORTANTE: Configurar ENVIRONMENT=PROD para producción o ENVIRONMENT=DEV para desarrollo
```

3. **Ejecutar con Docker Compose**
```bash
docker-compose up --build -d
```

4. **Verificar la instalación**
- API: http://localhost:8000
- Documentación: http://localhost:8000/docs

> 🐳 **Para configuración detallada de Docker**: Consulta [DOCKER_SETUP.md](docs/DOCKER_SETUP.md)

### 🛠️ Opción 2: Desarrollo Local

**Prerrequisitos:**
- Python 3.8+
- Docker (para MySQL)
- pip o uv (recomendado)

**Pasos:**

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd Lunance
```

2. **Instalar dependencias**
```bash
# Con uv (recomendado)
uv sync

# O con pip tradicional
pip install -e .
```

3. **Configurar MySQL**
```bash
# Levantar MySQL con Docker
docker run --name lunance-mysql \
  -e MYSQL_ROOT_PASSWORD=luna_root \
  -e MYSQL_DATABASE=lunance \
  -e MYSQL_USER=luna \
  -e MYSQL_PASSWORD=luna_root \
  -p 3306:3306 \
  -d mysql:8.0
```

4. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env para desarrollo local:
# - DB_HOST=localhost
# - ENVIRONMENT=DEV (importante para CORS y logs de desarrollo)
```

5. **Ejecutar migraciones y iniciar servidor**
```bash
alembic upgrade head
uvicorn src.main:app --reload
```

> 🐳 **Para gestión avanzada de contenedores**: Consulta [DOCKER_SETUP.md](docs/DOCKER_SETUP.md)

## 📖 Uso de la API

La API REST de Lunance IA v2 utiliza autenticación JWT y sigue los principios de Clean Architecture.

### Endpoints Principales
- 🔐 **Autenticación**: `/api/v2/auth/` (login, register, refresh, logout)
- 💳 **Cuentas**: `/api/v2/account/` (CRUD completo para gestión de cuentas)
- 💰 **Transacciones**: `/api/v2/transaction/` (próximamente)

### Documentación Interactiva
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 🧪 Cliente HTTP - Colección Bruno
Lunance IA incluye una colección completa de [Bruno](https://www.usebruno.com/) con todos los endpoints de la API pre-configurados.

**Ubicación**: `http/bruno collection/Lunance IA.json`

**Uso**:
1. Instala Bruno desde [usebruno.com](https://www.usebruno.com/)
2. Abre Bruno y selecciona "Open Collection"
3. Navega a `http/bruno collection/` y selecciona el archivo JSON
4. Configura las variables de entorno según tu setup (local/producción)
5. Ejecuta las peticiones pre-configuradas

> 💡 **Ventajas**: Bruno es un cliente API de código abierto, offline-first, que guarda las colecciones en archivos JSON planos (ideal para Git). No requiere cuenta ni sincronización en la nube.

> 📋 **Guía Completa de API**: Para ejemplos detallados, autenticación JWT, códigos de error y flujos completos, consulta [API_USAGE.md](docs/API_USAGE.md)

## 🏗️ Arquitectura

Lunance IA utiliza **Clean Architecture + Domain-Driven Design** para garantizar:

- ✅ **Separación clara de responsabilidades**
- ✅ **Código testeable y mantenible**
- ✅ **Escalabilidad empresarial**
- ✅ **Flexibilidad para cambios futuros**

### Capas Principales

- **Domain**: Lógica de negocio central (Entidades, Value Objects)
- **Application**: Casos de uso y comandos (CQRS)
- **Infrastructure**: Base de datos y servicios externos
- **Presentation**: API REST y validaciones

> 📖 **Documentación Completa**: Para detalles técnicos, ejemplos de código y patrones implementados, consulta [ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 🔒 Seguridad

- **JWT Access Tokens**: Expiración de 30 minutos
- **Refresh Tokens**: Expiración de 7 días con rotación
- **Password Hashing**: bcrypt con salt automático
- **OAuth2**: Flujo estándar de autenticación
- **Validación robusta**: Schemas Pydantic en todos los endpoints
- **CORS Configurado**: Según entorno (PROD: dominio específico, DEV: abierto)
- **Rate Limiting**: Protección contra abuso con límites específicos por endpoint (ej: registro 5/hora, login 10/min)
- **Manejo de Excepciones Robusto**: Sistema estandarizado de respuestas de error
- **Internacionalización (i18n)**: Mensajes de error en español e inglés

## 🛠️ Flujo de Desarrollo

### Calidad de Código
```bash
# Formateo automático
ruff format src/

# Linting
ruff check src/

# Corrección automática de issues
ruff check src/ --fix
```

### Testing
```bash
# Tests E2E (disponibles - valida API completa)
pytest src/tests/e2e/ -v

# Test específico de autenticación (22 tests)
pytest src/tests/e2e/test_auth_api.py -v

# Test de flujo completo
pytest src/tests/e2e/test_auth_api.py::TestCompleteAuthFlow -v

# Tests con output detallado para debugging
pytest src/tests/e2e/ -v -s

# Tests específicos por clase
pytest src/tests/e2e/test_auth_api.py::TestUserAuthentication -v
```

**Estado actual:**
- ✅ **E2E Tests**: 22 tests funcionando (API coverage 100%)
- 🚧 **Unit/Integration Tests**: En desarrollo
- ⚠️ **Coverage**: No disponible (tests HTTP externos)

> 🧪 **Documentación Completa de Tests**: Para configuración, comandos específicos y debugging, consulta [TEST USAGE](src/tests/TEST.md)

### Base de Datos
```bash
# Crear nueva migración
alembic revision --autogenerate -m "Descripción del cambio"

# Aplicar migraciones
alembic upgrade head

# Revertir migración
alembic downgrade -1

# Ver historial de migraciones
alembic history
```

### Desarrollo con uv
```bash
# Agregar nueva dependencia
uv add fastapi

# Agregar dependencia de desarrollo
uv add --dev pytest

# Actualizar dependencias
uv sync

# Crear entorno virtual
uv venv

# Activar entorno
source .venv/bin/activate  # Linux/macOS
# o
.venv\Scripts\activate     # Windows
```

## 🤝 Contribución

¡Las contribuciones son bienvenidas! Este proyecto sigue estándares profesionales de desarrollo.

### Inicio Rápido
1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

> 📋 **Guía Completa**: Para configuración del entorno, estándares de código, testing y flujo de desarrollo, consulta [CONTRIBUTING.md](docs/CONTRIBUTING.md)

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🐛 Reporte de Problemas

Si encuentras algún problema o tienes sugerencias, por favor crea un issue en el repositorio.

---

**Lunance IA** - Tu asistente inteligente para el manejo de finanzas personales 💰✨