"""
Скрипт для синхронизации ролей из .env файла с базой данных
"""
import sqlite3
import os
from dotenv import load_dotenv
import sys
import io

# Настройка кодировки для консоли Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Загружаем переменные из .env
load_dotenv()


def sync_roles():
    """Синхронизация ролей из .env с базой данных"""
    
    # Получаем ID из .env
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    dispatcher_ids_str = os.getenv("DISPATCHER_IDS", "")
    
    admin_ids = [int(id_.strip()) for id_ in admin_ids_str.split(",") if id_.strip()]
    dispatcher_ids = [int(id_.strip()) for id_ in dispatcher_ids_str.split(",") if id_.strip()]
    
    print("\n" + "="*80)
    print("🔄 СИНХРОНИЗАЦИЯ РОЛЕЙ ИЗ .ENV ФАЙЛА")
    print("="*80 + "\n")
    
    print(f"📋 Найдено в .env:")
    print(f"   Администраторы: {admin_ids}")
    print(f"   Диспетчеры: {dispatcher_ids}")
    print()
    
    # Подключаемся к базе данных
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    updated_count = 0
    created_count = 0
    
    # Обрабатываем администраторов
    print("👑 Обработка администраторов...")
    for admin_id in admin_ids:
        cursor.execute("SELECT id, telegram_id, role FROM users WHERE telegram_id = ?", (admin_id,))
        user = cursor.fetchone()
        
        if user:
            current_role = user['role']
            
            # Проверяем, есть ли уже роль ADMIN
            if 'ADMIN' not in current_role.split(','):
                # Добавляем роль ADMIN, сохраняя существующие
                roles = [r.strip() for r in current_role.split(',') if r.strip() and r.strip() != 'UNKNOWN']
                
                if 'ADMIN' not in roles:
                    roles.append('ADMIN')
                
                new_role = ','.join(sorted(set(roles)))
                
                cursor.execute("UPDATE users SET role = ? WHERE telegram_id = ?", (new_role, admin_id))
                print(f"   ✅ Обновлен {admin_id}: {current_role} → {new_role}")
                updated_count += 1
            else:
                print(f"   ℹ️  {admin_id}: уже администратор")
        else:
            print(f"   ⚠️  {admin_id}: пользователь не найден (отправьте /start боту)")
    
    # Обрабатываем диспетчеров
    print("\n📞 Обработка диспетчеров...")
    for dispatcher_id in dispatcher_ids:
        cursor.execute("SELECT id, telegram_id, role FROM users WHERE telegram_id = ?", (dispatcher_id,))
        user = cursor.fetchone()
        
        if user:
            current_role = user['role']
            
            # Проверяем, есть ли уже роль DISPATCHER
            if 'DISPATCHER' not in current_role.split(','):
                # Добавляем роль DISPATCHER, сохраняя существующие
                roles = [r.strip() for r in current_role.split(',') if r.strip() and r.strip() != 'UNKNOWN']
                
                if 'DISPATCHER' not in roles:
                    roles.append('DISPATCHER')
                
                new_role = ','.join(sorted(set(roles)))
                
                cursor.execute("UPDATE users SET role = ? WHERE telegram_id = ?", (new_role, dispatcher_id))
                print(f"   ✅ Обновлен {dispatcher_id}: {current_role} → {new_role}")
                updated_count += 1
            else:
                print(f"   ℹ️  {dispatcher_id}: уже диспетчер")
        else:
            print(f"   ⚠️  {dispatcher_id}: пользователь не найден (отправьте /start боту)")
    
    conn.commit()
    
    # Показываем обновленных пользователей
    print("\n📊 РЕЗУЛЬТАТЫ:")
    print("-" * 80)
    
    all_ids = set(admin_ids + dispatcher_ids)
    cursor.execute(f"SELECT telegram_id, username, first_name, last_name, role FROM users WHERE telegram_id IN ({','.join(['?']*len(all_ids))})", tuple(all_ids))
    users = cursor.fetchall()
    
    if users:
        for user in users:
            name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip() or user['username'] or f"ID: {user['telegram_id']}"
            roles = user['role']
            
            role_names = {
                'ADMIN': '👑 Администратор',
                'DISPATCHER': '📞 Диспетчер',
                'MASTER': '🔧 Мастер',
                'UNKNOWN': '❓ Неизвестно'
            }
            
            roles_display = ', '.join([role_names.get(r.strip(), r) for r in roles.split(',')])
            
            print(f"   {user['telegram_id']:>12} | {name:20} | {roles_display}")
    
    conn.close()
    
    print("\n" + "="*80)
    if updated_count > 0:
        print(f"✅ Обновлено пользователей: {updated_count}")
    else:
        print("ℹ️  Нет пользователей для обновления (все уже синхронизированы)")
    print("="*80 + "\n")
    
    return updated_count


if __name__ == "__main__":
    try:
        updated = sync_roles()
        
        if updated > 0:
            print("💡 ВАЖНО: Изменения вступят в силу при следующем обращении пользователя к боту.")
            print("   Пользователи увидят обновленное меню после команды /start\n")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}\n")
        import traceback
        traceback.print_exc()

