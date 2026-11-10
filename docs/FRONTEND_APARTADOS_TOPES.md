# Guía de frontend — Topes y desbordamiento en apartados

Qué cambió en la API de apartados (`/api/v2/positions/`) y qué hay que tocar del lado del
cliente. **Ningún endpoint existente cambió de forma**: todo lo nuevo es aditivo. Pero hay
**un cambio de comportamiento en el depósito** que sí puede romper suposiciones del front,
y está marcado abajo.

---

## Qué problema resuelve

Muchas SOFIPOs pagan su mejor tasa solo hasta cierto monto: los primeros 25,000 al 10% y
lo que pase de ahí a otra tasa. Ahora un apartado puede tener un **tope** y un **destino
para el excedente**. Encadenando dos apartados se representan los tramos:

```
Ahorro 10%  (tope 25,000)  ──desborda──▶  Excedente 5%  (sin tope)
```

Los primeros 25,000 rinden 10% y el resto 5%. No hay un concepto de "tramo" en la API:
son dos apartados conectados.

---

## 1. Campos nuevos en la respuesta de apartado

`PositionResponse` (lo devuelven crear, obtener, listar, depositar, retirar y actualizar)
trae tres campos más:

```jsonc
{
  // ...todo lo de antes, igual...
  "max_balance": 25000.00,              // null = sin tope
  "overflow_action": "TO_POSITION",     // "TO_AVAILABLE" | "TO_POSITION" | null
  "overflow_position_uuid": "770e..."   // solo con TO_POSITION
}
```

- `max_balance: null` significa **sin tope** — el apartado crece sin límite, como hasta hoy.
- `overflow_action` solo tiene valor cuando hay tope.
- El destino se identifica **por uuid**, nunca por id interno.

Un apartado a la vista con tope está "lleno" cuando `balance == max_balance`. Es el estado
normal de una cajita que ya llegó a su límite, no un error.

---

## 2. Crear un apartado con tope

`POST /api/v2/positions/` acepta un bloque `cap` **opcional**:

```jsonc
{
  "account_uuid": "550e...",
  "name": "Ahorro 10%",
  "position_type": "ON_DEMAND",
  "amount": 25000.00,
  "annual_rate": 10.00,
  "cap": {
    "max_balance": 25000.00,
    "overflow_action": "TO_AVAILABLE"    // opcional, es el default
  }
}
```

Reglas que conviene validar en el formulario antes de mandar:

| Regla | Si se rompe |
|-------|-------------|
| El tope solo aplica a `ON_DEMAND` | `409 FIXED_TERM_CAP_NOT_ALLOWED` |
| `amount` no puede superar `max_balance` | `409 POSITION_CAP_EXCEEDED` |
| `max_balance` debe ser > 0 | `400 VALIDATION_INVALID_POSITION_CAP` |
| `TO_POSITION` exige `overflow_position_uuid` | `409 INVALID_OVERFLOW_TARGET` |

> Si el usuario quiere apartar más de lo que cabe en el tope, la API **no** lo reparte
> sola: es un error de configuración. El flujo correcto es crear el apartado en el tope y
> depositar el resto después (ahí sí se desborda).

---

## 3. Endpoint nuevo: `PATCH /api/v2/positions/{position_uuid}/`

Cambia el nombre o la configuración de tope. Scope `investments:write`, 20 req/min,
devuelve un `PositionResponse` normal.

**Es el único camino para encadenar apartados.** El destino tiene que existir antes de que
otro lo apunte, así que la cadena no se puede armar solo con `POST`. El flujo de UI es:

1. Crear el apartado que recibe el excedente (ej. "Excedente 5%").
2. Crear —o ya tener— el de la tasa alta.
3. `PATCH` sobre el de la tasa alta apuntando al primero.

### ⚠️ Semántica del body: omitir ≠ mandar null

Esto es lo más fácil de romper. `cap` distingue tres intenciones:

```jsonc
{ "name": "Ahorro 10%" }                      // renombra, NO toca el tope
{ "cap": { "max_balance": 25000 } }           // pone/cambia el tope
{ "cap": null }                               // QUITA el tope y su destino
```

**Si tu formulario serializa todos los campos siempre, un simple "cambiar nombre" va a
mandar `cap: null` y le va a borrar el tope al usuario.** Manda solo las claves que el
usuario tocó, o construye el body condicionalmente.

Mandar `cap` **reemplaza el bloque completo**, no hace merge: si mandas
`{"cap": {"max_balance": 30000}}` sobre un apartado que desbordaba a otro, el destino se
pierde y vuelve a `TO_AVAILABLE`. Para conservarlo, incluye `overflow_action` y
`overflow_position_uuid` en el mismo bloque.

### Bajar el tope mueve dinero al instante

Si el tope nuevo queda por debajo del saldo actual, el excedente **sale en ese momento**:
recorre la cadena y lo que sobre entra al saldo disponible con su transacción. No espera
al proceso diario. La respuesta ya trae `balance` y `account_available_balance`
actualizados — úsalos en vez de recalcular en el cliente.

Vale la pena un diálogo de confirmación mostrando cuánto se va a mover.

---

## 4. ⚠️ Cambio de comportamiento: el depósito puede mover menos de lo que pediste

`POST /positions/{uuid}/deposit/` **no cambió de forma**, pero ahora un depósito en un
apartado con tope puede aceptar solo una parte, o nada:

| Escenario | Qué pasa realmente |
|-----------|--------------------|
| Depositas 500, caben 200, sin cadena | entran 200, **300 se quedan en el disponible** |
| Depositas 500, el apartado está lleno, sin cadena | **no se mueve nada**, no hay transacción |
| Depositas 500, caben 200, el resto va a otro apartado | salen los 500 del disponible, repartidos entre dos apartados |

**Qué hacer en el front:** no asumas que el monto depositado es el que pediste. Después de
la llamada, pinta los saldos con lo que trae la respuesta (`balance` y
`account_available_balance`) y, si `balance` no subió lo esperado, avisa al usuario a
dónde se fue el resto. Un toast del tipo *"Se apartaron 200; los otros 300 no cabían en el
tope y siguen en tu saldo disponible"* evita el reporte de bug clásico de "deposité 500 y
solo me tomó 200".

`withdraw` y `liquidate` no cambiaron nada.

---

## 5. Transacciones nuevas en el historial

Cuando el excedente cae al **saldo disponible**, se crea una transacción `TRANSFER` con
`position_id` y descripción `"Excedente del apartado {nombre}"`.

Dos consecuencias para las pantallas de movimientos:

- **Un apartado que vive en su tope genera una transacción diaria pequeña.** El tope no se
  rebasa ni un día, así que el rendimiento sale cada día. Para una cajita de 25,000 al 10%
  son unos ~6.85 diarios. Si el historial las muestra sueltas, conviene agruparlas o
  poder filtrarlas: son ruido para el usuario, no acciones suyas.
- **Mover dinero de un apartado a otro no genera transacción.** El dinero nunca pasó por
  el saldo disponible, así que no aparece en el historial. Si el usuario quiere ver ese
  movimiento, el lugar correcto es el detalle del apartado, no la lista de transacciones.

---

## 6. Proyecciones: la línea ahora se aplana

`GET /positions/{uuid}/projections/` gana campos:

```jsonc
{
  // ...
  "max_balance": 25000.00,
  "projected_overflow": 617.20,       // total que se desborda en el horizonte
  "daily_projections": [
    {
      "projection_date": "2026-08-15",
      "principal_amount": 25000.00,
      "yield_amount": 6.85,
      "projected_balance": 25000.00,  // no crece: está en el tope
      "overflow_amount": 6.85         // esto es lo que sale ese día
    }
  ]
}
```

Antes la gráfica de un apartado con tope dibujaba una curva creciente que en la realidad
nunca iba a existir. Ahora la serie `projected_balance` **se aplana en el tope**, que es lo
que de verdad va a pasar.

Sugerencia de gráfica: la meseta sola se ve como si el dinero no hiciera nada. Vale la pena
una segunda serie con `overflow_amount` (o acumularlo) para que se vea que sí está
generando, solo que el rendimiento se va a otro lado. `projected_overflow` es el número
titular: *"esta cajita te va a soltar 617 en 90 días"*.

La proyección agregada por cuenta (`/investments/{account_uuid}/projections/`) también trae
`overflow_amount` por día, ya sumado entre apartados.

---

## 7. Códigos de error nuevos

Todos con el formato de error de siempre:

| Código | HTTP | Cuándo |
|--------|------|--------|
| `POSITION_CAP_EXCEEDED` | 409 | El monto inicial supera el tope del apartado |
| `INVALID_OVERFLOW_TARGET` | 409 | El destino no existe, es de otra cuenta, no es a la vista, está liquidado, o cerraría un ciclo |
| `FIXED_TERM_CAP_NOT_ALLOWED` | 409 | Se intentó poner tope a un plazo fijo |
| `VALIDATION_INVALID_POSITION_CAP` | 400 | Tope ≤ 0, o destino de desbordamiento sin tope |

Ya vienen con mensajes en `es` y `en` según el header de idioma, igual que el resto.

---

## 8. Liquidar un apartado puede cambiar la configuración de otro

Si el usuario liquida un apartado que era **destino** de otro, los que lo apuntaban pasan
automáticamente a `TO_AVAILABLE` y reciben una notificación push. No heredan la cadena del
apartado liquidado.

**Refresca la lista de apartados después de liquidar**, no solo el que se cerró: la
respuesta de `liquidate` no incluye los apartados que se repararon, así que una UI que solo
actualice el apartado liquidado va a mostrar una configuración vieja en los otros.

---

## Lo que NO cambió

Para que no haya dudas al revisar:

- `current_balance` de la cuenta sigue siendo **solo el saldo disponible**.
- El dinero apartado sigue sin poder gastarse ni transferirse hasta regresarlo.
- Los apartados a plazo fijo se comportan exactamente igual que antes.
- Los apartados existentes quedaron **sin tope** (`max_balance: null`), o sea con el mismo
  comportamiento de siempre. Nada se migró ni cambió solo.
- Las respuestas de listar, obtener, retirar y liquidar mantienen su forma; solo ganaron
  los tres campos nuevos.

---

## Checklist sugerido

- [ ] Mostrar tope y destino en el detalle del apartado (y "lleno" cuando aplique)
- [ ] Formulario de creación con bloque `cap` opcional, solo para `ON_DEMAND`
- [ ] Pantalla de edición usando `PATCH`, **mandando solo lo que el usuario tocó**
- [ ] Flujo de encadenar: crear destino → conectar con `PATCH`
- [ ] Confirmación al bajar un tope (mueve dinero al instante)
- [ ] Depósito: pintar los saldos desde la respuesta y avisar si no cupo todo
- [ ] Gráfica de proyección con la meseta y el desbordamiento
- [ ] Manejo de los 4 códigos de error nuevos
- [ ] Refrescar la lista completa después de liquidar
- [ ] Decidir cómo mostrar (o agrupar) las transacciones diarias de excedente
