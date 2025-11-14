# 🏗️ Arquitectura Técnica - Lunance IA

## Introducción

Este documento describe la arquitectura técnica detallada de Lunance IA, incluyendo la estructura interna de cada capa, patrones de diseño implementados, y las decisiones arquitectónicas tomadas para construir un sistema robusto y escalable.

## 📁 Estructura Detallada del Proyecto

### 🎯 Capa de Dominio (`src/domain/`)

La capa de dominio contiene la lógica de negocio pura sin dependencias externas.

```
domain/
├── entities/                   # Entidades de negocio con identidad
│   ├── __init__.py
│   ├── account.py             # Entidad Account con reglas de negocio
│   ├── user.py                # Entidad User con validaciones
│   └── transaction.py         # Entidad Transaction con cálculos
├── objects/                   # Value Objects inmutables
│   ├── __init__.py
│   ├── money.py              # Value Object Money con validaciones
│   └── enums.py              # Enumeraciones de negocio (AccountType, etc.)
├── repositories/              # Interfaces abstractas para persistencia
│   ├── __init__.py
│   ├── account_repository.py  # Interface para operaciones de Account
│   ├── user_repository.py     # Interface para operaciones de User
│   └── transaction_repository.py
└── services/                  # Servicios de dominio
    ├── __init__.py
    └── account_service.py     # Lógica compleja entre entidades
```

#### Características del Dominio:
- **Sin dependencias externas**: Solo usa tipos nativos de Python
- **Reglas de negocio centralizadas**: Todas las validaciones en un lugar
- **Inmutabilidad**: Value Objects son inmutables por diseño
- **Interfaces puras**: Contratos sin implementación específica

### ⚡ Capa de Aplicación (`src/application/`)

Orquesta casos de uso utilizando el patrón CQRS.

```
application/
├── commands/                  # CQRS - Operaciones de escritura
│   ├── __init__.py
│   ├── create_account_command.py    # Comando para crear cuenta
│   ├── update_account_command.py    # Comando para actualizar cuenta
│   ├── delete_account_command.py    # Comando para eliminar cuenta
│   ├── auth_commands.py             # Comandos de autenticación
│   └── register_commands.py         # Comandos de registro
├── queries/                   # CQRS - Operaciones de lectura
│   ├── __init__.py
│   ├── get_account_by_id_query.py   # Consulta específica por ID
│   └── get_user_accounts_query.py   # Consulta múltiple por usuario
├── dto/                       # Data Transfer Objects
│   ├── __init__.py
│   ├── account_dto.py         # DTO para transferencia de datos de cuenta
│   └── transaction_dto.py     # DTO para transferencia de datos transacción
└── interfaces/                # Interfaces de aplicación
    └── __init__.py
```

#### Características de Aplicación:
- **Separación CQRS**: Comandos y consultas separados
- **DTOs**: Objetos de transferencia sin lógica de negocio
- **Handlers**: Cada comando/consulta tiene su handler específico
- **Use Cases**: Orquestación de entidades de dominio

### 🔧 Capa de Infraestructura (`src/infrastructure/`)

Implementa todos los detalles técnicos y servicios externos.

```
infrastructure/
├── database/                  # Persistencia de datos
│   ├── __init__.py
│   ├── connection.py          # Configuración de conexión SQLAlchemy
│   ├── models/               # Modelos de base de datos
│   │   ├── __init__.py
│   │   ├── account.py        # Modelo SQLAlchemy para Account
│   │   ├── user.py           # Modelo SQLAlchemy para User
│   │   ├── transaction.py    # Modelo SQLAlchemy para Transaction
│   │   ├── budget.py         # Modelo SQLAlchemy para Budget
│   │   ├── category.py       # Modelo SQLAlchemy para Category
│   │   ├── subscription.py   # Modelo SQLAlchemy para Subscription
│   │   ├── tag.py            # Modelo SQLAlchemy para Tag
│   │   ├── saving_goal.py    # Modelo SQLAlchemy para SavingGoal
│   │   ├── reminder.py       # Modelo SQLAlchemy para Reminder
│   │   └── refresh_token.py  # Modelo SQLAlchemy para RefreshToken
│   └── repositories/         # Implementaciones concretas de repositorios
│       ├── __init__.py
│       ├── sqlalchemy_account_repository.py    # Implementación Account
│       ├── sqlalchemy_user_repository.py       # Implementación User
│       └── sqlalchemy_transaction_repository.py # Implementación Transaction
├── external_services/         # Integraciones con servicios externos
│   ├── __init__.py
│   └── gemini.py             # Cliente para Google Gemini AI
├── security/                 # Servicios de seguridad
│   ├── __init__.py
│   └── auth_service.py       # Autenticación JWT y manejo de tokens
└── config/                   # Configuración de aplicación
    ├── __init__.py
    └── settings.py           # Variables de entorno y configuración
```

#### Características de Infraestructura:
- **Implementaciones concretas**: De las interfaces definidas en dominio
- **Adaptadores**: Para servicios externos (Gemini AI)
- **Configuración**: Manejo centralizado de variables de entorno
- **Persistencia**: Modelos SQLAlchemy separados de entidades de dominio

### 🌐 Capa de Presentación (`src/presentation/`)

Expone la aplicación através de API REST.

```
presentation/
├── api/
│   └── v2/                   # API versión 2 con Clean Architecture
│       ├── __init__.py
│       ├── endpoints/        # Endpoints específicos por dominio
│       │   ├── __init__.py
│       │   ├── auth.py      # Endpoints de autenticación y registro
│       │   └── account.py   # Endpoints CRUD para cuentas
│       └── router.py        # Router principal que agrupa endpoints
├── schemas/                 # Schemas Pydantic para validación
│   ├── requests/            # DTOs de entrada (requests)
│   │   ├── __init__.py
│   │   ├── auth.py         # Schemas para requests de auth
│   │   ├── account.py      # Schemas para requests de cuenta
│   │   └── transaction.py  # Schemas para requests de transacción
│   └── responses/           # DTOs de salida (responses)
│       ├── __init__.py
│       ├── auth.py         # Schemas para responses de auth
│       ├── account.py      # Schemas para responses de cuenta
│       └── transaction.py  # Schemas para responses de transacción
├── dependencies/            # Inyección de dependencias FastAPI
│   ├── __init__.py
│   ├── auth_deps.py        # Dependencias de autenticación
│   └── service_deps.py     # Dependencias de servicios
└── middleware/              # Middleware HTTP
    ├── __init__.py
    └── exception_handler.py # Manejador global de excepciones estandarizado
```

#### Características de Presentación:
- **API REST**: Endpoints organizados por dominio
- **Validación**: Schemas Pydantic para entrada y salida
- **Dependency Injection**: Sistema de DI de FastAPI
- **Versionado**: API v2 para nueva arquitectura

### 🔄 Recursos Compartidos (`src/shared/`)

Utilidades y recursos transversales a todas las capas.

```
shared/
├── exceptions/              # Sistema de excepciones personalizado
│   ├── __init__.py
│   ├── base.py             # Excepciones base del sistema
│   ├── domain.py           # Excepciones específicas de dominio
│   └── application.py      # Excepciones de casos de uso
├── constants/              # Constantes de negocio
│   ├── __init__.py
│   ├── business.py         # Constantes de reglas de negocio
│   └── validation_messages.py # Mensajes de validación y traducción
├── i18n/                   # Internacionalización
│   ├── __init__.py
│   └── messages.py         # Sistema de traducción de mensajes
├── utils/                  # Utilidades generales
│   ├── __init__.py
│   ├── money.py           # Utilidades para manejo monetario
│   ├── date.py            # Utilidades para fechas
│   ├── language.py        # Detección de idioma del usuario
│   ├── prompts.py         # Prompts para IA
│   └── validations.py     # Funciones de validación comunes
└── validators/             # Validadores de negocio
    ├── __init__.py
    └── business.py         # Validadores de reglas de negocio
```

### 🧪 Testing (`src/tests/`)

Estrategia completa de testing por capas.

```
tests/
├── conftest.py             # Configuración global de pytest
├── test_settings.py        # Configuración específica para tests
├── fixtures/               # Fixtures reutilizables
│   ├── __init__.py
│   ├── database.py         # Fixtures de base de datos
│   ├── users.py           # Fixtures de usuarios
│   └── accounts.py        # Fixtures de cuentas
├── unit/                  # Pruebas unitarias (sin dependencias externas)
│   ├── __init__.py
│   ├── domain/            # Tests de la capa de dominio
│   │   ├── __init__.py
│   │   └── test_money_value_object.py  # Test del Value Object Money
│   ├── application/       # Tests de casos de uso
│   │   └── __init__.py
│   └── infrastructure/    # Tests de implementaciones
│       └── __init__.py
├── integration/           # Pruebas de integración (con BD)
│   ├── __init__.py
│   ├── test_account_endpoints.py      # Tests de endpoints de cuenta
│   └── test_auth_endpoints.py         # Tests de endpoints de auth
└── e2e/                   # Pruebas end-to-end (flujos completos)
    └── __init__.py
```

## 🔄 Patrones de Diseño Implementados

### 1. Clean Architecture

**Inversión de Dependencias**: Las capas externas dependen de las internas.

```
┌─────────────────────────────────────────────────────────┐
│                    Frameworks & Drivers                 │
│              (FastAPI, SQLAlchemy, MySQL)               │
├─────────────────────────────────────────────────────────┤
│                Interface Adapters                       │
│            (Controllers, Repositories)                  │
├─────────────────────────────────────────────────────────┤
│                 Application Business Rules              │
│                    (Use Cases)                          │
├─────────────────────────────────────────────────────────┤
│                Enterprise Business Rules                │
│                   (Entities)                           │
└─────────────────────────────────────────────────────────┘
```

### 2. CQRS (Command Query Responsibility Segregation)

Separación entre operaciones de lectura y escritura:

```python
# Comando - Operación de escritura
@dataclass
class CreateAccountCommand:
    user_id: str
    name: str
    account_type: AccountType
    bank: Optional[str] = None
    initial_balance: Decimal = Decimal('0.00')

# Handler del comando
class CreateAccountCommandHandler:
    def __init__(self, account_repo: AccountRepository):
        self._account_repo = account_repo
    
    async def handle(self, command: CreateAccountCommand) -> Account:
        # Lógica de creación
        pass

# Consulta - Operación de lectura
@dataclass
class GetUserAccountsQuery:
    user_id: str
    include_inactive: bool = False

# Handler de la consulta
class GetUserAccountsQueryHandler:
    def __init__(self, account_repo: AccountRepository):
        self._account_repo = account_repo
    
    async def handle(self, query: GetUserAccountsQuery) -> List[Account]:
        # Lógica de consulta
        pass
```

### 3. Repository Pattern

Abstracción de la persistencia de datos:

```python
# Interface abstracta en Domain
from abc import ABC, abstractmethod

class AccountRepository(ABC):
    @abstractmethod
    async def save(self, account: Account) -> Account:
        pass
    
    @abstractmethod
    async def find_by_id(self, account_id: str) -> Optional[Account]:
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> List[Account]:
        pass
    
    @abstractmethod
    async def delete(self, account_id: str) -> bool:
        pass

# Implementación concreta en Infrastructure
class SQLAlchemyAccountRepository(AccountRepository):
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, account: Account) -> Account:
        db_account = AccountModel.from_entity(account)
        self._session.add(db_account)
        await self._session.commit()
        return db_account.to_entity()
    
    # ... otras implementaciones
```

### 4. Value Objects

Objetos inmutables con reglas de negocio:

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "MXN"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        if not self.currency:
            raise ValueError("Currency cannot be empty")
    
    def add(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} with {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def subtract(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        result_amount = self.amount - other.amount
        if result_amount < 0:
            raise ValueError("Subtraction would result in negative amount")
        return Money(result_amount, self.currency)
    
    def multiply(self, factor: Decimal) -> 'Money':
        return Money(self.amount * factor, self.currency)
    
    def is_zero(self) -> bool:
        return self.amount == Decimal('0')
    
    def __str__(self) -> str:
        return f"${self.amount:,.2f} {self.currency}"
```

### 5. Domain Entities

Entidades con identidad y comportamiento:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

@dataclass
class Account:
    user_id: str
    name: str
    account_type: AccountType
    balance: Money
    bank: Optional[str] = None
    is_active: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    @classmethod
    def create_new(
        cls,
        user_id: str,
        name: str,
        account_type: AccountType,
        bank: Optional[str] = None,
        initial_balance: Money = Money(Decimal('0'))
    ) -> 'Account':
        """Factory method para crear nueva cuenta"""
        if not user_id:
            raise ValueError("User ID is required")
        if not name.strip():
            raise ValueError("Account name cannot be empty")
        
        return cls(
            user_id=user_id,
            name=name.strip(),
            account_type=account_type,
            balance=initial_balance,
            bank=bank
        )
    
    def update_balance(self, new_balance: Money) -> None:
        """Actualiza el balance con validaciones de negocio"""
        if new_balance.currency != self.balance.currency:
            raise ValueError("Cannot change account currency")
        
        self.balance = new_balance
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Desactiva la cuenta"""
        if not self.balance.is_zero():
            raise ValueError("Cannot deactivate account with non-zero balance")
        
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def can_withdraw(self, amount: Money) -> bool:
        """Verifica si se puede retirar el monto especificado"""
        if amount.currency != self.balance.currency:
            return False
        
        # Lógica específica por tipo de cuenta
        if self.account_type == AccountType.CREDIT:
            # Las cuentas de crédito tienen lógica diferente
            return True
        
        return self.balance.amount >= amount.amount
```

## 🛡️ Sistema de Manejo de Excepciones

### Arquitectura de Excepciones

Lunance IA implementa un sistema robusto y estandarizado de manejo de excepciones que proporciona:

1. **Respuestas consistentes**: Todos los errores siguen el mismo formato
2. **Internacionalización**: Mensajes traducidos automáticamente
3. **Logging inteligente**: Diferentes niveles según el entorno
4. **Detalles contextuales**: Información específica según el tipo de error

### Jerarquía de Excepciones

```python
LunanceException (Base)
├── ValidationError          # Errores de validación
├── UnauthorizedError        # Errores de autenticación
├── BusinessRuleError        # Violaciones de reglas de negocio
└── Domain Exceptions        # Excepciones específicas de dominio
    ├── UserNotFoundError
    ├── AccountNotFoundError
    ├── InvalidCredentialsError
    ├── EmailAlreadyExistsError
    └── ... (más excepciones específicas)
```

### Middleware de Excepciones

El `exception_handler.py` (src/presentation/middleware/exception_handler.py:1) intercepta todas las excepciones y proporciona:

```python
# Estructura estándar de respuesta de error
{
    "error_code": "ERROR_CODE",      # Código de error estandarizado
    "message": "Mensaje traducido",  # Mensaje en idioma del usuario
    "details": [                     # Detalles específicos (opcional)
        {
            "loc": ["campo"],
            "msg": "Descripción",
            "type": "tipo_error",
            "input": "valor"
        }
    ]
}
```

### Mapeo de Excepciones

Cada excepción se mapea automáticamente a:
- **Código de error**: Identificador único (`AUTH_INVALID_CREDENTIALS`, `NOT_FOUND_ACCOUNT`, etc.)
- **HTTP Status Code**: Código HTTP apropiado (400, 401, 404, 409, 422, 500, etc.)
- **Mensaje traducido**: Según el idioma del usuario

Ejemplo en src/presentation/middleware/exception_handler.py:54:

```python
def map_exception_to_error_code(exc: Exception) -> tuple[str, int]:
    # Autenticación (401)
    if isinstance(exc, InvalidCredentialsError):
        return "AUTH_INVALID_CREDENTIALS", 401

    # Recursos no encontrados (404)
    elif isinstance(exc, AccountNotFoundError):
        return "NOT_FOUND_ACCOUNT", 404

    # Conflictos de negocio (409)
    elif isinstance(exc, EmailAlreadyExistsError):
        return "BUSINESS_EMAIL_EXISTS", 409

    # ... más mapeos
```

### Logging Basado en Entorno

- **PROD**: Logging de nivel WARNING (no expone detalles sensibles)
- **DEV**: Logging de nivel ERROR con stack traces completos

## 🌐 Sistema de Internacionalización (i18n)

### Detección Automática de Idioma

El sistema detecta automáticamente el idioma del usuario mediante:

1. **Header HTTP**: `Accept-Language`
2. **Fallback**: Español (es) como idioma por defecto

```python
# src/shared/utils/language.py
def get_user_language(request: Request) -> str:
    accept_language = request.headers.get("Accept-Language", "es")
    # Procesa y retorna el idioma adecuado
```

### Traducción de Mensajes

Todos los mensajes de error y validación se traducen automáticamente:

```python
# src/shared/i18n/messages.py
ERROR_MESSAGES = {
    "AUTH_INVALID_CREDENTIALS": {
        "es": "Las credenciales proporcionadas son inválidas",
        "en": "The provided credentials are invalid"
    },
    "NOT_FOUND_ACCOUNT": {
        "es": "La cuenta solicitada no fue encontrada",
        "en": "The requested account was not found"
    },
    # ... más mensajes
}
```

### Validación Multiidioma

Los errores de validación de Pydantic también se traducen:

```python
# src/shared/constants/validation_messages.py
def translate_validation_message(
    error_type: str,
    field_name: str,
    language: str
) -> str:
    # Traduce mensajes de validación como:
    # "El campo email es requerido" (es)
    # "The email field is required" (en)
```

### Idiomas Soportados

- **Español (es)**: Idioma por defecto
- **Inglés (en)**: Completamente soportado

## 🔒 Seguridad y Autenticación

### Configuración CORS Basada en Entorno

El sistema configura CORS dinámicamente según el entorno (src/main.py:35):

```python
if settings.ENVIRONMENT.upper() == "PROD":
    origins = ["https://lunance.app"]  # Dominio específico en producción
elif settings.ENVIRONMENT.upper() == "DEV":
    origins = ["*"]  # Abierto en desarrollo
else:
    raise ValueError("Invalid environment")
```

### Rate Limiting

Protección contra abuso con límites configurables:
- **Por IP**: Para usuarios no autenticados
- **Por usuario**: Para usuarios autenticados
- **Headers informativos**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`

### JWT Token Management

```python
from datetime import datetime, timedelta
from typing import Optional
import jwt

class AuthService:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self._secret_key = secret_key
        self._algorithm = algorithm
    
    def create_access_token(
        self, 
        user_id: str, 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=30)
        
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "type": "access"
        }
        
        return jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        expire = datetime.utcnow() + timedelta(days=7)
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "type": "refresh"
        }
        
        return jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)
```

## 🧪 Estrategia de Testing

### Pruebas Unitarias (Domain Layer)

```python
import pytest
from decimal import Decimal
from src.domain.objects.money import Money

class TestMoney:
    def test_create_money_with_valid_amount(self):
        money = Money(Decimal('100.50'), 'USD')
        assert money.amount == Decimal('100.50')
        assert money.currency == 'USD'
    
    def test_add_same_currency(self):
        money1 = Money(Decimal('100'), 'USD')
        money2 = Money(Decimal('50'), 'USD')
        result = money1.add(money2)
        assert result.amount == Decimal('150')
        assert result.currency == 'USD'
    
    def test_add_different_currency_raises_error(self):
        money1 = Money(Decimal('100'), 'USD')
        money2 = Money(Decimal('50'), 'EUR')
        
        with pytest.raises(ValueError, match="Cannot add USD with EUR"):
            money1.add(money2)
```

### Pruebas de Integración (API Endpoints)

```python
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
class TestAccountEndpoints:
    async def test_create_account_success(self, auth_headers):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v2/account/",
                json={
                    "name": "Mi Cuenta de Ahorros",
                    "account_type": "SAVINGS",
                    "bank": "BBVA",
                    "initial_balance": 1000.00
                },
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Mi Cuenta de Ahorros"
            assert data["account_type"] == "SAVINGS"
            assert data["balance"]["amount"] == 1000.00
```

## 🚀 Despliegue y Escalabilidad

### Consideraciones de Arquitectura

1. **Separación de Capas**: Permite escalar cada capa independientemente
2. **Interfaces Abstractas**: Facilita el cambio de implementaciones
3. **CQRS**: Permite optimizar lecturas y escrituras por separado
4. **Value Objects**: Reduce bugs y mejora la mantenibilidad
5. **Testing Strategy**: Cobertura completa desde unidad hasta e2e

### Evolución Futura

- **Microservicios**: La arquitectura permite extraer dominios a servicios separados
- **Event Sourcing**: Compatible con CQRS para auditoría completa
- **Cache Layer**: Fácil integración de Redis para consultas
- **Message Queues**: Para procesamiento asíncrono de comandos

---

Esta arquitectura proporciona una base sólida para el crecimiento y mantenimiento a largo plazo del sistema Lunance IA.