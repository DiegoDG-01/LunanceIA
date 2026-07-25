# Lunance IA - Personal Finance Management API

Lunance IA es una API REST completa para la gestión de finanzas personales construida con **Clean Architecture + Domain-Driven Design** usando FastAPI y Python. Implementa un backend empresarial robusto con separación clara de responsabilidades, patrones CQRS, y arquitectura hexagonal para el seguimiento de ingresos, gastos, presupuestos, suscripciones, metas de ahorro y recordatorios financieros.

## 🚀 Características Principales

### 💰 Gestión Financiera Completa
- **Seguimiento de Transacciones**: Registro detallado de ingresos y gastos
- **Gestión de Cuentas**: Soporte para múltiples tipos de cuenta (efectivo, débito, crédito, ahorros, inversión)
- **Inversiones**: Cálculo automático de rendimientos diarios (interés simple y compuesto) con proyecciones
- **Suscripciones**: Control de pagos recurrentes con generación automática de cargos
- **Presupuestos Inteligentes**: Configuración de límites de gasto por categoría con alertas automáticas
- **Metas de Ahorro**: Establecimiento y seguimiento de objetivos financieros
- **Tareas Programadas**: Procesamiento diario automático de suscripciones y rendimientos de inversión

### 🤖 Agentes IA
- **Análisis de Imagen**: Extrae datos (monto, categoría, descripción, fecha) de imágenes de recibos/tickets (límite: 2 por día)
- **Asesor de Gastos**: Analiza los gastos del mes actual y genera recomendaciones personalizadas de ahorro (límite: 1 por día)
- **Servidor MCP**: Expone la API como herramientas para agentes/LLM (consultar y registrar finanzas en lenguaje natural), autenticado por API Key con permisos por scope. Ver [MCP.md](docs/MCP.md)

### 🔐 Seguridad y Autenticación
- **Auth0 Integration**: Autenticación empresarial con Auth0
- **JWT Tokens**: Validación de tokens mediante Auth0
- **Autenticación OAuth2**: Estándar de la industria para APIs
- **API Keys**: Acceso programático con autenticación dual (JWT o `X-API-Key`) y permisos por scope; las keys se guardan hasheadas (SHA-256) y nunca permiten editar ni eliminar

### 🎯 Organización y Personalización
- **Sistema de Categorías**: Clasificación flexible de transacciones
- **Etiquetas Personalizadas**: Organización custom con colores
- **Recordatorios**: Sistema de notificaciones para pagos y revisiones
- **Soporte Multi-moneda**: Configuración por defecto en MXN

## 🛠️ Stack Tecnológico

### Core Technologies
- **Framework**: FastAPI 0.115+
- **Performance Engine**: Rust (fincore) con PyO3
- **Base de Datos**: MySQL con SQLAlchemy 2.0+ ORM
- **Migraciones**: Alembic 1.16+
- **Autenticación**: Auth0 + JWT (python-jose 3.5+)
- **Validación**: Pydantic 2.11+ con soporte de email
- **Seguridad**: bcrypt 4.3+ + Rate Limiting (fastapi-advanced-rate-limiter 2.1+)
- **IA**: Google Gemini API (google-genai 1.22+) + pydantic-ai-slim 1.72+ (agentes estructurados)
- **Procesamiento de Imágenes**: Pillow 12.0+

### 🦀 Motor de Cálculo Rust (Beta)
Lunance IA integra un motor de cálculo de alto rendimiento escrito en **Rust** para operaciones financieras críticas como proyecciones de inversión y simulaciones complejas. Este motor se comunica de forma transparente con Python, proporcionando lo mejor de ambos mundos: la agilidad de FastAPI y la potencia de Rust.

> 🧪 **Estado del Proyecto**: La implementación completa del motor de Rust está en proceso (Beta).

### Development Tools
- **Package Manager**: uv (gestor moderno de paquetes Python)
- **Code Quality**: Ruff 0.14+ (linting & formatting)
- **Testing**: pytest 8.4+ + pytest-asyncio + httpx
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
- Python 3.13+
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
- 🔐 **Autenticación**: `/api/v2/auth/` (me, logout) - Login/Register via Auth0
- 💳 **Cuentas**: `/api/v2/account/` (CRUD completo + activación/desactivación)
- 💰 **Transacciones**: `/api/v2/transaction/` (CRUD completo)
- 🔄 **Suscripciones**: `/api/v2/subscription/` (CRUD completo + cargos + activación)
- 📈 **Inversiones**: `/api/v2/investments/` (rendimientos históricos + proyecciones)
- 🏦 **Bancos**: `/api/v2/bank/` (catálogo de bancos)
- 🏷️ **Categorías**: `/api/v2/category/` (listado de categorías)
- 📊 **Dashboard**: `/api/v2/dashboard/` (resumen financiero)
- 🤖 **IA**: `/api/v2/ai/` (análisis de imágenes + asesor de gastos)
- 🔑 **API Keys**: `/api/v2/api-keys/` (crear/listar/revocar keys para acceso programático con scopes)

### Documentación Interactiva
> **Nota**: Swagger UI y ReDoc están deshabilitados por defecto en la configuración actual. Consulta la [Guía de API](docs/API_USAGE.md) para documentación detallada de endpoints.

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

> 🤖 **Servidor MCP (Model Context Protocol)**: Para exponer la API a agentes/LLM (herramientas disponibles, cómo ejecutarlo y probarlo), consulta [MCP.md](docs/MCP.md)

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

- **Auth0**: Autenticación y autorización empresarial
- **JWT Tokens**: Validación de tokens emitidos por Auth0
- **OAuth2**: Flujo estándar de autenticación
- **Validación robusta**: Schemas Pydantic en todos los endpoints
- **CORS Configurado**: Según entorno (PROD: dominio específico, DEV: abierto)
- **Rate Limiting**: Protección contra abuso con límites específicos por endpoint
- **Manejo de Excepciones Robusto**: Sistema estandarizado de respuestas de error
- **Internacionalización (i18n)**: Mensajes de error en español e inglés
- **Validación de Imágenes**: Verificación de formato en uploads

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
# Tests E2E (valida API completa)
pytest src/tests/e2e/ -v

# Test específico de autenticación
pytest src/tests/e2e/test_auth_api.py -v

# Tests con output detallado para debugging
pytest src/tests/e2e/ -v -s
```

**Estado actual:**
- ✅ **E2E Tests**: Tests de autenticación funcionando
- 🚧 **Unit/Integration Tests**: En desarrollo
- ⚠️ **Coverage**: Limitado (tests HTTP externos)

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

> ⚖️ **CLA obligatorio**: antes de mergear cualquier PR necesitamos que aceptes el [Contributor License Agreement](CONTRIBUTOR_LICENSE_AGREEMENT.md). Conservas el copyright de tu aporte; nos concedes permiso para distribuirlo bajo la licencia no comercial y bajo licencias comerciales futuras.

> 📋 **Guía Completa**: Para configuración del entorno, estándares de código, testing y flujo de desarrollo, consulta [CONTRIBUTING.md](docs/CONTRIBUTING.md)

Al participar aceptas el [Código de Conducta](CODE_OF_CONDUCT.md).

## 📄 Licencia

Lunance IA es **source-available**, no open source. El código está publicado bajo la [PolyForm Noncommercial License 1.0.0](LICENSE).

> ℹ️ El código es visible, forkeable y modificable, pero la restricción de uso comercial hace que **no cumpla la [Open Source Definition](https://opensource.org/osd)**. Por favor no lo describas como "open source".

**Lo que puedes hacer sin pedir permiso** — cualquier propósito no comercial:

- Uso personal, estudio, investigación, experimentación y testing
- Proyectos de aficionado y desarrollo amateur
- Modificar el código, crear obras derivadas y publicar forks
- Uso por organizaciones benéficas, instituciones educativas, organismos públicos de investigación, salud, seguridad o medio ambiente

**Lo que requiere permiso previo y por escrito** — cualquier uso comercial, incluyendo:

- Ofrecer Lunance IA (o un derivado) como producto o servicio SaaS
- Uso interno en una empresa como parte de su operación
- Reventa, distribución de pago o soporte comercial

Si tu caso encaja en el segundo grupo o no tienes claro dónde cae, escribe a **contacto@diegodg.com.mx** antes de desplegar.

Si redistribuyes el proyecto, conserva los archivos [LICENSE](LICENSE) y [NOTICE](NOTICE) tal como están.

> Required Notice: Copyright 2026 Diego DG (https://github.com/DiegoDG-01/LunanceIA)

El nombre y el logotipo **"Lunance"** no se licencian con el código: consulta [TRADEMARKS.md](TRADEMARKS.md) antes de usarlos en tu propio proyecto.

## 🐛 Reporte de Problemas

Si encuentras algún problema o tienes sugerencias, por favor crea un issue en el repositorio.

> 🔒 **¿Es una vulnerabilidad de seguridad?** No abras un issue público. Sigue el procedimiento de reporte privado descrito en [SECURITY.md](SECURITY.md).

---

**Lunance IA** - Tu asistente inteligente para el manejo de finanzas personales 💰✨
