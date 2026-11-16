"""`alembic/env.py` importa los modelos como `src.infrastructure.database.models`.

Si un modelo importa a otro con la ruta sin `src.`, Python carga el paquete dos veces con
nombres distintos y SQLAlchemy ve cada tabla definida dos veces: todo `alembic upgrade` falla
(también el del entrypoint de Docker), aunque la app y las pruebas funcionen. Se prueba en un
proceso aparte, con las mismas importaciones que `env.py`.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LIKE_ALEMBIC_ENV = """
import sys
sys.path.insert(0, "src")
from infrastructure.database.connection import Base
from src.infrastructure.database import models
assert "accounts" in Base.metadata.tables
"""


@pytest.mark.unit
def test_models_import_like_alembic_env():
    result = subprocess.run(
        [sys.executable, "-c", LIKE_ALEMBIC_ENV],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr[-2000:]
