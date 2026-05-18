# Installments API — Compras a Meses

Base URL: `/api/v2/installments`

Todos los endpoints requieren autenticación JWT. Incluye el token en el header:

```
Authorization: Bearer <access_token>
```

---

## Conceptos clave

Una **compra a meses** (`InstallmentPurchase`) representa el compromiso financiero completo.
Al crearla, el sistema genera automáticamente las **cuotas** (`InstallmentCharge`) — una por cada mes.

Cada cuota puede pagarse de forma individual con el endpoint de pago. Al pagar una cuota, se crea una transacción real en la cuenta y se descuenta el balance.

```
InstallmentPurchase  (ej. iPhone a 12 meses)
├── InstallmentCharge #1  → due: 2026-06-01  paid: false
├── InstallmentCharge #2  → due: 2026-07-01  paid: false
├── ...
└── InstallmentCharge #12 → due: 2027-05-01  paid: false
```

---

## Endpoints

### 1. Listar compras a meses

```
GET /api/v2/installments/
```

Retorna todas las compras activas del usuario con sus cuotas.

**Response `200 OK`:**

```json
[
  {
    "uuid": "abc123",
    "account_uuid": "cuenta-uuid",
    "category_id": 5,
    "description": "iPhone 15 Pro",
    "total_amount": "23999.00",
    "num_installments": 12,
    "installment_type": "NO_INTEREST",
    "annual_interest_rate": "0.00",
    "monthly_payment": "1999.92",
    "purchase_date": "2026-05-16",
    "notes": "Liverpool MSI",
    "is_active": true,
    "creation_date": "2026-05-16T10:30:00",
    "charges": [
      {
        "uuid": "charge-uuid-1",
        "installment_number": 1,
        "amount": "1999.92",
        "due_date": "2026-06-16",
        "paid": false,
        "paid_at": null
      },
      {
        "uuid": "charge-uuid-2",
        "installment_number": 2,
        "amount": "1999.92",
        "due_date": "2026-07-16",
        "paid": true,
        "paid_at": "2026-07-14T09:00:00"
      }
    ]
  }
]
```

---

### 2. Crear compra a meses

```
POST /api/v2/installments/
```

Crea la compra y genera automáticamente todas las cuotas mensuales.

**Request body:**

```json
{
  "account_uuid": "string (requerido) — UUID de la cuenta de tarjeta de crédito",
  "category_id": "integer (opcional) — ID de categoría",
  "description": "string (requerido, max 500) — nombre o descripción de la compra",
  "total_amount": "decimal (requerido, > 0) — monto total de la compra",
  "num_installments": "integer (requerido, 2–48) — número de meses",
  "installment_type": "string (requerido) — 'NO_INTEREST' o 'WITH_INTEREST'",
  "annual_interest_rate": "decimal (requerido, >= 0) — tasa anual en %; usar 0 si es MSI",
  "purchase_date": "date (requerido) — fecha de la compra (YYYY-MM-DD)",
  "notes": "string (opcional, max 1000)"
}
```

**Ejemplo MSI:**

```json
{
  "account_uuid": "abc-123",
  "category_id": 10,
  "description": "MacBook Air M3",
  "total_amount": 29999.00,
  "num_installments": 18,
  "installment_type": "NO_INTEREST",
  "annual_interest_rate": 0,
  "purchase_date": "2026-05-16",
  "notes": "Best Buy 18 MSI"
}
```

**Ejemplo con interés:**

```json
{
  "account_uuid": "abc-123",
  "description": "Refrigerador Samsung",
  "total_amount": 15000.00,
  "num_installments": 12,
  "installment_type": "WITH_INTEREST",
  "annual_interest_rate": 36.00,
  "purchase_date": "2026-05-16"
}
```

**Response `200 OK`:** mismo schema que el objeto en el listado (con todas las cuotas generadas).

**Validaciones:**
- `num_installments`: mínimo 2, máximo 48
- `total_amount`: debe ser mayor a 0
- `annual_interest_rate`: debe ser 0 cuando `installment_type` es `NO_INTEREST`
- `account_uuid`: debe pertenecer al usuario autenticado

---

### 3. Pagar una cuota

```
POST /api/v2/installments/{charge_uuid}/pay/
```

Registra el pago de una cuota. Crea una transacción de tipo `EXPENSE` en la cuenta y descuenta el balance.

**Path parameter:**
- `charge_uuid` — UUID de la cuota a pagar (obtenido del listado)

**Request body:**

```json
{
  "payment_date": "2026-06-14"
}
```

**Response `200 OK`:**

```json
{
  "uuid": "charge-uuid-1",
  "installment_number": 1,
  "amount": "1999.92",
  "due_date": "2026-06-16",
  "paid": true,
  "paid_at": "2026-06-14T15:30:00"
}
```

---

## Campos de referencia

### `installment_type`

| Valor | Descripción |
|---|---|
| `NO_INTEREST` | Meses Sin Interés (MSI) — el pago mensual es `total / n` |
| `WITH_INTEREST` | Con interés — se aplica fórmula de amortización bancaria |

### Cálculo del pago mensual

- **MSI:** `monthly_payment = total_amount / num_installments`
- **Con interés:** fórmula de amortización estándar con `annual_interest_rate`

El campo `monthly_payment` ya viene calculado en la respuesta — el front no necesita calcularlo.

---

## Flujo de integración sugerido

```
1. Usuario selecciona cuenta y llena el formulario de compra a meses
2. POST /api/v2/installments/  →  recibe la compra con todas las cuotas
3. Mostrar lista de cuotas con su fecha de vencimiento y estado (paid/pending)
4. Cuando el usuario quiere registrar el pago de un mes:
   POST /api/v2/installments/{charge_uuid}/pay/
5. Actualizar la cuota en UI a paid: true
```

---

## Errores comunes

| Código | Causa |
|---|---|
| `401` | Token inválido o expirado |
| `404` | `account_uuid` o `charge_uuid` no encontrado |
| `422` | Datos de request inválidos (validación de Pydantic) |
| `429` | Rate limit excedido (max 20 req/min en escritura, 50 req/min en lectura) |
