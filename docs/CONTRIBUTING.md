# 🤝 Guía de Contribución - Lunance IA

¡Gracias por tu interés en contribuir a Lunance IA! Este documento te guiará para hacer contribuciones efectivas al proyecto.

## 📋 Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Configuración del Entorno](#configuración-del-entorno)
- [Flujo de Contribución](#flujo-de-contribución)
- [Estándares de Código](#estándares-de-código)
- [Testing](#testing)
- [Documentación](#documentación)
- [Tipos de Contribuciones](#tipos-de-contribuciones)

## 📜 Código de Conducta

Al participar en este proyecto, te comprometes a mantener un ambiente respetuoso y colaborativo. Esperamos:

- ✅ **Respeto**: Trata a todos con cortesía y profesionalismo
- ✅ **Inclusión**: Acepta diferentes perspectivas y experiencias
- ✅ **Constructividad**: Ofrece críticas constructivas y útiles
- ❌ **No toleramos**: Lenguaje ofensivo, acoso o discriminación

## 🛠️ Configuración del Entorno

### Prerrequisitos

- **Python 3.13+**
- **MySQL 8.0+**
- **Git**
- **uv** (recomendado) o pip

### Setup Inicial

```bash
# 1. Fork y clonar el repositorio
git clone https://github.com/tu-usuario/lunance.git
cd lunance

# 2. Crear rama de desarrollo
git checkout -b feature/mi-nueva-funcionalidad

# 3. Configurar entorno virtual con uv
uv sync

# 4. Activar entorno virtual
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 6. Aplicar migraciones
alembic upgrade head

# 7. Instalar pre-commit hooks
pre-commit install

# 8. Verificar que todo funcione
pytest
```

### Variables de Entorno Requeridas

```env
# API Configuration
ENVIRONMENT=DEV  # DEV para desarrollo, PROD para producción

# Database Connection Details
DB_HOST=localhost  # localhost para desarrollo local
DB_PORT=3306
DB_NAME=lunance
DB_USER=luna
DB_PASSWORD=luna_root

# Auth0 Configuration
AUTH0_DOMAIN=tu_dominio.auth0.com
AUTH0_AUDIENCE=tu_api_audience
AUTH0_CLIENT_ID=tu_client_id

# GEMINI Configuration (para procesamiento de imágenes)
GEMINI_MODEL_ID=gemini-2.5-flash
GEMINI_API_KEY=tu_clave_api_gemini
```

**Nota sobre ENVIRONMENT:**
- **DEV**: Activa CORS abierto (`*`), logging detallado con stack traces
- **PROD**: CORS restrictivo (dominio específico), logging básico sin detalles sensibles

## 🔄 Flujo de Contribución

### 1. Crear Issue o Discusión

Antes de comenzar a trabajar:

- **🐛 Bug Reports**: Usa el template de bug report
- **✨ Feature Requests**: Usa el template de feature request
- **❓ Dudas**: Inicia una discusión en GitHub Discussions

### 2. Asignación y Planning

- Espera la asignación del issue antes de comenzar
- Lee la documentación técnica en [ARCHITECTURE.md](./ARCHITECTURE.md)
- Comenta tu enfoque propuesto en el issue

### 3. Desarrollo

```bash
# Crear rama específica
git checkout -b feature/nombre-descriptivo
git checkout -b bugfix/descripcion-del-bug
git checkout -b docs/actualizacion-documentacion

# Hacer commits atómicos y descriptivos
git commit -m "feat: add user authentication endpoint

- Implement JWT token generation
- Add login/logout functionality
- Include refresh token mechanism
- Add comprehensive error handling

Closes #123"
```

### 4. Pull Request

1. **Asegurar calidad**:
   ```bash
   # Ejecutar todas las verificaciones
   ruff check src/
   ruff format src/
   pytest --cov=src
   ```

2. **Crear PR** siguiendo el template
3. **Esperar revisión** del equipo
4. **Aplicar feedback** si es necesario

## 🎨 Estándares de Código

### Arquitectura y Patrones

- **Clean Architecture**: Respeta las capas de dominio, aplicación, infraestructura y presentación
- **DDD**: Usa entidades, value objects y servicios de dominio apropiadamente
- **CQRS**: Separa comandos (escritura) y consultas (lectura)
- **Repository Pattern**: Usa interfaces abstractas e implementaciones concretas

### Convenciones de Naming

```python
# Clases: PascalCase
class AccountRepository:
    pass

class CreateAccountCommand:
    pass

# Funciones y variables: snake_case
def get_user_accounts():
    pass

account_balance = Money(Decimal('100.00'))

# Constantes: UPPER_SNAKE_CASE
MAX_ACCOUNT_NAME_LENGTH = 100
DEFAULT_CURRENCY = "MXN"

# Archivos: snake_case
create_account.py  # Dentro de accounts/commands/
get_user_accounts.py  # Dentro de accounts/queries/
sqlalchemy_account_repository.py
```

### Estructura de Archivos

#### Comandos (CQRS)
```python
# src/application/accounts/commands/create_account.py
from dataclasses import dataclass
from domain.repositories.account_repository import AccountRepository

@dataclass
class CreateAccountCommand:
    user_id: str
    name: str
    account_type: AccountType
    initial_balance: Decimal = Decimal('0.00')

class CreateAccountHandler:
    def __init__(self, account_repo: AccountRepository):
        self._account_repo = account_repo

    async def handle(self, command: CreateAccountCommand) -> Account:
        # Lógica del caso de uso
        pass
```

**Nota**: Los comandos y queries están organizados por feature (accounts, transactions, etc.) con carpetas separadas para commands y queries. El nombre del archivo ya no incluye los sufijos "_command" o "_query" ya que la estructura de carpetas provee ese contexto.

#### Entidades de Dominio
```python
# src/domain/entities/account.py
from dataclasses import dataclass
from domain.objects.money import Money

@dataclass
class Account:
    id: str
    user_id: str
    name: str
    balance: Money

    @classmethod
    def create_new(cls, user_id: str, name: str) -> 'Account':
        # Factory method con validaciones
        pass

    def update_balance(self, new_balance: Money) -> None:
        # Método de dominio con reglas de negocio
        pass
```

### Manejo de Errores

```python
# Usar excepciones específicas de dominio
from shared.exceptions.domain import AccountNotFoundError, InsufficientBalanceError

# En handlers de aplicación
if not account:
    raise AccountNotFoundError(f"Account {account_id} not found")

# En endpoints
try:
    result = await handler.handle(command)
    return {"success": True, "data": result}
except AccountNotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e))
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

## 🧪 Testing

### Estrategia de Testing

```python
# Tests unitarios - Sin dependencias externas
# tests/unit/domain/test_money_value_object.py
def test_money_addition_same_currency():
    money1 = Money(Decimal('100'), 'USD')
    money2 = Money(Decimal('50'), 'USD')
    result = money1.add(money2)
    assert result.amount == Decimal('150')

# Tests de integración - Con base de datos
# tests/integration/test_account_repository.py
@pytest.mark.asyncio
async def test_create_account_integration(db_session):
    repo = SQLAlchemyAccountRepository(db_session)
    account = Account.create_new("user123", "Mi Cuenta")
    saved = await repo.save(account)
    assert saved.id is not None

# Tests de endpoints - API completa
# tests/integration/test_account_endpoints.py
@pytest.mark.asyncio
async def test_create_account_endpoint(client, auth_headers):
    response = await client.post(
        "/api/v2/account/",
        json={"name": "Test Account", "account_type": "SAVINGS"},
        headers=auth_headers
    )
    assert response.status_code == 201
```

### Cobertura Requerida

- **Mínimo**: 80% de cobertura general
- **Dominio**: 95% de cobertura (lógica de negocio crítica)
- **Endpoints**: 90% de cobertura (rutas principales)

### Comandos de Testing

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=src --cov-report=html

# Solo tests unitarios
pytest tests/unit/

# Solo tests de integración
pytest tests/integration/

# Test específico
pytest tests/unit/domain/test_money_value_object.py::test_money_addition

# Con output detallado
pytest -v -s
```

## 📚 Documentación

### Docstrings

```python
def create_account(self, command: CreateAccountCommand) -> Account:
    """
    Crea una nueva cuenta financiera para el usuario.

    Args:
        command: Comando con datos necesarios para crear la cuenta

    Returns:
        Account: La cuenta creada con ID asignado

    Raises:
        ValueError: Si los datos de la cuenta son inválidos
        UserNotFoundError: Si el usuario no existe

    Example:
        >>> command = CreateAccountCommand(
        ...     user_id="123",
        ...     name="Mi Cuenta de Ahorros",
        ...     account_type=AccountType.SAVINGS
        ... )
        >>> account = await handler.handle(command)
        >>> print(account.name)
        "Mi Cuenta de Ahorros"
    """
```

### README Updates

- Actualiza el README si cambias funcionalidad pública
- Incluye ejemplos de uso para nuevas features
- Mantén la documentación de instalación actualizada

### Comentarios en Código

```python
# ✅ Bien: Explica el "por qué"
# Usamos soft delete para mantener historial de auditoría
account.is_active = False

# ❌ Mal: Explica el "qué" (obvio del código)
# Set account to inactive
account.is_active = False

# ✅ Bien: Explica lógica de negocio compleja
# Las cuentas de crédito permiten balance negativo hasta el límite
if account.account_type == AccountType.CREDIT:
    return account.balance.amount >= account.credit_limit
```

## 🎯 Tipos de Contribuciones

### 🐛 Bug Fixes

1. **Reproduce el bug** con un test que falle
2. **Implementa la corrección** en la capa apropiada
3. **Verifica que el test** ahora pase
4. **Asegura que no rompiste** otros tests

### ✨ Nuevas Funcionalidades

1. **Diseña la funcionalidad** siguiendo Clean Architecture
2. **Implementa en capas**:
   - Dominio (entidades, value objects)
   - Aplicación (comandos, consultas)
   - Infraestructura (repositorios, servicios)
   - Presentación (endpoints, schemas)
3. **Agrega tests comprehensivos**
4. **Actualiza documentación**

### 🔧 Refactoring

1. **Mantén la funcionalidad** existente intacta
2. **Mejora la estructura** sin cambiar comportamiento
3. **Asegura que todos los tests** pasen
4. **Documenta los cambios** arquitectónicos

### 📖 Documentación

1. **Mantén consistencia** con el estilo existente
2. **Incluye ejemplos** de código cuando sea útil
3. **Actualiza referencias** cruzadas
4. **Verifica que los links** funcionen

## 🔍 Revisión de Código

### Checklist para Reviewer

- [ ] ¿Sigue Clean Architecture?
- [ ] ¿Hay tests apropiados?
- [ ] ¿El código es legible?
- [ ] ¿Las abstracciones son correctas?
- [ ] ¿Maneja errores apropiadamente?
- [ ] ¿La documentación está actualizada?

### Checklist para Autor

- [ ] ✅ Tests pasan localmente
- [ ] ✅ Linting y formatting aplicados
- [ ] ✅ Documentación actualizada
- [ ] ✅ Commits atómicos y descriptivos
- [ ] ✅ No incluye información sensible
- [ ] ✅ Sigue convenciones del proyecto

## 🚀 Deployment y Release

### Versionado Semántico

- **MAJOR** (v2.0.0): Cambios incompatibles en API
- **MINOR** (v1.1.0): Nueva funcionalidad compatible
- **PATCH** (v1.0.1): Bug fixes compatibles

### Branch Strategy

- **main**: Código en producción
- **develop**: Integración de nuevas features
- **feature/**: Desarrollo de funcionalidades
- **bugfix/**: Corrección de bugs
- **hotfix/**: Fixes urgentes para producción

## ❓ ¿Necesitas Ayuda?

- 💬 **GitHub Discussions**: Para preguntas generales
- 🐛 **GitHub Issues**: Para reportar bugs o solicitar features
- 📧 **Email**: [tu-email@ejemplo.com] para temas sensibles
- 📖 **Documentación**: Revisa [ARCHITECTURE.md](./ARCHITECTURE.md)

---

¡Gracias por contribuir a Lunance IA! 🚀💰
