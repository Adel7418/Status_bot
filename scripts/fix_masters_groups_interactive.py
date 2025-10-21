#!/usr/bin/env python3
"""
Интерактивный скрипт для настройки рабочих групп мастеров
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Database


async def fix_masters_groups():
    """Интерактивная настройка рабочих групп для мастеров"""

    db_path = os.getenv("DATABASE_PATH", "bot_database.db")
    print(f"Настройка рабочих групп в базе данных: {db_path}")
    print("=" * 80)
    print("\nВНИМАНИЕ! Этот скрипт позволяет вручную установить work_chat_id для мастеров.")
    print("Рекомендуется использовать интерфейс бота для настройки групп.\n")

    confirm = input("Продолжить? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y', 'да']:
        print("Отменено.")
        return

    db = Database()
    await db.connect()

    try:
        # Получаем всех мастеров без групп
        masters = await db.get_all_masters()

        if not masters:
            print("\n[!] В базе данных нет мастеров")
            return

        masters_without_groups = [m for m in masters if not m.work_chat_id]

        if not masters_without_groups:
            print("\n[+] Все мастера уже имеют настроенные рабочие группы!")
            return

        print(f"\nНайдено мастеров БЕЗ групп: {len(masters_without_groups)}\n")

        for i, master in enumerate(masters_without_groups, 1):
            print(f"\n{i}. {master.get_display_name()}")
            print(f"   Telegram ID: {master.telegram_id}")
            print(f"   Телефон: {master.phone}")
            print(f"   Специализация: {master.specialization}")

            setup = input(f"\nНастроить группу для этого мастера? (yes/no/skip): ").strip().lower()

            if setup in ['yes', 'y', 'да']:
                print("\nДля получения ID группы:")
                print("  1. Добавьте бота в группу с мастером")
                print("  2. Используйте @getidsbot или подобного")
                print("  3. Группы имеют отрицательные ID (например: -1234567890)")
                print("  4. Супергруппы: -100XXXXXXXXXX\n")

                try:
                    chat_id_str = input("Введите ID группы (или 'skip' для пропуска): ").strip()

                    if chat_id_str.lower() == 'skip':
                        print("Пропущено.")
                        continue

                    chat_id = int(chat_id_str)

                    if chat_id >= 0:
                        print("[!] ОШИБКА: ID группы должен быть отрицательным!")
                        continue

                    # Обновляем work_chat_id
                    await db.update_master_work_chat(master.telegram_id, chat_id)

                    print(f"[+] Группа {chat_id} успешно установлена для мастера {master.telegram_id}")

                except ValueError:
                    print("[!] ОШИБКА: Неверный формат ID")
                except Exception as e:
                    print(f"[!] ОШИБКА при установке группы: {e}")

            elif setup in ['skip', 's', 'пропустить']:
                print("Пропущено.")
                continue
            else:
                print("Пропущено.")

        print("\n" + "=" * 80)
        print("\nНастройка завершена. Проверка результата...\n")

        # Проверяем результат
        masters = await db.get_all_masters()
        with_groups = sum(1 for m in masters if m.work_chat_id)
        without_groups = sum(1 for m in masters if not m.work_chat_id)

        print(f"РЕЗУЛЬТАТ:")
        print(f"  [+] С группами: {with_groups}")
        print(f"  [!] БЕЗ групп: {without_groups}")

        if without_groups > 0:
            print(f"\n[!] Некоторые мастера все еще без групп.")
            print(f"Используйте интерфейс бота для их настройки.")

    finally:
        await db.disconnect()

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(fix_masters_groups())
