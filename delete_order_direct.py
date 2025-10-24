#!/usr/bin/env python3
"""
Прямое удаление заявки из базы данных
"""

import asyncio
import sys
from pathlib import Path


# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))

from app.database import Database


async def delete_order_direct(order_id: int):
    """Прямое удаление заявки из базы данных"""
    db = Database()
    await db.connect()

    try:
        # Получаем заявку
        order = await db.get_order_by_id(order_id)

        if not order:
            print(f"❌ Заявка #{order_id} не найдена")
            return False

        print(f"📋 Заявка #{order_id}:")
        print(f"   👤 Клиент: {order.client_name}")
        print(f"   📱 Техника: {order.equipment_type}")
        print(f"   📊 Статус: {order.status}")

        # Подтверждение
        confirm = input(f"\n❓ Вы уверены, что хотите УДАЛИТЬ заявку #{order_id}? (yes/no): ")

        if confirm.lower() not in ["yes", "y", "да", "д"]:
            print("❌ Удаление отменено")
            return False

        # Прямое удаление из базы данных
        async with db.get_session() as session:
            from sqlalchemy import text

            # Удаляем заявку
            await session.execute(
                text("DELETE FROM orders WHERE id = :order_id"), {"order_id": order_id}
            )

            # Удаляем связанные записи
            await session.execute(
                text("DELETE FROM order_status_history WHERE order_id = :order_id"),
                {"order_id": order_id},
            )

            await session.execute(
                text("DELETE FROM order_group_messages WHERE order_id = :order_id"),
                {"order_id": order_id},
            )

            await session.commit()

        print(f"✅ Заявка #{order_id} полностью удалена из базы данных")
        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

    finally:
        await db.disconnect()


async def main():
    if len(sys.argv) > 1:
        try:
            order_id = int(sys.argv[1])
            await delete_order_direct(order_id)
        except ValueError:
            print("❌ Неверный ID заявки. Используйте число.")
    else:
        print("❌ Укажите ID заявки для удаления")
        print("Пример: python delete_order_direct.py 97")


if __name__ == "__main__":
    asyncio.run(main())
