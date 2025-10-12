"""
Скрипт для автоматического удаления тестовых заявок мастера "Дисп"
(без запроса подтверждения)
"""
import sqlite3
import sys
import io

# Настройка кодировки для консоли Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def delete_test_orders_auto():
    """Автоматическое удаление тестовых заявок мастера 'Дисп'"""
    
    print("\n" + "="*80)
    print("🗑️  АВТОМАТИЧЕСКОЕ УДАЛЕНИЕ ТЕСТОВЫХ ЗАЯВОК")
    print("="*80 + "\n")
    
    # Подключение к БД
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Находим ID мастера "Дисп"
        cursor.execute("""
            SELECT m.id, m.telegram_id, u.first_name 
            FROM masters m
            JOIN users u ON m.telegram_id = u.telegram_id
            WHERE u.first_name = 'Дисп'
        """)
        master = cursor.fetchone()
        
        if not master:
            print("❌ Мастер 'Дисп' не найден в базе данных")
            conn.close()
            return 0
        
        master_id = master['id']
        print(f"✅ Найден мастер 'Дисп' (ID: {master_id}, Telegram ID: {master['telegram_id']})\n")
        
        # Находим все заявки этого мастера
        cursor.execute("""
            SELECT id, equipment_type, client_name, status, created_at
            FROM orders
            WHERE assigned_master_id = ?
        """, (master_id,))
        
        orders = cursor.fetchall()
        
        if not orders:
            print("ℹ️  У мастера 'Дисп' нет заявок для удаления")
            conn.close()
            return 0
        
        print(f"📋 Найдено заявок для удаления: {len(orders)}\n")
        
        # Показываем список заявок
        print("Список заявок, которые будут удалены:")
        print("-" * 80)
        for order in orders:
            status_emoji = {
                'NEW': '🆕', 'ASSIGNED': '👨‍🔧', 'ACCEPTED': '✅',
                'ONSITE': '🏠', 'CLOSED': '💰', 'REFUSED': '❌', 'DR': '⏳'
            }.get(order['status'], '❓')
            
            print(f"  {status_emoji} ID: {order['id']:3} | {order['equipment_type']:25} | {order['client_name']:20} | {order['status']}")
        print()
        
        # Удаляем заявки
        print("🗑️  Удаление заявок...")
        cursor.execute("DELETE FROM orders WHERE assigned_master_id = ?", (master_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        
        print(f"✅ Успешно удалено заявок: {deleted_count}\n")
        
        # Показываем обновленную статистику
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM orders
            GROUP BY status
        """)
        stats = cursor.fetchall()
        
        print(f"📊 Статистика после удаления:")
        print(f"   Всего заявок в БД: {total_orders}")
        
        if stats:
            print(f"   По статусам:")
            for stat in stats:
                status_names = {
                    'NEW': 'Новые', 'ASSIGNED': 'Назначены', 'ACCEPTED': 'Приняты',
                    'ONSITE': 'На объекте', 'CLOSED': 'Завершены', 'REFUSED': 'Отклонены',
                    'DR': 'Длительный ремонт'
                }
                print(f"      - {status_names.get(stat['status'], stat['status'])}: {stat['count']}")
        
        return deleted_count
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
        return 0
    finally:
        conn.close()
        print("\n" + "="*80)
        print("✅ ОПЕРАЦИЯ ЗАВЕРШЕНА!")
        print("="*80 + "\n")


if __name__ == "__main__":
    deleted = delete_test_orders_auto()
    sys.exit(0 if deleted >= 0 else 1)

