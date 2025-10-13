"""
Скрипт для импорта базы данных из JSON в SQLite
Использование: python import_db.py <json_file> [--database <db_file>]
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path


def import_database(json_path: str, db_path: str = "bot_database.db", clear_existing: bool = False) -> None:
    """
    Импорт данных из JSON в SQLite

    Args:
        json_path: Путь к JSON файлу с экспортом
        db_path: Путь к файлу базы данных
        clear_existing: Очистить существующие данные перед импортом
    """

    # Проверка существования JSON файла
    if not Path(json_path).exists():
        raise FileNotFoundError(f"JSON файл не найден: {json_path}")

    # Чтение JSON
    print(f"📖 Чтение JSON файла: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  📅 Дата экспорта: {data.get('export_date', 'неизвестно')}")
    print(f"  📊 Таблиц в экспорте: {len(data['tables'])}")

    # Подключение к БД
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Получение списка существующих таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    existing_tables = set(row[0] for row in cursor.fetchall())

    # Импорт данных
    total_rows = 0
    skipped_tables = []

    for table_name, rows in data["tables"].items():
        if not rows:
            print(f"  ⏭️  Таблица {table_name}: пропущена (нет данных)")
            skipped_tables.append(table_name)
            continue

        # Проверка существования таблицы
        if table_name not in existing_tables:
            print(f"  ⚠️  Таблица {table_name}: не существует в БД (пропущена)")
            skipped_tables.append(table_name)
            continue

        print(f"  📋 Импорт таблицы: {table_name}...", end=" ")

        # Очистка таблицы если требуется
        if clear_existing:
            cursor.execute(f"DELETE FROM {table_name}")

        # Получение колонок
        columns = list(rows[0].keys())
        placeholders = ",".join(["?" for _ in columns])
        columns_str = ",".join(columns)

        # Вставка данных
        inserted = 0
        errors = 0

        for row in rows:
            values = [row.get(col) for col in columns]
            try:
                cursor.execute(f"INSERT OR REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})", values)
                inserted += 1
            except sqlite3.Error as e:
                errors += 1
                if errors <= 3:  # Показать только первые 3 ошибки
                    print(f"\n    ⚠️  Ошибка при вставке: {e}")

        total_rows += inserted
        print(f"✅ ({inserted} строк, ошибок: {errors})")

    # Сохранение изменений
    conn.commit()
    conn.close()

    # Итоговая информация
    print()
    print("✅ Импорт завершен успешно!")
    print(f"  📁 База данных: {db_path}")
    print(f"  📊 Импортировано таблиц: {len(data['tables']) - len(skipped_tables)}")
    print(f"  📝 Всего строк: {total_rows}")
    if skipped_tables:
        print(f"  ⏭️  Пропущено таблиц: {len(skipped_tables)} ({', '.join(skipped_tables)})")

    # Размер БД
    db_size = Path(db_path).stat().st_size / 1024  # KB
    print(f"  💾 Размер БД: {db_size:.2f} KB")


def main():
    parser = argparse.ArgumentParser(description="Импорт базы данных из JSON в SQLite")

    parser.add_argument("json_file", type=str, help="Путь к JSON файлу с экспортом")

    parser.add_argument(
        "--database", "-d", type=str, default="bot_database.db", help="Путь к файлу базы данных (по умолчанию: bot_database.db)"
    )

    parser.add_argument(
        "--clear",
        "-c",
        action="store_true",
        help="Очистить существующие данные в таблицах перед импортом",
    )

    parser.add_argument(
        "--backup",
        "-b",
        action="store_true",
        help="Создать резервную копию БД перед импортом",
    )

    args = parser.parse_args()

    # Создание backup если требуется
    if args.backup and Path(args.database).exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{args.database}.backup_{timestamp}"
        import shutil

        shutil.copy2(args.database, backup_path)
        print(f"💾 Создана резервная копия: {backup_path}")
        print()

    try:
        import_database(args.json_file, args.database, args.clear)
    except FileNotFoundError as e:
        print(f"❌ Ошибка: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка чтения JSON: {e}")
        return 1
    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

