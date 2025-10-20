#!/usr/bin/env python3
"""
Скрипт для миграции существующих данных с шифрованием
Использовать ОДИН РАЗ после внедрения шифрования

ВНИМАНИЕ: Сделайте бэкап перед запуском!
"""

import asyncio
import logging
import sys
from pathlib import Path


# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.db import Database
from app.utils.encryption import decrypt, encrypt


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def migrate_orders_encryption(db: Database, dry_run: bool = True):
    """
    Шифрование существующих данных заявок

    Args:
        db: База данных
        dry_run: Если True, только показывает что будет сделано
    """
    logger.info("=" * 60)
    logger.info("🔐 Миграция шифрования данных заявок")
    logger.info(f"📋 Режим: {'DRY RUN (тестовый)' if dry_run else 'РЕАЛЬНЫЙ'}")
    logger.info("=" * 60)

    # Получаем все заявки
    cursor = await db.connection.execute(
        """
        SELECT id, client_name, client_phone, client_address
        FROM orders
        WHERE deleted_at IS NULL
        """
    )
    orders = await cursor.fetchall()

    logger.info(f"📊 Найдено заявок для обработки: {len(orders)}")

    if not orders:
        logger.info("✅ Нет заявок для обработки")
        return

    # Обрабатываем каждую заявку
    success_count = 0
    error_count = 0

    for order in orders:
        order_id = order["id"]
        client_name = order["client_name"]
        client_phone = order["client_phone"]
        client_address = order["client_address"]

        try:
            # Шифруем данные
            encrypted_name = encrypt(client_name) if client_name else None
            encrypted_phone = encrypt(client_phone) if client_phone else None
            encrypted_address = encrypt(client_address) if client_address else None

            logger.info(f"\n📋 Заявка #{order_id}:")
            logger.info(f"  Имя: {client_name[:20]}... → {encrypted_name[:30]}...")
            logger.info(f"  Телефон: {client_phone} → {encrypted_phone[:30]}...")
            logger.info(f"  Адрес: {client_address[:30]}... → {encrypted_address[:30]}...")

            # Проверяем дешифрование
            decrypted_name = decrypt(encrypted_name) if encrypted_name else None
            decrypted_phone = decrypt(encrypted_phone) if encrypted_phone else None
            decrypted_address = decrypt(encrypted_address) if encrypted_address else None

            # Валидация
            if decrypted_name != client_name:
                logger.error("  ❌ Ошибка проверки имени!")
                error_count += 1
                continue

            if decrypted_phone != client_phone:
                logger.error("  ❌ Ошибка проверки телефона!")
                error_count += 1
                continue

            if decrypted_address != client_address:
                logger.error("  ❌ Ошибка проверки адреса!")
                error_count += 1
                continue

            logger.info("  ✅ Проверка дешифрования пройдена")

            # Обновляем в БД (если не dry_run)
            if not dry_run:
                await db.connection.execute(
                    """
                    UPDATE orders
                    SET client_name = ?,
                        client_phone = ?,
                        client_address = ?,
                        version = version + 1
                    WHERE id = ?
                    """,
                    (encrypted_name, encrypted_phone, encrypted_address, order_id),
                )
                logger.info("  💾 Данные обновлены в БД")

            success_count += 1

        except Exception as e:
            logger.error(f"  ❌ Ошибка обработки заявки #{order_id}: {e}")
            error_count += 1

    # Коммитим изменения
    if not dry_run:
        await db.connection.commit()
        logger.info("\n💾 Изменения сохранены в БД")
    else:
        logger.info("\n🔍 DRY RUN завершен, изменения НЕ сохранены")

    # Итоговая статистика
    logger.info("\n" + "=" * 60)
    logger.info("📊 ИТОГОВАЯ СТАТИСТИКА:")
    logger.info(f"  ✅ Успешно обработано: {success_count}")
    logger.info(f"  ❌ Ошибок: {error_count}")
    logger.info(f"  📋 Всего: {len(orders)}")
    logger.info("=" * 60)


async def main():
    """Главная функция"""
    print("\n" + "=" * 60)
    print("🔐 СКРИПТ МИГРАЦИИ ШИФРОВАНИЯ")
    print("=" * 60)
    print("\n⚠️  ВНИМАНИЕ! Перед запуском:")
    print("  1. Сделайте бэкап базы данных")
    print("  2. Убедитесь что ENCRYPTION_KEY установлен в .env")
    print("  3. Сначала запустите в режиме DRY RUN")
    print()

    # Спрашиваем подтверждение
    mode = input("Выберите режим (dry/real): ").strip().lower()

    if mode not in ["dry", "real"]:
        print("❌ Неверный режим! Используйте 'dry' или 'real'")
        return

    dry_run = mode == "dry"

    if not dry_run:
        print("\n⚠️  ВЫ ВЫБРАЛИ РЕАЛЬНЫЙ РЕЖИМ!")
        confirm = input("Вы уверены? Введите 'YES' для продолжения: ").strip()
        if confirm != "YES":
            print("❌ Отменено")
            return

    # Подключаемся к БД
    logger.info("\n📡 Подключение к базе данных...")
    db = Database()
    await db.connect()

    try:
        # Запускаем миграцию
        await migrate_orders_encryption(db, dry_run=dry_run)

    finally:
        await db.disconnect()
        logger.info("\n👋 Отключение от БД")

    print("\n✅ Готово!")


if __name__ == "__main__":
    asyncio.run(main())
