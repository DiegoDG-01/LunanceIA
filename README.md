# Lunance IA - Personal Finance Management API

Lunance IA es una API REST completa para la gestión de finanzas personales construida con **Clean Architecture + Domain-Driven Design** usando FastAPI y Python. Implementa un backend empresarial robusto con separación clara de responsabilidades, patrones CQRS, y arquitectura hexagonal para el seguimiento de ingresos, gastos, presupuestos, suscripciones, metas de ahorro y recordatorios financieros.

> ### ℹ️ Este repositorio contiene únicamente el backend
>
> Aquí encontrarás la API REST y el servidor MCP. **La aplicación cliente (frontend) no forma parte de este repositorio y todavía no se ha publicado**: su liberación está prevista, pero **sin fecha estimada**.
>
> Puedes usar la API por tu cuenta desde cualquier cliente HTTP, con la colección de Bruno incluida en `http/` o con la documentación interactiva en `/docs` (disponible solo cuando `ENVIRONMENT` no es `PROD`). Consulta [API_USAGE.md](docs/API_USAGE.md) para empezar.

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
- **Autenticación propia**: Registro y login con usuario y contraseña, sin depender de proveedores externos
- **JWT Tokens**: La API emite y valida sus propios tokens (HS256); contraseñas hasheadas con bcrypt
- **Refresh tokens rotativos**: Se almacenan solo como hash SHA-256 y se revocan al cerrar sesión
- **API Keys**: Acceso programático con autenticación dual (JWT o `X-API-Key`) y permisos por scope; las keys se guardan hasheadas (SHA-256) y nunca permiten editar ni eliminar

### 🎯 Organización y Personalización
- **Sistema de Categorías**: Clasificación flexible de transacciones
- **Etiquetas Personalizadas**: Organización custom con colores
- **Recordatorios**: Sistema de notificaciones para pagos y revisiones
- **Soporte Multi-moneda**: Configuración por defecto en MXN

## 🛠️ Stack Tecnológico

### Core Technologies
- **Framework**: FastAPI 0.140+
- **Performance Engine**: Rust (fincore) con PyO3 + Maturin
- **Base de Datos**: MySQL con SQLAlchemy 2.0+ (aiomysql / pymysql)
- **Migraciones**: Alembic 1.18+
- **Autenticación**: JWT propio HS256 (python-jose 3.5+) + Refresh tokens hasheados
- **Validación**: Pydantic 2.13+ con `pydantic-settings` 2.14+
- **Hashing de contraseñas**: bcrypt 5.0+
- **Rate Limiting**: fastapi-advanced-rate-limiter 2.1+ (con Redis 7.4+)
- **IA**: pydantic-ai-slim 2.16+ con extras `[google, openai]` (Google Gemini 2.x por defecto, compatible con OpenAI/Ollama vía `AI_BASE_URL`)
- **Procesamiento de Imágenes**: Pillow 12.3+
- **Cabeceras de seguridad**: `secure` 1.0+
- **Tareas programadas**: APScheduler 3.11+ (suscripciones, ingresos, rendimientos)
- **Internacionalización**: i18n propio (es/en)

### 🦀 Motor de Cálculo Rust (Beta)
Lunance IA integra un motor de cálculo de alto rendimiento escrito en **Rust** para operaciones financieras críticas como proyecciones de inversión y simulaciones complejas. Este motor se comunica de forma transparente con Python, proporcionando lo mejor de ambos mundos: la agilidad de FastAPI y la potencia de Rust.

> 🧪 **Estado del Proyecto**: La implementación completa del motor de Rust está en proceso (Beta).

> 🔧 **Se compila e instala aparte** (`uv pip install ./fincore`) y no está en `uv.lock`, por lo que `uv sync` lo desinstala. Ver [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md#-fincore-desaparece-después-de-uv-sync).

### Development Tools
- **Package Manager**: uv (gestor moderno de paquetes Python)
- **Code Quality**: Ruff 0.14+ (linting & formatting)
- **Testing**: pytest 9.0+ + pytest-asyncio 1.3+ + pytest-cov 7.1+ + httpx 0.28+
- **Type checking**: Pyrefly 0.57+
- **Compilación Rust**: Maturin 1.12+ (en grupo `[dev]`)
- **Pruebas de carga**: Locust 2.32+ (en grupo `[dev]`)
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
git clone https://github.com/DiegoDG-01/LunanceIA.git
cd LunanceIA
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
git clone https://github.com/DiegoDG-01/LunanceIA.git
cd LunanceIA
```

2. **Instalar dependencias**
```bash
# Con uv (recomendado)
uv sync

# O con pip tradicional
pip install -e .
```

3. **Compilar el motor Rust** (necesario para las proyecciones de inversión)
```bash
# Requiere el toolchain de Rust: https://rustup.rs
uv pip install ./fincore
```

> ⚠️ `fincore` no forma parte de `uv.lock`, así que **cada `uv sync` lo desinstala**.
> Vuelve a ejecutar el comando de arriba, o usa `uv sync --inexact` para conservarlo.
> El porqué y las alternativas están en [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md#-fincore-desaparece-después-de-uv-sync).

4. **Configurar MySQL**
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

5. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env para desarrollo local:
# - DB_HOST=localhost
# - ENVIRONMENT=DEV (importante para CORS y logs de desarrollo)
# - AUTH0_DOMAIN y AUTH0_AUDIENCE: la app exige estas variables por
#   compatibilidad con el fallback legado, pero el flujo activo es JWT propio.
#   Puedes rellenarlas con cualquier valor no vacío si no usas Auth0.
```

6. **Ejecutar migraciones y iniciar servidor**
```bash
alembic upgrade head
uvicorn src.main:app --reload
```

> 🐳 **Para gestión avanzada de contenedores**: Consulta [DOCKER_SETUP.md](docs/DOCKER_SETUP.md)

## 📖 Uso de la API

La API REST de Lunance IA v2 utiliza autenticación JWT y sigue los principios de Clean Architecture.

### Endpoints Principales
- 🔐 **Autenticación**: `/api/v2/auth/` (register, login, refresh, logout, me)
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

- **Autenticación propia**: Usuario y contraseña, con contraseñas hasheadas mediante bcrypt
- **JWT Tokens**: Access tokens HS256 firmados por la API, con refresh tokens rotativos guardados como hash
- **Rate limiting de autenticación**: Límites por endpoint y por IP ante intentos fallidos
- **Validación robusta**: Schemas Pydantic en todos los endpoints
- **CORS Configurado**: Según entorno (PROD: lista cerrada de dominios, DEV/TEST: `FRONTEND_URL`)
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
# Toda la suite (unit + integration + e2e)
pytest

# Solo E2E (requieren la API levantada)
pytest src/tests/e2e/ -v

# Solo unitarios (no necesitan MySQL/Redis ni la API levantada)
pytest src/tests/unit/ -v

# Con cobertura
pytest --cov=src --cov-report=html
```

**Estado actual:**
- ✅ **E2E**: cobertura de auth, account, transaction, subscription, investment, budget, goal, transfer, installment, income, dashboard, ai, api-key, bank, category, security headers y edge cases.
- ✅ **Unit + Integration**: lógica de dominio (Money, Bank, RecurringIncome, IncomeDeposit), handlers de suscripciones, ingresos e instalaciones, lock de fila en MySQL, auth (commands + dependencies).
- 🧪 **Pyrefly** está configurado como type checker (`uv run pyrefly check`).

> 🧪 **Documentación Completa de Tests**: Para configuración, comandos específicos y debugging, consulta [TEST.md](src/tests/TEST.md)

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

> 🛠️ **¿Algo no funciona?**: Problemas conocidos del entorno de desarrollo y sus soluciones en [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

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
