# 📖 Guía de Uso de la API - Lunance IA

Esta guía te mostrará cómo usar la API REST de Lunance IA v2, incluyendo autenticación, endpoints principales y ejemplos prácticos.

## 📋 Tabla de Contenidos

- [Autenticación JWT](#autenticación-jwt)
- [Autenticación con API Keys](#-autenticación-con-api-keys)
- [Idempotencia (`Idempotency-Key`)](#-idempotencia-idempotency-key)
- [Endpoints Principales](#endpoints-principales)
- [Apartados de Inversión](#-apartados-de-inversión---apiv2positions)
- [Valores (acciones, ETFs, FIBRAs)](#-valores-acciones-etfs-fibras---apiv2securities)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Manejo de Errores](#manejo-de-errores)
- [Códigos de Estado](#códigos-de-estado)
- [Límites y Paginación](#límites-y-paginación)
- [IA - Análisis y Asesoría](#-ia---apiv2ai)

## 🔐 Autenticación JWT

La API gestiona la autenticación **por sí misma**, con correo y contraseña o con Google y Apple, y abre **una sesión por dispositivo**: puedes tener la web, el iPhone y la tablet abiertos a la vez y cerrar cualquiera desde otro.

### Cabeceras del dispositivo

| Cabecera | Valor | Dónde |
|---|---|---|
| `X-Lunance-Device` | UUID que el cliente genera **una sola vez** y guarda | Obligatoria en `/login`, `/google`, `/apple` y `/refresh` (`422` si falta o no es UUID) |
| `X-Lunance-Client` | `<plataforma>/<versión>`: `web/…`, `ios/…` o `android/…` | Opcional; sin ella se trata como `web` |

Volver a iniciar sesión desde el mismo dispositivo sustituye solo la sesión de ese dispositivo.

### Flujo de Autenticación

1. **Registro**: `POST /api/v2/auth/register` con correo, username y contraseña → `202`; llega un correo con un enlace de verificación
2. **Confirmar el correo**: la web abre el enlace y llama a `POST /api/v2/auth/email/verify` con el token → se crea la cuenta
3. **Login**: `POST /api/v2/auth/login` con **correo** y contraseña devuelve un *access token* y abre la sesión del dispositivo
4. **API Requests**: incluir el access token en el header `Authorization`
5. **Renovación**: `POST /api/v2/auth/refresh` cuando el access token caduca
6. **Cierre de sesión**: `POST /api/v2/auth/logout` (esta sesión o `all_devices`)
7. **Sesiones**: `GET /api/v2/auth/sessions` y `DELETE /api/v2/auth/sessions/{uuid}`
8. **Contraseña**: `POST /api/v2/auth/password/forgot` + `/password/reset` (con el enlace del correo) o `/password/change` (con sesión iniciada)
9. **Google y Apple**: `POST /api/v2/auth/google` o `/apple` con el ID token del proveedor (alta o login en un paso); vincular y desvincular desde ajustes con `/auth/providers/…`

### Características de los tokens

| | Access token | Refresh token |
|---|---|---|
| Formato | JWT EdDSA (Ed25519) | Opaco: `rt_` + 256 bits aleatorios |
| Vigencia | 10 min (`ACCESS_TOKEN_EXPIRE_MINUTES`) | La de la sesión: web 1 día sin uso / 7 días máximo; ios/android 30 / 90 días |
| Se envía en | Header `Authorization: Bearer` | Web: cookie `httpOnly` (`path=/api/v2/auth`). ios/android: body de `/refresh` y `/logout` |
| Almacenado en servidor | No | Sí, **solo su hash SHA-256** |

El access token lleva `iss`, `aud`, `sub` (UUID del usuario), `sid` (UUID de la sesión), `iat` y `exp`. El refresh token **rota en cada uso**. Si la respuesta de un `/refresh` se pierde, repetirlo con el mismo token durante unos segundos (`REFRESH_REUSE_GRACE_SECONDS`) devuelve el mismo token nuevo; reutilizar un refresh ya canjeado fuera de ese margen se trata como robo y **cierra la sesión entera** de ese dispositivo.

Cerrar una sesión (logout, `DELETE /auth/sessions/{uuid}` o reuso detectado) invalida su access token **al instante**, aunque no haya caducado: la siguiente petición responde `401 AUTH_SESSION_EXPIRED`.

### Guía para integrar un cliente (web y móvil)

1. **Identificador del dispositivo**: genera un UUID v4 la primera vez que se abre la app y guárdalo para siempre (web: `localStorage`; iOS: Keychain; Android: almacenamiento cifrado). Mándalo en `X-Lunance-Device` en `/login`, `/google`, `/apple` y `/refresh`. Si cambia, el servidor lo trata como otro dispositivo.
2. **`X-Lunance-Client`**: mándalo en **todas** las peticiones a `/auth/*` (`web/1.0.0`, `ios/1.4.0`, `android/1.4.0`). Decide dónde viaja el refresh token y qué duración tiene la sesión.
3. **Dónde guardar los tokens**:
   - Access token (10 min): en memoria. No hace falta persistirlo.
   - Refresh token: **web** → no lo toques, va en la cookie `httpOnly`; las peticiones a `/auth/refresh` y `/auth/logout` deben enviarse con credenciales (`fetch(..., {credentials: "include"})` o `withCredentials: true` en axios). **Móvil** → guárdalo en Keychain / almacenamiento cifrado y reemplázalo por el nuevo en cada `/refresh`.
4. **Al recibir un `401`**:
   - `JWT_VALIDATION_ERROR` (access token vencido o inválido) → llama a `/auth/refresh` **una sola vez** y repite la petición. Si varias peticiones fallan a la vez, comparte una misma llamada a `/refresh`: cada refresh token rota en cada uso y, pasado el margen de gracia de unos segundos, reusar uno ya canjeado cierra la sesión.
   - `AUTH_SESSION_EXPIRED` (sesión cerrada, vencida o revocada desde otro dispositivo) → borra los tokens y manda al usuario al login. No reintentes.
5. **`429` y `503`**: respeta el header `Retry-After` (segundos) antes de reintentar. `503` en login/registro significa que el servidor no puede comprobar los límites en ese momento.
6. **Rutas de la web que abren los correos**: `/verify-email?token=…`, `/reset-password?token=…` y `/verify-email/resend` (pantalla para pedir otro enlace). La web lee el `token` de la URL y llama al endpoint correspondiente.
7. **Escrituras**: los `POST` que crean recursos exigen `Idempotency-Key` (ver [Idempotencia](#-idempotencia-idempotency-key)); en la web, el header `Idempotent-Replayed` está expuesto por CORS para saber si una respuesta es la repetición de un reintento.

### Registro

```bash
curl -X POST "http://localhost:8000/api/v2/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "juan@example.com",
       "username": "juanperez",
       "password": "MiClave123!"
     }'
```

**Respuesta:** `202 Accepted`
```json
{
  "message": "Si el correo es válido, te enviamos un enlace para confirmar tu cuenta. Revisa tu bandeja de entrada y la carpeta de spam."
}
```

La cuenta **todavía no existe**: el registro queda pendiente (`pending_signups`, 7 días) y al correo llega un enlace `<EMAIL_LINK_BASE_URL>/verify-email?token=…` que vale 24 horas. El correo se guarda normalizado (sin espacios y en minúsculas) y el username debe ser único.

- **Anti-enumeración**: la respuesta es la misma tenga o no cuenta el correo. Si ya la tiene, no se guarda nada y al buzón le llega un aviso ("ya tienes una cuenta") en lugar del enlace.
- **Volver a registrarse** con un correo pendiente sustituye el registro (username y contraseña nuevos) e invalida los enlaces anteriores.
- **Username ocupado** (por una cuenta o por otro registro pendiente): `409 BUSINESS_USERNAME_EXISTS`. Es el único caso distinto, y no depende del correo.
- **Límites**: 5 registros por hora por IP y 5 correos de registro/reenvío por hora por buzón (`429`). Si Redis no responde: `503`.

> **Requisitos de la contraseña**: mínimo 8 caracteres (máximo 256), con al menos una mayúscula, una minúscula, un dígito y un carácter especial (`!@#$%^&*(),.?":{}|<>`). Solo se guarda su hash Argon2id. Si no los cumple, la API responde `400 VALIDATION_ERROR` y el detalle incluye códigos como `PASSWORD_TOO_SHORT` o `PASSWORD_MISSING_UPPERCASE`.

### Confirmar el correo

La web (ruta `/verify-email`) lee el `token` de la URL y lo manda:

```bash
curl -X POST "http://localhost:8000/api/v2/auth/email/verify" \
     -H "Content-Type: application/json" \
     -d '{"token": "<token del enlace>"}'
```

**Respuesta:** `200 OK`
```json
{
  "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "username": "juanperez",
  "email": "juan@example.com",
  "message": "Correo confirmado. Ya puedes iniciar sesión."
}
```

Crea la cuenta ya verificada; **no abre sesión** (después se hace login). Cada enlace sirve una vez: repetido, caducado o inventado → `400 AUTH_INVALID_TOKEN`. Si alguien tomó el username mientras tanto → `409 BUSINESS_USERNAME_EXISTS` (hay que volver a registrarse).

**Reenviar el enlace** ("no me llegó el correo"): `POST /api/v2/auth/email/verify/resend` con `{"email": "…"}` → siempre `202` con el mismo mensaje. Solo se manda algo si hay un registro pendiente; los enlaces anteriores siguen valiendo hasta caducar.

### Login

```bash
# App de iOS/Android: el refresh token llega en el body
curl -X POST "http://localhost:8000/api/v2/auth/login" \
     -H "Content-Type: application/json" \
     -H "X-Lunance-Device: 0b5f3c55-7f4e-4f0e-9a43-0d6c2d0d6b8e" \
     -H "X-Lunance-Client: ios/1.4.0" \
     -d '{
       "email": "juan@example.com",
       "password": "MiClave123!",
       "device_name": "iPhone de Juan"
     }'
```

**Respuesta (ios/android):**
```json
{
  "access_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 600,
  "refresh_token": "rt_Fo6BU0DC9Inbnp5l_4Lg0NQ0QebQJY_8PXrIQT-NYuc"
}
```

En la web (sin `X-Lunance-Client` o con `web/…`) la respuesta no trae `refresh_token`: llega en la cookie `refresh_token` (`HttpOnly`, `Path=/api/v2/auth`). `device_name` es opcional. El login es **por correo** (mayúsculas y espacios dan igual); el username ya no sirve para entrar.

| Caso | Respuesta |
|---|---|
| Correo inexistente o contraseña incorrecta | `401 AUTH_INVALID_CREDENTIALS` (misma respuesta y mismo coste) |
| Contraseña correcta de un registro sin confirmar | `403 AUTH_EMAIL_NOT_VERIFIED` (solo lo ve quien conoce esa contraseña) |
| Cuenta desactivada (tras validar la contraseña) | `401 AUTH_USER_INACTIVE` |
| Bloqueo por intentos fallidos | `429 AUTH_TOO_MANY_ATTEMPTS` con `Retry-After` |
| Redis no responde | `503 SERVICE_UNAVAILABLE` con `Retry-After: 5` |

**Bloqueo por intentos fallidos** (en Redis, la clave es un hash del correo):
- **Correo + IP**: tras 5 fallos seguidos, 1 minuto; cada fallo más lo duplica hasta 15 minutos. Frena a quien prueba desde una IP sin dejar fuera al dueño, que entra desde otra.
- **Correo** (desde cualquier IP): 30 fallos en una hora bloquean 15 minutos. Un dispositivo (`X-Lunance-Device`) que ya tuvo sesión en la cuenta se lo salta.
- Un login correcto reinicia los contadores; restablecer la contraseña quita el bloqueo del correo.
- Aparte sigue el rate limit de 10 intentos por minuto por IP.

### Recuperar la contraseña

```bash
# 1. Pedir el enlace (siempre 204, exista o no la cuenta)
curl -X POST "http://localhost:8000/api/v2/auth/password/forgot" \
     -H "Content-Type: application/json" \
     -d '{"email": "juan@example.com"}'

# 2. La web (ruta /reset-password) manda el token del enlace y la contraseña nueva
curl -X POST "http://localhost:8000/api/v2/auth/password/reset" \
     -H "Content-Type: application/json" \
     -d '{"token": "<token del enlace>", "password": "OtraClave456!"}'
```

- `/password/forgot` responde **siempre `204`**, también al llegar al límite del buzón (3 por hora; entonces no se manda nada). Si el correo tiene un registro sin confirmar, le llegan instrucciones para confirmarlo en lugar del enlace.
- El enlace (`<EMAIL_LINK_BASE_URL>/reset-password?token=…`) vale 1 hora y **una sola vez**; usarlo invalida los demás enlaces pendientes. Repetido o caducado → `400 AUTH_INVALID_TOKEN`.
- `/password/reset` responde `204` y **cierra todas las sesiones** de la cuenta (motivo `password_reset`): sus access tokens dejan de valer al instante. Después se inicia sesión con la contraseña nueva. Al buzón le llega un aviso de que la contraseña cambió.

### Cambiar la contraseña (con sesión iniciada)

```bash
curl -X POST "http://localhost:8000/api/v2/auth/password/change" \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"current_password": "MiClave123!", "new_password": "OtraClave456!"}'
```

**Respuesta:** `204`. Cierra las **demás** sesiones (motivo `password_change`); la de este access token sigue abierta. También invalida los enlaces de recuperación pendientes. Contraseña actual incorrecta → `400 AUTH_INVALID_CURRENT_PASSWORD` (la sesión no se cierra); igual a la actual → `400 VALIDATION_ERROR` (`PASSWORD_SAME_AS_CURRENT`). Cuenta creada con Google o Apple que aún no tiene contraseña → `409 AUTH_PASSWORD_NOT_SET` (se crea con "Olvidé mi contraseña", que prueba que el correo es suyo). Solo con access token (no con API key); límite de 5 por minuto por usuario.

### Iniciar sesión con Google

La app (web, iOS o Android) obtiene el **ID token** con el SDK de Google y lo manda tal cual. Si no hay cuenta, se crea en el momento (correo ya verificado, sin contraseña, username generado del nombre).

```bash
curl -X POST "http://localhost:8000/api/v2/auth/google" \
     -H "Content-Type: application/json" \
     -H "X-Lunance-Device: 0b5f3c55-7f4e-4f0e-9a43-0d6c2d0d6b8e" \
     -H "X-Lunance-Client: android/1.4.0" \
     -d '{"id_token": "<id token de Google>", "nonce": "<nonce en claro, opcional>", "device_name": "Pixel de Ana"}'
```

**Respuesta** (misma sesión que `/login`: en la web el refresh va en la cookie `httpOnly`):
```json
{
  "access_token": "eyJhbGciOiJFZERTQSIs...",
  "token_type": "bearer",
  "expires_in": 600,
  "refresh_token": "rt_…",
  "account_created": true,
  "provider_linked": false
}
```

- `account_created: true` → cuenta nueva: buen momento para ofrecer cambiar el username (`PATCH /auth/me`).
- `provider_linked: true` → había una cuenta con ese correo y se vinculó (se avisa por correo).
- **Nonce** (opcional): si la app lo usa, al proveedor se le pasa el **SHA-256 en hex** del nonce y a la API el valor **en claro**. Si el token trae `nonce`, este campo es obligatorio.
- **Cada ID token sirve una vez**: repetirlo responde `401`. Para reintentar, pide otro al SDK.

**Cuenta existente con el mismo correo**: se vincula sola solo si es un buzón de Gmail/googlemail o del dominio de Google Workspace de la cuenta de Google. Con cualquier otro correo responde:

```json
{
  "error": true,
  "error_code": "AUTH_PROVIDER_LINK_REQUIRED",
  "message": "Ya hay una cuenta con ese correo. Inicia sesión con tu método actual y vincula esta cuenta desde ajustes",
  "details": [{"loc": ["account", "login_methods"], "msg": "Métodos con los que puedes iniciar sesión en esa cuenta", "type": "LOGIN_METHODS", "input": ["password"]}]
}
```

### Iniciar sesión con Apple (Sign in with Apple)

```bash
curl -X POST "http://localhost:8000/api/v2/auth/apple" \
     -H "Content-Type: application/json" \
     -H "X-Lunance-Device: 0b5f3c55-7f4e-4f0e-9a43-0d6c2d0d6b8e" \
     -H "X-Lunance-Client: ios/1.4.0" \
     -d '{
       "id_token": "<identityToken de Apple>",
       "authorization_code": "<authorizationCode de Apple>",
       "nonce": "<nonce en claro>",
       "name": "Ana Pérez"
     }'
```

- `authorization_code` (recomendado): la API lo canjea por el refresh token de Apple y lo guarda **cifrado**; sirve para revocar el acceso cuando se borre la cuenta (Apple lo exige). Caduca a los 5 minutos y es de un solo uso: mándalo en cuanto lo recibas.
- `name`: Apple **solo** lo entrega la primera vez que el usuario autoriza la app; mándalo entonces para generar el username.
- Con el correo oculto de Apple (`…@privaterelay.appleid.com`) la cuenta usa esa dirección. Una cuenta existente se vincula sola solo si su correo es de iCloud (`icloud.com`, `me.com`, `mac.com`) o ese mismo relay privado; si no, `409 AUTH_PROVIDER_LINK_REQUIRED`.
- Misma respuesta que `/auth/google`.

### Vincular y desvincular Google o Apple (ajustes)

```bash
# Vincular (con sesión iniciada y confirmando la identidad; el correo del proveedor puede ser otro)
curl -X POST "http://localhost:8000/api/v2/auth/providers/google" \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"id_token": "<id token de Google>", "current_password": "MiClave123!"}'

curl -X POST "http://localhost:8000/api/v2/auth/providers/apple" \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"id_token": "<identityToken>", "authorization_code": "<authorizationCode>", "nonce": "<nonce>", "current_password": "MiClave123!"}'

# Desvincular
curl -X DELETE "http://localhost:8000/api/v2/auth/providers/google" \
     -H "Authorization: Bearer <access_token>"
```

**Confirmar la identidad para vincular**: un access token robado bastaría para meter un Google ajeno y quedarse con la cuenta, así que vincular pide además una prueba de que quien tiene la sesión es el dueño:

| La cuenta… | Qué hay que mandar | Si falta |
|---|---|---|
| Tiene contraseña (`"password"` en `login_methods`) | `current_password` en el body | `403 AUTH_REAUTH_REQUIRED`; contraseña incorrecta → `400 AUTH_INVALID_CURRENT_PASSWORD` |
| No tiene contraseña (solo Google/Apple) | Nada: la sesión debe haberse iniciado hace **menos de 10 minutos** | `403 AUTH_REAUTH_REQUIRED`: volver a iniciar sesión con Google/Apple y reintentar |

La comprobación va **antes** de usar el ID token, así que tras un `403` se puede pedir la contraseña y reintentar con el mismo token. Desvincular no pide confirmación (no da acceso a nadie y nunca deja la cuenta sin forma de entrar).

**Respuesta:** `200` con `{"login_methods": ["password", "google"]}`. Errores: esa cuenta del proveedor ya está en otro usuario → `409 AUTH_PROVIDER_IN_USE`; tu cuenta ya tiene otra cuenta de ese proveedor → `409 AUTH_PROVIDER_CONFLICT`; desvincular el único método de acceso → `409 AUTH_LAST_LOGIN_METHOD`. Desvincular algo que no está vinculado no hace nada. Ambas cosas se avisan por correo. Límite de 5 por minuto por usuario.

### Cambiar el username

```bash
curl -X PATCH "http://localhost:8000/api/v2/auth/me" \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"username": "ana_perez"}'
```

**Respuesta:** la misma que `GET /auth/me`. Ocupado por otra cuenta o apartado por un registro pendiente → `409 BUSINESS_USERNAME_EXISTS`.

### Usar Token en Requests

Incluye el access token en el header `Authorization` de todos los requests autenticados:

```bash
curl -X GET "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer <access_token>"
```

### Renovar el Token

```bash
# ios/android: refresh token en el body
curl -X POST "http://localhost:8000/api/v2/auth/refresh" \
     -H "Content-Type: application/json" \
     -H "X-Lunance-Device: 0b5f3c55-7f4e-4f0e-9a43-0d6c2d0d6b8e" \
     -H "X-Lunance-Client: ios/1.4.0" \
     -d '{"refresh_token": "<refresh_token>"}'

# web: sin body, el navegador manda la cookie
curl -X POST "http://localhost:8000/api/v2/auth/refresh" \
     -H "X-Lunance-Device: <uuid del navegador>" \
     --cookie "refresh_token=<refresh_token>"
```

**Respuesta:** un access token nuevo y un refresh token nuevo (en el body o en la cookie, según la plataforma). Descarta el anterior. El refresh solo vale desde el mismo dispositivo y plataforma que abrió la sesión. Si la sesión venció o se cerró: `401 AUTH_SESSION_EXPIRED` (hay que volver a iniciar sesión).

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
  "email": "juan@example.com",
  "email_verified": true,
  "is_active": true,
  "login_methods": ["password", "google"]
}
```

### Cerrar Sesión

```bash
curl -X POST "http://localhost:8000/api/v2/auth/logout" \
     -H "Content-Type: application/json" \
     -H "X-Lunance-Client: ios/1.4.0" \
     -d '{
       "refresh_token": "<refresh_token>",
       "all_devices": false
     }'
```

Cierra la sesión de este dispositivo (en la web, la del refresh de la cookie, y la borra). Con `"all_devices": true` cierra también las de los demás dispositivos. Es idempotente: un refresh desconocido o ya cerrado responde igual. Los access tokens de las sesiones cerradas dejan de valer al instante.

### Sesiones abiertas

```bash
curl -X GET "http://localhost:8000/api/v2/auth/sessions" \
     -H "Authorization: Bearer <access_token>"
```

**Respuesta:**
```json
[
  {
    "uuid": "279484a1-d2f6-40bc-9749-2e7750524fb7",
    "platform": "ios",
    "device_name": "iPhone de Juan",
    "client": "ios/1.4.0",
    "created_at": "2026-11-10T06:43:55Z",
    "last_seen_at": "2026-11-10T08:10:02Z",
    "last_ip": "203.0.113.5",
    "is_current": false
  }
]
```

`is_current` marca la sesión del access token con el que se pide. Para cerrar una desde otro dispositivo:

```bash
curl -X DELETE "http://localhost:8000/api/v2/auth/sessions/279484a1-d2f6-40bc-9749-2e7750524fb7" \
     -H "Authorization: Bearer <access_token>"
```

**Respuesta:** `204 No Content`. Solo se pueden cerrar sesiones propias y abiertas; cualquier otra responde `404` con `NOT_FOUND_SESSION`.

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

## 🔁 Idempotencia (`Idempotency-Key`)

Si la app manda una petición y se corta la señal antes de recibir la respuesta, no sabe si el
movimiento se guardó. Para que el reintento sea seguro, cada escritura lleva un identificador
de operación en el header `Idempotency-Key`: la API ejecuta esa operación **una sola vez** y,
si la recibe de nuevo, devuelve la respuesta que ya dio en lugar de repetir el cambio.

```bash
curl -X POST "http://localhost:8000/api/v2/transaction/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Idempotency-Key: 3f0c8a52-2b7e-4d1a-9f3e-6c5b1a2d7e90" \
     -H "Content-Type: application/json" \
     -d '{"account_uuid": "550e8400-e29b-41d4-a716-446655440000", "transaction_type": "EXPENSE", "amount": 250.50}'
```

**Dónde se usa**

| Peticiones | Header |
|------------|--------|
| `POST` que crean recursos o mueven dinero: cuentas, transacciones, transferencias, compras a meses y pago de mensualidades (`/installments/{charge_uuid}/pay/`), ingresos recurrentes, suscripciones, apartados y sus movimientos (`deposit`, `withdraw`, `liquidate`), metas, presupuestos y API keys | **Obligatorio**. Si falta o no es un UUID → `422 VALIDATION_ERROR` (con `loc: ["header", "Idempotency-Key"]`) y no se ejecuta nada |
| `PUT`, `PATCH` y `DELETE` | Opcional. Si se manda, se aplica la misma protección (útil en los *toggles* `activate`/`status`, que al repetirse se revertirían) |
| `/auth/*`, `/ai/*` y lecturas (`GET`) | No aplica (se ignora) |

Aplica igual con JWT y con API key (las tools del MCP mandan una clave nueva en cada llamada).

**Reglas para el cliente**

1. Genera un **UUID nuevo por cada operación** que el usuario inicia (por ejemplo, al pulsar
   "Guardar"), y guárdalo junto con la petición pendiente.
2. Si no llega respuesta (timeout, sin conexión, la app se cerró), **reintenta con la misma
   clave y exactamente el mismo cuerpo**. Nunca reutilices una clave para otra operación.
3. Las claves son **por usuario**: dos usuarios pueden mandar el mismo UUID sin pisarse.
4. Se guardan **al menos 24 horas** (un job diario borra las más antiguas). Un reintento
   pasado ese plazo se trata como una operación nueva.

**Qué responde un reintento**

| Situación | Respuesta |
|-----------|-----------|
| Misma clave, mismo método, ruta y cuerpo, y la operación ya terminó | El mismo código y el mismo cuerpo JSON de la primera vez, con el header `Idempotent-Replayed: true`. No se repite nada. (El orden de las claves del JSON puede variar.) |
| Misma clave con otro cuerpo, método o ruta | `422 IDEMPOTENCY_KEY_REUSED`. Es un error del cliente: genera una clave nueva |
| La primera petición sigue en curso | El reintento espera a que termine y recibe su respuesta |
| La primera petición falló (cualquier error 4xx/5xx) | No queda rastro de la clave: el reintento vuelve a ejecutar la operación |
| La operación se aplicó pero su respuesta no llegó a guardarse (el servidor se cayó justo en medio) | `409 IDEMPOTENCY_KEY_IN_USE`. **El cambio sí se aplicó**: vuelve a consultar el recurso (por ejemplo, la lista de transacciones) en lugar de reintentar a ciegas |

> **API keys:** la respuesta guardada de `POST /api-keys/` no incluye la key en claro (el
> backend solo guarda su hash). Un reintento devuelve el mismo cuerpo con `"raw_key": null`;
> si la app nunca recibió la key, revócala con el `uuid` de esa respuesta y crea otra.

## 🌐 Endpoints Principales

> Los `POST` de esta sección que crean recursos o mueven dinero (todos salvo `/auth/*` y `/ai/*`) exigen el header `Idempotency-Key`; ver [Idempotencia](#-idempotencia-idempotency-key).

> **Montos.** Los montos llegan como string decimal con sus decimales (`"250.50"`,
> `"10.00000000"`), para no perder precisión; algunos ejemplos de abajo los muestran como
> número por brevedad. La excepción es el dashboard (`/dashboard/` y `/dashboard/mobile/`),
> que manda números (`200.0`). Al enviar se aceptan string o número. Cada monto está en la
> moneda de su cuenta: las respuestas de movimientos, transferencias, suscripciones, compras a
> meses, apartados y presupuestos traen `currency` (`MXN`, `USD` o `EUR`).

### 🔐 Autenticación - `/api/v2/auth/`

> **Nota**: la API gestiona el registro y el login por sí misma. Ver [Autenticación JWT](#-autenticación-jwt) para el detalle del flujo y de los tokens.

#### Registro
```bash
POST /api/v2/auth/register
```

**Request:**
```json
{
  "email": "juan@example.com",
  "username": "juanperez",
  "password": "MiClave123!"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `email` | string | ✅ | Correo válido (máx. 254); se guarda en minúsculas y es el identificador de login |
| `username` | string | ✅ | 1–100 caracteres, único |
| `password` | string | ✅ | 8–256 caracteres, con mayúscula, minúscula, dígito y carácter especial |

**Response:** `202 Accepted` con `{"message": "…"}`, exista o no el correo. La cuenta se crea al confirmar el correo. Username ocupado → `409 BUSINESS_USERNAME_EXISTS`.

#### Confirmar el correo
```bash
POST /api/v2/auth/email/verify
```

**Request:** `{"token": "<token del enlace>"}`

**Response:** `200` con `user_uuid`, `username`, `email` y `message`. Token repetido, caducado o desconocido → `400 AUTH_INVALID_TOKEN`.

#### Reenviar el enlace de verificación
```bash
POST /api/v2/auth/email/verify/resend
```

**Request:** `{"email": "juan@example.com"}` → siempre `202` con `{"message": "…"}`.

#### Olvidé mi contraseña
```bash
POST /api/v2/auth/password/forgot
```

**Request:** `{"email": "juan@example.com"}` → siempre `204`.

#### Restablecer la contraseña
```bash
POST /api/v2/auth/password/reset
```

**Request:** `{"token": "<token del enlace>", "password": "OtraClave456!"}` → `204`; cierra todas las sesiones. Token repetido o caducado → `400 AUTH_INVALID_TOKEN`.

#### Cambiar la contraseña
```bash
POST /api/v2/auth/password/change
Authorization: Bearer <access_token>
```

**Request:** `{"current_password": "MiClave123!", "new_password": "OtraClave456!"}` → `204`; cierra las demás sesiones y conserva esta. Contraseña actual incorrecta → `400 AUTH_INVALID_CURRENT_PASSWORD`.

#### Login
```bash
POST /api/v2/auth/login
X-Lunance-Device: <uuid del dispositivo>     # obligatorio
X-Lunance-Client: ios/1.4.0                  # opcional; sin él, web
```

**Request:**
```json
{
  "email": "juan@example.com",
  "password": "MiClave123!",
  "device_name": "iPhone de Juan"
}
```

**Response:** en ios/android incluye `refresh_token`; en la web llega en la cookie `httpOnly`.
```json
{
  "access_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 600,
  "refresh_token": "rt_Fo6BU0DC9Inbnp5l_4Lg0NQ0QebQJY_8PXrIQT-NYuc"
}
```

Errores: `401 AUTH_INVALID_CREDENTIALS`, `403 AUTH_EMAIL_NOT_VERIFIED`, `429 AUTH_TOO_MANY_ATTEMPTS` (con `Retry-After`), `503` si Redis no responde.

#### Renovar Token
```bash
POST /api/v2/auth/refresh
X-Lunance-Device: <uuid del dispositivo>     # obligatorio, el mismo del login
```

**Request (solo ios/android; la web no manda body, usa la cookie):**
```json
{
  "refresh_token": "<refresh_token>"
}
```

**Response:** como la del login. El refresh token anterior queda invalidado.

#### Obtener Información del Usuario
```bash
GET /api/v2/auth/me
```

**Response:**
```json
{
  "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "username": "juanperez",
  "email": "juan@example.com",
  "email_verified": true,
  "is_active": true,
  "login_methods": ["password", "google"]
}
```

#### Cerrar Sesión
```bash
POST /api/v2/auth/logout
```

**Request** (`refresh_token` solo en ios/android; en la web se toma de la cookie):
```json
{
  "refresh_token": "<refresh_token>",
  "all_devices": false
}
```

**Response:**
```json
{
  "message": "Logout exitoso"
}
```

#### Sesiones abiertas
```bash
GET /api/v2/auth/sessions                 # lista las sesiones activas, marca is_current
DELETE /api/v2/auth/sessions/{uuid}       # 204; 404 si no existe o es de otro usuario
```

#### Google y Apple
```bash
POST /api/v2/auth/google                  # {id_token, nonce?, device_name?} → tokens + account_created/provider_linked
POST /api/v2/auth/apple                   # {id_token, authorization_code?, nonce?, name?, device_name?}
POST /api/v2/auth/apple/notifications     # avisos servidor a servidor de Apple ({payload}); responde 200
POST /api/v2/auth/providers/google        # vincular desde ajustes: {id_token, nonce?, current_password?} → {login_methods}
POST /api/v2/auth/providers/apple         # vincular desde ajustes: {id_token, authorization_code?, nonce?, current_password?}
DELETE /api/v2/auth/providers/{provider}  # desvincular google|apple → {login_methods}
PATCH /api/v2/auth/me                     # {username} → cambiar el username
```

| Código | Estado | Cuándo |
|---|---|---|
| `AUTH_INVALID_PROVIDER_TOKEN` | 401 | Firma, emisor, audiencia, caducidad, nonce o correo sin verificar; token ya usado; código de Apple rechazado |
| `AUTH_PROVIDER_LINK_REQUIRED` | 409 | Hay una cuenta con ese correo y el buzón no permite vincular solo (`details[0].input`: métodos de esa cuenta) |
| `AUTH_REAUTH_REQUIRED` | 403 | Vincular sin `current_password` (cuenta con contraseña) o con una sesión de más de 10 minutos (cuenta sin contraseña) |
| `AUTH_PROVIDER_CONFLICT` | 409 | La cuenta ya tiene otra cuenta del mismo proveedor |
| `AUTH_PROVIDER_IN_USE` | 409 | Esa cuenta del proveedor está vinculada a otro usuario |
| `AUTH_LAST_LOGIN_METHOD` | 409 | Desvincular dejaría la cuenta sin forma de entrar |
| `AUTH_PASSWORD_NOT_SET` | 409 | Cambiar la contraseña de una cuenta que no tiene |
| `AUTH_PROVIDER_NOT_CONFIGURED` | 503 | El proveedor no tiene client IDs en el servidor |
| `AUTH_PROVIDER_UNAVAILABLE` | 503 | No se pudieron obtener las claves públicas del proveedor (`Retry-After`) |
| `SERVICE_UNAVAILABLE` | 503 | Redis no responde: no se puede comprobar que el token no se usó antes |

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

Requiere `Idempotency-Key` ([ver Idempotencia](#-idempotencia-idempotency-key)).

**Response:** `201 Created` — ⚠️ `raw_key` se devuelve **una sola vez**; el backend solo guarda su hash. Un reintento con la misma `Idempotency-Key` devuelve `"raw_key": null`.
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

`currency` acepta `MXN`, `USD` o `EUR`, sin importar mayúsculas (`"usd"` se guarda como `USD`), y no se puede cambiar después. Cualquier otra → `422 VALIDATION_ERROR` con `loc: ["body", "currency"]`.

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
    "amount": "250.50",
    "currency": "MXN",
    "transaction_date": "2024-12-14",
    "description": "Compra en supermercado",
    "notes": "Compra semanal",
    "creation_date": "2024-12-14T10:30:00Z",
    "account_name": "Cuenta Principal",
    "account_type": "CHECKING",
    "account_uuid": "660e8400-e29b-41d4-a716-446655440001",
    "security_trade_uuid": null,
    "security_holding_uuid": null
  }
]
```

`security_trade_uuid` y `security_holding_uuid` vienen llenos cuando el movimiento lo creó una
operación de acciones (una compra, venta o dividendo). Ese movimiento no se edita ni se borra
desde `/transaction/` (responde `409 SECURITY_TRADE_TRANSACTION_LOCKED`): se cambia la
operación en `/securities/trades/{security_trade_uuid}`, y su tenencia se consulta en
`/securities/holdings/{security_holding_uuid}`. El detalle por UUID trae los mismos campos.

#### Obtener Transacción por UUID
```bash
GET /api/v2/transaction/{transaction_uuid}/
```

#### Crear Transacción
```bash
POST /api/v2/transaction/
```

El movimiento está en la moneda de su cuenta (`currency` en la respuesta): no se manda moneda.

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

Con `account_uuid` el movimiento se pasa a otra cuenta, pero solo si es de la misma moneda;
si no → `409 ACCOUNT_CURRENCY_MISMATCH`.

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

#### ⚠️ Movimientos que no se editan ni se eliminan por aquí

Editar o eliminar una transacción suelta solo aplica a ingresos y gastos capturados
directamente. Hay dos casos que este endpoint rechaza a propósito, porque tocarlos por
separado descuadraría los saldos:

| Movimiento | `PUT` | `DELETE` | Camino correcto |
|-----------|-------|----------|-----------------|
| Cualquier `TRANSFER` | `400 INVALID_TRANSACTION_TYPE` | `400 INVALID_TRANSACTION_TYPE` | `DELETE /transfers/{transfer_uuid}/` y volver a crearla |
| Gasto inicial de una compra a meses | `409 INSTALLMENT_TRANSACTION_LOCKED` | `409 INSTALLMENT_TRANSACTION_LOCKED` | `PATCH` o `DELETE` sobre la compra en `/installments/` |

Una transferencia son **dos movimientos** con el mismo `transfer_uuid`; editar uno solo
dejaría la contraparte con otro monto. Por eso `PUT` la rechaza aunque antes la aceptara.

El gasto inicial de una compra a meses se reconoce en el listado porque su `description`
empieza con `"Compra a meses: "`. Si el usuario intenta borrarlo, lo que quiere en realidad
es cancelar la compra completa.

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

Incluye `net_worth`, el patrimonio en pesos con la misma forma que
[`GET /securities/portfolio/`](#patrimonio). También lo trae `GET /api/v2/dashboard/mobile/`.

**Por moneda.** Los montos de monedas distintas nunca se suman:

- Los campos de siempre (`total_spent`, `total_income`, `total_purchases`, `top_category`,
  `top_account`, `today_transactions`, `category_distribution`) son **solo de MXN**.
- `by_currency` trae los mismos campos para cada moneda con movimientos en el mes (en orden
  MXN, USD, EUR). Una moneda sin movimientos no aparece.
- Cada elemento de `today_transactions` trae `currency`.

```json
{
  "total_spent": 200.0,
  "total_income": 0.0,
  "…": "…",
  "by_currency": [
    { "currency": "MXN", "total_spent": 200.0, "total_income": 0.0, "total_purchases": 1, "…": "…" },
    { "currency": "USD", "total_spent": 80.0, "total_income": 100.0, "total_purchases": 2,
      "top_category": "Alimentos", "top_account": "GBM USD",
      "today_transactions": [{ "date": "2026-11-15", "amount": 50.0, "currency": "USD", "…": "…" }],
      "category_distribution": [{ "category": "Alimentos", "count": 2, "percent_by_count": 100.0 }] }
  ]
}
```

`GET /api/v2/dashboard/mobile/` sigue la misma regla: `total_spent`, `top_category`,
`category_distribution` y `monthly_budget` son de MXN, y `by_currency` trae cada moneda con su
propio `monthly_budget`, que solo suma los presupuestos de esa moneda.

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
    "amount": "299.00",
    "currency": "MXN",
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
| `currency` | ❌ | La del apartado es la de su cuenta. Si se manda, debe coincidir; si no → `409 ACCOUNT_CURRENCY_MISMATCH` |
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

### 📉 Valores (acciones, ETFs, FIBRAs) - `/api/v2/securities/`

Catálogo de valores que cotizan en bolsa y sus precios de cierre. No es tiempo real: los
precios son el cierre de cada día hábil y se actualizan a la 01:00 y a las 13:00 UTC.

| Mercado | Qué incluye | Moneda |
|---------|-------------|--------|
| `BMV` | Acciones, FIBRAs y ETFs de la BMV y la BIVA | MXN |
| `SIC` | Valores extranjeros listados en México (Sistema Internacional de Cotizaciones) | MXN |
| `US` | Acciones y ETFs de EE. UU. comprados directamente | USD |

Los símbolos de BMV y SIC llevan la serie como la publica la BMV: `WALMEX*`, `FUNO11`,
`AAPL*`. Los de EE. UU. son el ticker: `AAPL`.

Scope con API key: `investments:read`.

#### Buscar valores
```bash
GET /api/v2/securities/search?q=walmex&market=BMV&limit=20
```

- `q` (obligatorio): símbolo o nombre. Primero aparece el símbolo exacto (`walmex`
  encuentra `WALMEX*`), luego los que empiezan igual y luego las coincidencias por nombre;
  los activos antes que los suspendidos.
- `market` (opcional): `BMV`, `SIC` o `US`. Sin él, busca en los tres.
- BMV y SIC tienen el catálogo completo. Para EE. UU., un símbolo que no esté se consulta al
  proveedor y se agrega al catálogo. Si el proveedor no responde, se devuelve lo que ya
  hay.

**Response:**
```json
[
  {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "market": "BMV",
    "symbol": "WALMEX*",
    "name": "WAL - MART DE MEXICO, S.A.B. DE C.V.",
    "instrument_type": "STOCK",
    "currency": "MXN",
    "exchange": "BMV",
    "isin": "MX01WA000038",
    "is_active": true
  }
]
```

`instrument_type`: `STOCK`, `ETF`, `FIBRA` u `OTHER` (CKDs, certificados, etc.).

> En las FIBRAs, el nombre es el del fiduciario (por ejemplo, `FUNO11` aparece como
> «BANCO ACTINVER…»): búscalas por símbolo.

#### Precios de cierre de un valor
```bash
GET /api/v2/securities/instruments/{instrument_uuid}/prices?from=2026-11-01&to=2026-11-13
```

Cierres guardados, sin ajustar por splits ni dividendos, en la moneda del valor. Sin `from`
y `to`, los últimos 30 días; el rango máximo es de 3,660 días. Solo hay precios de los
valores que alguien sigue.

**Response:**
```json
{
  "instrument": { "uuid": "…", "market": "BMV", "symbol": "WALMEX*", "…": "…" },
  "prices": [
    {
      "price_date": "2026-11-02",
      "close": "50.390000",
      "is_trading_day": false,
      "provider": "databursatil"
    }
  ]
}
```

`is_trading_day: false` marca los feriados de la bolsa, en los que el proveedor repite el
cierre anterior.

#### Registrar una operación
```bash
POST /api/v2/securities/trades/
Idempotency-Key: <uuid>
```

Scope con API key: `investments:write`. La `Idempotency-Key` es obligatoria.

| `trade_type` | Campos | Dinero |
|--------------|--------|--------|
| `BUY` | `quantity`, `price`, `fees` | Sale del disponible `quantity × price + fees` (transacción `TRANSFER`) |
| `SELL` | `quantity`, `price`, `fees`, `tax_withheld` | Entra `quantity × price − fees − tax_withheld` (`TRANSFER`) |
| `DIVIDEND` | `gross_amount`, `tax_withheld` | Entra el neto como ingreso en «Inversiones» (`INCOME`) |
| `SPLIT` | `split_from`, `split_to` | No mueve dinero; multiplica los títulos por `split_to / split_from` |

```json
{
  "account_uuid": "…",
  "instrument_uuid": "…",
  "trade_type": "BUY",
  "trade_date": "2026-11-03",
  "quantity": "10",
  "price": "54.79",
  "fees": "11.60",
  "notes": "Primera compra"
}
```

- La cuenta debe estar en la moneda del valor (BMV y SIC en MXN, EE. UU. en USD) y no puede
  ser tarjeta de crédito.
- La fecha no puede ser futura. Una operación con fecha pasada se acomoda en su lugar y la
  tenencia se recalcula desde el principio.
- Costo promedio: la comisión de compra entra al costo; una venta realiza
  `cantidad × precio − comisión − cantidad × costo promedio` (antes de impuestos).
- La primera operación de un valor descarga su historia de precios en segundo plano.

**Response (201):**
```json
{
  "trade": {
    "uuid": "…",
    "account_uuid": "…",
    "instrument": { "symbol": "WALMEX*", "market": "BMV", "…": "…" },
    "trade_type": "BUY",
    "trade_date": "2026-11-03",
    "quantity": "10.00000000",
    "price": "54.790000",
    "fees": "11.60",
    "tax_withheld": "0.00",
    "gross_amount": null,
    "cash_amount": "559.50",
    "split_from": null,
    "split_to": null,
    "notes": "Primera compra",
    "created_at": "2026-11-14T19:00:00Z"
  },
  "holding": {
    "uuid": "…",
    "quantity": "10.00000000",
    "avg_cost": "55.950000",
    "cost_basis": "559.50",
    "realized_pnl": "0.00",
    "dividends": "0.00",
    "status": "OPEN",
    "…": "…"
  },
  "account_available_balance": "9440.50"
}
```

#### Editar o borrar una operación
```bash
PUT /api/v2/securities/trades/{trade_uuid}
DELETE /api/v2/securities/trades/{trade_uuid}
```

`PUT` reemplaza todos los datos (mismo cuerpo que el POST sin `account_uuid`,
`instrument_uuid` ni `trade_type`: para cambiarlos, borra y registra otra). El disponible se
ajusta solo por la diferencia y la transacción se rehace con los datos nuevos. `DELETE`
revierte el movimiento de dinero; responde como el POST, con `trade: null`, y `holding: null`
si el valor ya no tiene operaciones en la cuenta.

Se rechazan con `409 INSUFFICIENT_SHARES` si dejan alguna venta o split posterior sin
títulos (por ejemplo, borrar la compra detrás de una venta).

> La transacción de una operación no se edita ni se borra desde `/transaction/`: responde
> `409 SECURITY_TRADE_TRANSACTION_LOCKED`. En `GET /transaction/` se reconoce porque trae
> `security_trade_uuid` y `security_holding_uuid`.

#### Listar operaciones
```bash
GET /api/v2/securities/trades/?account_uuid=…&instrument_uuid=…&limit=100&offset=0
```

Las más recientes primero.

#### Tenencias
```bash
GET /api/v2/securities/holdings/?account_uuid=…&include_closed=false
GET /api/v2/securities/holdings/{holding_uuid}
```

Cantidad, costo y ganancia de cada valor, valuados con el último cierre guardado. El detalle
agrega todas sus operaciones.

```json
{
  "uuid": "…",
  "account_uuid": "…",
  "account_name": "GBM",
  "instrument": { "symbol": "AAPL", "market": "US", "currency": "USD", "…": "…" },
  "quantity": "2.00000000",
  "avg_cost": "200.000000",
  "cost_basis": "400.00",
  "realized_pnl": "0.00",
  "dividends": "0.00",
  "status": "OPEN",
  "opened_at": "2026-11-03",
  "closed_at": null,
  "last_price": "210.000000",
  "last_price_date": "2026-11-13",
  "market_value": "420.00",
  "unrealized_pnl": "20.00",
  "unrealized_pnl_pct": "5.00",
  "fx_rate": "18.55250000",
  "market_value_mxn": "7792.05"
}
```

- Los campos de valuación llegan en `null` mientras no haya precios del valor.
- `fx_rate` y `market_value_mxn`: FIX de Banxico del último día publicado (solo para valores
  que no son en pesos; en pesos, `market_value_mxn` es igual a `market_value`).
- Una tenencia se cierra (`CLOSED`) al vender todos los títulos; `include_closed=true` las
  incluye.

#### Historia diaria de una tenencia
```bash
GET /api/v2/securities/holdings/{holding_uuid}/history?from=2026-01-01&to=2026-12-31
```

Una foto por día de calendario desde la primera operación: hasta hoy, o hasta la última
operación si la tenencia se cerró. Sin `from` y `to`, los últimos 365 días; el rango máximo es
de 3,660 días.

```json
{
  "holding": { "uuid": "…", "instrument": { "symbol": "WALMEX*", "…": "…" }, "…": "…" },
  "snapshots": [
    {
      "snapshot_date": "2026-11-15",
      "quantity": "100.00000000",
      "close": "54.790000",
      "price_date": "2026-11-13",
      "market_value": "5479.00",
      "fx_rate": null,
      "market_value_mxn": "5479.00",
      "cost_basis": "5806.73",
      "unrealized_pnl": "-327.73",
      "realized_pnl": "0.00",
      "dividends": "0.00"
    }
  ]
}
```

- Los fines de semana, feriados o días sin precio usan el último cierre conocido:
  `price_date` dice de qué día es. Antes del primer cierre, la valuación llega en `null`.
- `market_value_mxn` usa el FIX de Banxico del día (o el último publicado). En un valor en
  dólares recién registrado llega en `null` hasta la siguiente corrida del job de precios,
  que descarga el tipo de cambio.
- Las fotos se rehacen solas cuando cambia algo que las afecta: una operación (desde su
  fecha), un cierre corregido por el proveedor o el tipo de cambio. Después de registrar o
  editar una operación se actualizan en segundo plano en unos segundos.

#### Patrimonio
```bash
GET /api/v2/securities/portfolio/
```

Todo lo del usuario en pesos al día de hoy:

```json
{
  "as_of": "2026-11-15",
  "cash": "21400.00",
  "credit_cards": "-1200.00",
  "positions": "1952.00",
  "securities": "550.00",
  "invested": "2502.00",
  "net_worth": "22702.00",
  "fx_rates": { "USD": "18.55250000" },
  "missing": []
}
```

- `cash`: disponible de las cuentas que no son tarjeta de crédito. El dinero en apartados
  no está aquí: está en `positions`.
- `credit_cards`: saldo de las tarjetas de crédito, negativo cuando hay deuda.
- `positions`: apartados de inversión no liquidados (capital más rendimiento acumulado).
- `securities`: tenencias abiertas al último cierre guardado.
- `invested` = `positions` + `securities`; `net_worth` = `cash` + `credit_cards` + `invested`.
- Lo que no está en pesos se convierte con el último tipo de cambio de Banxico (`fx_rates`):
  el FIX para USD y la cotización del euro (serie SF46410) para EUR. El job de precios los
  baja para toda moneda que tenga una cuenta, un apartado o un valor. Lo que no
  tiene precio o tipo de cambio no se suma y queda en `missing`, por ejemplo
  `"AAPL: sin precio guardado"` o `"Cuenta: sin tipo de cambio EUR/MXN"`.

#### Historia de lo invertido
```bash
GET /api/v2/securities/portfolio/history?from=2026-01-01&to=2026-12-31
```

Un punto por día de calendario con lo invertido en pesos: apartados más acciones. No
incluye el disponible de las cuentas, porque no hay histórico de saldos. Sin `from` y `to`,
los últimos 365 días; el rango máximo es de 3,660 días. Los días anteriores a la primera
inversión no se devuelven.

```json
{
  "start": "2026-01-01",
  "end": "2026-12-31",
  "days": [
    {
      "date": "2026-11-12",
      "positions": "1952.00",
      "securities": "550.00",
      "total": "2502.00",
      "complete": true
    }
  ]
}
```

- `positions`: el `cumulative_balance` del último rendimiento de cada apartado (los
  rendimientos se generan a diario a las 12:00 UTC). Un apartado liquidado deja de contar
  después de su último rendimiento; uno con tasa 0 no genera rendimientos y no aparece.
- `securities`: la suma de `market_value_mxn` de las fotos diarias de las tenencias.
- `complete: false` quiere decir que el día está incompleto: una tenencia sin cierre o sin
  tipo de cambio ese día, fotos que el job todavía no genera (por ejemplo, hoy antes de la
  corrida) o que se van a rehacer por una operación editada, o un apartado en otra moneda
  sin tipo de cambio. El total de ese día no incluye lo que falta.


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

**Response:** lista con `uuid`, `name`, `category_id`, `category_name`, `limit_amount`, `currency`, `period`, `start_date`, `end_date`, `is_active`, `alert_percentage` y `creation_date`.

#### Obtener Presupuesto por UUID
```bash
GET /api/v2/budgets/{budget_uuid}/
```

#### Progreso de un Presupuesto
```bash
GET /api/v2/budgets/{budget_uuid}/progress/
```

Progreso del presupuesto en el periodo actual.

**Response:** `uuid`, `name`, `category_id`, `category_name`, `limit_amount`, `currency`, `spent_amount`, `remaining_amount`, `percentage_used`, `alert_percentage`, `is_alert_triggered`, `is_limit_exceeded`, `period`, `period_start`, `period_end` e `is_active`.

#### Crear Presupuesto
```bash
POST /api/v2/budgets/
```

**Request:**
```json
{
  "name": "Comida mensual",
  "limit_amount": 5000.00,
  "currency": "MXN",
  "period": "mensual",
  "category_id": 1,
  "end_date": null,
  "alert_percentage": 80
}
```

`category_id` es opcional (si se omite, aplica a todas las categorías), igual que `start_date`, `end_date` y `alert_percentage` (default 80, rango 1-100). Las fechas de vigencia se reservan para presupuestos temporales y aún no afectan el cálculo de progreso. Periodos disponibles: `semanal`, `quincenal`, `mensual`, `trimestral`, `anual`.

`currency` (`MXN`, `USD` o `EUR`, default `MXN`) es la moneda del límite: el presupuesto solo
cuenta los gastos de cuentas en esa moneda. Otra moneda → `422 VALIDATION_ERROR`.

**Response:** `201 Created`

#### Actualizar Presupuesto
```bash
PATCH /api/v2/budgets/{budget_uuid}/
```

**Request:** todos los campos son opcionales (`name`, `limit_amount`, `currency`, `period`, `start_date`, `end_date`, `alert_percentage`, `category_id`).

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

#### Cómo se contabiliza una compra a meses

Una compra a meses genera movimientos reales en el historial, no solo un registro aparte:

```
Crear compra de 24,000 a 12 meses
  └─ EXPENSE de 24,000 en la TDC        ← el gasto ocurre una sola vez, el día de la compra

Pagar la cuota 1 (2,000)
  └─ TRANSFER de 2,000: cuenta de ahorro ──▶ TDC
       · sale del disponible de la cuenta origen
       · libera 2,000 de crédito en la TDC
```

Dos consecuencias que conviene tener claras:

- **El gasto se registra completo el día de la compra**, no repartido mes con mes. Los
  reportes por categoría y los presupuestos ven los 24,000 en el mes de la compra, que es
  como funciona una tarjeta de crédito en la vida real.
- **Pagar una cuota no es un ingreso.** Es un movimiento entre cuentas propias, así que no
  infla los ingresos del mes. (Antes sí lo hacía: los pagos se registraban como `INCOME`.)

#### Listar Compras a Plazos
```bash
GET /api/v2/installments/
```

**Response:** lista de compras con `uuid`, `account_uuid`, `category_id`, `description`, `total_amount`, `currency`, `num_installments`, `installment_type` (`NO_INTEREST` o `WITH_INTEREST`), `annual_interest_rate`, `monthly_payment`, `purchase_date`, `notes`, `is_active`, `creation_date` y `charges` (cada cargo con `uuid`, `installment_number`, `amount`, `due_date`, `paid` y `paid_at`).

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

`account_uuid` **debe ser una tarjeta de crédito** (`400 VALIDATION_ERROR` si no lo es).

Además de la compra y sus cargos, la llamada crea un `EXPENSE` por `total_amount` en esa
tarjeta, con la `category_id` y las `notes` que mandaste y descripción
`"Compra a meses: {description}"`. Ese movimiento queda enlazado a la compra y **no se
puede editar ni eliminar por separado** desde `/api/v2/transaction/`; devuelve
`409 INSTALLMENT_TRANSACTION_LOCKED`.

#### Pagar un Cargo
```bash
POST /api/v2/installments/{charge_uuid}/pay/
```

**Request:**
```json
{
  "source_account_uuid": "550e8400-e29b-41d4-a716-446655440001",
  "payment_date": "2026-08-15"
}
```

`source_account_uuid` identifica la cuenta de ahorro, débito o efectivo desde la
que sale el dinero. El pago crea una transferencia entre esa cuenta y la tarjeta
de crédito; no se contabiliza como ingreso.

Los dos movimientos que se generan comparten `transfer_uuid` y llevan descripción
`"Pago de cuota {compra} (3/12) a {tarjeta}"` y `"... desde {cuenta origen}"`.

**Errores posibles:**

| Código | HTTP | Cuándo |
|--------|------|--------|
| `NOT_FOUND` | 404 | El cargo no existe o no es del usuario |
| `NOT_FOUND_ACCOUNT` | 404 | `source_account_uuid` no existe o no es del usuario |
| `INSTALLMENT_CHARGE_ALREADY_PAID` | 409 | Ese cargo ya se pagó |
| `SAME_ACCOUNT_TRANSFER` | 409 | La cuenta origen es la misma tarjeta de la compra |
| `TRANSFER_ACCOUNT_TYPE_NOT_ALLOWED` | 409 | Se intentó pagar desde otra tarjeta de crédito |
| `TRANSFER_CURRENCY_MISMATCH` | 409 | La cuenta origen no está en la moneda de la tarjeta |
| `INSUFFICIENT_FUNDS` | 422 | La cuenta origen no tiene saldo disponible suficiente |

**Response:** el cargo actualizado (`uuid`, `installment_number`, `amount`, `due_date`, `paid`, `paid_at`).

Cuando se paga el último cargo, la compra pasa a `is_active: false` sola.

#### Actualizar Compra a Plazos
```bash
PATCH /api/v2/installments/{purchase_uuid}/
```

**Request:** todos los campos son opcionales (`description`, `notes`, `category_id`).

> Cambia únicamente el registro de la compra. **El gasto inicial en la tarjeta conserva su
> descripción y su categoría originales**, así que después de un `PATCH` los dos pueden no
> coincidir en el historial de movimientos.

#### Eliminar Compra a Plazos
```bash
DELETE /api/v2/installments/{purchase_uuid}/
```

Revierte toda la contabilidad de la compra en una sola operación:

- Borra el `EXPENSE` inicial y devuelve su monto al crédito disponible de la tarjeta.
- Borra las **dos patas** de la transferencia de cada cuota ya pagada, regresando el dinero
  a la cuenta origen y quitándole a la tarjeta el crédito que ese pago había liberado.
- Borra los cargos y la compra.

Los saldos de todas las cuentas involucradas cambian, no solo el de la tarjeta: conviene
refrescar la lista de cuentas después de eliminar, no únicamente la TDC.

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

La cuenta origen no puede ser una tarjeta de crédito (`409 TRANSFER_ACCOUNT_TYPE_NOT_ALLOWED`)
ni la misma que el destino (`409 SAME_ACCOUNT_TRANSFER`), y necesita saldo disponible
suficiente (`422 INSUFFICIENT_FUNDS`). Las dos cuentas deben estar en la misma moneda; entre
monedas distintas → `409 TRANSFER_CURRENCY_MISMATCH`.

**Response:** `201 Created` con `transfer_uuid`, `amount`, `currency`, `transfer_date`, `description`, `source_account_name`, `source_account_uuid`, `destination_account_name`, `destination_account_uuid` y `creation_date`.

#### Eliminar Transferencia
```bash
DELETE /api/v2/transfers/{transfer_uuid}/
```

Borra los dos movimientos y revierte ambos saldos.

> **No se pueden borrar las transferencias generadas por el pago de una cuota.** Devuelven
> `409 TRANSFER_NOT_ALLOWED`: esa transferencia es la que marca el cargo como pagado, y
> borrarla dejaría la cuota en un estado inconsistente. Para deshacerla hay que eliminar la
> compra a meses completa.

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
# 1. Registrar el usuario (202: llega un correo con el enlace de verificación;
#    en local, en Mailpit: http://localhost:8025)
curl -X POST "http://localhost:8000/api/v2/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "juan@example.com",
       "username": "juanperez",
       "password": "MiClave123!"
     }'

# 2. Confirmar el correo con el token del enlace (crea la cuenta)
curl -X POST "http://localhost:8000/api/v2/auth/email/verify" \
     -H "Content-Type: application/json" \
     -d '{"token": "<token del enlace>"}'

# 3. Iniciar sesión con el correo y guardar los tokens
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v2/auth/login" \
     -H "Content-Type: application/json" \
     -H "X-Lunance-Device: $(uuidgen)" \
     -H "X-Lunance-Client: ios/1.0.0" \
     -d '{
       "email": "juan@example.com",
       "password": "MiClave123!"
     }')

export ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r .access_token)
export REFRESH_TOKEN=$(echo "$RESPONSE" | jq -r .refresh_token)

# 4. Verificar usuario autenticado
curl -X GET "http://localhost:8000/api/v2/auth/me" \
     -H "Authorization: Bearer $ACCESS_TOKEN"

# 5. Crear primera cuenta
curl -X POST "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Idempotency-Key: $(uuidgen)" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Cuenta Principal",
       "account_type": "CHECKING",
       "bank_id": 1,
       "initial_balance": 5000.00
     }'

# 6. Listar todas las cuentas
curl -X GET "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Gestión de Múltiples Cuentas

```bash
# Crear cuenta de ahorros
curl -X POST "http://localhost:8000/api/v2/account/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Idempotency-Key: $(uuidgen)" \
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
     -H "Idempotency-Key: $(uuidgen)" \
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
     -H "Idempotency-Key: $(uuidgen)" \
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
     -H "Idempotency-Key: $(uuidgen)" \
     -H "Content-Type: application/json" \
     -d '{"amount": 1500.00}'

# Tramos por monto: primero el apartado que recibe el excedente...
curl -X POST "http://localhost:8000/api/v2/positions/" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Idempotency-Key: $(uuidgen)" \
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
- `JWT_VALIDATION_ERROR` (401): access token inválido, expirado o mal formado → renovar con `/auth/refresh`
- `AUTH_SESSION_EXPIRED` (401): la sesión se cerró, venció o el refresh token no es válido → volver a iniciar sesión
- `AUTH_USER_INACTIVE` (401): usuario inactivo
- `AUTH_INVALID_PROVIDER_TOKEN` (401): ID token de Google/Apple inválido o ya usado
- `AUTH_EMAIL_NOT_VERIFIED` (403): el correo del registro aún no se confirma
- `AUTH_REAUTH_REQUIRED` (403): para vincular Google/Apple hay que confirmar la identidad (contraseña actual o un login reciente)
- `AUTH_INVALID_TOKEN` (400): enlace de verificación o de recuperación inválido, caducado o ya usado
- `AUTH_INVALID_CURRENT_PASSWORD` (400): la contraseña actual no coincide
- `AUTH_TOO_MANY_ATTEMPTS` (429): login bloqueado por intentos fallidos (`Retry-After`)
- Google/Apple y vinculación: `AUTH_PROVIDER_LINK_REQUIRED`, `AUTH_PROVIDER_CONFLICT`, `AUTH_PROVIDER_IN_USE`, `AUTH_LAST_LOGIN_METHOD`, `AUTH_PASSWORD_NOT_SET` (409) y `AUTH_PROVIDER_NOT_CONFIGURED`, `AUTH_PROVIDER_UNAVAILABLE` (503); ver [Google y Apple](#google-y-apple)

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
- `NOT_FOUND_SESSION`: Sesión no encontrada, ya cerrada o de otro usuario (`DELETE /auth/sessions/{uuid}`)
- `NOT_FOUND_INSTRUMENT`: Valor no encontrado en el catálogo (`/securities/instruments/{uuid}/…`)
- `NOT_FOUND_SECURITY_TRADE`: Operación no encontrada o de otro usuario
- `NOT_FOUND_SECURITY_HOLDING`: Tenencia no encontrada o de otro usuario
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
- `BUSINESS_EMAIL_EXISTS` (409): al confirmar un registro, el correo ya tiene una cuenta
- `BUSINESS_USERNAME_EXISTS` (409): el username está ocupado (registro, confirmación o `PATCH /auth/me`)
- `BUSINESS_ACCOUNT_HAS_TRANSACTIONS` (409): Cuenta tiene transacciones
- `BUSINESS_RULE_VIOLATION` (400): Violación de regla de negocio genérica
- `INSUFFICIENT_FUNDS` (422): Fondos insuficientes (en apartados se compara siempre contra el **saldo disponible**, no contra el total de la cuenta)

**Códigos de transferencias y compras a plazos:**
- `SAME_ACCOUNT_TRANSFER` (409): La cuenta origen y la destino son la misma
- `TRANSFER_ACCOUNT_TYPE_NOT_ALLOWED` (409): Una tarjeta de crédito no puede ser el origen de una transferencia
- `TRANSFER_NOT_ALLOWED` (409): La transferencia pertenece al pago de una cuota; hay que eliminar la compra a meses
- `INSTALLMENT_CHARGE_ALREADY_PAID` (409): El cargo ya fue pagado
- `INSTALLMENT_TRANSACTION_LOCKED` (409): El movimiento es el gasto inicial de una compra a meses; se edita o elimina desde la compra
- `INVALID_TRANSACTION_TYPE` (400): Se intentó editar o eliminar una transferencia con los endpoints de transacción

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
- `INSUFFICIENT_SHARES` (409): Una venta o split pide más títulos de los que hay ese día (también al editar o borrar una operación anterior)
- `SECURITY_ACCOUNT_TYPE_NOT_ALLOWED` (409): Las tarjetas de crédito no admiten acciones
- `SECURITY_CURRENCY_MISMATCH` (409): La cuenta no está en la moneda del valor
- `TRANSFER_CURRENCY_MISMATCH` (409): Las cuentas de una transferencia (o del pago de una compra a meses) no están en la misma moneda
- `ACCOUNT_CURRENCY_MISMATCH` (409): Se pidió otra moneda que la de la cuenta, o mover un movimiento, suscripción o ingreso recurrente a una cuenta de otra moneda
- `SECURITY_TRADE_TRANSACTION_LOCKED` (409): La transacción es de una operación de acciones; se edita desde `/securities/trades/`
- `VALIDATION_INVALID_SECURITY_TRADE` (400): Faltan o sobran campos para el tipo de operación, fecha futura, o comisiones que superan la venta

### Errores de Idempotencia (409 / 422)

```json
{
  "error_code": "IDEMPOTENCY_KEY_REUSED",
  "message": "Esta Idempotency-Key ya se usó con una petición distinta; genera una clave nueva por operación",
  "details": null
}
```

- `IDEMPOTENCY_KEY_REUSED` (422): la misma `Idempotency-Key` llegó con otro cuerpo, método o ruta
- `IDEMPOTENCY_KEY_IN_USE` (409): la operación de esa clave se aplicó pero su respuesta no está guardada; consulta el recurso antes de reintentar
- `VALIDATION_ERROR` (422) con `loc: ["header", "Idempotency-Key"]`: falta el header o no es un UUID

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
| 202 | Accepted | Registro o reenvío de verificación recibido (la respuesta no revela si el correo existe) |
| 204 | No Content | Operación sin cuerpo de respuesta (p. ej. `/auth/password/*`) |
| 400 | Bad Request | Error de validación en el request |
| 401 | Unauthorized | Token inválido o faltante |
| 403 | Forbidden | Sin permisos para el recurso, `AUTH_EMAIL_NOT_VERIFIED` o `AUTH_REAUTH_REQUIRED` |
| 404 | Not Found | Recurso no encontrado |
| 409 | Conflict | Regla de negocio en conflicto, `BUSINESS_USERNAME_EXISTS` o `IDEMPOTENCY_KEY_IN_USE` |
| 422 | Unprocessable Entity | Error de validación de datos |
| 429 | Too Many Requests | Se excedió el límite de rate limiting, o `AUTH_TOO_MANY_ATTEMPTS` (bloqueo del login) |
| 500 | Internal Server Error | Error interno del servidor |
| 503 | Service Unavailable | Redis no responde en login, registro o recuperación de contraseña, o Google/Apple no está disponible o configurado (con `Retry-After`) |

## 📄 Límites y Paginación

### Rate Limiting

La API implementa rate limiting específico por endpoint para proteger contra abuso. Los límites son aplicados por IP/usuario.

#### Endpoints de Autenticación

| Endpoint | Límite | Razón |
|----------|--------|-------|
| `POST /auth/register` | **5 requests/hora** por IP + **5 correos/hora por buzón** (compartido con el reenvío) | Evita el alta masiva y llenar el buzón de otro |
| `POST /auth/email/verify` | **10 requests/minuto** | Confirmación del correo |
| `POST /auth/email/verify/resend` | **5 requests/minuto** por IP + límite por buzón | Reenvío del enlace |
| `POST /auth/password/forgot` | **5 requests/minuto** por IP + **3 correos/hora por buzón** (al pasarlo responde 204 sin mandar nada) | Recuperación de contraseña |
| `POST /auth/password/reset` | **10 requests/minuto** | Recuperación de contraseña |
| `POST /auth/password/change` | **5 requests/minuto** por usuario | Comprueba la contraseña actual |
| `POST /auth/login` | **10 requests/minuto** + bloqueo por correo (ver [Login](#login)) | Frena los ataques de fuerza bruta |
| `POST /auth/refresh` | **20 requests/minuto** | Renovación de sesión |
| `POST /auth/logout` | **10 requests/minuto** | Operación normal |
| `GET /auth/sessions` | **30 requests/minuto** | Lista de sesiones |
| `DELETE /auth/sessions/{uuid}` | **20 requests/minuto** | Cerrar una sesión |
| `GET /auth/me` | **100 requests/minuto** | Lectura de perfil frecuente |
| `PATCH /auth/me` | **5 requests/minuto** por usuario | Cambiar el username |
| `POST /auth/google`, `POST /auth/apple` | **10 requests/minuto** (`503` si Redis no responde) | Login con proveedor |
| `POST /auth/providers/{google,apple}`, `DELETE /auth/providers/{provider}` | **5 requests/minuto** por usuario (compartido) | Vincular y desvincular |
| `POST /auth/apple/notifications` | **100 requests/minuto** | Avisos de Apple (servidor a servidor) |

> **Nota**: además de estos límites por endpoint, los intentos de autenticación fallidos se limitan por IP, y el login se bloquea por correo (+ IP) tras varios fallos (`429 AUTH_TOO_MANY_ATTEMPTS`). Superarlos devuelve `429` aunque las credenciales acaben siendo correctas. Si Redis no responde, login, registro, verificación y recuperación de contraseña responden `503`.

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

#### Endpoints de Valores

| Endpoint | Límite | Nota |
|----------|--------|------|
| `GET /securities/search` | **30 requests/minuto** | Puede consultar al proveedor de EE. UU. |
| `GET /securities/instruments/{uuid}/prices` | **50 requests/minuto** | Cierres guardados |
| `POST /securities/trades/` | **20 requests/minuto** | Exige `Idempotency-Key` |
| `PUT` / `DELETE /securities/trades/{uuid}` | **20 requests/minuto** | Aceptan `Idempotency-Key` |
| `GET /securities/trades/` | **50 requests/minuto** | Listado |
| `GET /securities/holdings/` y `/{uuid}` | **50 requests/minuto** | Tenencias valuadas |
| `GET /securities/holdings/{uuid}/history` | **50 requests/minuto** | Fotos diarias |
| `GET /securities/portfolio/` | **50 requests/minuto** | Patrimonio en pesos |
| `GET /securities/portfolio/history` | **50 requests/minuto** | Lo invertido por día |

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
import uuid

import httpx

class LunanceClient:
    def __init__(self, base_url="http://localhost:8000", token=None, device_id=None):
        self.base_url = base_url
        self.token = token
        self.refresh_token = None
        # Genera el id del dispositivo una sola vez y guárdalo: identifica la sesión.
        self.device = {
            "X-Lunance-Device": device_id or str(uuid.uuid4()),
            "X-Lunance-Client": "ios/1.0.0",  # el refresh llega en el body
        }
        self.client = httpx.AsyncClient()

    async def login(self, email: str, password: str):
        """Inicia sesión y guarda el access token para las siguientes llamadas."""
        response = await self.client.post(
            f"{self.base_url}/api/v2/auth/login",
            json={"email": email, "password": password},
            headers=self.device,
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
            json={"refresh_token": self.refresh_token},
            headers=self.device,
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
