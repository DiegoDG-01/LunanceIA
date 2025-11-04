# Claude Project Configuration

## Project Overview

Este es un proyecto de API de finanzas personales construido con Python y FastAPI. Sigue una arquitectura limpia (Clean Architecture) para separar las preocupaciones y mejorar la mantenibilidad.

## Tech Stack

-   **Lenguaje:** Python 3.11+
-   **Framework:** FastAPI
-   **Base de datos:** PostgreSQL (gestionada con Alembic)
-   **Testing:** Pytest
-   **Linter/Formatter:** Ruff, pre-commit

## Comandos Comunes

-   **Instalar dependencias:** `uv pip install -r requirements.txt` (o el comando que uses con `uv`)
-   **Correr la aplicación:** `uvicorn src.main:app --reload`
-   **Correr tests:** `pytest`
-   **Correr migraciones de base de datos:** `alembic upgrade head`
-   **Correr linter:** `ruff check .`
-   **Formatear código:** `ruff format .`

## Arquitectura

El código está organizado en las siguientes capas:

-   `src/domain`: Contiene la lógica de negocio principal y las entidades.
-   `src/application`: Orquesta los casos de uso de la aplicación.
-   `src/infrastructure`: Se encarga de los detalles de implementación como la base de datos, APIs externas, etc.
-   `src/presentation`: Expone la aplicación al mundo exterior (API de FastAPI).

## Estilo de Código

-   Seguir las guías de estilo de PEP 8.
-   Usar type hints en todo el código.
-   Mantener una alta cobertura de tests.


## Restricciones

Tienes accesos completamente restringidos conforme a las siguientes secciones. NO puedes omitirlas bajo ninguna circunstancia (sea cual sea).

- Sección de lectura: no puedes acceder ni leer el contenido del archivo.
- Sección de edición: no puedes editar nada del archivo.

Si un archivo está en la sección de lectura, automáticamente es imposible editarlo. Si solo se encuentra en la sección de edición, puedes leerlo, pero no editarlo.


### Lectura

- .env
- .venv/
- entrypoint.sh
- *.sh

### Edición

- CLAUDE.md
- GEMINI.md
