"""
Скрипт для создания таблицы order_reports в базе данных city2
"""
import asyncio
import os
import sys
from pathlib import Path

# Добавляем путь к проекту в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import aiosqlite
from dotenv import load_dotenv

# Загружаем переменные окружения для city2
load_dotenv("env.city2")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/city2/bot_database.db")

# Создаем директорию, если её нет
db_path = Path(DATABASE_PATH)
db_path.parent.mkdir(parents=True, exist_ok=True)


async def create_order_reports_table():
    """Создает таблицу order_reports если её нет"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем, существует ли таблица
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='order_reports'"
        )
        table_exists = await cursor.fetchone()

        if table_exists:
            print(f"[SKIP] Таблица order_reports уже существует в {DATABASE_PATH}")
            return

        # Создаем таблицу
        await db.execute("""
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
        """)

        await db.commit()
        print(f"[OK] Таблица order_reports создана в {DATABASE_PATH}")


async def main():
    """Главная функция"""
    try:
        await create_order_reports_table()
        print("[OK] Миграция завершена успешно")
    except Exception as e:
        print(f"[ERROR] Ошибка при создании таблицы: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
