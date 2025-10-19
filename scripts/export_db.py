"""
Скрипт для экспорта базы данных SQLite в JSON
Использование: python export_db.py [--output <filename>]
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path


def export_database(db_path: str = "bot_database.db", output_path: str = None) -> str:
    """
    Экспорт данных из SQLite в JSON

    Args:
        db_path: Путь к файлу базы данных
        output_path: Путь для сохранения JSON (опционально)

    Returns:
        Путь к созданному файлу
    """

    # Проверка существования БД
    if not Path(db_path).exists():
        raise FileNotFoundError(f"База данных не найдена: {db_path}")

    # Подключение к БД
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    export_data = {
        "export_date": datetime.now().isoformat(),
        "database_path": db_path,
        "tables": {},
        "metadata": {},
    }

    # Получение списка таблиц
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    tables = [row[0] for row in cursor.fetchall()]

    print(f"📊 Найдено таблиц: {len(tables)}")

    # Экспорт данных каждой таблицы
    total_rows = 0
    for table in tables:
        print(f"  📋 Экспорт таблицы: {table}...", end=" ")

        # Получение схемы таблицы
        cursor.execute(f"PRAGMA table_info({table})")
        schema = cursor.fetchall()
        export_data["metadata"][table] = {
            "columns": [
                {"name": col[1], "type": col[2], "notnull": bool(col[3]), "pk": bool(col[5])}
                for col in schema
            ]
        }

        # Экспорт данных
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        export_data["tables"][table] = [dict(row) for row in rows]

        total_rows += len(rows)
        print(f"✅ ({len(rows)} строк)")

    conn.close()

    # Формирование имени файла
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"db_export_{timestamp}.json"

    # Сохранение в JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

    # Информация о размере
    file_size = Path(output_path).stat().st_size / 1024  # KB
    db_size = Path(db_path).stat().st_size / 1024  # KB

    print()
    print("✅ Экспорт завершен успешно!")
    print(f"  📁 Файл: {output_path}")
    print(f"  📊 Таблиц: {len(tables)}")
    print(f"  📝 Всего строк: {total_rows}")
    print(f"  💾 Размер БД: {db_size:.2f} KB")
    print(f"  💾 Размер JSON: {file_size:.2f} KB")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Экспорт базы данных SQLite в JSON")

    parser.add_argument(
        "--database",
        "-d",
        type=str,
        default="bot_database.db",
        help="Путь к файлу базы данных (по умолчанию: bot_database.db)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Путь для сохранения JSON (по умолчанию: db_export_<timestamp>.json)",
    )

    args = parser.parse_args()

    try:
        export_database(args.database, args.output)
    except FileNotFoundError as e:
        print(f"❌ Ошибка: {e}")
        return 1
    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
