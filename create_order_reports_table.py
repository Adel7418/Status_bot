#!/usr/bin/env python3
"""
Скрипт для создания таблицы order_reports в базе данных
Использование:
    python create_order_reports_table.py --db-path data/city2/bot_database.db
    python create_order_reports_table.py --db-path data/bot_database.db
"""
import argparse
import sqlite3
import sys
from pathlib import Path


def create_order_reports_table(db_path: str) -> bool:
    """Создает таблицу order_reports если её нет"""
    db_path_obj = Path(db_path)

    if not db_path_obj.exists():
        print(f"❌ Файл базы данных не найден: {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path_obj))
        cursor = conn.cursor()

        # Проверяем существование таблицы
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='order_reports'
        """
        )

        if cursor.fetchone():
            print(f"✅ Таблица order_reports уже существует в {db_path}")
            conn.close()
            return True

        # Создаем таблицу
        cursor.execute(
            """
            CREATE TABLE order_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                equipment_type VARCHAR(255) NOT NULL,
                client_name VARCHAR(255) NOT NULL,
                client_address VARCHAR(500),
                master_id INTEGER,
                master_name VARCHAR(255),
                dispatcher_id INTEGER,
                dispatcher_name VARCHAR(255),
                total_amount REAL DEFAULT 0.0,
                materials_cost REAL DEFAULT 0.0,
                master_profit REAL DEFAULT 0.0,
                company_profit REAL DEFAULT 0.0,
                out_of_city INTEGER DEFAULT 0,
                has_review INTEGER DEFAULT 0,
                created_at DATETIME,
                closed_at DATETIME,
                completion_time_hours REAL
            )
        """
        )

        conn.commit()
        conn.close()

        print(f"✅ Таблица order_reports успешно создана в {db_path}")
        return True

    except Exception as e:
        print(f"❌ Ошибка при создании таблицы order_reports: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Создание таблицы order_reports")
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/city2/bot_database.db",
        help="Путь к файлу базы данных (по умолчанию: data/city2/bot_database.db)",
    )

    args = parser.parse_args()

    if create_order_reports_table(args.db_path):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
