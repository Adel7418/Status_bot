"""
Alembic environment configuration for SQLite
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Устанавливаем URL базы данных из конфигурации
config.set_main_option('sqlalchemy.url', f'sqlite:///{Config.DATABASE_PATH}')

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# Импортируем ORM модели для автогенерации миграций
from app.database.orm_models import Base
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_name(name, type_, parent_names):
    """Фильтр для игнорирования некоторых объектов при автогенерации"""
    # Игнорируем временные таблицы Alembic
    if type_ == "table" and name.startswith("_alembic"):
        return False
    return True


def include_object(object, name, type_, reflected, compare_to):
    """Фильтр для игнорирования некоторых изменений при автогенерации"""
    # Игнорируем изменения внешних ключей в SQLite (они часто без имен)
    if type_ == "foreign_key_constraint":
        return False
    return True


def process_revision_directives(context, revision, directives):
    """
    Постобработка директив миграции для фильтрации ненужных операций.
    Для SQLite игнорируем:
    1. modify_nullable - PRIMARY KEY всегда NOT NULL, колонки с server_default безопасны
    2. remove_fk/add_fk - внешние ключи часто создаются без имен в SQLite
    """
    if directives and directives[0].upgrade_ops:
        script = directives[0]

        def op_tag(op) -> str | None:
            to_diff = getattr(op, "to_diff_tuple", None)
            if callable(to_diff):
                try:
                    diff = to_diff()
                except Exception:
                    return None
                if isinstance(diff, tuple) and diff:
                    return diff[0]
                if isinstance(diff, list) and diff and isinstance(diff[0], tuple):
                    return diff[0][0]
            return None

        def should_drop(op) -> bool:
            tag = op_tag(op)
            return tag in {"modify_nullable", "remove_fk", "add_fk"}

        def filter_ops(container):
            if not hasattr(container, "ops"):
                return
            new_ops = []
            for child in list(container.ops):
                if hasattr(child, "ops"):
                    filter_ops(child)
                    if getattr(child, "ops", None):
                        new_ops.append(child)
                    continue
                if should_drop(child):
                    continue
                new_ops.append(child)
            container.ops = new_ops

        filter_ops(script.upgrade_ops)

        if not getattr(script.upgrade_ops, "ops", None):
            directives[:] = []


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Важно для SQLite при ALTER TABLE
        compare_type=False,  # Игнорировать изменения типов для SQLite
        compare_server_default=False,  # Игнорировать изменения server_default
        include_name=include_name,  # Фильтр имен
        include_object=include_object,  # Фильтр объектов
        process_revision_directives=process_revision_directives,  # Постобработка директив
        compare_nullable=False,  # Игнорировать изменения nullable для SQLite
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Важно для SQLite при ALTER TABLE
            compare_type=False,  # Игнорировать изменения типов для SQLite
            compare_server_default=False,  # Игнорировать изменения server_default
            include_name=include_name,  # Фильтр имен
            include_object=include_object,  # Фильтр объектов
            process_revision_directives=process_revision_directives,  # Постобработка директив
            compare_nullable=False,  # Игнорировать изменения nullable для SQLite
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
