#!/usr/bin/env python3
"""
Скрипт для ручного восстановления заявок из истории Telegram
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_database


async def restore_order(
    equipment_type: str,
    description: str,
    client_name: str,
    client_address: str,
    client_phone: str,
    dispatcher_id: int,  # Telegram ID диспетчера
    created_at: str | None = None,  # Формат: "2025-10-20 14:30:00"
    notes: str = "",
):
    """
    Восстановление заявки

    Args:
        equipment_type: Тип техники
        description: Описание проблемы
        client_name: Имя клиента
        client_address: Адрес клиента
        client_phone: Телефон клиента
        dispatcher_id: Telegram ID диспетчера (кто создал заявку)
        created_at: Дата создания (опционально)
        notes: Примечания (опционально)
    """
    db = get_database()
    await db.connect()

    try:
        # Создаем заявку
        order = await db.create_order(
            equipment_type=equipment_type,
            description=description,
            client_name=client_name,
            client_address=client_address,
            client_phone=client_phone,
            dispatcher_id=dispatcher_id,
            notes=notes,
        )

        # Если указана дата создания, обновляем её вручную
        if created_at:
            await db.connection.execute(
                "UPDATE orders SET created_at = ? WHERE id = ?",
                (created_at, order.id),
            )
            await db.connection.commit()

        print(f"✅ Заявка #{order.id} восстановлена!")
        print(f"   Тип: {equipment_type}")
        print(f"   Клиент: {client_name}")
        print(f"   Адрес: {client_address}")
        print(f"   Телефон: {client_phone}")
        if created_at:
            print(f"   Дата: {created_at}")
        print()

        return order.id

    finally:
        await db.disconnect()


async def main():
    """Примеры восстановления заявок"""
    print("=" * 80)
    print("ВОССТАНОВЛЕНИЕ ЗАЯВОК ИЗ ИСТОРИИ TELEGRAM")
    print("=" * 80)
    print()

    # ПРИМЕР 1: Заявка без указания даты (будет текущая дата)
    # await restore_order(
    #     equipment_type="Холодильник",
    #     description="Не морозит",
    #     client_name="Иван Петров",
    #     client_address="ул. Пушкина, д. 10, кв. 5",
    #     client_phone="+79123456789",
    #     dispatcher_id=123456789,  # ЗАМЕНИТЕ на реальный Telegram ID диспетчера
    # )

    # ПРИМЕР 2: Заявка с указанием даты создания
    # await restore_order(
    #     equipment_type="Стиральная машина",
    #     description="Не включается",
    #     client_name="Мария Сидорова",
    #     client_address="ул. Ленина, д. 20",
    #     client_phone="+79111111111",
    #     dispatcher_id=123456789,
    #     created_at="2025-10-15 10:30:00",
    #     notes="Срочная заявка",
    # )

    # ДОБАВЬТЕ СВОИ ЗАЯВКИ НИЖЕ:
    # Раскомментируйте и заполните данные из истории Telegram

    # await restore_order(
    #     equipment_type="",
    #     description="",
    #     client_name="",
    #     client_address="",
    #     client_phone="",
    #     dispatcher_id=0,  # ОБЯЗАТЕЛЬНО укажите!
    #     created_at="2025-10-20 12:00:00",  # Опционально
    # )

    print("=" * 80)
    print("ℹ️  Раскомментируйте примеры выше и заполните данными из Telegram!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
