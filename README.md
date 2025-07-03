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

### Prerrequisitos
- Python 3.8+
- MySQL
- pip o uv (recomendado)

### 1. Clonar el repositorio
```bash
git clone <repository-url>
cd Lunance
```

### 2. Instalar dependencias
```bash
# Con uv (recomendado) - Gestor moderno de paquetes
uv sync

# O con pip tradicional
pip install -e .
```

### 3. Configurar variables de entorno
Crear un archivo `.env` en la raíz del proyecto:
```env
# Base de datos
DATABASE_URL=mysql+pymysql://usuario:password@localhost:3306/lunance

# Autenticación JWT
SECRET_KEY=tu_clave_secreta_muy_segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
REFRESH_TOKEN_SECRET_KEY=tu_clave_secreta_refresh_muy_segura

# Configuración de aplicación
DEBUG=True
ENVIRONMENT=development

# Servicios externos (opcional)
GEMINI_API_KEY=tu_clave_api_gemini
```

### 4. Ejecutar migraciones
```bash
alembic upgrade head
```

### 5. Configurar pre-commit (opcional pero recomendado)
```bash
# Instalar pre-commit hooks para calidad de código
pre-commit install
```

### 6. Ejecutar pruebas
```bash
# Ejecutar todas las pruebas
pytest

# Con cobertura
pytest --cov=src

# Ejecutar linting
ruff check src/
ruff format src/
```

### 7. Iniciar el servidor
```bash
# Desarrollo
uvicorn src.main:app --reload

# Producción
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## 📖 Uso de la API

### Autenticación JWT
```bash
# Obtener token de acceso (API v2)
curl -X POST "http://localhost:8000/api/v2/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "tu_email@ejemplo.com",
       "password": "tu_password"
     }'

# Respuesta
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}

# Usar token en requests autenticados
curl -X GET "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Renovar token usando refresh token
curl -X POST "http://localhost:8000/api/v2/auth/refresh" \
     -H "Content-Type: application/json" \
     -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

### Endpoints API v2 (Clean Architecture)

#### 🔐 **Autenticación** - `/api/v2/auth/`
- `POST /login` - Iniciar sesión
- `POST /register` - Registrar usuario
- `POST /refresh` - Renovar token
- `POST /logout` - Cerrar sesión

#### 💳 **Cuentas** - `/api/v2/account/`
- `GET /` - Listar cuentas del usuario
- `POST /` - Crear nueva cuenta
- `GET /{account_id}` - Obtener cuenta por ID
- `PUT /{account_id}` - Actualizar cuenta
- `DELETE /{account_id}` - Eliminar cuenta

#### 💰 **Transacciones** - `/api/v2/transaction/` (Próximamente)
- `GET /` - Listar transacciones
- `POST /` - Crear transacción
- `GET /{transaction_id}` - Obtener transacción
- `PUT /{transaction_id}` - Actualizar transacción
- `DELETE /{transaction_id}` - Eliminar transacción

### Documentación Interactiva
Una vez iniciado el servidor, accede a:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

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
# Ejecutar todas las pruebas
pytest

# Pruebas con cobertura
pytest --cov=src --cov-report=html

# Pruebas específicas
pytest tests/unit/domain/  # Solo pruebas de dominio
pytest tests/integration/  # Solo pruebas de integración
pytest tests/e2e/         # Solo pruebas end-to-end

# Pruebas con output detallado
pytest -v -s
```

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