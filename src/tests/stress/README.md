# Pruebas de Estrés con Locust

## Requisitos

- Python 3.13+
- Locust instalado (`uv sync` para instalar dependencias de desarrollo)
- Token JWT válido de Auth0

## Obtener Token de Auth0

1. Inicia sesión en la aplicación cliente o usa la API de Auth0 directamente
2. Copia el `access_token` del response de autenticación
3. Expórtalo como variable de entorno:
   ```bash
   export LOCUST_AUTH_TOKEN="eyJhbGciOi..."
   ```

## Ejecución

### Con Web UI (desarrollo)

```bash
LOCUST_AUTH_TOKEN="tu-token" locust -f src/tests/stress/locustfile.py
```

Abre `http://localhost:8089` en tu navegador y configura:
- **Number of users**: Cantidad total de usuarios simulados
- **Spawn rate**: Usuarios creados por segundo
- **Host**: URL de la API (por defecto `http://localhost:8000`)

### Headless (CI/CD)

```bash
LOCUST_AUTH_TOKEN="tu-token" locust -f src/tests/stress/locustfile.py \
  --headless -u 50 -r 5 --run-time 60s --host http://localhost:8000
```

| Parámetro      | Descripción                        |
| -------------- | ---------------------------------- |
| `-u 50`        | 50 usuarios concurrentes           |
| `-r 5`         | 5 usuarios nuevos por segundo      |
| `--run-time`   | Duración total de la prueba        |
| `--host`       | URL base de la API                 |

### Ejemplos de configuración

| Escenario      | Usuarios | Spawn Rate | Duración |
| -------------- | -------- | ---------- | -------- |
| Smoke test     | 5        | 1          | 30s      |
| Carga normal   | 50       | 5          | 2m       |
| Estrés         | 200      | 10         | 5m       |
| Pico de carga  | 500      | 20         | 5m       |

## Endpoints cubiertos

| Endpoint                    | Método | Peso | Descripción              |
| --------------------------- | ------ | ---- | ------------------------ |
| `/api/v2/auth/me`           | GET    | 1    | Info del usuario         |
| `/api/v2/account/`          | GET    | 3    | Listar cuentas           |
| `/api/v2/account/`          | POST   | 1    | Crear cuenta             |
| `/api/v2/account/{uuid}`    | GET    | 1    | Obtener cuenta           |
| `/api/v2/transaction/`      | GET    | 5    | Listar transacciones     |
| `/api/v2/transaction/`      | POST   | 2    | Crear transacción        |
| `/api/v2/dashboard/`        | GET    | 3    | Resumen del dashboard    |
| `/api/v2/subscription/`     | GET    | 2    | Listar suscripciones     |

## Notas

- Los UUIDs de cuentas creadas durante la prueba se reutilizan en GETs y transacciones
- Los tasks de `get_account` y `create_transaction` se omiten si aún no hay cuentas creadas
- El host por defecto es `http://localhost:8000`, configurable con `--host`
