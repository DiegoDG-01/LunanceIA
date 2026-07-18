# Incomes API — Ingresos Recurrentes

Base URL: `/api/v2/incomes`

Todos los endpoints requieren autenticación JWT. Incluye el token en el header:

```
Authorization: Bearer <access_token>
```

Si se usa API Key en lugar de JWT, los scopes requeridos son `incomes:read` (GETs) e `incomes:write` (POST).

---

## Conceptos clave

Un **ingreso recurrente** (`RecurringIncome`) es una regla: *"me depositan $15,000 cada quincena en la cuenta X"*. Aplica para nómina, renta, pensión, o cualquier ingreso que se repite.

El usuario solo **registra la regla una vez**. Un job automático corre cada noche (00:15 UTC) y, cuando la fecha de pago llega:

1. Crea un **depósito** (`IncomeDeposit`) — el registro histórico de esa ejecución.
2. Crea una **transacción** tipo `INCOME` en la cuenta.
3. **Incrementa el balance** de la cuenta.
4. Avanza `next_payment_date` según la frecuencia.
5. Genera una notificación push.

```
RecurringIncome  (ej. Nómina quincenal $15,000)
├── IncomeDeposit  → 2026-07-01  PAGADO  → transaction #1041
├── IncomeDeposit  → 2026-07-15  PAGADO  → transaction #1187
└── next_payment_date: 2026-07-29   ← lo que el front debe mostrar como "próximo pago"
```

**Comportamientos importantes para el front:**

- `next_payment_date` es el dato estrella: "tu próxima nómina cae el 29 de julio".
- Si el servidor estuvo caído, el job **recupera los periodos perdidos** (uno por fecha, con la fecha original). El front no necesita hacer nada.
- Los depósitos son de solo lectura — no hay endpoint para crearlos manualmente; los genera el sistema.
- Un ingreso pausado (`is_active: false`) no genera depósitos hasta reactivarse.
- Si el ingreso tiene `end_date`, solo se pagan periodos cuya fecha caiga dentro del rango — después el ingreso deja de generar depósitos (pero conserva su historial).

---

## Enums

**`frequency`** (frecuencia del ingreso):

| Valor | Significado |
|---|---|
| `DAILY` | Diario |
| `WEEKLY` | Semanal |
| `BIWEEKLY` | Cada 14 días |
| `MONTHLY` | Mensual (mismo día de cada mes) |
| `BIMONTHLY` | Bimestral |
| `QUARTERLY` | Trimestral |
| `SEMI_ANNUAL` | Semestral |
| `ANNUAL` | Anual |

> 💡 **Quincena mexicana (día 15 y último de mes):** NO es `BIWEEKLY` (eso son 14 días exactos). Se modela con **dos ingresos `MONTHLY`**: uno con `start_date` el día 15 y otro con `start_date` el día 31 (el sistema lo ajusta automáticamente al último día en meses cortos: 28-feb → 31-mar → 30-abr...). Considera ofrecer esto como atajo en el UI ("¿Te pagan por quincena?").

**`status`** de un depósito (mismo enum que cargos de suscripción):

| Valor | Significado |
|---|---|
| `pendiente` | Reservado, en proceso |
| `pagado` | Depositado — tiene `transaction_id` |
| `fallido` | Falló (ej. cuenta eliminada) |
| `cancelado` | Cancelado |

---

## Endpoints

### 1. Listar ingresos recurrentes

```
GET /api/v2/incomes/
```

**Query params** (todos opcionales):

| Param | Tipo | Default | Descripción |
|---|---|---|---|
| `account_uuid` | string | — | Filtrar por cuenta |
| `category_id` | int | — | Filtrar por categoría |
| `active_only` | bool | `false` | Solo activos |
| `limit` | int | 100 | Máx. 1000 |
| `offset` | int | 0 | Paginación |

**Response `200 OK`:**

```json
[
  {
    "uuid": "9b2f...",
    "name": "Nómina Empresa X",
    "account_uuid": "11a3...",
    "account_name": "BBVA Débito",
    "category_name": "Sueldo",
    "frequency": "MONTHLY",
    "amount": "15000.00",
    "currency": "MXN",
    "start_date": "2026-07-15",
    "end_date": null,
    "next_payment_date": "2026-08-15",
    "is_active": true,
    "description": "Nómina mensual",
    "creation_date": "2026-07-17T22:40:00Z"
  }
]
```

Rate limit: 50/min.

---

### 2. Detalle de un ingreso

```
GET /api/v2/incomes/{income_uuid}/
```

**Response `200 OK`:** mismo objeto que el listado.

**`404`** si el uuid no existe o no pertenece al usuario.

---

### 3. Historial de depósitos

```
GET /api/v2/incomes/{income_uuid}/deposits/
```

**Query params:** `limit` (default 100), `offset`.

Ordenados del más reciente al más antiguo.

**Response `200 OK`:**

```json
[
  {
    "uuid": "7c1d...",
    "deposit_date": "2026-07-15",
    "amount": "15000.00",
    "currency": "MXN",
    "status": "pagado",
    "transaction_uuid": "4f8a1c02-93d7-4b1e-a2f6-77b0c9e51d34"
  }
]
```

`transaction_uuid` permite navegar a la transacción (`GET /api/v2/transaction/{transaction_uuid}/`). Es `null` si la transacción fue eliminada por el usuario o si el depósito no está `pagado`.

Un ingreso recién creado devuelve `[]` (los depósitos aparecen cuando el job corre). Rate limit: 20/min.

---

### 4. Crear ingreso recurrente

```
POST /api/v2/incomes/
```

**Body:**

```json
{
  "account_uuid": "11a3...",
  "category_id": 3,
  "name": "Nómina Empresa X",
  "amount": 15000.00,
  "frequency": "MONTHLY",
  "start_date": "2026-08-15",
  "end_date": null,
  "next_payment_date": null,
  "description": "Nómina mensual"
}
```

| Campo | Requerido | Reglas |
|---|---|---|
| `account_uuid` | ✅ | Cuenta del usuario (destino del depósito) |
| `category_id` | ✅ | > 0 (típicamente la categoría "Sueldo") |
| `name` | ✅ | 1-100 caracteres |
| `amount` | ✅ | > 0 |
| `frequency` | ✅ | Ver enum |
| `start_date` | ✅ | `YYYY-MM-DD` |
| `end_date` | ❌ | Debe ser ≥ `start_date`, si no → error |
| `next_payment_date` | ❌ | Default: `start_date`. Útil si el alta se hace a mitad de periodo |
| `description` | ❌ | Máx. 500 caracteres |

**Response `201 Created`:** el objeto completo (incluye `uuid` y `next_payment_date` resueltos).

> ⚠️ Si `start_date` es hoy o una fecha pasada, el **primer depósito se genera esa misma noche** (y si es pasada, se generan todos los periodos desde entonces). Conviene avisarlo en el UI de confirmación.

Rate limit: 20/min.

---

### 5. Actualizar ingreso

```
PATCH /api/v2/incomes/{income_uuid}/
```

**Body:** todos los campos opcionales — solo se actualiza lo enviado (partial update).

```json
{
  "name": "Nómina Nueva Empresa",
  "amount": 18000.00
}
```

Campos aceptados: `account_uuid`, `name`, `amount`, `frequency`, `start_date`, `end_date`, `next_payment_date`, `is_active`, `description`, `category_id`.

**Response `200 OK`:** el objeto actualizado.

---

### 6. Pausar / reactivar (toggle)

```
PATCH /api/v2/incomes/{income_uuid}/activate/
```

Sin body. Invierte `is_active` en cada llamada.

**Response `200 OK`:** el objeto con el nuevo estado. Rate limit: 5/min.

---

### 7. Eliminar ingreso

```
DELETE /api/v2/incomes/{income_uuid}/
```

**Response `204 No Content`.** Elimina también su historial de depósitos (cascade). Las transacciones ya generadas en la cuenta **no** se eliminan. Rate limit: 5/min.

---

## Errores

Formato estándar de toda la API (`StandardErrorResponse`):

```json
{
  "error": true,
  "error_code": "NOT_FOUND",
  "message": "Ingreso recurrente con ID 9b2f... no encontrado",
  "details": null
}
```

| Código HTTP | Cuándo |
|---|---|
| `401` | Sin token / token inválido |
| `403` | API key sin el scope `incomes:read`/`incomes:write` |
| `404` | Ingreso inexistente o de otro usuario (también en `/deposits/`) |
| `400` / `422` | Validación: `end_date < start_date`, `amount <= 0`, frequency inválida, etc. |
| `429` | Rate limit excedido |

---

## Checklist sugerido para el front

- [ ] Lista de ingresos con `name`, `amount`, `frequency` y **`next_payment_date`** destacado.
- [ ] Badge de estado (`is_active`) + toggle pausar/reactivar.
- [ ] Alta con selector de frecuencia (y atajo "quincenal" que cree los 2 ingresos MONTHLY).
- [ ] Aviso al crear con fecha pasada/hoy: "se depositará esta noche".
- [ ] Vista de historial de depósitos por ingreso (endpoint 3).
- [ ] Los depósitos aparecen también como transacciones normales en el listado de transacciones (tipo `INCOME`, descripción `"Ingreso recurrente: {name}"`) — no duplicar en UI si se mezclan fuentes.
