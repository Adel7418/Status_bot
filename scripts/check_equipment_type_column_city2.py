"""
Скрипт для проверки наличия колонки equipment_type в таблице orders (city2)
"""
import asyncio
import os
import sys
import aiosqlite
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv("env.city2")

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/city2/bot_database.db")

async def check_equipment_type_column():
    """Проверяет наличие колонки equipment_type в таблице orders"""
    conn = None
    try:
        conn = await aiosqlite.connect(DATABASE_PATH)
        cursor = await conn.cursor()

        # Проверяем структуру таблицы orders
        await cursor.execute("PRAGMA table_info(orders)")
        columns = await cursor.fetchall()

        column_names = [col[1] for col in columns]
        print(f"[INFO] Колонки в таблице orders: {', '.join(column_names)}")

        if "equipment_type" in column_names:
            print(f"[OK] Колонка equipment_type существует в таблице orders")

            # Проверяем, есть ли данные в этой колонке
            await cursor.execute("SELECT COUNT(*) FROM orders WHERE equipment_type IS NOT NULL AND equipment_type != ''")
            count = await cursor.fetchone()
            print(f"[INFO] Заказов с заполненным equipment_type: {count[0]}")

            # Проверяем примеры данных
            await cursor.execute("SELECT id, equipment_type FROM orders WHERE equipment_type IS NOT NULL AND equipment_type != '' LIMIT 5")
            examples = await cursor.fetchall()
            if examples:
                print(f"[INFO] Примеры заказов с equipment_type:")
                for order_id, equipment_type in examples:
                    print(f"  - Заказ #{order_id}: {equipment_type}")
        else:
            print(f"[ERROR] Колонка equipment_type НЕ существует в таблице orders!")
            print(f"[INFO] Нужно добавить колонку через миграцию или скрипт")
            return False

        return True

    except Exception as e:
        print(f"[ERROR] Ошибка при проверке: {e}")
        return False
    finally:
        if conn:
            await conn.close()


async def add_equipment_type_column():
    """Добавляет колонку equipment_type в таблицу orders, если её нет"""
    conn = None
    try:
        conn = await aiosqlite.connect(DATABASE_PATH)
        cursor = await conn.cursor()

        # Проверяем наличие колонки
        await cursor.execute("PRAGMA table_info(orders)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        if "equipment_type" in column_names:
            print(f"[SKIP] Колонка equipment_type уже существует")
            return True

        # Добавляем колонку
        await cursor.execute("""
            ALTER TABLE orders
            ADD COLUMN equipment_type TEXT NOT NULL DEFAULT ''
        """)

        await conn.commit()
        print(f"[OK] Колонка equipment_type добавлена в таблицу orders")
        return True

    except Exception as e:
        print(f"[ERROR] Ошибка при добавлении колонки: {e}")
        if conn:
            await conn.rollback()
        return False
    finally:
        if conn:
            await conn.close()


async def main():
    """Главная функция"""
    print(f"Проверка базы данных: {DATABASE_PATH}")
    print("=" * 50)

    # Проверяем наличие колонки
    exists = await check_equipment_type_column()

    if not exists:
        print("\n" + "=" * 50)
        print("Попытка добавить колонку equipment_type...")
        success = await add_equipment_type_column()
        if success:
            print("\nПовторная проверка:")
            await check_equipment_type_column()


if __name__ == "__main__":
    asyncio.run(main())
