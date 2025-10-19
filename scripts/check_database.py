"""
Скрипт для быстрой проверки данных в базе
"""

import io
import sqlite3
import sys


# Настройка кодировки для консоли Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def check_database():
    """Проверка основных таблиц базы данных"""

    conn = sqlite3.connect("bot_database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Проверка пользователей
    cursor.execute(
        """
        SELECT id, telegram_id, username, first_name, last_name, role, created_at
        FROM users
        ORDER BY created_at DESC
    """
    )
    users = cursor.fetchall()

    print("\n" + "=" * 80)
    print("👥 ПОЛЬЗОВАТЕЛИ")
    print("=" * 80)

    if users:
        print(f"\nВсего пользователей: {len(users)}\n")
        for user in users:
            print(f"ID: {user['id']} | TG: {user['telegram_id']}")
            print(f"   Username: @{user['username'] or '-'}")
            print(f"   Имя: {user['first_name'] or '-'} {user['last_name'] or '-'}")
            print(f"   Роль: {user['role']}")
            print(f"   Создан: {user['created_at']}")
            print()
    else:
        print("Пользователей нет\n")

    # Проверка мастеров
    cursor.execute(
        """
        SELECT m.id, m.telegram_id, u.first_name, u.last_name,
               m.phone, m.specialization, m.is_active, m.is_approved,
               m.work_chat_id
        FROM masters m
        LEFT JOIN users u ON m.telegram_id = u.telegram_id
        ORDER BY m.created_at DESC
    """
    )
    masters = cursor.fetchall()

    print("\n" + "=" * 80)
    print("👨‍🔧 МАСТЕРА")
    print("=" * 80)

    if masters:
        print(f"\nВсего мастеров: {len(masters)}\n")
        for master in masters:
            name = f"{master['first_name'] or ''} {master['last_name'] or ''}".strip() or "-"
            status = "✅ Подтвержден" if master["is_approved"] else "⏳ Ожидает"
            active = "🟢 Активен" if master["is_active"] else "🔴 Неактивен"
            work_chat = master["work_chat_id"] if master["work_chat_id"] else "-"

            print(f"ID: {master['id']} | TG: {master['telegram_id']}")
            print(f"   Имя: {name}")
            print(f"   Телефон: {master['phone']}")
            print(f"   Специализация: {master['specialization']}")
            print(f"   Статус: {status} | {active}")
            print(f"   Рабочий чат: {work_chat}")
            print()
    else:
        print("Мастеров нет\n")

    # Проверка заявок
    cursor.execute(
        """
        SELECT o.id, o.equipment_type, o.client_name, o.status,
               u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
               u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name,
               o.total_amount, o.notes, o.scheduled_time, o.created_at,
               o.dispatcher_id, o.assigned_master_id
        FROM orders o
        LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
        LEFT JOIN masters m ON o.assigned_master_id = m.id
        LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
        ORDER BY o.created_at DESC
        LIMIT 20
    """
    )
    orders = cursor.fetchall()

    print("\n" + "=" * 80)
    print("📋 ЗАЯВКИ (последние 20)")
    print("=" * 80)

    if orders:
        print(f"\nВсего заявок в выборке: {len(orders)}\n")
        for order in orders:
            status_emoji = {
                "NEW": "🆕",
                "ASSIGNED": "👨‍🔧",
                "ACCEPTED": "✅",
                "ONSITE": "🏠",
                "CLOSED": "💰",
                "REFUSED": "❌",
                "DR": "⏳",
            }.get(order["status"], "❓")

            # Форматируем имена с fallback на ID
            dispatcher_display = (
                order["dispatcher_name"].strip()
                if order["dispatcher_name"] and order["dispatcher_name"].strip()
                else f"ID: {order['dispatcher_id']}"
                if order["dispatcher_id"]
                else "-"
            )
            master_display = (
                order["master_name"].strip()
                if order["master_name"] and order["master_name"].strip()
                else f"Master ID: {order['assigned_master_id']}"
                if order["assigned_master_id"]
                else "-"
            )

            print(f"Заявка #{order['id']} | {status_emoji} {order['status']}")
            print(f"   Оборудование: {order['equipment_type']}")
            print(f"   Клиент: {order['client_name']}")
            print(f"   Диспетчер: {dispatcher_display}")
            print(f"   Мастер: {master_display}")
            if order["notes"]:
                print(f"   📝 Заметки: {order['notes']}")
            if order["scheduled_time"]:
                print(f"   ⏰ Время прибытия: {order['scheduled_time']}")
            if order["total_amount"]:
                print(f"   💰 Сумма: {order['total_amount']:.0f} ₽")
            print(f"   Создана: {order['created_at']}")
            print()
    else:
        print("Заявок нет\n")

    # Статистика по заявкам
    cursor.execute(
        """
        SELECT status, COUNT(*) as count
        FROM orders
        GROUP BY status
        ORDER BY count DESC
    """
    )
    stats = cursor.fetchall()

    print("\n" + "=" * 80)
    print("📊 СТАТИСТИКА ПО ЗАЯВКАМ")
    print("=" * 80)

    if stats:
        print()
        for stat in stats:
            status_names = {
                "NEW": "🆕 Новые",
                "ASSIGNED": "👨‍🔧 Назначены",
                "ACCEPTED": "✅ Приняты",
                "ONSITE": "🏠 На объекте",
                "CLOSED": "💰 Завершены",
                "REFUSED": "❌ Отклонены",
                "DR": "⏳ Длительный ремонт",
            }
            status_name = status_names.get(stat["status"], stat["status"])
            print(f"   {status_name}: {stat['count']}")
        print()
    else:
        print("Нет статистики\n")

    # Проверка пользователей с множественными ролями
    cursor.execute(
        """
        SELECT telegram_id, username, first_name, last_name, role
        FROM users
        WHERE role LIKE '%,%'
        ORDER BY created_at DESC
    """
    )
    multi_role_users = cursor.fetchall()

    if multi_role_users:
        print("\n" + "=" * 80)
        print("👥 ПОЛЬЗОВАТЕЛИ С МНОЖЕСТВЕННЫМИ РОЛЯМИ")
        print("=" * 80)
        print()

        for user in multi_role_users:
            name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip() or "-"
            roles = user["role"].split(",")
            role_names = {
                "ADMIN": "👑 Администратор",
                "DISPATCHER": "📋 Диспетчер",
                "MASTER": "👨‍🔧 Мастер",
                "UNKNOWN": "❓ Неизвестно",
            }
            roles_str = ", ".join([role_names.get(r.strip(), r) for r in roles])

            print(f"TG: {user['telegram_id']} | @{user['username'] or '-'}")
            print(f"   Имя: {name}")
            print(f"   Роли: {roles_str}")
            print()

    # Проверка истории изменений статусов (последние 20)
    cursor.execute(
        """
        SELECT
            h.id,
            h.order_id,
            h.old_status,
            h.new_status,
            h.changed_by,
            u.first_name || ' ' || COALESCE(u.last_name, '') as changed_by_name,
            h.changed_at,
            h.notes
        FROM order_status_history h
        LEFT JOIN users u ON h.changed_by = u.telegram_id
        ORDER BY h.changed_at DESC
        LIMIT 20
    """
    )
    history = cursor.fetchall()

    if history:
        print("\n" + "=" * 80)
        print("📜 ИСТОРИЯ ИЗМЕНЕНИЙ СТАТУСОВ (последние 20)")
        print("=" * 80)
        print()

        for h in history:
            changed_by_name = (
                h["changed_by_name"].strip() if h["changed_by_name"] else f"ID: {h['changed_by']}"
            )
            status_names = {
                "NEW": "🆕 Новая",
                "ASSIGNED": "👨‍🔧 Назначена",
                "ACCEPTED": "✅ Принята",
                "ONSITE": "🏠 На объекте",
                "CLOSED": "💰 Завершена",
                "REFUSED": "❌ Отклонена",
                "DR": "⏳ Длительный ремонт",
            }
            old = status_names.get(h["old_status"], h["old_status"]) if h["old_status"] else "-"
            new = status_names.get(h["new_status"], h["new_status"])

            print(f"Заявка #{h['order_id']} | {old} → {new}")
            print(f"   Изменил: {changed_by_name}")
            print(f"   Время: {h['changed_at']}")
            if h["notes"]:
                print(f"   Примечание: {h['notes']}")
            print()

    conn.close()


if __name__ == "__main__":
    try:
        check_database()
    except Exception:
        import traceback

        traceback.print_exc()
