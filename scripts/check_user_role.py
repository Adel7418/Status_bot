#!/usr/bin/env python3
"""
Скрипт для проверки роли пользователя по Telegram ID
"""
import asyncio
import sys
from pathlib import Path


# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.db import Database


async def check_user_role(telegram_id: int):
    """
    Проверка роли пользователя

    Args:
        telegram_id: Telegram ID пользователя
    """
    db = Database()
    await db.connect()

    try:
        user = await db.get_user_by_telegram_id(telegram_id)

        if not user:
            print(f"❌ Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            return

        print("\n✅ Пользователь найден:\n")
        print(f"   ID в базе: {user.id}")
        print(f"   Telegram ID: {user.telegram_id}")
        print(f"   Имя: {user.first_name} {user.last_name or ''}")
        if user.username:
            print(f"   Username: @{user.username}")
        print(f"   Основная роль: {user.role}")

        # Проверяем дополнительные роли
        if user.additional_roles:
            roles_list = (
                user.additional_roles.split(",") if isinstance(user.additional_roles, str) else []
            )
            all_roles = [user.role] + roles_list
            print(f"   Все роли: {', '.join(all_roles)}")
        else:
            print("   Дополнительные роли: нет")

        print(
            f"\n📊 Доступ к отчетам: {'✅ Есть' if user.role in ['admin', 'dispatcher'] else '❌ Нет'}"
        )
        print()

    finally:
        await db.disconnect()


async def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование: python check_user_role.py <telegram_id>")
        print("Пример: python check_user_role.py 123456789")
        sys.exit(1)

    try:
        telegram_id = int(sys.argv[1])
        await check_user_role(telegram_id)
    except ValueError:
        print("❌ Ошибка: Telegram ID должен быть числом")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
