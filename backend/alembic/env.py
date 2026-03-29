import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Make sure backend/ is on sys.path so models can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import Base

# Import all models so Alembic picks them up for autogenerate
import auth.models       # noqa: F401
import companies.models  # noqa: F401
import knowledge.models  # noqa: F401
import analytics.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from environment if set
database_url = os.getenv("DATABASE_URL", "")
# Alembic needs sync driver — replace asyncpg with psycopg2
if database_url:
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
