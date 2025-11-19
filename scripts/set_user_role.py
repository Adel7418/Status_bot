#!/usr/bin/env python3
"""
Скрипт для установки роли пользователя по Telegram ID
"""

import asyncio
import sys
from pathlib import Path


# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import UserRole
from app.database.db import Database


async def set_user_role(telegram_id: int, new_role: str):
    """
    Установка роли пользователя

    Args:
        telegram_id: Telegram ID пользователя
        new_role: Новая роль пользователя
    """
    # Проверяем валидность роли
    valid_roles = [UserRole.ADMIN, UserRole.DISPATCHER, UserRole.MASTER, UserRole.UNKNOWN]

    if new_role not in valid_roles:
        print(f"❌ Ошибка: недопустимая роль '{new_role}'")
        print(f"Допустимые роли: {', '.join(valid_roles)}")
        return

    db = Database()
    await db.connect()

    try:
        user = await db.get_user_by_telegram_id(telegram_id)

        if not user:
            print(f"❌ Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            print("\nПользователь должен сначала запустить бота командой /start")
            return

        old_role = user.role

        # Обновляем роль
        await db.connection.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?", (new_role, telegram_id)
        )
        await db.connection.commit()

        print("\n✅ Роль пользователя успешно изменена!\n")
        print(f"   Telegram ID: {telegram_id}")
        print(f"   Имя: {user.first_name} {user.last_name or ''}")
        if user.username:
            print(f"   Username: @{user.username}")
        print(f"   Старая роль: {old_role}")
        print(f"   Новая роль: {new_role}")
        print()

        if new_role == UserRole.DISPATCHER:
            print("📊 Теперь пользователь имеет доступ к отчетам!")
        elif new_role == UserRole.ADMIN:
            print("🔑 Теперь пользователь имеет полный административный доступ!")
        elif new_role == UserRole.MASTER:
            print("🔧 Теперь пользователь зарегистрирован как мастер!")

        print("\n⚠️  Пользователю нужно перезапустить бота командой /start для обновления меню.")
        print()

    finally:
        await db.disconnect()


async def main():
    """Главная функция"""
    if len(sys.argv) < 3:
        print("Использование: python set_user_role.py <telegram_id> <role>")
        print("\nДопустимые роли:")
        print(f"  - {UserRole.ADMIN} - Администратор (полный доступ)")
        print(
            f"  - {UserRole.DISPATCHER} - Диспетчер (создание заявок, назначение мастеров, отчеты)"
        )
        print(f"  - {UserRole.MASTER} - Мастер (работа с назначенными заявками)")
        print(f"  - {UserRole.UNKNOWN} - Неизвестный (без доступа)")
        print("\nПример: python set_user_role.py 123456789 dispatcher")
        sys.exit(1)

    try:
        telegram_id = int(sys.argv[1])
        new_role = sys.argv[2].lower()
        await set_user_role(telegram_id, new_role)
    except ValueError:
        print("❌ Ошибка: Telegram ID должен быть числом")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
