# Tests para Lunance IA

Este directorio contiene los tests automatizados de la API. La suite está escrita con
`pytest` (9.0+), `pytest-asyncio` (modo `auto`) y `httpx` (cliente ASGI en proceso para
E2E rápidos, sin tener que levantar uvicorn).

## Estructura

```
src/tests/
├── __init__.py
├── conftest.py                 # Fixtures globales: BD en memoria, usuario mock, auth dual
├── e2e/                        # Tests end-to-end (HTTP in-process)
│   ├── test_account_api.py
│   ├── test_ai_api.py
│   ├── test_api_key_api.py
│   ├── test_auth_api.py
│   ├── test_bank_api.py
│   ├── test_budget_api.py
│   ├── test_category_api.py
│   ├── test_dashboard_api.py
│   ├── test_edge_cases.py
│   ├── test_goal_api.py
│   ├── test_income_api.py
│   ├── test_installment_api.py
│   ├── test_investment_yield_api.py
│   ├── test_notification_api.py
│   ├── test_security_headers.py
│   ├── test_subscription_api.py
│   ├── test_transaction_api.py
│   └── test_transfer_api.py
├── integration/                # Tests de integración (BD real opcional)
│   ├── test_mysql_account_row_lock.py   # Requiere MYSQL_TEST_DATABASE_URL
│   └── test_real_app.py
└── unit/                       # Tests unitarios (sin red, sin BD)
    ├── test_account_repository_lock.py
    ├── test_auth_commands.py
    ├── test_auth_deps.py
    ├── application/            # Handlers / processors
    └── domain/                 # Value objects y entidades
```

## Ejecución

### Dependencias

```bash
uv sync --frozen --all-groups
uv pip install ./fincore    # necesario para tests que tocan proyecciones
```

### Suites

```bash
# Toda la suite
pytest

# Por carpeta
pytest src/tests/e2e/        -v
pytest src/tests/integration/ -v
pytest src/tests/unit/        -v

# Por marcador
pytest -m e2e        -v
pytest -m integration -v
pytest -m unit       -v
pytest -m auth       -v
pytest -m api        -v

# Por test específico
pytest src/tests/e2e/test_auth_api.py::TestAPIConnectivity -v
pytest src/tests/e2e/test_auth_api.py::TestCompleteAuthFlow -v

# Con cobertura
pytest --cov=src --cov-report=html
```

### Requisitos según el tipo de test

| Suite | API levantada | MySQL | Notas |
|---|---|---|---|
| `unit/` | No | No | Todo en memoria; ideal para CI rápido y para `git commit`. |
| `integration/` | No | Solo `test_mysql_account_row_lock.py` (lee `MYSQL_TEST_DATABASE_URL`) | El resto usa SQLite en memoria, igual que los E2E. |
| `e2e/` | No (in-process con `httpx.ASGITransport`) | No (SQLite en memoria) | El `conftest.py` levanta el `FastAPI` app y sobrescribe `get_db` y las dependencias de auth. |

> Los E2E de este repo **no** lanzan la API contra `http://127.0.0.1:8000`: hablan
> con la app por ASGI dentro del mismo proceso, usando SQLite. Eso permite que la
> suite entera corra en CI en segundos sin necesidad de un MySQL real.
> Si quieres reproducir el flujo "real" con la API ya levantada, el script
> `scripts/verify_transaction_lock.py` sirve como ejemplo de cliente HTTP externo.

### Variables de entorno de apoyo

```bash
# Solo necesarias para tests que apunten a un MySQL real (integration/test_mysql_*)
export MYSQL_TEST_DATABASE_URL="mysql+aiomysql://luna:luna_root@localhost:3306/lunance_test"

# Para clientes HTTP externos (no usados por la suite por defecto)
export TEST_API_BASE_URL="http://127.0.0.1:8000/api/v2"
export TEST_TIMEOUT=30
```

## Cobertura por área

| Área | Suite | Cobertura |
|---|---|---|
| Auth (JWT propio, dual auth API Key) | `e2e/test_auth_api.py`, `unit/test_auth_commands.py`, `unit/test_auth_deps.py` | Registro, login, refresh, logout, `/auth/me`, scopes, Auth0 fallback (legado). |
| Cuentas, transacciones, transferencias, suscripciones, presupuestos, metas, MSI, ingresos, dashboard, IA, bancos, categorías, API keys, notificaciones, edge cases, security headers | `e2e/test_*.py` | CRUD completo, enforcement de scopes, validaciones, race conditions. |
| Dominio (Money, Bank, RecurringIncome, IncomeDeposit) | `unit/domain/` | Value objects y entidades puras. |
| Handlers de aplicación (suscripciones, ingresos, MSI, cuentas, transactions) | `unit/application/` | Procesadores y casos de uso. |
| Locking pesimista (`SELECT ... FOR UPDATE`) | `unit/test_account_repository_lock.py`, `integration/test_mysql_account_row_lock.py` | Emisión de `FOR UPDATE` y verificación contra un MySQL real (cuando `MYSQL_TEST_DATABASE_URL` está definido). |

## Debugging

```bash
# Output completo con prints
pytest src/tests/e2e/test_auth_api.py -v -s

# Solo fallos, sin traceback
pytest src/tests/e2e/ --tb=no -q

# Parar en el primer fallo
pytest -x

# Repetir el último fallo
pytest --lf

# Cobertura en HTML
pytest --cov=src --cov-report=html && open htmlcov/index.html
```

## Convenciones

- Los archivos siguen el patrón `test_*.py`, las clases `Test*` y las funciones `test_*`
  (forzado por `pytest.ini`).
- Los markers `e2e`, `integration`, `unit`, `auth`, `api`, `slow` están registrados en
  `pyproject.toml` y `pytest.ini`.
- Para añadir un nuevo E2E, replica el patrón de `test_auth_api.py`: hereda de una
  clase `Test*` con `async def test_*` (no hace falta `@pytest.mark.asyncio`, está en
  modo `auto`).
- Para tests que necesiten un usuario distinto al `MOCK_USER_ID`, crea un fixture que
  inserte otra fila en `users` antes del request.
