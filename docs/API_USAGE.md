# 📖 Guía de Uso de la API - Lunance IA

Esta guía te mostrará cómo usar la API REST de Lunance IA v2, incluyendo autenticación, endpoints principales y ejemplos prácticos.

## 📋 Tabla de Contenidos

- [Autenticación JWT](#autenticación-jwt)
- [Autenticación con API Keys](#-autenticación-con-api-keys)
- [Endpoints Principales](#endpoints-principales)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Manejo de Errores](#manejo-de-errores)
- [Códigos de Estado](#códigos-de-estado)
- [Límites y Paginación](#límites-y-paginación)
- [IA - Análisis y Asesoría](#-ia---apiv2ai)

## 🔐 Autenticación con Auth0

La API utiliza **Auth0** para autenticación. Los tokens JWT son emitidos por Auth0 y validados por la API.

### Flujo de Autenticación

1. **Login/Register**: Se realiza directamente con Auth0 (frontend)
2. **Token JWT**: Auth0 emite un access token
3. **API Requests**: Incluir el token en el header `Authorization`

### Usar Token en Requests

Incluye el token de Auth0 en el header `Authorization` de todos los requests autenticados:

```bash
curl -X GET "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer <auth0_access_token>"
```

### Obtener Información del Usuario

```bash
curl -X GET "http://localhost:8000/api/v2/auth/me" \
     -H "Authorization: Bearer <auth0_access_token>"
```

**Respuesta:**
```json
{
  "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Juan Pérez",
  "email": "juan@ejemplo.com",
  "is_active": true
}
```

### Cerrar Sesión

```bash
curl -X POST "http://localhost:8000/api/v2/auth/logout" \
     -H "Authorization: Bearer <auth0_access_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "refresh_token": "<refresh_token>"
     }'
```

## 🔑 Autenticación con API Keys

Además del JWT (usuarios humanos), la API soporta **API keys** para acceso programático: integraciones, automatizaciones y agentes/LLM (vía MCP). El usuario genera la key desde la app y la incluye en el header `X-API-Key`.

### JWT vs API Key

| | JWT (`Authorization: Bearer`) | API Key (`X-API-Key`) |
|---|---|---|
| Para | Usuario en la app | Acceso programático / integraciones |
| Alcance | Acceso completo | Limitado por **scopes** |
| Puede editar / eliminar | Sí | **No** (solo lectura y creación) |

Los endpoints aceptan **ambos** métodos (autenticación dual): si llega `X-API-Key` se usa esa vía; si no, se valida el JWT. Un usuario por JWT siempre tiene acceso completo; una API key solo puede hacer lo que sus scopes permitan.

### Scopes disponibles

| Scope | Permite |
|-------|---------|
| `transactions:read` | Listar y ver transacciones |
| `transactions:write` | Crear transacciones |
| `accounts:read` | Listar / ver cuentas *(pendiente de habilitar)* |
| `categories:read` | Listar categorías *(pendiente de habilitar)* |
| `dashboard:read` | Ver dashboard *(pendiente de habilitar)* |

> No existen scopes de edición ni eliminación **a propósito**: una API key nunca puede modificar ni borrar datos.

### Usar una API Key en Requests

```bash
curl -X GET "http://localhost:8000/api/v2/transaction/" \
     -H "X-API-Key: moon_xxxxxxxxxxxxxxxxxxxxxxxx"
```

Si la key no tiene el scope requerido, la API responde `403 Forbidden`. Si es inválida, fue revocada o expiró, responde `401 Unauthorized`.

> La gestión de keys (crear / listar / revocar) se hace **con JWT**, no con API key. Ver [API Keys](#-api-keys---apiv2api-keys) en la sección de endpoints.

## 🌐 Endpoints Principales

### 🔐 Autenticación - `/api/v2/auth/`

> **Nota**: Login y registro se manejan directamente con Auth0. La API solo expone endpoints para obtener información del usuario y cerrar sesión.

#### Obtener Información del Usuario
```bash
GET /api/v2/auth/me
```

**Response:**
```json
{
  "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Juan Pérez",
  "email": "juan@ejemplo.com",
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
DELETE /api/v2/api-keys/{api_key_uuid}/
```

**Response:** `204 No Content` si se revocó; `404 Not Found` si no existe o no pertenece al usuario. La revocación es permanente (la key queda inactiva).

### 💳 Cuentas - `/api/v2/account/`

#### Listar Cuentas del Usuario
```bash
GET /api/v2/account/
```

**Response:**
```json
{
  "accounts": [
    {
      "id": "123",
      "name": "Cuenta de Ahorros BBVA",
      "account_type": "SAVINGS",
      "bank": "BBVA",
      "balance": {
        "amount": 15500.75,
        "currency": "MXN"
      },
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": "124",
      "name": "Tarjeta de Crédito Banamex",
      "account_type": "CREDIT",
      "bank": "Banamex",
      "balance": {
        "amount": -2500.00,
        "currency": "MXN"
      },
      "is_active": true,
      "created_at": "2024-02-01T14:22:00Z"
    }
  ]
}
```

#### Crear Nueva Cuenta
```bash
POST /api/v2/account/
```

**Request:**
```json
{
  "name": "Mi Cuenta de Ahorros",
  "account_type": "SAVINGS",
  "bank": "BBVA",
  "initial_balance": 1000.00
}
```

**Response:**
```json
{
  "id": "125",
  "name": "Mi Cuenta de Ahorros",
  "account_type": "SAVINGS",
  "bank": "BBVA",
  "balance": {
    "amount": 1000.00,
    "currency": "MXN"
  },
  "is_active": true,
  "created_at": "2024-07-03T16:45:00Z"
}
```

#### Obtener Cuenta por ID
```bash
GET /api/v2/account/{account_id}
```

**Response:**
```json
{
  "id": "123",
  "name": "Cuenta de Ahorros BBVA",
  "account_type": "SAVINGS",
  "bank": "BBVA",
  "balance": {
    "amount": 15500.75,
    "currency": "MXN"
  },
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-06-30T09:15:00Z"
}
```

#### Actualizar Cuenta
```bash
PUT /api/v2/account/{account_id}
```

**Request:**
```json
{
  "name": "Cuenta Principal BBVA",
  "bank": "BBVA Bancomer"
}
```

#### Eliminar Cuenta
```bash
DELETE /api/v2/account/{account_id}
```

**Response:**
```json
{
  "message": "Cuenta eliminada exitosamente"
}
```

#### Activar/Desactivar Cuenta
```bash
PATCH /api/v2/account/{account_uuid}/status/
```

Alterna el estado activo/inactivo de la cuenta.

**Response:** Misma estructura que obtener cuenta por ID.

### 💰 Transacciones - `/api/v2/transaction/`

> **Acceso por API key:** lectura requiere scope `transactions:read` y la creación `transactions:write`. `PUT` y `DELETE` son **solo JWT** (no accesibles con API key).

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
| `transaction_type` | string | Tipo: `INCOME` o `EXPENSE` |
| `category_id` | int | ID de categoría |
| `account_uuid` | string | UUID de la cuenta |

**Response:**
```json
[
  {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "category": "Alimentación",
    "transaction_type": "EXPENSE",
    "amount": 250.50,
    "transaction_date": "2024-12-14",
    "description": "Compra en supermercado",
    "notes": "Compra semanal",
    "creation_date": "2024-12-14T10:30:00Z",
    "account_name": "Cuenta Principal",
    "account_type": "CHECKING",
    "account_bank": "BBVA"
  }
]
```

#### Obtener Transacción por UUID
```bash
GET /api/v2/transaction/{transaction_uuid}
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

**Frecuencias disponibles:** `DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`

#### Actualizar Suscripción
```bash
PUT /api/v2/subscription/{subscription_uuid}/
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

### 📈 Inversiones - `/api/v2/investments/`

#### Obtener Rendimientos de una Cuenta de Inversión
```bash
GET /api/v2/investments/{account_id}/yields/
```

Retorna el historial de rendimientos diarios generados automáticamente para una cuenta de inversión.

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
- `SIMPLE`: Usa el `base_principal` (se actualiza con transacciones de ingreso)
- `COMPOUND`: Usa el balance actual de la cuenta como principal

#### Obtener Proyecciones de Inversión
```bash
GET /api/v2/investments/{account_id}/projections/
```

Retorna proyecciones de rendimiento futuro basadas en la configuración actual de la cuenta.

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

### 🤖 IA - `/api/v2/ai/`

#### Analizar Imagen (Recibo/Ticket)
```bash
POST /api/v2/ai/analyze/image
```

Usa Google Gemini para extraer datos estructurados de una imagen de recibo o ticket. Detecta automáticamente si es una transacción o una suscripción.

**Límite de rate:** 2 requests por día por IP.

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

> **Nota**: Si no hay transacciones registradas en el mes actual, el endpoint retorna `404` con código `NOT_FOUND_TRANSACTION_ACTIVITY`.

### 🏦 Bancos - `/api/v2/bank/`

#### Listar Bancos
```bash
GET /api/v2/bank/
```

Retorna el catálogo de bancos disponibles.

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

## 💡 Ejemplos de Uso

### Flujo Completo con Auth0

```bash
# 1. Obtener token de Auth0 (desde tu aplicación frontend)
# El login/registro se maneja directamente con Auth0

# 2. Guardar el token de Auth0
export ACCESS_TOKEN="<auth0_access_token>"

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
       "bank": "Santander",
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
       "bank": "BBVA",
       "initial_balance": 2000.00
     }'

# Crear cuenta de inversión
curl -X POST "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Inversiones GBM",
       "account_type": "INVESTMENT",
       "bank": "GBM",
       "initial_balance": 10000.00
     }'

# Actualizar nombre de cuenta
curl -X PUT "http://localhost:8000/api/v2/account/123" \
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
- `UNAUTHORIZED`: Token inválido o faltante

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
- `INSUFFICIENT_FUNDS` (400): Fondos insuficientes

### Rate Limit Exceeded (429)

```json
{
  "detail": "Rate limit exceeded: 100 per 1 minute"
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
| `GET /auth/me` | **100 requests/minuto** | Lectura de perfil frecuente |
| `POST /auth/logout` | **10 requests/minuto** | Operación normal |

> **Nota**: Login y registro se manejan a través de Auth0, no tienen rate limiting en esta API.

#### Endpoints de Cuentas

| Endpoint | Límite |
|----------|--------|
| `GET /account/` | **50 requests/minuto** |
| `POST /account/` | **50 requests/minuto** |
| `GET /account/{id}` | **50 requests/minuto** |
| `PUT /account/{id}` | **50 requests/minuto** |
| `DELETE /account/{id}` | **50 requests/minuto** |

#### Endpoints de Transacciones

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /transaction/` | **50 requests/minuto** | Listado con filtros |
| `POST /transaction/` | **20 requests/minuto** | Creación manual |
| `GET /transaction/{uuid}` | **50 requests/minuto** | Detalle de transacción |
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
| `GET /subscription/{uuid}/` | **50 requests/minuto** | Detalle |
| `POST /subscription/` | **20 requests/minuto** | Creación |
| `PUT /subscription/{uuid}/` | **20 requests/minuto** | Actualización |
| `PATCH /subscription/{uuid}/activate/` | **5 requests/minuto** | Activar/desactivar |
| `DELETE /subscription/{uuid}/` | **5 requests/minuto** | Eliminación |

#### Endpoints de Inversiones

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /investments/{id}/yields/` | **50 requests/minuto** | Rendimientos históricos |
| `GET /investments/{id}/projections/` | **30 requests/minuto** | Proyecciones |

#### Endpoints de IA

| Endpoint | Límite | Nota |
|----------|--------|------|
| `POST /ai/analyze/image` | **2 requests/día** | Análisis de imagen con Gemini |
| `GET /ai/expense_advisor` | **1 request/día** | Análisis de gastos del mes |

#### Endpoints de Bancos

| Endpoint | Límite |
|----------|--------|
| `GET /bank/` | **10 requests/minuto** |

#### Endpoints de Dashboard

| Endpoint | Límite |
|----------|--------|
| `GET /dashboard/` | **10 requests/minuto** |

#### Endpoints Generales

| Endpoint | Límite |
|----------|--------|
| `GET /` | **10 requests/minuto** |
| `GET /health` | **5 requests/minuto** |

### ⚠️ Consideraciones Importantes

**Para Desarrollo y Testing:**
- Los endpoints de IA (`/ai/analyze/image` y `/ai/expense_advisor`) tienen límites diarios muy bajos (2/día y 1/día respectivamente)
- Los límites se aplican por IP, por lo que múltiples ejecuciones de tests desde la misma máquina se acumularán
- **Recomendación**: El rate limiting se deshabilita automáticamente cuando `ENVIRONMENT=TEST`, úsalo en tests

**Respuesta al Exceder el Límite:**
Cuando se excede el rate limit, recibirás un error `429 Too Many Requests` con el siguiente formato:

```json
{
  "detail": "Rate limit exceeded: 5 per 1 hour"
}
```

La respuesta incluye los siguientes headers:
- `Retry-After`: Segundos hasta que puedas reintentar
- `X-RateLimit-Remaining`: `0`

> **Nota**: Los límites expresados en días (p. ej. endpoints `/ai/`) muestran `per 1 day` en el mensaje.

### Paginación (Próximamente)

Los endpoints que retornan listas soportarán paginación:

```bash
GET /api/v2/account/?page=1&size=20
```

**Response con paginación:**
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "size": 20,
  "pages": 8
}
```

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
        self.client = httpx.AsyncClient()

    def set_token(self, auth0_token: str):
        """Configura el token de Auth0 obtenido desde el frontend."""
        self.token = auth0_token

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
client.set_token("<auth0_access_token>")
user = await client.get_me()
accounts = await client.get_accounts()
```

## 📚 Documentación

> **Nota**: Swagger UI y ReDoc están deshabilitados por defecto en la configuración actual. Usa esta guía y la colección de Bruno como referencia principal para la API.

---

> 💡 **Tip**: Para desarrollo y testing, usa la documentación interactiva de Swagger. Para integración en producción, sigue los ejemplos de esta guía.

¿Tienes preguntas sobre el uso de la API? Consulta la [guía de contribución](./CONTRIBUTING.md) o crea un issue en el repositorio.
