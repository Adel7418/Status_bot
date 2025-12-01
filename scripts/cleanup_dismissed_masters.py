#!/usr/bin/env python3
"""
Скрипт для очистки ролей MASTER у уволенных мастеров.

Находит пользователей с ролью MASTER, у которых нет записи в таблице masters,
и удаляет у них роли MASTER и SENIOR_MASTER.

Использование:
    python scripts/cleanup_dismissed_masters.py
    # или
    python scripts/cleanup_dismissed_masters.py --dry-run  # показать без изменений
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import UserRole
from app.database.orm_database import ORMDatabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def find_dismissed_masters_with_role(db: ORMDatabase) -> list[dict]:
    """
    Находит пользователей с ролью MASTER, но без записи в таблице masters.

    Returns:
        Список словарей с информацией о пользователях
    """
    from sqlalchemy import select

    from app.database.orm_models import Master, User

    async with db.get_session() as session:
        # Получаем всех пользователей с ролью MASTER
        stmt = select(User).where(User.role.like("%MASTER%"))
        result = await session.execute(stmt)
        users_with_master_role = result.scalars().all()

        # Проверяем, есть ли у них запись в таблице masters
        dismissed_users = []
        for user in users_with_master_role:
            # Проверяем наличие мастера
            master_stmt = select(Master).where(Master.telegram_id == user.telegram_id)
            master_result = await session.execute(master_stmt)
            master = master_result.scalar_one_or_none()

            if not master:
                # У пользователя есть роль MASTER, но нет записи мастера
                user_info = {
                    "telegram_id": user.telegram_id,
                    "first_name": user.first_name or "",
                    "last_name": user.last_name or "",
                    "username": user.username or "",
                    "role": user.role,
                }
                dismissed_users.append(user_info)

        return dismissed_users


async def remove_master_roles(
    db: ORMDatabase, telegram_id: int, dry_run: bool = False
) -> bool:
    """
    Удаляет роли MASTER и SENIOR_MASTER у пользователя.

    Args:
        db: База данных
        telegram_id: Telegram ID пользователя
        dry_run: Если True, только показывает что будет сделано

    Returns:
        True если успешно
    """
    if dry_run:
        logger.info(f"[DRY RUN] Удалил бы роли для {telegram_id}")
        return True

    # Удаляем обе роли
    success1 = await db.remove_user_role(telegram_id, UserRole.MASTER)
    success2 = await db.remove_user_role(telegram_id, UserRole.SENIOR_MASTER)

    return success1 or success2


async def main(dry_run: bool = False):
    """
    Основная функция скрипта.

    Args:
        dry_run: Если True, только показывает что будет сделано без изменений
    """
    logger.info("=" * 60)
    logger.info("Скрипт очистки ролей уволенных мастеров")
    logger.info("=" * 60)

    if dry_run:
        logger.info("РЕЖИМ: DRY RUN (без реальных изменений)")
    else:
        logger.info("РЕЖИМ: ВЫПОЛНЕНИЕ (с изменениями в БД)")

    logger.info("")

    db = ORMDatabase()
    await db.connect()

    try:
        # Находим уволенных мастеров с ролью
        logger.info("Поиск уволенных мастеров с ролью MASTER...")
        dismissed_users = await find_dismissed_masters_with_role(db)

        if not dismissed_users:
            logger.info("✅ Уволенных мастеров с ролью MASTER не найдено!")
            logger.info("База данных в порядке.")
            return

        logger.info(f"Найдено уволенных мастеров с ролью: {len(dismissed_users)}")
        logger.info("")

        # Показываем информацию о найденных пользователях
        logger.info("Список найденных пользователей:")
        for i, user in enumerate(dismissed_users, 1):
            display_name = user["first_name"]
            if user["last_name"]:
                display_name += f" {user['last_name']}"
            if not display_name.strip():
                display_name = user["username"] or f"User{user['telegram_id']}"

            logger.info(
                f"  {i}. {display_name} (ID: {user['telegram_id']}, Роль: {user['role']})"
            )

        logger.info("")

        # Подтверждение (если не dry-run)
        if not dry_run:
            response = input(
                f"Удалить роли у {len(dismissed_users)} пользователей? (yes/no): "
            )
            if response.lower() not in ["yes", "y", "да"]:
                logger.info("Отменено пользователем.")
                return
            logger.info("")

        # Удаляем роли
        success_count = 0
        failed_count = 0

        for user in dismissed_users:
            telegram_id = user["telegram_id"]
            display_name = user["first_name"]
            if user["last_name"]:
                display_name += f" {user['last_name']}"
            if not display_name.strip():
                display_name = user["username"] or f"User{telegram_id}"

            try:
                success = await remove_master_roles(db, telegram_id, dry_run)
                if success:
                    action = "Удалил бы" if dry_run else "Удалены"
                    logger.info(f"✅ {action} роли для {display_name} (ID: {telegram_id})")
                    success_count += 1
                else:
                    logger.warning(
                        f"⚠️ Не удалось удалить роли для {display_name} (ID: {telegram_id})"
                    )
                    failed_count += 1
            except Exception as e:
                logger.error(
                    f"❌ Ошибка при удалении ролей для {display_name} (ID: {telegram_id}): {e}"
                )
                failed_count += 1

        # Итоги
        logger.info("")
        logger.info("=" * 60)
        logger.info("ИТОГИ:")
        logger.info(f"  Успешно: {success_count}")
        logger.info(f"  Ошибок: {failed_count}")
        logger.info("=" * 60)

        if dry_run:
            logger.info("")
            logger.info("Это был DRY RUN. Для реального выполнения запустите:")
            logger.info("  python scripts/cleanup_dismissed_masters.py")

    finally:
        await db.disconnect()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Очистка ролей MASTER у уволенных мастеров"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать что будет сделано без реальных изменений",
    )

    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run))
