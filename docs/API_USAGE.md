# 📖 Guía de Uso de la API - Lunance IA

Esta guía te mostrará cómo usar la API REST de Lunance IA v2, incluyendo autenticación, endpoints principales y ejemplos prácticos.

## 📋 Tabla de Contenidos

- [Autenticación JWT](#autenticación-jwt)
- [Autenticación con API Keys](#-autenticación-con-api-keys)
- [Endpoints Principales](#endpoints-principales)
- [Apartados de Inversión](#-apartados-de-inversión---apiv2positions)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Manejo de Errores](#manejo-de-errores)
- [Códigos de Estado](#códigos-de-estado)
- [Límites y Paginación](#límites-y-paginación)
- [IA - Análisis y Asesoría](#-ia---apiv2ai)

## 🔐 Autenticación JWT

La API gestiona la autenticación **por sí misma**, con usuario y contraseña. Emite y valida sus propios tokens JWT: ese es el flujo principal. Existe además un *fallback* legado que acepta tokens de Auth0 (`validate_auth0_user`), por lo que las variables `AUTH0_DOMAIN` y `AUTH0_AUDIENCE` siguen siendo **obligatorias** en la configuración.

### Flujo de Autenticación

1. **Registro**: `POST /api/v2/auth/register` con usuario y contraseña
2. **Login**: `POST /api/v2/auth/login` devuelve un *access token* y un *refresh token*
3. **API Requests**: incluir el access token en el header `Authorization`
4. **Renovación**: `POST /api/v2/auth/refresh` cuando el access token caduca
5. **Cierre de sesión**: `POST /api/v2/auth/logout` revoca el refresh token

### Características de los tokens

| | Access token | Refresh token |
|---|---|---|
| Algoritmo | HS256 | HS256 |
| Firmado con | `SECRET_KEY` | `SECRET_KEY_REFRESH` |
| Vigencia | `ACCESS_TOKEN_EXPIRE_MINUTES` (60 min por defecto en `settings.py` y `.env.example`) | `REFRESH_TOKEN_EXPIRE_DAYS` (7 días por defecto) |
| Se envía en | Header `Authorization: Bearer` | Cuerpo de `/refresh` y `/logout` |
| Almacenado en servidor | No | Sí, **solo su hash SHA-256** |

El access token lleva las claims `sub` (UUID del usuario), `iss: "lunance"`, `iat` y `exp`. El refresh token **rota en cada uso**: `/refresh` devuelve uno nuevo y guarda su hash.

### Registro

```bash
curl -X POST "http://localhost:8000/api/v2/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "juanperez",
       "password": "MiClave123!"
     }'
```

**Respuesta:** `200 OK`
```json
{
  "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "username": "juanperez",
  "message": "Usuario registrado exitosamente"
}
```

> **Requisitos de la contraseña**: mínimo 8 caracteres, con al menos una mayúscula, una minúscula, un dígito y un carácter especial (`!@#$%^&*(),.?":{}|<>`). Se almacena con `bcrypt`. Si no los cumple, la API responde `400 VALIDATION_ERROR` y el detalle incluye códigos como `PASSWORD_TOO_SHORT` o `PASSWORD_MISSING_UPPERCASE`.

### Login

```bash
curl -X POST "http://localhost:8000/api/v2/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "juanperez",
       "password": "MiClave123!"
     }'
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Credenciales incorrectas devuelven `401 AUTH_INVALID_CREDENTIALS`; una cuenta desactivada devuelve `401 AUTH_USER_INACTIVE`.

### Usar Token en Requests

Incluye el access token en el header `Authorization` de todos los requests autenticados:

```bash
curl -X GET "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer <access_token>"
```

### Renovar el Token

```bash
curl -X POST "http://localhost:8000/api/v2/auth/refresh" \
     -H "Content-Type: application/json" \
     -d '{
       "refresh_token": "<refresh_token>"
     }'
```

**Respuesta:** un par nuevo de tokens. Descarta el refresh token anterior: ya no sirve.

### Obtener Información del Usuario

```bash
curl -X GET "http://localhost:8000/api/v2/auth/me" \
     -H "Authorization: Bearer <access_token>"
```

**Respuesta:**
```json
{
  "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "username": "juanperez",
  "is_active": true
}
```

### Cerrar Sesión

```bash
curl -X POST "http://localhost:8000/api/v2/auth/logout" \
     -H "Content-Type: application/json" \
     -d '{
       "refresh_token": "<refresh_token>"
     }'
```

Revoca ese refresh token en el servidor. El access token que ya tengas seguirá siendo válido hasta que expire por su cuenta.

## 🔑 Autenticación con API Keys

Además del JWT (usuarios humanos), la API soporta **API keys** para acceso programático: integraciones, automatizaciones y agentes/LLM (vía MCP). El usuario genera la key desde la app y la incluye en el header `X-API-Key`.

### JWT vs API Key

| | JWT (`Authorization: Bearer`) | API Key (`X-API-Key`) |
|---|---|---|
| Para | Usuario en la app | Acceso programático / integraciones |
| Alcance | Acceso completo | Limitado por **scopes** |
| Puede editar / eliminar | Sí | **Sí**, si la key tiene el scope `<recurso>:write` |

Los endpoints de recursos (cuentas, transacciones, categorías, dashboard, suscripciones, inversiones, bancos, ingresos, presupuestos, metas, plazos y transferencias) aceptan **ambos** métodos (autenticación dual): si llega `X-API-Key` se usa esa vía; si no, se valida el JWT. Un usuario por JWT siempre tiene acceso completo; una API key solo puede hacer lo que sus scopes permitan. En cambio, `/ai/*`, `/notifications`, `/auth/*` y `/api-keys/*` son **solo JWT**.

### Scopes disponibles

| Scope | Permite |
|-------|---------|
| `transactions:read` | Listar y ver transacciones |
| `transactions:write` | Crear, editar y eliminar transacciones |
| `accounts:read` | Listar / ver cuentas y su actividad |
| `accounts:write` | Crear, editar, activar/desactivar y eliminar cuentas |
| `categories:read` | Listar categorías |
| `dashboard:read` | Ver el dashboard financiero |
| `budgets:read` | Listar / ver presupuestos y su progreso |
| `budgets:write` | Crear, editar, activar/desactivar y eliminar presupuestos |
| `goals:read` | Listar / ver metas de ahorro |
| `goals:write` | Crear, editar, activar/desactivar y eliminar metas de ahorro |
| `investments:read` | Ver apartados de inversión, rendimientos y proyecciones |
| `investments:write` | Crear apartados, depositar, retirar y liquidar |
| `subscriptions:read` | Listar / ver suscripciones y sus cargos |
| `subscriptions:write` | Crear, editar, activar/desactivar y eliminar suscripciones |
| `installments:read` | Listar compras a plazos (MSI) |
| `installments:write` | Crear, pagar, editar y eliminar compras a plazos (MSI) |
| `transfers:write` | Crear y eliminar transferencias entre cuentas |
| `banks:read` | Ver el catálogo de bancos |
| `incomes:read` | Listar / ver ingresos recurrentes y sus depósitos |
| `incomes:write` | Crear, editar, activar/desactivar y eliminar ingresos recurrentes |

> El scope `:write` de cada recurso habilita **crear, editar y eliminar** en ese
> recurso (el chequeo solo verifica la presencia del scope); una key que solo tenga
> `:read` no puede modificar nada. `transfers` solo tiene `:write` (crear y eliminar);
> las transferencias se consultan dentro de las transacciones.

> 🤖 **Uso vía MCP:** estos scopes son la base del servidor MCP que expone la API a
> agentes/LLM. Para ejecutarlo, sus herramientas y cómo probarlo, consulta
> [MCP.md](MCP.md).

### Usar una API Key en Requests

```bash
curl -X GET "http://localhost:8000/api/v2/transaction/" \
     -H "X-API-Key: moon_xxxxxxxxxxxxxxxxxxxxxxxx"
```

Si la key no tiene el scope requerido, la API responde `403 Forbidden`. Si es inválida, fue revocada o expiró, responde `401 Unauthorized`.

> La gestión de keys (crear / listar / revocar / eliminar) se hace **con JWT**, no con API key. Ver [API Keys](#-api-keys---apiv2api-keys) en la sección de endpoints.

## 🌐 Endpoints Principales

### 🔐 Autenticación - `/api/v2/auth/`

> **Nota**: la API gestiona el registro y el login por sí misma. Ver [Autenticación JWT](#-autenticación-jwt) para el detalle del flujo y de los tokens.

#### Registro
```bash
POST /api/v2/auth/register
```

**Request:**
```json
{
  "username": "juanperez",
  "password": "MiClave123!"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `username` | string | ✅ | 1–100 caracteres, único |
| `password` | string | ✅ | Mínimo 8 caracteres, con mayúscula, minúscula, dígito y carácter especial |

**Response:**
```json
{
  "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "username": "juanperez",
  "message": "Usuario registrado exitosamente"
}
```

Si el nombre de usuario ya existe, responde `400 VALIDATION_ERROR`.

#### Login
```bash
POST /api/v2/auth/login
```

**Request:**
```json
{
  "username": "juanperez",
  "password": "MiClave123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Renovar Token
```bash
POST /api/v2/auth/refresh
```

**Request:**
```json
{
  "refresh_token": "<refresh_token>"
}
```

**Response:** un par nuevo de tokens. El refresh token anterior queda invalidado.
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Obtener Información del Usuario
```bash
GET /api/v2/auth/me
```

**Response:**
```json
{
  "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "username": "juanperez",
  "is_active": true
}
```

#### Cerrar Sesión
```bash
POST /api/v2/auth/logout
```

**Request:**
```json
{
  "refresh_token": "<refresh_token>"
}
```

**Response:**
```json
{
  "message": "Logout exitoso"
}
```

### 🔑 API Keys - `/api/v2/api-keys/`

> Gestión de API keys del usuario. **Estos endpoints requieren JWT** (no se pueden usar con una API key).

#### Crear API Key
```bash
POST /api/v2/api-keys/
```

**Request:**
```json
{
  "name": "Mi integración",
  "scopes": ["transactions:read", "transactions:write"],
  "expires_at": "2026-12-31T23:59:59Z"
}
```
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `name` | string | ✅ | Nombre identificador (1–100 chars) |
| `scopes` | array | ✅ | Mínimo 1; solo valores válidos del enum de scopes |
| `expires_at` | datetime | ❌ | Expiración ISO 8601 (`null`/omitido = no expira) |

**Response:** `201 Created` — ⚠️ `raw_key` se devuelve **una sola vez**; el backend solo guarda su hash.
```json
{
  "raw_key": "moon_AbC123dEf456...",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Mi integración",
  "key_prefix": "moon_AbC123",
  "scopes": ["transactions:read", "transactions:write"],
  "expires_at": "2026-12-31T23:59:59Z",
  "created_at": "2026-06-09T14:30:00Z"
}
```

#### Listar API Keys
```bash
GET /api/v2/api-keys/
```

**Response:** lista de keys del usuario. Nunca incluye `raw_key` ni el hash.
```json
[
  {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Mi integración",
    "key_prefix": "moon_AbC123",
    "scopes": ["transactions:read", "transactions:write"],
    "is_active": true,
    "expires_at": "2026-12-31T23:59:59Z",
    "last_used_at": "2026-06-09T15:00:00Z",
    "created_at": "2026-06-09T14:30:00Z"
  }
]
```

#### Revocar API Key
```bash
PATCH /api/v2/api-keys/{api_key_uuid}/revoke/
```

Desactiva la key **sin borrarla**: deja de autenticar, pero se conserva en el listado para auditoría.

**Response:** `204 No Content` si se revocó; `404 Not Found` si no existe o no pertenece al usuario.

#### Eliminar API Key
```bash
DELETE /api/v2/api-keys/{api_key_uuid}/
```

**Response:** `204 No Content` si se eliminó; `404 Not Found` si no existe o no pertenece al usuario. El borrado es **permanente**: la key desaparece del listado.

### 💳 Cuentas - `/api/v2/account/`

#### Listar Cuentas del Usuario
```bash
GET /api/v2/account/
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `only_active` | bool | Solo cuentas activas (default: false) |
| `limit` | int | Máximo de resultados (default: 50, max: 150) |
| `offset` | int | Offset para paginación (default: 0) |

**Response:** `total` indica el número de cuentas devueltas en la respuesta.
```json
{
  "accounts": [
    {
      "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Cuenta de Ahorros BBVA",
      "account_type": "SAVINGS",
      "bank_id": 1,
      "bank_name": "BBVA México",
      "bank_code": "BBVA",
      "current_balance": 15500.75,
      "currency": "MXN",
      "is_active": true,
      "credit_card_settings": null
    },
    {
      "account_uuid": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Tarjeta de Crédito Banamex",
      "account_type": "CREDIT_CARD",
      "bank_id": 2,
      "bank_name": "Banamex",
      "bank_code": "BANAMEX",
      "current_balance": -2500.00,
      "currency": "MXN",
      "is_active": true,
      "credit_card_settings": null
    }
  ],
  "total": 2
}
```

#### Crear Nueva Cuenta
```bash
POST /api/v2/account/
```

**Request:** `bank_id` es el ID del banco del catálogo (`GET /api/v2/bank/`). Opcionales: `currency` (default `MXN`), `is_active` y `credit_card_settings` (solo `CREDIT_CARD`).

> 💡 El tipo `INVESTMENT` es solo una **etiqueta de organización** (para plataformas
> como GBM o CetesDirecto): no configura rendimientos. Para que el dinero genere
> rendimientos, crea un apartado con [`POST /api/v2/positions/`](#-apartados-de-inversión---apiv2positions)
> en cualquier cuenta que no sea de crédito.
```json
{
  "name": "Mi Cuenta de Ahorros",
  "account_type": "SAVINGS",
  "bank_id": 1,
  "initial_balance": 1000.00
}
```

**Response:** `201 Created`
```json
{
  "account_uuid": "770e8400-e29b-41d4-a716-446655440002",
  "name": "Mi Cuenta de Ahorros",
  "account_type": "SAVINGS",
  "bank_id": 1,
  "bank_name": "BBVA México",
  "bank_code": "BBVA",
  "current_balance": 1000.00,
  "currency": "MXN",
  "is_active": true,
  "credit_card_settings": null
}
```

#### Obtener Cuenta por UUID
```bash
GET /api/v2/account/{account_uuid}
```

**Response:**
```json
{
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Cuenta de Ahorros BBVA",
  "account_type": "SAVINGS",
  "bank_id": 1,
  "bank_name": "BBVA México",
  "bank_code": "BBVA",
  "current_balance": 15500.75,
  "currency": "MXN",
  "is_active": true,
  "credit_card_settings": null
}
```

#### Actualizar Cuenta
```bash
PATCH /api/v2/account/{account_uuid}/
```

**Request:** todos los campos son opcionales (`name`, `bank_id`, `current_balance`, `credit_card_settings`). Ten en cuenta que `current_balance` es el **saldo disponible**: no incluye el dinero que esté en apartados de inversión.
```json
{
  "name": "Cuenta Principal BBVA",
  "bank_id": 1
}
```

**Response:** Misma estructura que obtener cuenta por UUID.

#### Eliminar Cuenta
```bash
DELETE /api/v2/account/{account_uuid}/
```

**Response:** `204 No Content` (sin cuerpo).

#### Activar/Desactivar Cuenta
```bash
PATCH /api/v2/account/{account_uuid}/status/
```

Alterna el estado activo/inactivo de la cuenta.

**Response:** Misma estructura que obtener cuenta por UUID.

#### Actividad Reciente de una Cuenta
```bash
GET /api/v2/account/{account_uuid}/activity
```

Retorna los movimientos recientes de la cuenta. Requiere scope `accounts:read`.

**Response:** lista de movimientos con `name` (nombre de la cuenta), `transaction_type` (`INCOME`, `EXPENSE` o `TRANSFER`), `category_name`, `amount` y `transaction_date`.

### 💰 Transacciones - `/api/v2/transaction/`

> **Acceso por API key:** lectura requiere scope `transactions:read`; crear (`POST`), editar (`PUT`) y eliminar (`DELETE`) requieren `transactions:write`.

#### Listar Transacciones
```bash
GET /api/v2/transaction/
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `skip` | int | Saltar N transacciones (default: 0) |
| `limit` | int | Máximo de resultados (default: 100, max: 1000) |
| `start_date` | date | Filtrar desde esta fecha |
| `end_date` | date | Filtrar hasta esta fecha |
| `transaction_type` | string | Tipo: `INCOME`, `EXPENSE` o `TRANSFER` |
| `category_id` | int | ID de categoría |
| `account_uuid` | string | UUID de la cuenta |

**Response:**
```json
[
  {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "transfer_uuid": null,
    "category": "Alimentación",
    "transaction_type": "EXPENSE",
    "amount": 250.50,
    "transaction_date": "2024-12-14",
    "description": "Compra en supermercado",
    "notes": "Compra semanal",
    "creation_date": "2024-12-14T10:30:00Z",
    "account_name": "Cuenta Principal",
    "account_type": "CHECKING",
    "account_uuid": "660e8400-e29b-41d4-a716-446655440001"
  }
]
```

#### Obtener Transacción por UUID
```bash
GET /api/v2/transaction/{transaction_uuid}/
```

#### Crear Transacción
```bash
POST /api/v2/transaction/
```

**Request:**
```json
{
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "category_id": 1,
  "transaction_type": "EXPENSE",
  "amount": 250.50,
  "description": "Compra en supermercado",
  "notes": "Compra semanal",
  "transaction_date": "2024-12-14"
}
```

#### Actualizar Transacción
```bash
PUT /api/v2/transaction/{transaction_uuid}/
```

**Request:**
```json
{
  "description": "Descripción actualizada",
  "notes": "Notas actualizadas",
  "category_id": 2,
  "transaction_type": "EXPENSE",
  "amount": 300.00,
  "transaction_date": "2024-12-15"
}
```

#### Eliminar Transacción
```bash
DELETE /api/v2/transaction/{transaction_uuid}/
```

**Response:** `204 No Content`

### 🏷️ Categorías - `/api/v2/category/`

#### Listar Categorías
```bash
GET /api/v2/category/
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `only_active` | bool | Solo categorías activas (default: true) |

**Response:**
```json
{
  "categories": [
    {
      "id": 1,
      "name": "Alimentación",
      "type": "EXPENSE",
      "description": "Gastos de comida y supermercado",
      "color": "#FF5733",
      "icon": "food",
      "is_active": true
    }
  ],
  "total": 1
}
```

### 📊 Dashboard - `/api/v2/dashboard/`

#### Obtener Resumen Financiero
```bash
GET /api/v2/dashboard/
```

Retorna un resumen del estado financiero del usuario.

### 🔄 Suscripciones - `/api/v2/subscription/`

#### Listar Suscripciones
```bash
GET /api/v2/subscription/
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `account_uuid` | string | Filtrar por UUID de la cuenta |
| `category_id` | int | Filtrar por ID de categoría |
| `active_only` | bool | Solo suscripciones activas (default: false) |
| `limit` | int | Máximo de resultados (default: 100, max: 1000) |
| `offset` | int | Offset para paginación (default: 0) |

**Response:**
```json
[
  {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Netflix Premium",
    "account_name": "Cuenta Principal",
    "account_uuid": "660e8400-e29b-41d4-a716-446655440001",
    "category_name": "Entretenimiento",
    "frequency": "MONTHLY",
    "amount": 299.00,
    "billing_day": 15,
    "description": "Plan Premium 4K",
    "service_url": "https://netflix.com",
    "start_date": "2024-01-01",
    "end_date": null,
    "next_charge_date": "2024-07-15",
    "is_active": true
  }
]
```

#### Obtener Suscripción por UUID
```bash
GET /api/v2/subscription/{subscription_uuid}/
```

**Response:** Misma estructura que un elemento individual del listado.

#### Crear Suscripción
```bash
POST /api/v2/subscription/
```

**Request:**
```json
{
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "category_id": 5,
  "name": "Spotify Premium",
  "amount": 149.00,
  "frequency": "MONTHLY",
  "start_date": "2024-01-01",
  "end_date": null,
  "billing_day": 1,
  "description": "Plan familiar",
  "service_url": "https://spotify.com"
}
```

**Frecuencias disponibles:** `DAILY`, `WEEKLY`, `BIWEEKLY`, `MONTHLY`, `BIMONTHLY`, `QUARTERLY`, `SEMI_ANNUAL`, `ANNUAL`

#### Actualizar Suscripción
```bash
PATCH /api/v2/subscription/{subscription_uuid}/
```

**Request:** (todos los campos son opcionales excepto `account_uuid`)
```json
{
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Netflix Premium",
  "amount": 299.00,
  "frequency": "MONTHLY"
}
```

#### Activar/Desactivar Suscripción
```bash
PATCH /api/v2/subscription/{subscription_uuid}/activate/
```

Alterna el estado activo/inactivo de la suscripción.

#### Eliminar Suscripción
```bash
DELETE /api/v2/subscription/{subscription_uuid}/
```

**Response:** `204 No Content`

#### Listar Cargos de Suscripciones
```bash
GET /api/v2/subscription/charges/
```

Retorna el historial de cargos generados automáticamente para las suscripciones del usuario.

**Response:**
```json
[
  {
    "charge_id": "abc123",
    "subscription_name": "Netflix Premium",
    "charge_date": "2024-06-15",
    "charge_amount": 299.00,
    "charge_status": "COMPLETED",
    "transaction_id": "def456",
    "transaction_amount": 299.00,
    "transaction_description": "Cargo automático - Netflix Premium",
    "category_name": "Entretenimiento",
    "account_name": "Cuenta Principal"
  }
]
```

#### Últimos Cargos de una Suscripción
```bash
GET /api/v2/subscription/{subscription_uuid}/transactions/
```

Retorna los últimos cargos generados por una suscripción. Requiere scope `subscriptions:read`.

**Response:** lista con `name` (nombre de la suscripción), `account_name`, `amount` y `charge_date` de cada cargo.

### 🐷 Apartados de Inversión - `/api/v2/positions/`

Un **apartado** (o "cajita", como en las apps bancarias y SOFIPOs) es una porción de
dinero **dentro de una cuenta** que genera rendimientos. Una misma cuenta puede tener
varios apartados con tasas y plazos distintos.

**Las dos reglas que rigen todo:**

1. El `current_balance` de una cuenta es **solo el saldo disponible**. El dinero de los
   apartados vive aparte; el total de la cuenta es `available_balance + invested_balance`,
   y lo calcula el endpoint de listado.
2. **El dinero apartado no se puede gastar ni transferir**, ni siquiera el de apartados a
   la vista: primero hay que regresarlo al disponible con `withdraw` o `liquidate`. Una
   transferencia que exceda el disponible falla aunque el total de la cuenta alcance.

**Tipos de apartado (`position_type`):**

| Tipo | Comportamiento |
|------|----------------|
| `ON_DEMAND` | A la vista: admite depósitos y retiros parciales en cualquier momento. El rendimiento diario capitaliza directo en su `balance`. |
| `FIXED_TERM` | Plazo fijo: requiere `term_days` o `maturity_date`, no admite depósitos ni retiros parciales. El rendimiento se acumula en `accrued_yield` y se entrega al vencer. |

**Qué pasa al vencer un plazo (`on_maturity`):**

| Valor | Al llegar la fecha de vencimiento |
|-------|-----------------------------------|
| `AUTO_RENEW` | Reinvierte capital + rendimiento por el mismo plazo. |
| `LIQUIDATE` | Deposita capital + rendimiento en el saldo disponible y cierra el apartado. |
| `HOLD` (default) | El apartado pasa a `MATURED`, **deja de generar rendimiento** y espera la decisión del usuario. |

#### Topes y desbordamiento

Muchas SOFIPOs pagan su mejor tasa solo hasta cierto monto: los primeros 25,000 al 10%
y lo que pase de ahí a otra tasa. Eso se representa con un **tope** (`max_balance`) y un
**destino para el excedente**, encadenando apartados:

```
Ahorro 10%  (tope 25,000)  ──desborda──▶  Excedente 5%  (sin tope)
```

Los primeros 25,000 rinden 10% y el resto 5%, sin que ningún apartado necesite entender
de tramos. El tope solo aplica a apartados **a la vista**: un plazo fijo tiene su monto
cerrado hasta el vencimiento.

| Campo | Qué hace |
|-------|----------|
| `max_balance` | Tope de capital. `null` = sin tope. |
| `overflow_action` | `TO_AVAILABLE` (el excedente vuelve al saldo disponible) o `TO_POSITION` (pasa a otro apartado). Por defecto `TO_AVAILABLE`. |
| `overflow_position_uuid` | Apartado destino. Obligatorio con `TO_POSITION`, debe ser de la misma cuenta, a la vista y activo. |

**Cómo se comporta:**

- **El tope nunca se rebasa, ni un día.** Un apartado lleno sigue rindiendo sobre su tope,
  y ese rendimiento se desborda cada día.
- **El excedente recorre la cadena completa.** Si el destino también está lleno, sigue al
  suyo; lo que ningún apartado absorbe cae al saldo disponible. El dinero nunca se pierde.
- **Solo genera transacción lo que cruza al disponible.** Mover dinero de un apartado a
  otro no aparece en el historial porque nunca pasó por el saldo disponible.
- **No se permiten ciclos**: la API los rechaza al configurar el destino.
- **Si liquidas el apartado destino**, los que lo apuntaban pasan a `TO_AVAILABLE` y
  reciben una notificación. No heredan la cadena del apartado liquidado.
- **El monto inicial no puede superar el tope**: crea el apartado dentro del tope y
  deposita el resto después.

#### Crear un Apartado
```bash
POST /api/v2/positions/
```

Mueve `amount` del saldo disponible de la cuenta hacia el apartado nuevo. Funciona en
cualquier cuenta **excepto tarjetas de crédito**.

**Request:**
```json
{
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Plazo 90 días",
  "position_type": "FIXED_TERM",
  "amount": 5000.00,
  "annual_rate": 12.50,
  "interest_type": "COMPOUND",
  "term_days": 90,
  "early_withdrawal_penalty": 10.00,
  "on_maturity": "HOLD"
}
```

| Campo | Requerido | Descripción |
|-------|-----------|-------------|
| `account_uuid` | ✅ | Cuenta dueña del apartado |
| `name` | ✅ | Nombre visible (máx. 100 caracteres) |
| `position_type` | ✅ | `ON_DEMAND` o `FIXED_TERM` |
| `amount` | ✅ | Monto a apartar (> 0, sale del disponible) |
| `annual_rate` | ✅ | Tasa anual en porcentaje (≥ 0) |
| `interest_type` | ❌ | `SIMPLE` o `COMPOUND` (default `COMPOUND`) |
| `term_days` | Solo plazo | Días de plazo (alternativa a `maturity_date`) |
| `maturity_date` | Solo plazo | Fecha de vencimiento `YYYY-MM-DD` |
| `lock_period_end_date` | ❌ | Antes de esta fecha no se permite liquidar |
| `early_withdrawal_penalty` | ❌ | % (0-100) que se castiga **solo sobre los rendimientos**; el capital nunca se toca |
| `on_maturity` | ❌ | `AUTO_RENEW`, `LIQUIDATE` o `HOLD` (default `HOLD`) |
| `currency` | ❌ | Default `MXN` |
| `cap` | ❌ | Tope y destino del excedente (solo a la vista). Ver [Topes y desbordamiento](#topes-y-desbordamiento) |

**Con tope:**
```json
{
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Ahorro 10%",
  "position_type": "ON_DEMAND",
  "amount": 25000.00,
  "annual_rate": 10.00,
  "cap": { "max_balance": 25000.00, "overflow_action": "TO_AVAILABLE" }
}
```

**Response:** `201 Created`
```json
{
  "position_uuid": "770e8400-e29b-41d4-a716-446655440009",
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Plazo 90 días",
  "position_type": "FIXED_TERM",
  "status": "ACTIVE",
  "balance": 5000.00,
  "accrued_yield": 0.00,
  "total_value": 5000.00,
  "currency": "MXN",
  "annual_rate": 12.50,
  "interest_type": "COMPOUND",
  "start_date": "2026-08-14",
  "on_maturity": "HOLD",
  "term_days": 90,
  "lock_period_end_date": null,
  "maturity_date": "2026-11-12",
  "early_withdrawal_penalty": 10.00,
  "max_balance": null,
  "overflow_action": null,
  "overflow_position_uuid": null,
  "created_at": "2026-08-14T18:00:00Z",
  "account_available_balance": 1200.00
}
```

`balance` es el capital, `accrued_yield` el rendimiento acumulado aún no entregado y
`total_value` la suma de ambos. `account_available_balance` es el disponible que le queda
a la cuenta después de la operación. Estados posibles (`status`): `ACTIVE`, `MATURED`
(plazo vencido en espera) y `LIQUIDATED` (cerrado).

#### Listar Apartados de una Cuenta
```bash
GET /api/v2/positions/account/{account_uuid}/
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `include_liquidated` | bool | Incluir apartados ya cerrados (default: false) |

**Response:**
```json
{
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "account_name": "Cuenta SOFIPO",
  "available_balance": 1200.00,
  "invested_balance": 5012.34,
  "total_balance": 6212.34,
  "currency": "MXN",
  "positions": [ { "position_uuid": "...", "name": "Plazo 90 días" } ]
}
```

> Este es el endpoint que debe alimentar la tarjeta de cuenta en un cliente: trae el
> disponible, el invertido y el total ya calculados. Los apartados liquidados nunca
> suman al `invested_balance`.

#### Obtener un Apartado
```bash
GET /api/v2/positions/{position_uuid}/
```

**Response:** misma estructura que la respuesta de creación.

#### Actualizar un Apartado
```bash
PATCH /api/v2/positions/{position_uuid}/
```

Cambia el nombre o la configuración de tope. **Es el único camino para encadenar
apartados**: el destino tiene que existir antes de que otro lo apunte, así que no se
puede armar la cadena solo con `POST`.

```jsonc
{ "name": "Ahorro 10%" }                          // renombra, no toca el tope
{ "cap": { "max_balance": 25000 } }               // tope, excedente al disponible
{ "cap": { "max_balance": 25000,                  // encadena a otro apartado
           "overflow_action": "TO_POSITION",
           "overflow_position_uuid": "770e..." } }
{ "cap": null }                                   // quita el tope
```

> Omitir `cap` deja la configuración como estaba; mandarlo en `null` la quita. Sin esa
> distinción, renombrar un apartado le borraría el tope sin querer.

Bajar el tope por debajo del saldo actual **saca el excedente en el momento**, no espera
al proceso diario: el dinero recorre la cadena y lo que sobre entra al saldo disponible
con su transacción.

**Response:** misma estructura que la respuesta de creación.

#### Depositar en un Apartado
```bash
POST /api/v2/positions/{position_uuid}/deposit/
```

Mueve dinero del disponible al apartado. **Solo apartados a la vista**; en un plazo fijo
responde `409`.

**Request:**
```json
{ "amount": 500.00 }
```

**Response:** el apartado actualizado, con el nuevo `account_available_balance`.

#### Retirar de un Apartado
```bash
POST /api/v2/positions/{position_uuid}/withdraw/
```

Regresa dinero del apartado al disponible: es el único camino para poder gastarlo o
transferirlo. **Solo apartados a la vista** (los plazos fijos se cierran completos con
`liquidate`).

**Request:**
```json
{ "amount": 400.00 }
```

#### Liquidar un Apartado
```bash
POST /api/v2/positions/{position_uuid}/liquidate/
```

Cierra el apartado por completo y acredita capital + rendimiento al saldo disponible
(sin cuerpo en el request). Liquidar un plazo fijo **antes de vencer** aplica la
penalización sobre los rendimientos; si aún corre el `lock_period_end_date`, responde
`409`.

**Response:**
```json
{
  "position_uuid": "770e8400-e29b-41d4-a716-446655440009",
  "name": "Plazo 90 días",
  "payout_amount": 5075.00,
  "currency": "MXN",
  "status": "LIQUIDATED",
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "account_available_balance": 6275.00
}
```

#### Rendimientos de un Apartado
```bash
GET /api/v2/positions/{position_uuid}/yields/
```

Historial de rendimientos diarios del apartado (`limit` default 365, máx. 1825; `offset`
para paginar). Misma estructura que los rendimientos por cuenta.

#### Proyecciones de un Apartado
```bash
GET /api/v2/positions/{position_uuid}/projections/?days=90
```

**Response:**
```json
{
  "position_uuid": "770e8400-e29b-41d4-a716-446655440009",
  "name": "Plazo 90 días",
  "current_value": 5012.34,
  "annual_rate": 12.50,
  "interest_type": "COMPOUND",
  "maturity_date": "2026-11-12",
  "projected_final_balance": 5150.00,
  "daily_projections": [
    {
      "projection_date": "2026-08-15",
      "principal_amount": 5012.34,
      "yield_amount": 1.61,
      "projected_balance": 5013.95,
      "overflow_amount": 0.00
    }
  ],
  "projected_overflow": 0.00,
  "max_balance": null
}
```

Si omites `days`, proyecta hasta el vencimiento (plazo fijo) o 365 días (a la vista). Un
plazo fijo nunca se proyecta más allá de su fecha de vencimiento.

**Apartados con tope:** la proyección **se aplana en el tope** en vez de seguir creciendo,
porque ese dinero no se queda ahí. `overflow_amount` es lo que ese día sale del apartado
y `projected_overflow` el total del horizonte — la respuesta a "¿cuánto me va a soltar
esta cajita en 90 días?". Un apartado lleno desborda exactamente lo que rinde:

```json
{
  "projection_date": "2026-08-15",
  "principal_amount": 25000.00,
  "yield_amount": 6.53,
  "projected_balance": 25000.00,
  "overflow_amount": 6.53
}
```

#### Procesos automáticos

| Job | Hora (UTC) | Qué hace |
|-----|------------|----------|
| Rendimientos diarios | 12:00 | Calcula el rendimiento de cada apartado activo. A la vista capitaliza en `balance`; a plazo fijo suma a `accrued_yield`. El día del vencimiento todavía genera rendimiento. Si un apartado con tope ya está lleno, el rendimiento se desborda. |
| Vencimientos | 12:30 | Ejecuta el `on_maturity` de cada plazo vencido y envía una notificación. |

> Las transacciones (tipo `TRANSFER`, con el campo `position_id`) se crean **cuando el
> dinero cruza al saldo disponible**: apartar, retirar, liquidar, vencer, o desbordar un
> apartado lleno hacia el disponible. El rendimiento que se queda dentro del apartado
> solo se registra en sus yields, y el que se desborda hacia otro apartado tampoco
> genera transacción porque nunca pasa por el disponible.
>
> Un apartado a la vista que vive en su tope desborda su rendimiento **todos los días**:
> el tope no se rebasa ni un día, así que espera un movimiento diario pequeño por cada
> apartado lleno cuyo excedente termine en el disponible.

---

### 📈 Inversiones - `/api/v2/investments/`

Vista agregada **por cuenta**. Para el detalle de cada apartado usa
[`/api/v2/positions/`](#-apartados-de-inversión---apiv2positions).

#### Obtener Rendimientos de una Cuenta
```bash
GET /api/v2/investments/{account_id}/yields/
```

Retorna el historial de rendimientos diarios de todos los apartados de la cuenta.

**Response:**
```json
[
  {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "yield_date": "2024-06-15",
    "principal_amount": 10000.00,
    "yield_amount": 2.74,
    "cumulative_balance": 10002.74,
    "annual_rate": 10.00,
    "interest_type": "SIMPLE",
    "created_at": "2024-06-15T12:00:00Z"
  }
]
```

**Tipos de interés:**
- `SIMPLE`: Usa el `base_principal` del apartado (el capital, sin los rendimientos ya generados)
- `COMPOUND`: Usa el valor total del apartado (capital + rendimiento acumulado)

#### Obtener Proyecciones de una Cuenta
```bash
GET /api/v2/investments/{account_id}/projections/
```

Suma día a día las proyecciones de todos los apartados activos de la cuenta. Cada plazo
fijo se proyecta solo hasta su vencimiento y después aporta su valor final sin crecer
(no se asume renovación).

**Response:**
```json
{
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "current_balance": 10000.00,
  "annual_rate": 10.00,
  "interest_type": "SIMPLE",
  "maturity_date": "2025-01-01",
  "projected_final_balance": 11000.00,
  "daily_projections": [
    {
      "projection_date": "2024-06-16",
      "principal_amount": 10000.00,
      "yield_amount": 2.74,
      "projected_balance": 10002.74
    }
  ]
}
```

> `current_balance` aquí es la suma de los apartados activos, no el disponible de la
> cuenta. `annual_rate`, `interest_type` y `maturity_date` llegan en `null` cuando la
> cuenta tiene **más de un apartado**, porque en ese caso no existe una sola tasa: pide
> el detalle apartado por apartado.

### 🤖 IA - `/api/v2/ai/`

#### Analizar Imagen (Recibo/Ticket)
```bash
POST /api/v2/ai/analyze/image
```

Usa Google Gemini para extraer datos estructurados de una imagen de recibo o ticket. Detecta automáticamente si es una transacción o una suscripción.

**Límite de rate:** 1 request por día por IP.

**Request:** `multipart/form-data`
- `file`: Archivo de imagen (PNG, JPG, etc.)

**Response:**
```json
{
  "is_subscription": false,
  "amount": "250.50",
  "description": "Compra en supermercado",
  "category": "ALIMENTACION",
  "category_id": null,
  "transaction_date": "2024-12-14",
  "notes": null,
  "transaction_type": "EXPENSE",
  "frequency": null,
  "billing_day": null,
  "name": null
}
```

Si `is_subscription=true`, los campos `frequency`, `billing_day` y `name` estarán presentes y `transaction_type` será `null`.

#### Asesor de Gastos
```bash
GET /api/v2/ai/expense_advisor
```

Analiza las transacciones del mes actual del usuario y genera recomendaciones personalizadas de ahorro por categoría.

**Límite de rate:** 1 request por día por IP.

**Response:**
```json
{
  "suggestions": [
    {
      "category": "Alimentación",
      "current_amount": 4500.00,
      "suggested_amount": 3500.00,
      "tip": "Considera planificar comidas semanales para reducir gastos en restaurantes."
    }
  ],
  "total_current": 12000.00,
  "total_suggested": 9500.00,
  "summary": "Tus gastos del mes están por encima del promedio recomendado. Las categorías con mayor potencial de ahorro son Alimentación y Entretenimiento."
}
```

> **Nota**: Si no hay transacciones registradas en el mes actual, el endpoint retorna `404` con código `NOT_FOUND_ACTIVITY`.

### 🏦 Bancos - `/api/v2/bank/`

#### Listar Bancos
```bash
GET /api/v2/bank/
```

Retorna el catálogo de bancos disponibles.

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `only_active` | bool | Solo bancos activos (default: true) |

**Response:**
```json
{
  "banks": [
    {
      "id": 1,
      "name": "BBVA México",
      "code": "BBVA",
      "country": "MX",
      "logo_url": "https://example.com/bbva-logo.png",
      "color": "#004481",
      "is_active": true
    }
  ],
  "total": 1
}
```

### 💵 Ingresos Recurrentes - `/api/v2/incomes/`

Gestiona ingresos recurrentes (nómina, renta, etc.). La lectura requiere scope `incomes:read`; crear, editar y eliminar requieren `incomes:write`.

#### Listar Ingresos
```bash
GET /api/v2/incomes/
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `account_uuid` | string | Filtrar por UUID de la cuenta |
| `category_id` | int | Filtrar por ID de categoría |
| `active_only` | bool | Solo ingresos activos (default: false) |
| `limit` | int | Máximo de resultados (default: 100, max: 1000) |
| `offset` | int | Offset para paginación (default: 0) |

**Response:** lista de ingresos con `uuid`, `name`, `account_uuid`, `account_name`, `category_name`, `frequency`, `amount`, `currency`, `start_date`, `end_date`, `next_payment_date`, `is_active`, `description` y `creation_date`.

#### Obtener Ingreso por UUID
```bash
GET /api/v2/incomes/{income_uuid}/
```

**Response:** Misma estructura que un elemento individual del listado.

#### Listar Depósitos de un Ingreso
```bash
GET /api/v2/incomes/{income_uuid}/deposits/
```

Historial de depósitos generados automáticamente por el ingreso recurrente. Acepta `limit` y `offset`.

**Response:** lista con `uuid`, `deposit_date`, `amount`, `currency`, `status` y `transaction_uuid` de cada depósito.

#### Crear Ingreso
```bash
POST /api/v2/incomes/
```

**Request:**
```json
{
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "category_id": 3,
  "name": "Nómina Empresa X",
  "amount": 15000.00,
  "frequency": "BIWEEKLY",
  "start_date": "2026-08-01",
  "end_date": null,
  "next_payment_date": null,
  "description": "Pago quincenal de nómina"
}
```

Campos opcionales: `end_date`, `next_payment_date` (default: `start_date`) y `description`. Las frecuencias son las mismas que en suscripciones.

**Response:** `201 Created` con la misma estructura del listado.

#### Actualizar Ingreso
```bash
PATCH /api/v2/incomes/{income_uuid}/
```

**Request:** todos los campos son opcionales (`account_uuid`, `name`, `amount`, `frequency`, `start_date`, `end_date`, `next_payment_date`, `is_active`, `description`, `category_id`).

#### Activar/Desactivar Ingreso
```bash
PATCH /api/v2/incomes/{income_uuid}/activate/
```

Alterna el estado activo/inactivo del ingreso.

#### Eliminar Ingreso
```bash
DELETE /api/v2/incomes/{income_uuid}/
```

**Response:** `204 No Content`

### 🎯 Presupuestos - `/api/v2/budgets/`

La lectura requiere scope `budgets:read`; crear, editar y eliminar requieren `budgets:write`.

#### Listar Presupuestos
```bash
GET /api/v2/budgets/
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `active_only` | bool | Solo presupuestos activos (default: false) |
| `category_id` | int | Filtrar por categoría |

**Response:** lista con `uuid`, `name`, `category_id`, `category_name`, `limit_amount`, `period`, `start_date`, `end_date`, `is_active`, `alert_percentage` y `creation_date`.

#### Obtener Presupuesto por UUID
```bash
GET /api/v2/budgets/{budget_uuid}/
```

#### Progreso de un Presupuesto
```bash
GET /api/v2/budgets/{budget_uuid}/progress/
```

Progreso del presupuesto en el periodo actual.

**Response:** `uuid`, `name`, `category_id`, `category_name`, `limit_amount`, `spent_amount`, `remaining_amount`, `percentage_used`, `alert_percentage`, `is_alert_triggered`, `is_limit_exceeded`, `period`, `period_start`, `period_end` e `is_active`.

#### Crear Presupuesto
```bash
POST /api/v2/budgets/
```

**Request:**
```json
{
  "name": "Comida mensual",
  "limit_amount": 5000.00,
  "period": "mensual",
  "start_date": "2025-05-01",
  "category_id": 1,
  "end_date": null,
  "alert_percentage": 80
}
```

`category_id` es opcional (si se omite, aplica a todas las categorías) y `alert_percentage` es opcional (default 80, rango 1-100). Periodos disponibles: `semanal`, `quincenal`, `mensual`, `trimestral`, `anual`.

**Response:** `201 Created`

#### Actualizar Presupuesto
```bash
PATCH /api/v2/budgets/{budget_uuid}/
```

**Request:** todos los campos son opcionales (`name`, `limit_amount`, `period`, `start_date`, `end_date`, `alert_percentage`, `category_id`).

#### Activar/Desactivar Presupuesto
```bash
PATCH /api/v2/budgets/{budget_uuid}/activate/
```

Alterna el estado activo/inactivo del presupuesto.

#### Eliminar Presupuesto
```bash
DELETE /api/v2/budgets/{budget_uuid}/
```

**Response:** `204 No Content`

### 🏆 Metas de Ahorro - `/api/v2/goals/`

La lectura requiere scope `goals:read`; crear, editar y eliminar requieren `goals:write`.

#### Listar Metas
```bash
GET /api/v2/goals/
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `active_only` | bool | Solo metas activas (default: false) |

**Response:** lista con `uuid`, `account_uuid`, `account_name`, `name`, `target_amount`, `current_amount`, `progress_percentage`, `target_date`, `description`, `is_active`, `completion_date` y `creation_date`.

#### Obtener Meta por UUID
```bash
GET /api/v2/goals/{goal_uuid}/
```

#### Crear Meta
```bash
POST /api/v2/goals/
```

**Request:**
```json
{
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Viaje a Japón",
  "target_amount": 50000.00,
  "target_date": "2027-01-01",
  "description": "Ahorro para vacaciones"
}
```

`target_date` y `description` son opcionales.

**Response:** `201 Created`

#### Actualizar Meta
```bash
PUT /api/v2/goals/{goal_uuid}/
```

**Request:** todos los campos son opcionales (`name`, `target_amount`, `target_date`, `description`).

#### Activar/Desactivar Meta
```bash
PATCH /api/v2/goals/{goal_uuid}/activate/
```

Alterna el estado activo/inactivo de la meta.

#### Eliminar Meta
```bash
DELETE /api/v2/goals/{goal_uuid}/
```

**Response:** `204 No Content`

### 🛒 Compras a Plazos (MSI) - `/api/v2/installments/`

La lectura requiere scope `installments:read`; crear, pagar, editar y eliminar requieren `installments:write`.

#### Listar Compras a Plazos
```bash
GET /api/v2/installments/
```

**Response:** lista de compras con `uuid`, `account_uuid`, `category_id`, `description`, `total_amount`, `num_installments`, `installment_type` (`NO_INTEREST` o `WITH_INTEREST`), `annual_interest_rate`, `monthly_payment`, `purchase_date`, `notes`, `is_active`, `creation_date` y `charges` (cada cargo con `uuid`, `installment_number`, `amount`, `due_date`, `paid` y `paid_at`).

#### Crear Compra a Plazos
```bash
POST /api/v2/installments/
```

**Request:**
```json
{
  "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "category_id": 10,
  "description": "Laptop a 12 meses",
  "total_amount": 24000.00,
  "num_installments": 12,
  "installment_type": "NO_INTEREST",
  "annual_interest_rate": 0,
  "purchase_date": "2026-07-15",
  "notes": null
}
```

`num_installments` admite valores de 2 a 48; `annual_interest_rate` es 0 si es a meses sin intereses.

#### Pagar un Cargo
```bash
POST /api/v2/installments/{charge_uuid}/pay/
```

**Request:**
```json
{
  "payment_date": "2026-08-15"
}
```

**Response:** el cargo actualizado (`uuid`, `installment_number`, `amount`, `due_date`, `paid`, `paid_at`).

#### Actualizar Compra a Plazos
```bash
PATCH /api/v2/installments/{purchase_uuid}/
```

**Request:** todos los campos son opcionales (`description`, `notes`, `category_id`).

#### Eliminar Compra a Plazos
```bash
DELETE /api/v2/installments/{purchase_uuid}/
```

**Response:** `204 No Content`

### 🔁 Transferencias - `/api/v2/transfers/`

Requieren scope `transfers:write` (crear y eliminar). Las transferencias se consultan dentro de las transacciones.

#### Crear Transferencia
```bash
POST /api/v2/transfers/
```

**Request:**
```json
{
  "source_account_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "destination_account_uuid": "660e8400-e29b-41d4-a716-446655440001",
  "amount": 1000.00,
  "description": "Ahorro mensual",
  "notes": null,
  "transfer_date": "2026-07-28"
}
```

`description`, `notes` y `transfer_date` son opcionales.

**Response:** `201 Created` con `transfer_uuid`, `amount`, `transfer_date`, `description`, `source_account_name`, `source_account_uuid`, `destination_account_name`, `destination_account_uuid` y `creation_date`.

#### Eliminar Transferencia
```bash
DELETE /api/v2/transfers/{transfer_uuid}/
```

**Response:** `204 No Content`

### 🔔 Notificaciones - `/api/v2/notifications/`

#### Obtener y Limpiar Notificaciones
```bash
GET /api/v2/notifications/
```

Retorna las notificaciones pendientes del usuario y las limpia (una vez leídas, desaparecen). **Solo JWT** (no accesible con API key). Límite: 5 requests/minuto.

**Response:** lista con `id`, `title`, `message`, `type` (`sms`, `email` o `push`) y `created_at`.

## 💡 Ejemplos de Uso

### Flujo Completo desde Cero

```bash
# 1. Registrar el usuario
curl -X POST "http://localhost:8000/api/v2/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "juanperez",
       "password": "MiClave123!"
     }'

# 2. Iniciar sesión y guardar los tokens
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v2/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "juanperez",
       "password": "MiClave123!"
     }')

export ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r .access_token)
export REFRESH_TOKEN=$(echo "$RESPONSE" | jq -r .refresh_token)

# 3. Verificar usuario autenticado
curl -X GET "http://localhost:8000/api/v2/auth/me" \
     -H "Authorization: Bearer $ACCESS_TOKEN"

# 4. Crear primera cuenta
curl -X POST "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Cuenta Principal",
       "account_type": "CHECKING",
       "bank_id": 1,
       "initial_balance": 5000.00
     }'

# 5. Listar todas las cuentas
curl -X GET "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Gestión de Múltiples Cuentas

```bash
# Crear cuenta de ahorros
curl -X POST "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Ahorro para Vacaciones",
       "account_type": "SAVINGS",
       "bank_id": 1,
       "initial_balance": 2000.00
     }'

# Crear cuenta de inversión (la etiqueta no genera rendimientos por sí sola)
curl -X POST "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Inversiones GBM",
       "account_type": "INVESTMENT",
       "bank_id": 5,
       "initial_balance": 10000.00
     }'

# Apartar 6,000 de esa cuenta a plazo fijo de 90 días al 12.5%
curl -X POST "http://localhost:8000/api/v2/positions/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
       "name": "Plazo 90 días",
       "position_type": "FIXED_TERM",
       "amount": 6000.00,
       "annual_rate": 12.50,
       "term_days": 90,
       "on_maturity": "AUTO_RENEW"
     }'

# Ver el disponible, lo invertido y el total de la cuenta
curl -X GET "http://localhost:8000/api/v2/positions/account/550e8400-e29b-41d4-a716-446655440000/" \
     -H "Authorization: Bearer $ACCESS_TOKEN"

# Regresar dinero de un apartado a la vista al saldo disponible
curl -X POST "http://localhost:8000/api/v2/positions/770e8400-e29b-41d4-a716-446655440009/withdraw/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"amount": 1500.00}'

# Tramos por monto: primero el apartado que recibe el excedente...
curl -X POST "http://localhost:8000/api/v2/positions/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "account_uuid": "550e8400-e29b-41d4-a716-446655440000",
       "name": "Excedente 5%",
       "position_type": "ON_DEMAND",
       "amount": 0.01,
       "annual_rate": 5.00
     }'

# ...y después se conecta el de la tasa alta con su tope
curl -X PATCH "http://localhost:8000/api/v2/positions/770e8400-e29b-41d4-a716-446655440009/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "cap": {
         "max_balance": 25000.00,
         "overflow_action": "TO_POSITION",
         "overflow_position_uuid": "880e8400-e29b-41d4-a716-446655440010"
       }
     }'

# Actualizar nombre de cuenta
curl -X PATCH "http://localhost:8000/api/v2/account/550e8400-e29b-41d4-a716-446655440000/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Ahorros Vacaciones Europa 2024"
     }'
```

## ⚠️ Manejo de Errores

La API retorna errores en un formato estándar con soporte de internacionalización (español e inglés). Todos los errores siguen la estructura:

```json
{
  "error_code": "ERROR_CODE",
  "message": "Mensaje descriptivo del error",
  "details": [
    {
      "loc": ["ubicación", "del", "error"],
      "msg": "Descripción específica del error",
      "type": "tipo_de_error",
      "input": "valor proporcionado (opcional)"
    }
  ]
}
```

### Errores de Autenticación (401)

```json
{
  "error_code": "AUTH_INVALID_CREDENTIALS",
  "message": "Las credenciales proporcionadas son inválidas",
  "details": null
}
```

**Otros códigos de autenticación:**
- `AUTH_USER_INACTIVE`: Usuario inactivo
- `JWT_VALIDATION_ERROR`: Token JWT inválido, expirado o mal formado

### Errores de Validación (422)

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Los datos proporcionados no son válidos",
  "details": [
    {
      "loc": ["body", "email"],
      "msg": "El campo email es requerido",
      "type": "missing",
      "input": null
    }
  ]
}
```

**Otros códigos de validación:**
- `VALIDATION_INVALID_AMOUNT`: Monto inválido
- `VALIDATION_INVALID_CURRENCY`: Moneda inválida
- `VALIDATION_INVALID_IMAGE`: Imagen inválida

### Errores de Recursos No Encontrados (404)

```json
{
  "error_code": "NOT_FOUND_ACCOUNT",
  "message": "La cuenta solicitada no fue encontrada",
  "details": null
}
```

**Otros códigos de recursos no encontrados:**
- `NOT_FOUND_USER`: Usuario no encontrado
- `NOT_FOUND_TRANSACTION`: Transacción no encontrada
- `NOT_FOUND_CATEGORY`: Categoría no encontrada
- `NOT_FOUND`: Recurso genérico no encontrado

### Errores de Negocio (409 o 400)

```json
{
  "error_code": "BUSINESS_ACCOUNT_HAS_BALANCE",
  "message": "No se puede eliminar una cuenta con balance diferente a cero",
  "details": null
}
```

**Otros códigos de negocio:**
- `BUSINESS_EMAIL_EXISTS` (409): Email ya registrado
- `BUSINESS_ACCOUNT_HAS_TRANSACTIONS` (409): Cuenta tiene transacciones
- `BUSINESS_RULE_VIOLATION` (400): Violación de regla de negocio genérica
- `INSUFFICIENT_FUNDS` (422): Fondos insuficientes (en apartados se compara siempre contra el **saldo disponible**, no contra el total de la cuenta)

**Códigos de apartados de inversión:**
- `NOT_FOUND_INVESTMENT_POSITION` (404): Apartado no encontrado
- `INVESTMENT_POSITION_NOT_ACTIVE` (409): El apartado ya está liquidado o vencido y no admite la operación
- `INVESTMENT_POSITION_LOCKED` (409): El plazo aún está en su periodo de permanencia y no puede liquidarse
- `FIXED_TERM_DEPOSIT_NOT_ALLOWED` (409): Un plazo fijo no admite depósitos después de creado
- `FIXED_TERM_WITHDRAWAL_NOT_ALLOWED` (409): Un plazo fijo no admite retiros parciales; debe liquidarse completo
- `INVESTMENT_POSITION_NOT_MATURED` (409): El plazo aún no llega a su vencimiento
- `POSITION_ACCOUNT_TYPE_NOT_ALLOWED` (409): Las tarjetas de crédito no admiten apartados
- `VALIDATION_INVALID_FIXED_TERM_CONFIG` (400): Un plazo fijo requiere `term_days` o `maturity_date` válidos
- `POSITION_CAP_EXCEEDED` (409): El monto inicial supera el tope del apartado
- `INVALID_OVERFLOW_TARGET` (409): El destino del excedente no existe, es de otra cuenta, no es a la vista, está liquidado o cerraría un ciclo
- `FIXED_TERM_CAP_NOT_ALLOWED` (409): Un plazo fijo no admite tope ni desbordamiento
- `VALIDATION_INVALID_POSITION_CAP` (400): Tope menor o igual a cero, o destino de desbordamiento sin tope

### Rate Limit Exceeded (429)

```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Límite de solicitudes excedido",
  "details": [
    {
      "loc": ["rate_limit"],
      "msg": "Rate limit exceeded: 100 per 1 minute",
      "type": "rate_limit_exceeded",
      "input": null
    }
  ]
}
```

La respuesta incluye headers:
- `Retry-After`: Segundos hasta que puedas reintentar
- `X-RateLimit-Remaining`: `0`

### Internacionalización

La API detecta automáticamente el idioma del usuario mediante el header `Accept-Language`. Idiomas soportados:
- **Español (es)**: Idioma por defecto
- **Inglés (en)**

Ejemplo de request con idioma específico:
```bash
curl -X GET "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Accept-Language: en"
```

## 🚦 Códigos de Estado HTTP

| Código | Significado | Uso |
|--------|-------------|-----|
| 200 | OK | Operación exitosa |
| 201 | Created | Recurso creado exitosamente |
| 400 | Bad Request | Error de validación en el request |
| 401 | Unauthorized | Token inválido o faltante |
| 403 | Forbidden | Sin permisos para el recurso |
| 404 | Not Found | Recurso no encontrado |
| 422 | Unprocessable Entity | Error de validación de datos |
| 429 | Too Many Requests | Se excedió el límite de rate limiting |
| 500 | Internal Server Error | Error interno del servidor |

## 📄 Límites y Paginación

### Rate Limiting

La API implementa rate limiting específico por endpoint para proteger contra abuso. Los límites son aplicados por IP/usuario.

#### Endpoints de Autenticación

| Endpoint | Límite | Razón |
|----------|--------|-------|
| `POST /auth/register` | **5 requests/hora** | Evita el alta masiva de cuentas |
| `POST /auth/login` | **10 requests/minuto** | Frena los ataques de fuerza bruta |
| `POST /auth/refresh` | **20 requests/minuto** | Renovación de sesión |
| `POST /auth/logout` | **10 requests/minuto** | Operación normal |
| `GET /auth/me` | **100 requests/minuto** | Lectura de perfil frecuente |

> **Nota**: además de estos límites por endpoint, los intentos de autenticación fallidos se limitan por IP. Superarlos devuelve `429` aunque las credenciales acaben siendo correctas.

#### Endpoints de Cuentas

| Endpoint | Límite |
|----------|--------|
| `GET /account/` | **50 requests/minuto** |
| `POST /account/` | **50 requests/minuto** |
| `GET /account/{uuid}` | **50 requests/minuto** |
| `GET /account/{uuid}/activity` | **50 requests/minuto** |
| `PATCH /account/{uuid}/` | **50 requests/minuto** |
| `PATCH /account/{uuid}/status/` | **50 requests/minuto** |
| `DELETE /account/{uuid}/` | **50 requests/minuto** |

#### Endpoints de Transacciones

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /transaction/` | **50 requests/minuto** | Listado con filtros |
| `POST /transaction/` | **20 requests/minuto** | Creación manual |
| `GET /transaction/{uuid}/` | **50 requests/minuto** | Detalle de transacción |
| `PUT /transaction/{uuid}/` | **15 requests/minuto** | Actualización |
| `DELETE /transaction/{uuid}/` | **10 requests/minuto** | Eliminación |

#### Endpoints de Categorías

| Endpoint | Límite |
|----------|--------|
| `GET /category/` | **50 requests/minuto** |

#### Endpoints de Suscripciones

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /subscription/` | **50 requests/minuto** | Listado |
| `GET /subscription/charges/` | **50 requests/minuto** | Historial de cargos |
| `GET /subscription/{uuid}/` | Sin límite específico | Detalle |
| `GET /subscription/{uuid}/transactions/` | **20 requests/minuto** | Últimos cargos |
| `POST /subscription/` | **20 requests/minuto** | Creación |
| `PATCH /subscription/{uuid}/` | **20 requests/minuto** | Actualización |
| `PATCH /subscription/{uuid}/activate/` | **5 requests/minuto** | Activar/desactivar |
| `DELETE /subscription/{uuid}/` | **5 requests/minuto** | Eliminación |

#### Endpoints de Inversiones

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /investments/{id}/yields/` | **50 requests/minuto** | Rendimientos históricos de la cuenta |
| `GET /investments/{id}/projections/` | **30 requests/minuto** | Proyecciones agregadas de la cuenta |

#### Endpoints de Apartados de Inversión

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /positions/account/{uuid}/` | **50 requests/minuto** | Listado por cuenta |
| `GET /positions/{uuid}/` | **50 requests/minuto** | Detalle |
| `GET /positions/{uuid}/yields/` | **50 requests/minuto** | Rendimientos del apartado |
| `GET /positions/{uuid}/projections/` | **30 requests/minuto** | Proyecciones del apartado |
| `POST /positions/` | **20 requests/minuto** | Creación |
| `PATCH /positions/{uuid}/` | **20 requests/minuto** | Nombre y configuración de tope |
| `POST /positions/{uuid}/deposit/` | **20 requests/minuto** | Apartar dinero |
| `POST /positions/{uuid}/withdraw/` | **20 requests/minuto** | Regresar al disponible |
| `POST /positions/{uuid}/liquidate/` | **10 requests/minuto** | Cierre del apartado |

#### Endpoints de IA

| Endpoint | Límite | Nota |
|----------|--------|------|
| `POST /ai/analyze/image` | **1 request/día** | Análisis de imagen con Gemini |
| `GET /ai/expense_advisor` | **1 request/día** | Análisis de gastos del mes |

#### Endpoints de Bancos

| Endpoint | Límite |
|----------|--------|
| `GET /bank/` | **10 requests/minuto** |

#### Endpoints de Dashboard

| Endpoint | Límite |
|----------|--------|
| `GET /dashboard/` | **10 requests/minuto** |

#### Endpoints de Ingresos

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /incomes/` | **50 requests/minuto** | Listado |
| `GET /incomes/{uuid}/` | **50 requests/minuto** | Detalle |
| `GET /incomes/{uuid}/deposits/` | **20 requests/minuto** | Historial de depósitos |
| `POST /incomes/` | **20 requests/minuto** | Creación |
| `PATCH /incomes/{uuid}/` | **20 requests/minuto** | Actualización |
| `PATCH /incomes/{uuid}/activate/` | **5 requests/minuto** | Activar/desactivar |
| `DELETE /incomes/{uuid}/` | **5 requests/minuto** | Eliminación |

#### Endpoints de Presupuestos

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /budgets/` | **50 requests/minuto** | Listado |
| `GET /budgets/{uuid}/` | **50 requests/minuto** | Detalle |
| `GET /budgets/{uuid}/progress/` | **50 requests/minuto** | Progreso del periodo actual |
| `POST /budgets/` | **20 requests/minuto** | Creación |
| `PATCH /budgets/{uuid}/` | **20 requests/minuto** | Actualización |
| `PATCH /budgets/{uuid}/activate/` | **5 requests/minuto** | Activar/desactivar |
| `DELETE /budgets/{uuid}/` | **5 requests/minuto** | Eliminación |

#### Endpoints de Metas de Ahorro

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /goals/` | **50 requests/minuto** | Listado |
| `GET /goals/{uuid}/` | **50 requests/minuto** | Detalle |
| `POST /goals/` | **20 requests/minuto** | Creación |
| `PUT /goals/{uuid}/` | **20 requests/minuto** | Actualización |
| `PATCH /goals/{uuid}/activate/` | **5 requests/minuto** | Activar/desactivar |
| `DELETE /goals/{uuid}/` | **5 requests/minuto** | Eliminación |

#### Endpoints de Compras a Plazos

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /installments/` | **50 requests/minuto** | Listado |
| `POST /installments/` | **20 requests/minuto** | Creación |
| `POST /installments/{charge_uuid}/pay/` | **20 requests/minuto** | Pago de cargo |
| `PATCH /installments/{purchase_uuid}/` | **20 requests/minuto** | Actualización |
| `DELETE /installments/{purchase_uuid}/` | **20 requests/minuto** | Eliminación |

#### Endpoints de Transferencias

| Endpoint | Límite | Nota |
|----------|--------|------|
| `POST /transfers/` | **20 requests/minuto** | Creación |
| `DELETE /transfers/{transfer_uuid}/` | **10 requests/minuto** | Eliminación |

#### Endpoints de Notificaciones

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /notifications/` | **5 requests/minuto** | Obtiene y limpia notificaciones |

#### Endpoints de API Keys

| Endpoint | Límite | Nota |
|----------|--------|------|
| `POST /api-keys/` | **10 requests/minuto** | Creación |
| `GET /api-keys/` | **50 requests/minuto** | Listado |
| `PATCH /api-keys/{uuid}/revoke/` | **10 requests/minuto** | Revocación |
| `DELETE /api-keys/{uuid}/` | **10 requests/minuto** | Eliminación |

#### Endpoints Generales

| Endpoint | Límite |
|----------|--------|
| `GET /` | **10 requests/minuto** |
| `GET /health` | **5 requests/minuto** |

### ⚠️ Consideraciones Importantes

**Para Desarrollo y Testing:**
- Los endpoints de IA (`/ai/analyze/image` y `/ai/expense_advisor`) tienen límites diarios muy bajos (1 request/día cada uno)
- Los límites se aplican por IP, por lo que múltiples ejecuciones de tests desde la misma máquina se acumularán
- **Recomendación**: El rate limiting se deshabilita automáticamente cuando `ENVIRONMENT=TEST`, úsalo en tests

**Respuesta al Exceder el Límite:**
Cuando se excede el rate limit, recibirás un error `429 Too Many Requests` con el siguiente formato:

```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Límite de solicitudes excedido",
  "details": [
    {
      "loc": ["rate_limit"],
      "msg": "Rate limit exceeded: 5 per 1 hour",
      "type": "rate_limit_exceeded",
      "input": null
    }
  ]
}
```

La respuesta incluye los siguientes headers:
- `Retry-After`: Segundos hasta que puedas reintentar
- `X-RateLimit-Remaining`: `0`

> **Nota**: Los límites expresados en días (p. ej. endpoints `/ai/`) muestran `per 1 day` en el mensaje.

### Paginación

Los endpoints de listado soportan paginación por `limit`/`offset` (transacciones usa `skip`/`limit`):

```bash
GET /api/v2/account/?limit=20&offset=0
```

Algunas respuestas de listado (cuentas, categorías y bancos) incluyen además el campo `total` con el número de elementos devueltos en la respuesta.

## 🔧 Herramientas Recomendadas

### 🧪 Bruno Collection

Lunance IA incluye una colección completa de [Bruno](https://www.usebruno.com/) con todos los endpoints de la API pre-configurados para facilitar el testing y desarrollo.

**📁 Ubicación**: `http/bruno collection/Lunance IA.json`

#### ¿Qué es Bruno?

Bruno es un cliente API de código abierto, offline-first y Git-friendly que:
- ✅ **No requiere cuenta**: Trabaja completamente offline
- ✅ **Git-friendly**: Guarda colecciones en archivos JSON planos versionables
- ✅ **Open source**: Software libre y gratuito
- ✅ **Rápido y ligero**: Menor uso de recursos que alternativas
- ✅ **Variables de entorno**: Soporte completo para múltiples entornos

#### Instalación y Configuración

**1. Instalar Bruno**
```bash
# macOS
brew install bruno

# O descarga desde https://www.usebruno.com/downloads
```

**2. Importar la Colección**
1. Abre Bruno
2. Click en "Open Collection"
3. Navega a `http/bruno collection/`
4. Selecciona el archivo `Lunance IA.json`

**3. Configurar Variables de Entorno**

Configura las variables de entorno correspondientes.

**4. Flujo de Trabajo Recomendado**
1. Ejecuta el request de **Register** o **Login** en la carpeta `Auth`
2. Copia el `access_token` de la respuesta y pégalo en las variables de entorno
3. Todos los demás requests usarán ese token automáticamente desde las variables
4. Explora las carpetas organizadas por endpoint (Auth, Accounts, etc.)

> ⚠️ **Nota**: El guardado automático de tokens mediante scripts post-request estará disponible en una futura actualización.

#### Ventajas sobre cURL

| Característica | cURL | Bruno |
|----------------|------|-------|
| Interfaz visual | ❌ | ✅ |
| Historial de requests | ❌ | ✅ |
| Variables de entorno | Manual | ✅ Soporte completo |
| Guardar tokens | Manual | 🔄 Manual (por ahora) |
| Organización | ❌ | ✅ Carpetas |
| Versionable en Git | ❌ | ✅ JSON plano |
| Tests automatizados | ❌ | ✅ Soporte scripts |

#### Tips Útiles

- **Variables de entorno**: Usa variables para cambiar fácilmente entre entornos (Local, Staging, Production)
- **Testing rápido**: Usa `Ctrl/Cmd + Enter` para ejecutar requests rápidamente
- **Colecciones compartibles**: Comparte la colección con tu equipo vía Git
- **Organización**: Los requests están organizados por módulos para fácil navegación

### Cliente Python

```python
import httpx

class LunanceClient:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.token = token
        self.refresh_token = None
        self.client = httpx.AsyncClient()

    async def login(self, username: str, password: str):
        """Inicia sesión y guarda el access token para las siguientes llamadas."""
        response = await self.client.post(
            f"{self.base_url}/api/v2/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        return data

    async def refresh(self):
        """Renueva el par de tokens. El refresh token anterior queda invalidado."""
        response = await self.client.post(
            f"{self.base_url}/api/v2/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        return data

    async def get_me(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v2/auth/me",
            headers=headers
        )
        return response.json()

    async def get_accounts(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v2/account/",
            headers=headers
        )
        return response.json()

# Uso
client = LunanceClient()
await client.login("juanperez", "MiClave123!")
user = await client.get_me()
accounts = await client.get_accounts()
```

## 📚 Documentación

> **Nota**: Swagger UI (`/docs`) y ReDoc (`/redoc`) están **habilitados** cuando `ENVIRONMENT != "PROD"`; en producción se deshabilitan (junto con `/openapi.json`). En producción, usa esta guía y la colección de Bruno como referencia principal para la API.

---

> 💡 **Tip**: Para desarrollo y testing, usa la documentación interactiva de Swagger. Para integración en producción, sigue los ejemplos de esta guía.

¿Tienes preguntas sobre el uso de la API? Consulta la [guía de contribución](./CONTRIBUTING.md) o crea un issue en el repositorio.
