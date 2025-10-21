#!/usr/bin/env python3
"""
Скрипт для проверки настроенных рабочих групп у мастеров
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Database


async def check_masters_groups():
    """Проверка настроенных рабочих групп у мастеров"""

    db_path = os.getenv("DATABASE_PATH", "bot_database.db")
    print(f"Проверка базы данных: {db_path}")
    print("=" * 80)

    db = Database()
    await db.connect()

    try:
        # Получаем всех мастеров
        masters = await db.get_all_masters()

        if not masters:
            print("[!] В базе данных нет мастеров")
            return

        print(f"\nВсего мастеров в системе: {len(masters)}\n")

        masters_with_groups = []
        masters_without_groups = []

        for master in masters:
            display_name = master.get_display_name()
            status = "[+] Одобрен" if master.is_approved else "[-] Не одобрен"
            active = "[+] Активен" if master.is_active else "[-] Неактивен"

            print(f"\n{'='*80}")
            print(f"Мастер: {display_name}")
            print(f"   Telegram ID: {master.telegram_id}")
            print(f"   Телефон: {master.phone}")
            print(f"   Специализация: {master.specialization}")
            print(f"   Статус: {status}")
            print(f"   Активность: {active}")

            if master.work_chat_id:
                print(f"   [+] Рабочая группа: {master.work_chat_id}")
                masters_with_groups.append(master)
            else:
                print(f"   [!] Рабочая группа: НЕ УСТАНОВЛЕНА")
                masters_without_groups.append(master)

        # Итоговая статистика
        print(f"\n{'='*80}")
        print(f"\nСТАТИСТИКА:")
        print(f"   [+] Мастеров с настроенной группой: {len(masters_with_groups)}")
        print(f"   [!] Мастеров БЕЗ группы: {len(masters_without_groups)}")

        if masters_without_groups:
            print(f"\n[!] ВНИМАНИЕ! Следующие мастера НЕ СМОГУТ получать заявки:")
            for master in masters_without_groups:
                print(f"   - {master.get_display_name()} (ID: {master.telegram_id})")

            print(f"\nЧТО ДЕЛАТЬ:")
            print(f"   1. Зайдите в бота от имени администратора")
            print(f"   2. Нажмите 'Мастера'")
            print(f"   3. Выберите мастера")
            print(f"   4. Нажмите 'Установить рабочую группу'")
            print(f"   5. Добавьте бота в группу с мастером")
            print(f"   6. Выберите эту группу через кнопку")

    finally:
        await db.disconnect()

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(check_masters_groups())
