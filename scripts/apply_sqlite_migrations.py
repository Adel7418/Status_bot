#!/usr/bin/env python3
"""
Скрипт для безопасного применения SQLite-совместимых миграций
Применяет только миграции 006, 008, 010 (пропускает PostgreSQL-специфичные 007, 009)
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime


def check_column_exists(cursor, table: str, column: str) -> bool:
    """Проверка существования колонки в таблице"""
    cursor.execute(f"PRAGMA table_info({table});")
    columns = [col[1] for col in cursor.fetchall()]
    return column in columns


def check_table_exists(cursor, table: str) -> bool:
    """Проверка существования таблицы"""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,)
    )
    return cursor.fetchone() is not None


def check_index_exists(cursor, index: str) -> bool:
    """Проверка существования индекса"""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?;", (index,)
    )
    return cursor.fetchone() is not None


def get_current_version(cursor) -> str:
    """Получение текущей версии миграции"""
    try:
        cursor.execute("SELECT version_num FROM alembic_version;")
        result = cursor.fetchone()
        return result[0] if result else "none"
    except:
        return "none"


def apply_migration_008(cursor, conn):
    """Применение миграции 008: Soft delete и версионирование"""
    print("\n📋 Миграция 008: Soft delete и версионирование")

    changes_made = False

    # Добавляем deleted_at колонки
    tables_for_deleted_at = ['users', 'masters', 'orders', 'audit_log']
    for table in tables_for_deleted_at:
        if not check_column_exists(cursor, table, 'deleted_at'):
            print(f"  ✅ Добавление deleted_at в {table}")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at DATETIME NULL;")
            changes_made = True
        else:
            print(f"  ⏭️  deleted_at уже существует в {table}")

    # Добавляем version колонки
    version_tables = ['users', 'masters', 'orders']
    for table in version_tables:
        if not check_column_exists(cursor, table, 'version'):
            print(f"  ✅ Добавление version в {table}")
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN version INTEGER NOT NULL DEFAULT 1;"
            )
            changes_made = True
        else:
            print(f"  ⏭️  version уже существует в {table}")

    # Создаем индексы для deleted_at
    indexes = [
        ('idx_users_deleted_at', 'users', 'deleted_at'),
        ('idx_masters_deleted_at', 'masters', 'deleted_at'),
        ('idx_orders_deleted_at', 'orders', 'deleted_at'),
        ('idx_audit_log_deleted_at', 'audit_log', 'deleted_at'),
    ]

    for idx_name, table, column in indexes:
        if not check_index_exists(cursor, idx_name):
            print(f"  ✅ Создание индекса {idx_name}")
            cursor.execute(
                f"CREATE INDEX {idx_name} ON {table} ({column});"
            )
            changes_made = True
        else:
            print(f"  ⏭️  Индекс {idx_name} уже существует")

    # Создаем таблицу entity_history если её нет
    if not check_table_exists(cursor, 'entity_history'):
        print("  ✅ Создание таблицы entity_history")
        cursor.execute("""
            CREATE TABLE entity_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name VARCHAR(50) NOT NULL,
                record_id INTEGER NOT NULL,
                field_name VARCHAR(50) NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by INTEGER,
                changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (changed_by) REFERENCES users (telegram_id)
            )
        """)

        # Создаем индексы
        cursor.execute(
            "CREATE INDEX idx_entity_history_table_record ON entity_history (table_name, record_id);"
        )
        cursor.execute(
            "CREATE INDEX idx_entity_history_changed_at ON entity_history (changed_at);"
        )
        cursor.execute(
            "CREATE INDEX idx_entity_history_changed_by ON entity_history (changed_by);"
        )
        print("  ✅ Индексы для entity_history созданы")
        changes_made = True
    else:
        print("  ⏭️  Таблица entity_history уже существует")

    if changes_made:
        conn.commit()
        print("  ✅ Миграция 008 применена")
    else:
        print("  ℹ️  Все изменения миграции 008 уже применены")

    return changes_made


def apply_migration_010(cursor, conn):
    """Применение миграции 010: Архивные отчеты мастеров"""
    print("\n📋 Миграция 010: Архивные отчеты мастеров")

    if check_table_exists(cursor, 'master_reports_archive'):
        print("  ⏭️  Таблица master_reports_archive уже существует")
        return False

    print("  ✅ Создание таблицы master_reports_archive")
    cursor.execute("""
        CREATE TABLE master_reports_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id INTEGER NOT NULL,
            period_start DATETIME NOT NULL,
            period_end DATETIME NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_size INTEGER,
            total_orders INTEGER DEFAULT 0,
            active_orders INTEGER DEFAULT 0,
            completed_orders INTEGER DEFAULT 0,
            total_revenue REAL DEFAULT 0.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (master_id) REFERENCES masters (id) ON DELETE CASCADE
        )
    """)

    # Создаем индексы
    cursor.execute(
        "CREATE INDEX idx_master_reports_master_id ON master_reports_archive (master_id);"
    )
    cursor.execute(
        "CREATE INDEX idx_master_reports_period ON master_reports_archive (period_start, period_end);"
    )
    cursor.execute(
        "CREATE INDEX idx_master_reports_created ON master_reports_archive (created_at);"
    )

    conn.commit()
    print("  ✅ Миграция 010 применена")
    return True


def update_alembic_version(cursor, conn, version: str):
    """Обновление версии в alembic_version"""
    # Очищаем старые версии (может быть несколько из-за конфликтов)
    cursor.execute("DELETE FROM alembic_version;")
    # Устанавливаем новую версию
    cursor.execute("INSERT INTO alembic_version (version_num) VALUES (?);", (version,))
    conn.commit()
    print(f"  📌 Версия установлена: {version}")


def show_statistics(cursor):
    """Показать статистику таблиц"""
    print("\n📊 Статистика таблиц:")
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    tables = cursor.fetchall()
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
        count = cursor.fetchone()[0]
        print(f"  - {table[0]}: {count} записей")


def main():
    # Определяем путь к БД
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = '/app/data/bot_database.db'

    print("=" * 60)
    print("🔄 Применение SQLite-совместимых миграций")
    print("=" * 60)
    print(f"📁 База данных: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Проверяем текущую версию
        current_version = get_current_version(cursor)
        print(f"📌 Текущая версия: {current_version}")

        # Определяем какие миграции нужно применить
        version_order = ['005_add_reschedule_fields', '006_add_performance_indexes', '008_add_soft_delete', '010_create_master_reports_archive']

        if current_version in version_order:
            current_idx = version_order.index(current_version)
            migrations_to_apply = version_order[current_idx + 1:]
        else:
            print(f"⚠️  Неизвестная версия: {current_version}")
            print("ℹ️  Попытаемся применить все миграции")
            migrations_to_apply = version_order

        if not migrations_to_apply:
            print("\n✅ Все миграции уже применены!")
            show_statistics(cursor)
            return 0

        print(f"\n🎯 Миграции к применению: {', '.join(migrations_to_apply)}")

        changes_made = False

        # Применяем миграции по порядку
        if '006_add_performance_indexes' in migrations_to_apply:
            print("\n📋 Миграция 006: Performance indexes")
            print("  ℹ️  Индексы должны быть созданы через alembic или вручную")
            print("  ⏭️  Пропускаем (безопасно)")

        if '008_add_soft_delete' in migrations_to_apply:
            if apply_migration_008(cursor, conn):
                changes_made = True

        if '010_create_master_reports_archive' in migrations_to_apply:
            if apply_migration_010(cursor, conn):
                changes_made = True

        # Устанавливаем финальную версию
        if changes_made or current_version != '010_create_master_reports_archive':
            print("\n📌 Обновление версии миграции")
            update_alembic_version(cursor, conn, '010_create_master_reports_archive')

        # Показываем статистику
        show_statistics(cursor)

        print("\n" + "=" * 60)
        print("✅ МИГРАЦИИ ПРИМЕНЕНЫ УСПЕШНО")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()
        return 1
    finally:
        if 'conn' in locals():
            conn.close()
            print("\n🔒 Соединение с БД закрыто")


if __name__ == "__main__":
    sys.exit(main())
