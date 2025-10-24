#!/usr/bin/env python3
"""
Скрипт для удаления заявки со статусом LONG_REPAIR (DR)
"""

import asyncio
import sys
from pathlib import Path


# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))

from app.config import OrderStatus
from app.database import Database


async def delete_long_repair_order(order_id: int):
    """
    Удаляет заявку со статусом LONG_REPAIR (DR)

    Args:
        order_id: ID заявки для удаления
    """
    db = Database()
    await db.connect()

    try:
        # Получаем заявку
        order = await db.get_order_by_id(order_id)

        if not order:
            print(f"❌ Заявка #{order_id} не найдена")
            return False

        if order.status != OrderStatus.DR:
            print(
                f"❌ Заявка #{order_id} не в статусе LONG_REPAIR (DR). Текущий статус: {order.status}"
            )
            return False

        print(f"📋 Заявка #{order_id}:")
        print(f"   👤 Клиент: {order.client_name}")
        print(f"   📱 Техника: {order.equipment_type}")
        print(f"   📝 Описание: {order.description}")
        print(f"   📊 Статус: {order.status}")

        # Подтверждение
        confirm = input(f"\n❓ Вы уверены, что хотите удалить заявку #{order_id}? (yes/no): ")

        if confirm.lower() not in ["yes", "y", "да", "д"]:
            print("❌ Удаление отменено")
            return False

        # Мягкое удаление заявки
        success = await db.soft_delete_order(order_id)

        if success:
            print(f"✅ Заявка #{order_id} успешно удалена")

            # Добавляем в аудит
            await db.add_audit_log(
                user_id=0,  # Системное действие
                action="DELETE_ORDER_SCRIPT",
                details=f"Order #{order_id} with LONG_REPAIR status deleted by script",
            )

            return True
        else:
            print(f"❌ Ошибка при удалении заявки #{order_id}")
            return False

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

    finally:
        await db.disconnect()


async def list_long_repair_orders():
    """Показывает список заявок со статусом LONG_REPAIR"""
    db = Database()
    await db.connect()

    try:
        # Получаем все заявки со статусом DR
        # Используем SQL запрос напрямую
        async with db.get_session() as session:
            from sqlalchemy import text

            result = await session.execute(
                text("SELECT * FROM orders WHERE status = :status"), {"status": OrderStatus.DR}
            )
            orders = result.fetchall()

        if not orders:
            print("✅ Нет заявок со статусом LONG_REPAIR (DR)")
            return

        print(f"📋 Найдено заявок со статусом LONG_REPAIR: {len(orders)}\n")

        for order in orders:
            print(f"📋 Заявка #{order.id}:")
            print(f"   👤 Клиент: {order.client_name}")
            print(f"   📱 Техника: {order.equipment_type}")
            print(f"   📝 Описание: {order.description}")
            print(f"   📅 Создана: {order.created_at}")
            print()

    except Exception as e:
        print(f"❌ Ошибка при получении списка заявок: {e}")

    finally:
        await db.disconnect()


async def main():
    """Главная функция"""
    print("Script for deleting orders with LONG_REPAIR status\n")

    if len(sys.argv) > 1:
        # Удаление конкретной заявки
        try:
            order_id = int(sys.argv[1])
            await delete_long_repair_order(order_id)
        except ValueError:
            print("❌ Неверный ID заявки. Используйте число.")
    else:
        # Показать список заявок
        await list_long_repair_orders()
        print("\nFor deleting specific order use:")
        print("   python delete_long_repair_order.py <ORDER_ID>")


if __name__ == "__main__":
    asyncio.run(main())
