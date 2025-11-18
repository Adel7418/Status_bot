"""
Скрипт для исправления записи в таблице alembic_version для city1
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


async def fix_alembic_version():
    """Исправляет запись в таблице alembic_version"""
    conn = None
    try:
        conn = await aiosqlite.connect(DATABASE_PATH)
        cursor = await conn.cursor()

        # Проверяем, существует ли таблица alembic_version
        await cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        )
        table_exists = await cursor.fetchone()

        if not table_exists:
            print(f"[SKIP] Таблица alembic_version не существует в {DATABASE_PATH}")
            print("[INFO] Это нормально для новой базы данных")
            return

        # Проверяем текущую запись
        await cursor.execute("SELECT version_num FROM alembic_version")
        current_version = await cursor.fetchone()

        if current_version:
            print(f"[INFO] Текущая ревизия в базе данных: {current_version[0]}")

            # Проверяем, является ли ревизия '004' (неправильная)
            if current_version[0] == "004":
                print("[WARN] Обнаружена неправильная ревизия '004'")
                print("[INFO] Удаляем запись, чтобы Alembic мог определить правильную ревизию")
                await cursor.execute("DELETE FROM alembic_version")
                await conn.commit()
                print(
                    "[OK] Запись удалена. Используйте 'alembic stamp head' для установки правильной ревизии"
                )
            else:
                print(f"[OK] Ревизия '{current_version[0]}' корректна")
        else:
            print("[INFO] Таблица alembic_version пуста")

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
        await fix_alembic_version()
        print("[OK] Проверка завершена")
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
