#!/usr/bin/env python3
"""
Отладка функции get_all_masters() - почему не читается work_chat_id
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

async def main():
    """Отладка get_all_masters"""
    print("=" * 80)
    print("ОТЛАДКА GET_ALL_MASTERS()")
    print("=" * 80)
    print()

    # Импортируем после добавления в path
    from app.database.db import Database

    db = Database()
    await db.connect()

    try:
        # Выполним тот же SQL запрос, что и в get_all_masters()
        query = """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE 1=1
            ORDER BY m.created_at DESC
        """

        cursor = await db.connection.execute(query)
        rows = await cursor.fetchall()

        print(f"📊 Найдено строк: {len(rows)}")
        print()

        # Проверяем первую строку детально
        if rows:
            first_row = rows[0]
            print("🔍 Первая строка (raw):")
            print(f"   Тип: {type(first_row)}")
            print(f"   Ключи: {first_row.keys()}")
            print()

            print("📋 Значения всех полей:")
            for key in first_row.keys():
                value = first_row[key]
                print(f"   {key}: {value} (type: {type(value).__name__})")
            print()

            # Проверяем, есть ли work_chat_id
            if "work_chat_id" in first_row.keys():
                print(f"✅ 'work_chat_id' присутствует в результате!")
                print(f"   Значение: {first_row['work_chat_id']}")
            else:
                print(f"❌ 'work_chat_id' ОТСУТСТВУЕТ в результате!")
                print(f"   Доступные поля: {list(first_row.keys())}")

            print()

            # Проверяем условие из get_all_masters()
            print("🔧 Проверка условия из get_all_masters():")
            print(f"   'work_chat_id' in row: {'work_chat_id' in first_row}")
            print(f"   row['work_chat_id']: {first_row.get('work_chat_id', 'KEY NOT FOUND')}")
            print(f"   row['work_chat_id'] is not None: {first_row.get('work_chat_id') is not None}")

            work_chat_id_value = (
                first_row["work_chat_id"]
                if "work_chat_id" in first_row and first_row["work_chat_id"] is not None
                else None
            )
            print(f"   Результат условия: {work_chat_id_value}")

    finally:
        await db.disconnect()

    print()
    print("=" * 80)
    print("ОТЛАДКА ЗАВЕРШЕНА")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
