"""
Скрипт для создания таблицы specialization_rates для city1
"""

import asyncio
import os
import sys
import aiosqlite
from dotenv import load_dotenv

# Сначала проверяем переменную окружения DATABASE_PATH (для Docker)
# Если не установлена, загружаем из .env файла
DATABASE_PATH = os.getenv("DATABASE_PATH")
if not DATABASE_PATH:
    load_dotenv("env.city1")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/city1/bot_database.db")


async def create_specialization_rates_table():
    """Создает таблицу specialization_rates, если она не существует"""
    conn = None
    try:
        conn = await aiosqlite.connect(DATABASE_PATH)
        cursor = await conn.cursor()

        # Проверяем, существует ли таблица
        await cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='specialization_rates'"
        )
        table_exists = await cursor.fetchone()

        if table_exists:
            print(f"[SKIP] Таблица specialization_rates уже существует в {DATABASE_PATH}")
            return

        # Создаем таблицу specialization_rates
        await cursor.execute(
            """
            CREATE TABLE specialization_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                specialization_name VARCHAR(255) NOT NULL UNIQUE,
                master_percentage REAL NOT NULL DEFAULT 50.0,
                company_percentage REAL NOT NULL DEFAULT 50.0,
                is_default INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted_at DATETIME,
                CHECK (master_percentage >= 0 AND master_percentage <= 100),
                CHECK (company_percentage >= 0 AND company_percentage <= 100),
                CHECK (master_percentage + company_percentage = 100)
            )
        """
        )

        # Создаем индекс
        await cursor.execute(
            """
            CREATE INDEX idx_specialization_rates_name ON specialization_rates(specialization_name)
        """
        )

        # Вставляем начальные данные
        await cursor.execute(
            """
            INSERT INTO specialization_rates (specialization_name, master_percentage, company_percentage, is_default)
            VALUES ('электрик', 50.0, 50.0, 0)
        """
        )
        await cursor.execute(
            """
            INSERT INTO specialization_rates (specialization_name, master_percentage, company_percentage, is_default)
            VALUES ('сантехник', 50.0, 50.0, 0)
        """
        )

        await conn.commit()
        print(f"[OK] Таблица specialization_rates создана в {DATABASE_PATH}")
        print(f"[OK] Добавлены начальные данные: электрик и сантехник - 50/50")

    except Exception as e:
        print(f"[ERROR] Ошибка при работе с базой данных: {e}")
        if conn:
            await conn.rollback()
        raise
    finally:
        if conn:
            await conn.close()


async def main():
    """Главная функция"""
    try:
        await create_specialization_rates_table()
        print("[OK] Миграция завершена успешно")
    except Exception as e:
        print(f"[ERROR] Ошибка при создании таблицы: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
