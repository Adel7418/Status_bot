# Исправление проблемы LONG_REPAIR на сервере

## Проблема
На сервере есть заявки со статусом `LONG_REPAIR`, которые зависли и не могут быть обработаны, потому что:
1. В коде используется хардкод `'LONG_REPAIR'` вместо `OrderStatus.DR`
2. State Machine не знает, как обрабатывать статус `LONG_REPAIR`

## Решение

### Шаг 1: Создать скрипт для исправления

Создайте файл `fix_long_repair_production.py` на сервере:

```python
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
```

### Шаг 2: Исправить код

1. **Создайте бэкап:**
```bash
cp app/handlers/master.py app/handlers/master.py.backup
```

2. **Исправьте код:**
```bash
sed -i "s/'LONG_REPAIR'/OrderStatus.DR/g" app/handlers/master.py
```

3. **Проверьте исправление:**
```bash
grep -n "LONG_REPAIR" app/handlers/master.py
```

### Шаг 3: Запустить исправление данных

```bash
python fix_long_repair_production.py
```

### Шаг 4: Перезапустить бота

```bash
# Если используете Docker
docker-compose restart

# Или если запускаете напрямую
pkill -f bot.py
python bot.py &
```

## Проверка результата

После исправления проверьте:

1. **Статусы в базе:**
```bash
python -c "
import sqlite3
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()
cursor.execute('SELECT DISTINCT status FROM orders ORDER BY status')
print('Статусы:', [row[0] for row in cursor.fetchall()])
cursor.execute('SELECT COUNT(*) FROM orders WHERE status = \"LONG_REPAIR\"')
print('LONG_REPAIR заявок:', cursor.fetchone()[0])
conn.close()
"
```

2. **Код исправлен:**
```bash
grep -c "OrderStatus.DR" app/handlers/master.py
```

## Откат (если что-то пошло не так)

```bash
# Восстановить код
cp app/handlers/master.py.backup app/handlers/master.py

# Перезапустить бота
docker-compose restart
```

## Безопасность

- ✅ Создан бэкап кода
- ✅ Исправление только статуса (не удаление данных)
- ✅ Логирование в audit_log
- ✅ Возможность отката
