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
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Se ha excedido el límite de peticiones",
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
| `POST /auth/register` | **5 requests/hora** | Prevención de spam y registro masivo |
| `POST /auth/login` | **10 requests/minuto** | Protección contra fuerza bruta |
| `POST /auth/refresh` | **20 requests/minuto** | Renovación frecuente permitida |
| `POST /auth/logout` | **10 requests/minuto** | Operación normal |
| `GET /auth/me` | **100 requests/minuto** | Lectura de perfil frecuente |

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
| `GET /transaction/` | **50 requests/minuto** | - |
| `POST /transaction/` | **50 requests/minuto** | - |
| `POST /transaction/upload-image` | **5 requests/minuto** | Procesamiento intensivo de imágenes |
| `GET /transaction/{id}` | **20 requests/minuto** | - |
| `PUT /transaction/{id}` | **15 requests/minuto** | - |
| `DELETE /transaction/{id}` | **10 requests/minuto** | - |

#### Endpoints Generales

| Endpoint | Límite |
|----------|--------|
| `GET /` | **50 requests/minuto** |
| `GET /health` | **5 requests/minuto** |

### ⚠️ Consideraciones Importantes

**Para Desarrollo y Testing:**
- El límite de **5 registros/hora** en `/auth/register` puede afectar la ejecución repetida de tests
- Si ejecutas tests automatizados que crean usuarios, considera espaciarlos en el tiempo
- Los límites se aplican por IP, por lo que múltiples ejecuciones de tests desde la misma máquina se acumularán
- **Recomendación**: Para desarrollo local, considera aumentar temporalmente estos límites en el código o usar usuarios pre-existentes en tus tests

**Respuesta al Exceder el Límite:**
Cuando se excede el rate limit, recibirás un error `429 Too Many Requests` con el siguiente formato:

```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Se ha excedido el límite de peticiones",
  "details": [
    {
      "loc": ["rate_limit"],
      "msg": "Rate limit exceeded: 5 per 1 hour",
      "type": "rate_limit_exceeded"
    }
  ]
}
```

La respuesta también incluye headers útiles:
- `X-RateLimit-Limit`: Límite máximo de requests
- `X-RateLimit-Remaining`: Requests restantes en la ventana actual
- `Retry-After`: Segundos hasta que puedas reintentar (opcional)

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