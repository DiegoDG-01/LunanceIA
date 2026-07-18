# API Keys — Cambios para el front en creación de keys

**TL;DR:** hay 2 scopes nuevos (`incomes:read`, `incomes:write`) que deben aparecer en el
selector de scopes al crear una API key, **cambió el significado de todos los scopes
`:write`** (antes solo permitían *crear*, ahora permiten *crear, editar y eliminar*), y
hay un **breaking change en el endpoint de revocar** (ver sección al final). El endpoint
de creación de keys no cambió.

---

## Qué NO cambió

El contrato del endpoint es el mismo:

```
POST /api/v2/api-keys/
{
  "name": "Mi agente",
  "scopes": ["transactions:read", "incomes:read"],
  "expires_at": null
}
```

- `name`: 1-100 caracteres, requerido.
- `scopes`: array con al menos 1 valor del catálogo (abajo), requerido.
- `expires_at`: datetime opcional (`null` = no expira).
- La key completa (`raw_key`) se muestra **una sola vez** en el response de creación —
  eso ya lo manejan.

---

## Cambio 1: dos scopes nuevos (ingresos recurrentes)

Agregar al selector:

| Scope | Permite |
|---|---|
| `incomes:read` | Listar ingresos recurrentes y su historial de depósitos |
| `incomes:write` | Crear, editar, pausar/reactivar y eliminar ingresos recurrentes |

Si el selector del front está hardcodeado (lista estática de scopes), hay que añadirlos a
mano. Si se genera desde el enum del OpenAPI (`/openapi.json` → `APIKeyScope`), se
actualizan solos — verificar.

---

## Cambio 2: los scopes `:write` ahora son más poderosos ⚠️

Antes, un scope `:write` solo permitía **crear** registros (editar/eliminar estaba
bloqueado para API keys, era exclusivo de la sesión JWT). Ahora un `:write` habilita el
**CRUD completo** del recurso vía API key / MCP:

- Crear
- Editar (update parcial)
- Pausar / reactivar (toggles de estado)
- **Eliminar (permanente)**
- Pagar cuotas de MSI (en `installments:write`)

**Qué implica para el front:**

1. **Actualizar el copy del selector.** Si hoy dice algo como "Permite crear
   transacciones", debe decir "Permite crear, editar y **eliminar** transacciones". El
   usuario tiene que entender qué poder está otorgando.
2. **Considerar un aviso/confirmación** al seleccionar cualquier scope `:write`
   ("esta key podrá modificar y borrar datos de forma permanente").
3. Si existe UI de detalle/listado de keys ya creadas, revisar que el copy de los scopes
   mostrados también se actualice.

Las keys existentes no cambian de scopes por sí solas — pero las que **ya tenían**
`:write` ganaron estos poderes automáticamente. Puede valer un aviso a usuarios con keys
`:write` activas.

---

## Catálogo completo de scopes (19)

Para construir el selector agrupado por recurso:

| Recurso | Read | Write |
|---|---|---|
| Transacciones | `transactions:read` | `transactions:write` |
| Cuentas | `accounts:read` | `accounts:write` |
| Presupuestos | `budgets:read` | `budgets:write` |
| Metas de ahorro | `goals:read` | `goals:write` |
| Suscripciones | `subscriptions:read` | `subscriptions:write` |
| **Ingresos recurrentes** 🆕 | `incomes:read` | `incomes:write` |
| Compras a meses (MSI) | `installments:read` | `installments:write` |
| Transferencias | — | `transfers:write` |
| Categorías | `categories:read` | — |
| Dashboard | `dashboard:read` | — |
| Inversiones | `investments:read` | — |
| Bancos | `banks:read` | — |

Asimetrías a respetar en el UI (no inventar los faltantes):

- **Transferencias** solo tiene write (crear y eliminar transferencias; no hay listado
  por API key).
- **Categorías, dashboard, inversiones y bancos** son solo lectura.

---

## Sugerencia de UX (opcional pero recomendada)

Presets al crear la key, para que el usuario no arme scope por scope:

- **Solo lectura** → todos los `:read` (8 scopes). Ideal para agentes de
  consulta/reportes; no puede modificar nada.
- **Acceso completo** → los 19 scopes. Para asistentes que gestionan las finanzas
  (con el aviso de escritura).
- **Personalizado** → el selector granular agrupado por recurso.

Contexto de por qué importa: estas keys son las que se conectan al **servidor MCP**
(asistentes de IA). Un agente con `:write` puede editar y borrar registros reales del
usuario — la elección de scopes en este formulario es ahora la frontera de seguridad
principal. Detalle completo de qué herramienta MCP usa cada scope: `docs/MCP.md`.

---

## ⚠️ Breaking change: revocar y eliminar ahora son operaciones distintas

Antes `DELETE /api-keys/{uuid}/` solo **revocaba** (la key dejaba de funcionar pero
seguía apareciendo en el listado con `is_active: false`, para siempre). Ahora:

| Operación | Endpoint | Efecto |
|---|---|---|
| **Revocar** | `PATCH /api-keys/{uuid}/revoke/` 🆕 | La key deja de autenticar pero se conserva en el listado (`is_active: false`) |
| **Eliminar** | `DELETE /api-keys/{uuid}/` (cambió) | Borra la key permanentemente — desaparece del listado |

**Acción requerida en el front:**

1. El botón "Revocar" actual llama `DELETE` — debe cambiar a `PATCH .../revoke/`.
   Si no se actualiza, revocará... borrando la key sin dejar rastro.
2. Agregar el botón/acción "Eliminar" (con confirmación — es permanente e irreversible)
   que llame al `DELETE`.
3. UX sugerida: en keys activas ofrecer ambas acciones; en keys ya revocadas, solo
   "Eliminar" (para limpiar el listado).

Ambos endpoints devuelven `204` en éxito y `404` si la key no existe o no es del
usuario. Ambos requieren sesión JWT — no se pueden invocar con una API key (una key no
puede administrar keys).
