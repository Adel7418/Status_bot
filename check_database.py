"""
Скрипт для быстрой проверки данных в базе
"""
import sqlite3
from datetime import datetime
from tabulate import tabulate
import sys
import io

# Настройка кодировки для консоли Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def check_database():
    """Проверка основных таблиц базы данных"""
    
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📊 ПРОВЕРКА БАЗЫ ДАННЫХ БОТА")
    print("="*80 + "\n")
    
    # Проверка пользователей
    print("👥 ПОЛЬЗОВАТЕЛИ:")
    print("-" * 80)
    cursor.execute("""
        SELECT id, telegram_id, username, first_name, last_name, role, created_at 
        FROM users 
        ORDER BY created_at DESC
    """)
    users = cursor.fetchall()
    
    if users:
        users_data = []
        for user in users:
            users_data.append([
                user['id'],
                user['telegram_id'],
                user['username'] or '-',
                user['first_name'] or '-',
                user['last_name'] or '-',
                user['role']  # Теперь может быть "DISPATCHER,MASTER"
            ])
        
        print(tabulate(users_data, 
                      headers=['ID', 'Telegram ID', 'Username', 'Имя', 'Фамилия', 'Роли'],
                      tablefmt='grid'))
        print(f"\nВсего пользователей: {len(users)}\n")
    else:
        print("Нет пользователей\n")
    
    # Проверка мастеров
    print("\n🔧 МАСТЕРА:")
    print("-" * 80)
    cursor.execute("""
        SELECT m.id, m.telegram_id, u.first_name, u.last_name, 
               m.phone, m.specialization, m.is_active, m.is_approved,
               m.work_chat_id
        FROM masters m
        LEFT JOIN users u ON m.telegram_id = u.telegram_id
        ORDER BY m.created_at DESC
    """)
    masters = cursor.fetchall()
    
    if masters:
        masters_data = []
        for master in masters:
            name = f"{master['first_name'] or ''} {master['last_name'] or ''}".strip() or '-'
            status = '✅' if master['is_approved'] else '⏳'
            active = '🟢' if master['is_active'] else '🔴'
            work_chat = master['work_chat_id'] if master['work_chat_id'] else '-'
            
            masters_data.append([
                master['id'],
                master['telegram_id'],
                name,
                master['phone'],
                master['specialization'],
                f"{status} {active}",
                work_chat
            ])
        
        print(tabulate(masters_data,
                      headers=['ID', 'Telegram ID', 'Имя', 'Телефон', 'Специализация', 'Статус', 'Группа'],
                      tablefmt='grid'))
        print(f"\nВсего мастеров: {len(masters)}\n")
    else:
        print("Нет мастеров\n")
    
    # Проверка заявок
    print("\n📋 ЗАЯВКИ:")
    print("-" * 80)
    cursor.execute("""
        SELECT o.id, o.equipment_type, o.client_name, o.status, 
               u1.first_name || ' ' || u1.last_name as dispatcher_name,
               u2.first_name || ' ' || u2.last_name as master_name,
               o.total_amount, o.created_at
        FROM orders o
        LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
        LEFT JOIN masters m ON o.assigned_master_id = m.id
        LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
        ORDER BY o.created_at DESC
        LIMIT 20
    """)
    orders = cursor.fetchall()
    
    if orders:
        orders_data = []
        for order in orders:
            status_emoji = {
                'NEW': '🆕',
                'ASSIGNED': '👨‍🔧',
                'ACCEPTED': '✅',
                'ONSITE': '🏠',
                'CLOSED': '💰',
                'REFUSED': '❌',
                'DR': '⏳'
            }.get(order['status'], '❓')
            
            orders_data.append([
                order['id'],
                order['equipment_type'][:20],
                order['client_name'][:15],
                f"{status_emoji} {order['status']}",
                (order['dispatcher_name'] or '-')[:15],
                (order['master_name'] or '-')[:15],
                f"{order['total_amount']:.0f} ₽" if order['total_amount'] else '-'
            ])
        
        print(tabulate(orders_data,
                      headers=['ID', 'Тип техники', 'Клиент', 'Статус', 'Диспетчер', 'Мастер', 'Сумма'],
                      tablefmt='grid'))
        print(f"\nПоказано последних 20 заявок\n")
    else:
        print("Нет заявок\n")
    
    # Статистика по заявкам
    print("\n📊 СТАТИСТИКА ПО ЗАЯВКАМ:")
    print("-" * 80)
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM orders
        GROUP BY status
        ORDER BY count DESC
    """)
    stats = cursor.fetchall()
    
    if stats:
        stats_data = []
        for stat in stats:
            status_names = {
                'NEW': 'Новые',
                'ASSIGNED': 'Назначены',
                'ACCEPTED': 'Приняты',
                'ONSITE': 'На объекте',
                'CLOSED': 'Завершены',
                'REFUSED': 'Отклонены',
                'DR': 'Длительный ремонт'
            }
            stats_data.append([
                status_names.get(stat['status'], stat['status']),
                stat['count']
            ])
        
        print(tabulate(stats_data,
                      headers=['Статус', 'Количество'],
                      tablefmt='grid'))
    
    # Проверка пользователей с множественными ролями
    print("\n\n👥 ПОЛЬЗОВАТЕЛИ С НЕСКОЛЬКИМИ РОЛЯМИ:")
    print("-" * 80)
    cursor.execute("""
        SELECT telegram_id, username, first_name, last_name, role
        FROM users
        WHERE role LIKE '%,%'
        ORDER BY created_at DESC
    """)
    multi_role_users = cursor.fetchall()
    
    if multi_role_users:
        multi_data = []
        for user in multi_role_users:
            name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip() or '-'
            roles = user['role'].split(',')
            role_names = {
                'ADMIN': 'Администратор',
                'DISPATCHER': 'Диспетчер',
                'MASTER': 'Мастер',
                'UNKNOWN': 'Неизвестно'
            }
            roles_str = ', '.join([role_names.get(r.strip(), r) for r in roles])
            
            multi_data.append([
                user['telegram_id'],
                user['username'] or '-',
                name,
                roles_str
            ])
        
        print(tabulate(multi_data,
                      headers=['Telegram ID', 'Username', 'Имя', 'Роли'],
                      tablefmt='grid'))
        print(f"\nВсего с несколькими ролями: {len(multi_role_users)}")
    else:
        print("Пока нет пользователей с несколькими ролями")
    
    conn.close()
    
    print("\n" + "="*80)
    print("✅ Проверка завершена!")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        check_database()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}\n")
        import traceback
        traceback.print_exc()

