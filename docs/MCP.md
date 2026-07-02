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

Cada tool llama a un endpoint que exige el scope indicado. Solo hay **lectura y creación**
(no editar/eliminar).

| Sección | Tools | Scope requerido |
|---|---|---|
| **Transacciones** | `list_transactions`, `get_transaction` | `transactions:read` |
| | `create_transaction` | `transactions:write` |
| **Cuentas** | `list_accounts`, `get_account`, `get_account_activity` | `accounts:read` |
| | `create_account` | `accounts:write` |
| **Categorías** | `list_categories` | `categories:read` |
| **Dashboard** | `get_dashboard` | `dashboard:read` |
| **Presupuestos** | `list_budgets`, `get_budget`, `get_budget_progress` | `budgets:read` |
| | `create_budget` | `budgets:write` |
| **Metas de ahorro** | `list_goals`, `get_goal` | `goals:read` |
| | `create_goal` | `goals:write` |
| **Inversiones** | `get_investment_yields`, `get_investment_projections` | `investments:read` |
| **Suscripciones** | `list_subscriptions`, `list_subscription_charges`, `get_subscription` | `subscriptions:read` |
| | `create_subscription` | `subscriptions:write` |
| **Compras a plazos (MSI)** | `list_installments` | `installments:read` |
| | `create_installment` | `installments:write` |
| **Transferencias** | `create_transfer` | `transfers:write` |
| **Bancos** | `list_banks` | `banks:read` |

> Total: **26 herramientas**. Excluidos a propósito del MCP: `auth`, `api-keys` (por
> seguridad), `ai` (el MCP ya es la capa de IA), y todas las operaciones de
> **editar/eliminar** y el **pago de cuotas** (`installment pay`).

---

## ✅ Requisitos

1. **La API de Lunance corriendo** en `:8000` (`uvicorn src.main:app --reload`).
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

### Docker

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
- **Solo lectura y creación.** Ninguna tool edita ni elimina datos.
- **Transferencias:** `create_transfer` mueve dinero real entre cuentas; su descripción
  instruye al agente a confirmar con el usuario antes de ejecutar.
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
