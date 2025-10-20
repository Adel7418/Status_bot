#!/usr/bin/env python3
"""
Скрипт для детальной диагностики пользователя и его доступа
"""
import asyncio
import sys
from pathlib import Path


# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import UserRole
from app.database.db import Database


async def diagnose_user(telegram_id: int):
    """
    Детальная диагностика пользователя

    Args:
        telegram_id: Telegram ID пользователя
    """
    db = Database()
    await db.connect()

    try:
        # Получаем пользователя
        user = await db.get_user_by_telegram_id(telegram_id)

        if not user:
            print(f"\n❌ Пользователь с Telegram ID {telegram_id} НЕ НАЙДЕН в базе данных")
            print("\n💡 Решение: Пользователь должен сначала запустить бота командой /start\n")
            return

        print("\n" + "=" * 60)
        print("📊 ДИАГНОСТИКА ПОЛЬЗОВАТЕЛЯ")
        print("=" * 60)

        print("\n✅ Пользователь найден в базе данных:")
        print(f"   ID в базе: {user.id}")
        print(f"   Telegram ID: {user.telegram_id}")
        print(f"   Имя: {user.first_name} {user.last_name or ''}")
        if user.username:
            print(f"   Username: @{user.username}")

        print("\n🔑 РОЛИ:")
        print(f"   Поле 'role' в БД: '{user.role}'")
        print(f"   Основная роль (get_primary_role): '{user.get_primary_role()}'")
        print(f"   Все роли (get_roles): {user.get_roles()}")

        # Проверяем регистр
        primary_role = user.get_primary_role()
        print("\n🔍 ПРОВЕРКА РЕГИСТРА:")
        print(
            f"   Роль в верхнем регистре: {primary_role == primary_role.upper()} {'✅' if primary_role == primary_role.upper() else '❌'}"
        )
        print("   Ожидаемые роли:")
        print(f"      - {UserRole.ADMIN} (для администратора)")
        print(f"      - {UserRole.DISPATCHER} (для диспетчера)")
        print(f"      - {UserRole.MASTER} (для мастера)")
        print(f"      - {UserRole.UNKNOWN} (без доступа)")

        # Проверяем доступ к отчетам
        print("\n📊 ДОСТУП К ОТЧЕТАМ:")
        has_reports_access = primary_role in [UserRole.ADMIN, UserRole.DISPATCHER]
        print(f"   Основная роль: {primary_role}")
        print(f"   Требуемые роли: {UserRole.ADMIN} или {UserRole.DISPATCHER}")
        print(f"   Доступ к отчетам: {'✅ ЕСТЬ' if has_reports_access else '❌ НЕТ'}")

        if has_reports_access:
            print("\n   ✅ Пользователь ДОЛЖЕН видеть кнопку '📊 Отчеты' в меню")
            print("   ✅ Пользователь ДОЛЖЕН иметь доступ ко всем отчетам")
        else:
            print("\n   ❌ Пользователь НЕ должен видеть кнопку '📊 Отчеты'")
            print("   ❌ У пользователя НЕТ доступа к отчетам")

        # Проверяем другие роли из списка
        all_roles = user.get_roles()
        print("\n👥 ПРОВЕРКА ВСЕХ РОЛЕЙ:")
        for role in all_roles:
            is_valid = role in [
                UserRole.ADMIN,
                UserRole.DISPATCHER,
                UserRole.MASTER,
                UserRole.UNKNOWN,
            ]
            print(f"   - {role}: {'✅ валидная' if is_valid else '❌ НЕВАЛИДНАЯ!'}")

        # Рекомендации
        print("\n💡 РЕКОМЕНДАЦИИ:")
        if not has_reports_access and primary_role != UserRole.DISPATCHER:
            print("   1. Установите роль DISPATCHER командой:")
            print(f"      python scripts/set_user_role.py {telegram_id} dispatcher")

        if primary_role != primary_role.upper():
            print("   ⚠️  ПРОБЛЕМА: Роль хранится не в верхнем регистре!")
            print(f"      Исправьте роль в базе данных на: {primary_role.upper()}")

        print("\n   2. После изменения роли, пользователь должен перезапустить бота:")
        print("      /start")

        print("\n   3. Проверьте логи бота при нажатии кнопки '📊 Отчеты':")
        print(f"      docker logs telegram_repair_bot_prod -f | grep {telegram_id}")

        print("\n" + "=" * 60 + "\n")

    finally:
        await db.disconnect()


async def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование: python diagnose_user.py <telegram_id>")
        print("Пример: python diagnose_user.py 123456789")
        sys.exit(1)

    try:
        telegram_id = int(sys.argv[1])
        await diagnose_user(telegram_id)
    except ValueError:
        print("❌ Ошибка: Telegram ID должен быть числом")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
