"""
Скрипт для очистки временных таблиц Alembic для city1
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

async def cleanup_temp_tables():
    """Удаляет временные таблицы Alembic (с префиксом _alembic_tmp_)"""
    conn = None
    try:
        conn = await aiosqlite.connect(DATABASE_PATH)
        cursor = await conn.cursor()

        # Получаем список всех таблиц
        await cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '_alembic_tmp_%'")
        temp_tables = await cursor.fetchall()

        if temp_tables:
            print(f"[INFO] Найдено {len(temp_tables)} временных таблиц Alembic:")
            for table in temp_tables:
                table_name = table[0]
                print(f"  - {table_name}")
            
            # Удаляем каждую временную таблицу
            for table in temp_tables:
                table_name = table[0]
                try:
                    await cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                    print(f"[OK] Удалена временная таблица: {table_name}")
                except Exception as e:
                    print(f"[WARN] Не удалось удалить таблицу {table_name}: {e}")
            
            await conn.commit()
            print(f"[OK] Очистка завершена. Удалено {len(temp_tables)} временных таблиц")
        else:
            print("[SKIP] Временные таблицы Alembic не найдены")

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
        await cleanup_temp_tables()
        print("[OK] Проверка завершена")
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

