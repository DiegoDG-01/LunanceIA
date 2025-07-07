import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Configurar el path para que apunte a src
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Ahora tanto 'config' como 'models' deberían ser importables
from src.infrastructure.database.connection import Base
from src.infrastructure.database.connection import engine
from src.infrastructure.config.settings import settings

# Importar todos los modelos para que Alembic los detecte
from src.infrastructure.database.models.user import UserModel
from src.infrastructure.database.models.account import AccountModel
from src.infrastructure.database.models.transaction import TransactionModel
from src.infrastructure.database.models.category import CategoryModel
from src.infrastructure.database.models.subscription import SubscriptionModel
from src.infrastructure.database.models.subscription import SubscriptionChargeModel
from src.infrastructure.database.models.saving_goal import SavingGoalModel
from src.infrastructure.database.models.budget import BudgetModel
from src.infrastructure.database.models.tag import TagModel
from src.infrastructure.database.models.reminder import ReminderModel

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
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
    connectable = engine  # Cambiado de engine_from_config(...)

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