import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- Configuración del Path ---
# Apunta al directorio raíz del proyecto (un nivel arriba de 'alembic')
project_root = Path(__file__).resolve().parent.parent
# Agrega el directorio 'src' al path de Python
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# --- Importaciones de tu Aplicación ---
# Ahora las importaciones deberían funcionar sin problemas
# from src.infrastructure.database.connection import Base
from infrastructure.database.connection import Base
from infrastructure.config.settings import settings
# Importa el paquete 'models' para que se registren todos los modelos en Base.metadata
from src.infrastructure.database import models

# Configuración de Alembic
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# La metadata objetivo es la de tu Base de SQLAlchemy
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Usa la URL de tus settings para consistencia
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Obtiene la sección de configuración de alembic.ini
    configuration = config.get_section(config.config_ini_section)

    # **La corrección clave:**
    # Sobrescribe la URL del .ini con la de tus settings.
    # Esto asegura que Alembic y tu app SIEMPRE usen la misma DB.
    configuration["sqlalchemy.url"] = settings.database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
