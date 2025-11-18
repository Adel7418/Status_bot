#!/usr/bin/env python3
"""
Скрипт для применения миграции refuse_reason

Добавляет колонку refuse_reason в таблицу orders для хранения причин отказа
"""

import sqlite3
import sys
from pathlib import Path


def check_column_exists(db_path: str, table: str, column: str) -> bool:
    """Проверяет существование колонки в таблице"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]

    conn.close()
    return column in columns


def add_refuse_reason_column(db_path: str) -> None:
    """Добавляет колонку refuse_reason в таблицу orders"""

    # Проверяем существование файла БД
    if not Path(db_path).exists():
        print(f"❌ База данных не найдена: {db_path}")
        return

    print(f"📂 Работаем с базой данных: {db_path}")

    # Проверяем существование колонки
    if check_column_exists(db_path, "orders", "refuse_reason"):
        print("✅ Колонка 'refuse_reason' уже существует в таблице orders")
        print("   Миграция не требуется.")
        return

    # Добавляем колонку
    print("📝 Добавляем колонку 'refuse_reason' в таблицу orders...")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Создаем backup
        print("💾 Создаем бэкап...")
        backup_path = f"{db_path}.backup_before_refuse_reason"
        import shutil

        shutil.copy2(db_path, backup_path)
        print(f"   Бэкап сохранен: {backup_path}")

        # Добавляем колонку
        cursor.execute(
            """
            ALTER TABLE orders
            ADD COLUMN refuse_reason VARCHAR(500)
        """
        )

        conn.commit()
        conn.close()

        # Проверяем результат
        if check_column_exists(db_path, "orders", "refuse_reason"):
            print("✅ Колонка 'refuse_reason' успешно добавлена!")
            print("   Теперь можно использовать функционал причин отказа.")
        else:
            print("❌ Ошибка: колонка не была добавлена")

    except Exception as e:
        print(f"❌ Ошибка при добавлении колонки: {e}")
        print("   Восстановите базу данных из бэкапа если необходимо")
        sys.exit(1)


def main():
    """Основная функция"""

    print("=" * 60)
    print("🔧 Миграция: Добавление поля refuse_reason")
    print("=" * 60)
    print()

    # Определяем пути к базам данных
    databases = [
        "data/bot_database.db",
        "data/city1/bot_database.db",
        "data/city2/bot_database.db",
        "bot_database.db",  # Если запускается из корня
    ]

    # Фильтруем только существующие базы
    existing_dbs = [db for db in databases if Path(db).exists()]

    if not existing_dbs:
        print("❌ Не найдено ни одной базы данных!")
        print("   Проверьте пути:")
        for db in databases:
            print(f"   - {db}")
        sys.exit(1)

    print(f"Найдено баз данных: {len(existing_dbs)}")
    print()

    # Применяем миграцию для каждой БД
    for db_path in existing_dbs:
        add_refuse_reason_column(db_path)
        print()

    print("=" * 60)
    print("✅ Миграция завершена!")
    print("=" * 60)
    print()
    print("📋 Следующие шаги:")
    print("   1. Перезапустите бота")
    print("   2. Протестируйте функционал отказа с причиной")
    print("   3. Проверьте статистику в админ-панели")
    print()


if __name__ == "__main__":
    main()
