# 📖 Guía de Uso de la API - Lunance IA

Esta guía te mostrará cómo usar la API REST de Lunance IA v2, incluyendo autenticación, endpoints principales y ejemplos prácticos.

## 📋 Tabla de Contenidos

- [Autenticación JWT](#autenticación-jwt)
- [Endpoints Principales](#endpoints-principales)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Manejo de Errores](#manejo-de-errores)
- [Códigos de Estado](#códigos-de-estado)
- [Límites y Paginación](#límites-y-paginación)

## 🔐 Autenticación JWT

La API utiliza JWT (JSON Web Tokens) para autenticación. Todos los endpoints requieren autenticación excepto login y register.

### Obtener Token de Acceso

```bash
curl -X POST "http://localhost:8000/api/v2/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "usuario@ejemplo.com",
       "password": "tu_password_seguro"
     }'
```

**Respuesta exitosa:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Usar Token en Requests

Incluye el token en el header `Authorization` de todos los requests autenticados:

```bash
curl -X GET "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Renovar Token

Cuando el access token expire, usa el refresh token para obtener uno nuevo:

```bash
curl -X POST "http://localhost:8000/api/v2/auth/refresh" \
     -H "Content-Type: application/json" \
     -d '{
       "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
     }'
```

## 🌐 Endpoints Principales

### 🔐 Autenticación - `/api/v2/auth/`

#### Registrar Usuario
```bash
POST /api/v2/auth/register
```

**Request:**
```json
{
  "email": "nuevo@ejemplo.com",
  "password": "password_seguro123",
  "first_name": "Juan",
  "last_name": "Pérez"
}
```

**Response:**
```json
{
  "message": "Usuario registrado exitosamente",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Iniciar Sesión
```bash
POST /api/v2/auth/login
```

#### Renovar Token
```bash
POST /api/v2/auth/refresh
```

#### Cerrar Sesión
```bash
POST /api/v2/auth/logout
```

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

### 💰 Transacciones - `/api/v2/transaction/` (Próximamente)

Los endpoints de transacciones estarán disponibles próximamente con funcionalidades como:

- `GET /` - Listar transacciones con filtros
- `POST /` - Crear nueva transacción
- `GET /{transaction_id}` - Obtener transacción específica
- `PUT /{transaction_id}` - Actualizar transacción
- `DELETE /{transaction_id}` - Eliminar transacción

## 💡 Ejemplos de Uso

### Flujo Completo: Registro y Creación de Cuenta

```bash
# 1. Registrar nuevo usuario
curl -X POST "http://localhost:8000/api/v2/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "maria@ejemplo.com",
       "password": "MiPassword123",
       "first_name": "María",
       "last_name": "González"
     }'

# 2. Iniciar sesión
curl -X POST "http://localhost:8000/api/v2/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "maria@ejemplo.com",
       "password": "MiPassword123"
     }'

# 3. Guardar el token de la respuesta
export ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

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

La API retorna errores en formato estándar con detalles descriptivos:

### Errores de Autenticación

```json
{
  "detail": "Could not validate credentials",
  "type": "authentication_error"
}
```

### Errores de Validación

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "type": "validation_error"
}
```

### Errores de Negocio

```json
{
  "detail": "No se puede eliminar cuenta con balance diferente a cero",
  "type": "business_rule_error"
}
```

### Errores de Recursos No Encontrados

```json
{
  "detail": "Cuenta no encontrada",
  "type": "not_found_error"
}
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
| 500 | Internal Server Error | Error interno del servidor |

## 📄 Límites y Paginación

### Rate Limiting

- **Límite por IP**: 100 requests por minuto
- **Límite por usuario autenticado**: 1000 requests por minuto

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

### Postman Collection

Importa nuestra colección de Postman para probar todos los endpoints:
```
[Enlace a colección Postman - Próximamente]
```

### Cliente Python

```python
import httpx

class LunanceClient:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.token = token
        self.client = httpx.Client()
    
    async def login(self, email: str, password: str):
        response = await self.client.post(
            f"{self.base_url}/api/v2/auth/login",
            json={"email": email, "password": password}
        )
        data = response.json()
        self.token = data["access_token"]
        return data
    
    async def get_accounts(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v2/account/",
            headers=headers
        )
        return response.json()

# Uso
client = LunanceClient()
await client.login("user@example.com", "password")
accounts = await client.get_accounts()
```

## 📚 Documentación Interactiva

Una vez iniciado el servidor, accede a la documentación interactiva:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Estas herramientas te permiten:
- ✅ Probar todos los endpoints directamente
- ✅ Ver esquemas de request/response
- ✅ Generar código en múltiples lenguajes
- ✅ Descargar especificación OpenAPI

---

> 💡 **Tip**: Para desarrollo y testing, usa la documentación interactiva de Swagger. Para integración en producción, sigue los ejemplos de esta guía.

¿Tienes preguntas sobre el uso de la API? Consulta la [guía de contribución](./CONTRIBUTING.md) o crea un issue en el repositorio.