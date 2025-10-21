#!/usr/bin/env python3
"""
Скрипт для тестирования чтения work_chat_id мастеров
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Database


async def main():
    """Тестирование чтения work_chat_id"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ЧТЕНИЯ WORK_CHAT_ID")
    print("=" * 80)
    print()

    db = Database()
    await db.connect()

    try:
        # Получаем всех мастеров
        masters = await db.get_all_masters()

        print(f"📊 Найдено мастеров: {len(masters)}")
        print()

        for master in masters:
            print(f"👤 Мастер: {master.get_display_name()}")
            print(f"   ID: {master.id}")
            print(f"   Telegram ID: {master.telegram_id}")
            print(f"   Специализация: {master.specialization}")
            print(f"   Активен: {'✅' if master.is_active else '❌'}")
            print(f"   Одобрен: {'✅' if master.is_approved else '❌'}")
            print(f"   work_chat_id: {master.work_chat_id}")
            print(f"   Тип work_chat_id: {type(master.work_chat_id)}")
            print(f"   work_chat_id is None: {master.work_chat_id is None}")
            print(f"   work_chat_id == 0: {master.work_chat_id == 0}")
            print(f"   bool(work_chat_id): {bool(master.work_chat_id)}")
            print(f"   not work_chat_id: {not master.work_chat_id}")

            # Проверяем условие из inline.py
            warning = " ⚠️ НЕТ ГРУППЫ" if not master.work_chat_id else ""
            print(f"   Результат проверки: '{warning}'")
            print()

        # Проверяем конкретного мастера 659747369
        print("=" * 80)
        print("ПРОВЕРКА КОНКРЕТНОГО МАСТЕРА 659747369")
        print("=" * 80)
        print()

        master = await db.get_master_by_telegram_id(659747369)
        if master:
            print(f"✅ Мастер найден!")
            print(f"   work_chat_id: {master.work_chat_id}")
            print(f"   Тип: {type(master.work_chat_id)}")
            print(f"   Значение в if not: {not master.work_chat_id}")
            print(f"   Значение в bool(): {bool(master.work_chat_id)}")

            # Дополнительная проверка
            if master.work_chat_id:
                print(f"   ✅ work_chat_id установлен")
            else:
                print(f"   ❌ work_chat_id НЕ установлен (пустой, None или 0)")
        else:
            print("❌ Мастер 659747369 не найден!")

    finally:
        await db.disconnect()

    print()
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
