# 🤖 Servidor MCP — Lunance

El servidor **MCP (Model Context Protocol)** expone la API de Lunance como un conjunto
de **herramientas (tools)** que un agente/LLM puede invocar para consultar y registrar
finanzas del usuario en lenguaje natural.

- 📖 Autenticación por scopes y contrato de API Keys: [API_USAGE.md](API_USAGE.md#-autenticación-con-api-keys)

---

## 📋 Tabla de contenido

- [¿Cómo funciona?](#-cómo-funciona)
- [Herramientas disponibles](#-herramientas-disponibles)
- [Requisitos](#-requisitos)
- [Ejecutar el servidor](#-ejecutar-el-servidor)
- [Probar con el MCP Inspector](#-probar-con-el-mcp-inspector)
- [Conectar desde Claude Desktop](#-conectar-desde-claude-desktop)
- [Configuración](#-configuración)
- [Seguridad](#-seguridad)
- [Agregar una herramienta nueva](#-agregar-una-herramienta-nueva)

---

## 🔧 ¿Cómo funciona?

El MCP **no accede a la base de datos**: es un **proxy** que traduce las llamadas de las
tools en peticiones HTTP a la propia API de Lynance (`/api/v2`), reenviando la
`X-API-Key` del usuario.

```
Agente/LLM  ──(MCP, streamable-http :8001/mcp)──►  Servidor MCP  ──(HTTP + X-API-Key)──►  API Lunance :8000
```

- Transporte: **streamable-http**, escucha en `MCP_HOST:MCP_PORT` (por defecto
  `localhost:8001`), endpoint `/mcp`.
- La **API Key viaja en el header `X-API-Key`** de cada request MCP; el servidor la
  extrae y la inyecta en la llamada a la API (`presentation/mcp/client.py`).
- Los **scopes de la key deciden qué tools responden**: si la key no tiene el scope del
  endpoint subyacente, la API responde `403` y la tool devuelve ese error como texto.
- Protección **anti DNS-rebinding** activada (`allowed_hosts` / `allowed_origins`).

Código: `src/presentation/mcp/` → `server.py` (tools), `client.py` (cliente HTTP),
`config.py` (settings).

---

## 🧰 Herramientas disponibles

Cada tool llama a un endpoint que exige el scope indicado. El CRUD completo está
disponible: las operaciones de **lectura** requieren el scope `:read` del recurso y las de
**creación/edición/eliminación** el scope `:write`.

| Sección | Tools | Scope requerido |
|---|---|---|
| **Transacciones** | `list_transactions`, `get_transaction` | `transactions:read` |
| | `create_transaction`, `update_transaction`, `delete_transaction` | `transactions:write` |
| **Cuentas** | `list_accounts`, `get_account`, `get_account_activity` | `accounts:read` |
| | `create_account`, `update_account`, `set_account_status`, `delete_account` | `accounts:write` |
| **Categorías** | `list_categories` | `categories:read` |
| **Dashboard** | `get_dashboard` | `dashboard:read` |
| **Presupuestos** | `list_budgets`, `get_budget`, `get_budget_progress` | `budgets:read` |
| | `create_budget`, `update_budget`, `toggle_budget`, `delete_budget` | `budgets:write` |
| **Metas de ahorro** | `list_goals`, `get_goal` | `goals:read` |
| | `create_goal`, `update_goal`, `toggle_goal`, `delete_goal` | `goals:write` |
| **Inversiones** | `get_investment_yields`, `get_investment_projections` | `investments:read` |
| **Apartados de inversión** | `list_positions`, `get_position`, `get_position_yields`, `get_position_projections` | `investments:read` |
| | `create_position`, `deposit_to_position`, `withdraw_from_position`, `liquidate_position` | `investments:write` |
| **Suscripciones** | `list_subscriptions`, `list_subscription_charges`, `get_subscription` | `subscriptions:read` |
| | `create_subscription`, `update_subscription`, `toggle_subscription`, `delete_subscription` | `subscriptions:write` |
| **Ingresos recurrentes** | `list_incomes`, `get_income_deposits` | `incomes:read` |
| | `create_income`, `update_income`, `toggle_income`, `delete_income` | `incomes:write` |
| **Compras a plazos (MSI)** | `list_installments` | `installments:read` |
| | `create_installment`, `update_installment`, `pay_installment_charge`, `delete_installment` | `installments:write` |
| **Transferencias** | `create_transfer`, `delete_transfer` | `transfers:write` |
| **Bancos** | `list_banks` | `banks:read` |

> Total: **58 herramientas**. Excluidos a propósito del MCP: `auth` y `api-keys` (por
> seguridad) y `ai` (el MCP ya es la capa de IA).
>
> Un **apartado de inversión** vive dentro de una cuenta y genera rendimientos (a la
> vista o a plazo fijo). El dinero apartado no cuenta en el saldo disponible: para
> gastarlo o transferirlo primero hay que regresarlo con `withdraw_from_position` o
> `liquidate_position`.
>
> Para limitar a un agente a solo-lectura, emite su API key únicamente con scopes
> `:read` — las tools de escritura devolverán `403`.

---

## ✅ Requisitos

1. **La API de Lunance corriendo** en `:8000` (`uvicorn src.main:app --reload`, o
   `docker compose up -d`, que ya la levanta junto al MCP).
2. Una **API Key** (`moon_...`) creada desde la app (`POST /api/v2/api-keys/`) con los
   scopes que quieras usar.
3. Dependencias del grupo `mcp` instaladas (ver abajo).

---

## 🚀 Ejecutar el servidor

### Local (uv)

```bash
# 1. Instalar deps del MCP SIN borrar el motor Rust fincore (que no está en el lock).
uv sync --group mcp --inexact

# 2. Levantar el servidor MCP (streamable-http en :8001, endpoint /mcp).
PYTHONPATH=src uv run --no-sync python -m presentation.mcp.server
```

> ⚠️ **Importante:** usa siempre `--inexact` al sincronizar. Un `uv sync` normal borra
> el módulo `fincore` (no está en el lockfile) y rompe el arranque de la API. El MCP
> necesita `PYTHONPATH=src` porque el proyecto no se instala como paquete.

### Docker Compose — recomendado

`docker-compose.yml` ya incluye el servicio `mcp` (construido desde `Dockerfile.mcp`), así
que levanta MCP + API + MySQL en la misma red con un solo comando:

```bash
docker compose up -d          # todo el stack (db, api, mcp)
docker compose up -d mcp      # solo el MCP (arrastra api y db por depends_on)
```

El servicio trae ya resueltas las variables que en `docker run` tendrías que pasar a mano:
`LUNANCE_API_BASE_URL=http://api:8000` (la API por nombre de servicio en la red interna),
`MCP_HOST=0.0.0.0` y los allowed hosts/origins de local.

### Docker (imagen suelta)

Solo si quieres el MCP aislado, contra una API que ya corre fuera de compose:

```bash
docker build -f Dockerfile.mcp -t lunance-mcp .
docker run -p 8001:8001 \
  -e LUNANCE_API_BASE_URL=http://host.docker.internal:8000 \
  lunance-mcp
```

---

## 🔍 Probar con el MCP Inspector

Con el servidor corriendo:

```bash
npx @modelcontextprotocol/inspector
```

En la UI del Inspector:

1. **Transport Type:** `Streamable HTTP`
2. **URL:** `http://localhost:8001/mcp`
3. **Headers:** agrega `X-API-Key` = `moon_...` ← *esto autentica al usuario*
4. **Connect → List Tools** y prueba, p. ej., `list_transactions`, `list_accounts`,
   `get_dashboard`.

> La autenticación va en el **header `X-API-Key`**, no en la config. Los **scopes de esa
> key** determinan qué tools responden `200` y cuáles `403`.

---

## 🖥️ Conectar desde Claude Desktop

El MCP de Lunance habla **`streamable-http`** (endpoint `/mcp`) y autentica por header
**`X-API-Key`**. Claude Desktop, en cambio, solo arranca servidores por **`stdio`** desde
`claude_desktop_config.json`, así que no puede hablarle directo — ni siquiera en
`localhost`. Hace falta **`mcp-remote`** como puente stdio ↔ HTTP:

```json
{
  "mcpServers": {
    "lunance": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8001/mcp",
        "--header",
        "X-API-Key: moon_TU_API_KEY"
      ]
    }
  }
}
```

Tras editarlo, **reinicia Claude Desktop**.

Notas:

- `--header "X-API-Key: ..."` autentica contra el MCP; los scopes de esa key deciden qué
  tools responden.
- **No uses `--sse`**: no es una flag de `mcp-remote` (se ignora en silencio). La real es
  `--transport <http-first|sse-only|…>`, y aquí no hace falta: el servidor corre
  `mcp.run(transport="streamable-http")`, así que **no monta endpoint SSE** y `sse-only`
  daría 404.

### Si el MCP no corre en la misma máquina que Claude Desktop

Un MCP en otro equipo de la red local necesita **tres** cambios; si falta alguno, la
conexión falla:

| Dónde | Qué | Por qué |
|---|---|---|
| Servidor | `MCP_HOST=0.0.0.0` | El default `localhost` escucha solo en loopback: inalcanzable desde otro equipo |
| Servidor | `MCP_ALLOWED_HOSTS` / `MCP_ALLOWED_ORIGINS` con el host real | Con los defaults solo-localhost, la protección anti DNS-rebinding responde `421`. En compose el servicio `mcp` trae `localhost:8001,127.0.0.1:8001,mcp:8001`: tampoco cubre la IP de red, hay que añadirla |
| Cliente | `--allow-http` en `mcp-remote` | `mcp-remote` **rechaza URLs `http://` que no sean `localhost`/`127.0.0.1`** y aborta |

Los `args` quedarían así:

```
"mcp-remote", "http://192.168.1.50:8001/mcp", "--allow-http",
"--header", "X-API-Key: moon_TU_API_KEY"
```

> ⚠️ **Por qué esto parece un problema de transporte y no lo es:** el `421` del chequeo de
> Host es un 4xx, y `mcp-remote` reacciona a los 4xx **cayendo al transporte SSE legacy**.
> El error que ves acaba hablando de SSE, cuando la causa real es el `Host` no permitido (o
> la falta de `--allow-http`). Añadir flags de SSE no lo arregla: revisa las tres filas de
> arriba.

Si el MCP va por HTTPS con certificado self-signed, `--allow-http` no aplica; lo que salta
la validación TLS es `"env": { "NODE_TLS_REJECT_UNAUTHORIZED": "0" }`. ⚠️ Deja la conexión
sin verificar frente a MITM: no lo dejes fijo sin entender por qué falla el certificado.

---

## ⚙️ Configuración

Variables de entorno (leídas por `presentation/mcp/config.py`, admite `.env`):

| Variable | Default | Descripción |
|---|---|---|
| `MCP_HOST` | `localhost` | Host donde escucha el MCP (en Docker: `0.0.0.0`) |
| `MCP_PORT` | `8001` | Puerto del MCP |
| `LUNANCE_API_BASE_URL` | `http://localhost:8000` | URL base de la API de Lunance |
| `MCP_ALLOWED_HOSTS` | `localhost:8001,127.0.0.1:8001` | Hosts permitidos (anti DNS-rebinding) |
| `MCP_ALLOWED_ORIGINS` | `http://localhost:8001,http://127.0.0.1:8001` | Orígenes permitidos |

> ⚠️ **Producción:** `MCP_ALLOWED_HOSTS` / `MCP_ALLOWED_ORIGINS` vienen con valores
> **solo localhost**. Antes de desplegar hay que definir el host y origen reales.

---

## 🔒 Seguridad

- **Doble candado:** la key se valida (existencia, usuario, expiración) **y** se comprueba
  el scope del endpoint (`require_scope`). Sin el scope → `403`.
- **Escritura bajo scope explícito:** editar/eliminar requiere que la API key tenga el
  scope `:write` del recurso. Una key solo-lectura no puede modificar nada.
- **Operaciones destructivas:** todas las tools `delete_*` (y `create_transfer`, que mueve
  dinero real) instruyen al agente en su descripción a pedir confirmación explícita del
  usuario antes de ejecutar. Los deletes son permanentes.
- Las API Keys se guardan **hasheadas (SHA-256)**; la key completa (`raw_key`) se muestra
  una sola vez al crearla.
- Protección anti **DNS-rebinding** vía `allowed_hosts` / `allowed_origins`.

---

## ➕ Agregar una herramienta nueva

Exponer un endpoint nuevo por MCP requiere **4 pasos** (no basta con crear la tool):

1. **Scope** — si no existe, añádelo al enum `APIKeyScope`
   (`src/domain/objects/enums.py`).
2. **Enforcement** — aplica `require_scope(APIKeyScope.X.value)` en el endpoint
   (read → `:read`, create → `:write`). Sin esto, el endpoint no acepta la API Key.
3. **Tool** — define la función con `@mcp.tool()` en `server.py` y llama a
   `request_api(method, path, get_api_key(ctx), ...)`.
4. **Tests + frontend** — agrega el test de enforcement en
   `src/tests/e2e/test_api_key_api.py` y añade el scope al type `ApiKeyScope` del
   frontend.

> Regla de oro: **nunca** agregues un scope al enum sin enforzarlo en su endpoint — un
> scope "decorativo" da falsa sensación de permiso.
