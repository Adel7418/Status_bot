"""
Скрипт для удаления тестовых заявок мастера "Дисп"
"""
import sqlite3
import sys
import io

# Настройка кодировки для консоли Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def delete_test_orders():
    """Удаление тестовых заявок мастера 'Дисп'"""
    
    print("\n" + "="*80)
    print("🗑️  УДАЛЕНИЕ ТЕСТОВЫХ ЗАЯВОК")
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
            return
        
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
            return
        
        print(f"📋 Найдено заявок для удаления: {len(orders)}\n")
        
        # Показываем список заявок
        print("Список заявок:")
        print("-" * 80)
        for order in orders:
            print(f"  ID: {order['id']:3} | {order['equipment_type']:25} | {order['client_name']:20} | {order['status']}")
        print()
        
        # Подтверждение удаления
        response = input("❓ Удалить эти заявки? (yes/y для подтверждения): ").strip().lower()
        
        if response not in ['yes', 'y', 'да', 'д']:
            print("\n❌ Удаление отменено")
            conn.close()
            return
        
        # Удаляем заявки
        print("\n🗑️  Удаление заявок...")
        cursor.execute("DELETE FROM orders WHERE assigned_master_id = ?", (master_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        
        print(f"✅ Удалено заявок: {deleted_count}\n")
        
        # Показываем обновленную статистику
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        
        print(f"📊 Осталось заявок в БД: {total_orders}")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    print("\n" + "="*80)
    print("✅ ГОТОВО!")
    print("="*80 + "\n")


if __name__ == "__main__":
    delete_test_orders()

