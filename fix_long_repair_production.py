#!/usr/bin/env python3
"""
Исправление заявок со статусом LONG_REPAIR на продакшене
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))

from app.config import OrderStatus
from app.database import Database

async def check_long_repair_orders():
    """Проверяет количество заявок со статусом LONG_REPAIR"""
    db = Database()
    await db.connect()
    
    try:
        async with db.get_session() as session:
            from sqlalchemy import text
            
            # Проверяем все статусы
            result = await session.execute(
                text("SELECT DISTINCT status FROM orders ORDER BY status")
            )
            statuses = [row[0] for row in result.fetchall()]
            print("Статусы в базе данных:")
            for status in statuses:
                print(f"  - {status}")
            
            # Считаем заявки с LONG_REPAIR
            result = await session.execute(
                text("SELECT COUNT(*) FROM orders WHERE status = 'LONG_REPAIR'")
            )
            long_repair_count = result.scalar()
            
            result = await session.execute(
                text("SELECT COUNT(*) FROM orders WHERE status = 'DR'")
            )
            dr_count = result.scalar()
            
            print(f"\nЗаявок со статусом 'LONG_REPAIR': {long_repair_count}")
            print(f"Заявок со статусом 'DR': {dr_count}")
            
            if long_repair_count > 0:
                # Показываем примеры
                result = await session.execute(
                    text("SELECT id, client_name, equipment_type, created_at FROM orders WHERE status = 'LONG_REPAIR' LIMIT 5")
                )
                orders = result.fetchall()
                
                print("\nПримеры заявок с LONG_REPAIR:")
                for order in orders:
                    print(f"  #{order.id}: {order.client_name} - {order.equipment_type} ({order.created_at})")
                    
            return long_repair_count
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return 0
    finally:
        await db.disconnect()

async def fix_long_repair_orders():
    """Исправляет заявки со статусом LONG_REPAIR"""
    db = Database()
    await db.connect()
    
    try:
        async with db.get_session() as session:
            from sqlalchemy import text
            
            # Получаем заявки с LONG_REPAIR
            result = await session.execute(
                text("SELECT id, client_name, equipment_type FROM orders WHERE status = 'LONG_REPAIR'")
            )
            orders = result.fetchall()
            
            if not orders:
                print("Нет заявок со статусом LONG_REPAIR")
                return
                
            print(f"Найдено {len(orders)} заявок со статусом LONG_REPAIR:")
            for order in orders:
                print(f"  #{order.id}: {order.client_name} - {order.equipment_type}")
            
            # Исправляем статус
            await session.execute(
                text("UPDATE orders SET status = :new_status WHERE status = 'LONG_REPAIR'"),
                {"new_status": OrderStatus.DR}
            )
            
            # Добавляем в аудит
            await db.add_audit_log(
                user_id=0,
                action="FIX_LONG_REPAIR_STATUS",
                details=f"Fixed {len(orders)} orders from LONG_REPAIR to DR status",
            )
            
            await session.commit()
            print(f"\nУспешно исправлено {len(orders)} заявок")
            
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        await db.disconnect()

async def main():
    """Главная функция"""
    print("=== Исправление LONG_REPAIR на продакшене ===")
    
    # Проверяем текущее состояние
    count = await check_long_repair_orders()
    
    if count > 0:
        print(f"\nНайдено {count} заявок для исправления")
        confirm = input("Продолжить исправление? (yes/no): ")
        
        if confirm.lower() in ["yes", "y", "да", "д"]:
            await fix_long_repair_orders()
            print("\nИсправление завершено!")
        else:
            print("Исправление отменено")
    else:
        print("\nНет заявок для исправления")

if __name__ == "__main__":
    asyncio.run(main())
