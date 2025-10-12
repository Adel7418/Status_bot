"""
Скрипт для синхронизации ролей из .env файла с базой данных
"""
import io
import os
import sqlite3
import sys

from dotenv import load_dotenv


# Настройка кодировки для консоли Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Загружаем переменные из .env
load_dotenv()


def sync_roles():
    """Синхронизация ролей из .env с базой данных"""

    # Получаем ID из .env
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    dispatcher_ids_str = os.getenv("DISPATCHER_IDS", "")

    admin_ids = [int(id_.strip()) for id_ in admin_ids_str.split(",") if id_.strip()]
    dispatcher_ids = [int(id_.strip()) for id_ in dispatcher_ids_str.split(",") if id_.strip()]



    # Подключаемся к базе данных
    conn = sqlite3.connect("bot_database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    updated_count = 0

    # Обрабатываем администраторов
    for admin_id in admin_ids:
        cursor.execute("SELECT id, telegram_id, role FROM users WHERE telegram_id = ?", (admin_id,))
        user = cursor.fetchone()

        if user:
            current_role = user["role"]

            # Проверяем, есть ли уже роль ADMIN
            if "ADMIN" not in current_role.split(","):
                # Добавляем роль ADMIN, сохраняя существующие
                roles = [r.strip() for r in current_role.split(",") if r.strip() and r.strip() != "UNKNOWN"]

                if "ADMIN" not in roles:
                    roles.append("ADMIN")

                new_role = ",".join(sorted(set(roles)))

                cursor.execute("UPDATE users SET role = ? WHERE telegram_id = ?", (new_role, admin_id))
                updated_count += 1
            else:
                pass
        else:
            pass

    # Обрабатываем диспетчеров
    for dispatcher_id in dispatcher_ids:
        cursor.execute("SELECT id, telegram_id, role FROM users WHERE telegram_id = ?", (dispatcher_id,))
        user = cursor.fetchone()

        if user:
            current_role = user["role"]

            # Проверяем, есть ли уже роль DISPATCHER
            if "DISPATCHER" not in current_role.split(","):
                # Добавляем роль DISPATCHER, сохраняя существующие
                roles = [r.strip() for r in current_role.split(",") if r.strip() and r.strip() != "UNKNOWN"]

                if "DISPATCHER" not in roles:
                    roles.append("DISPATCHER")

                new_role = ",".join(sorted(set(roles)))

                cursor.execute("UPDATE users SET role = ? WHERE telegram_id = ?", (new_role, dispatcher_id))
                updated_count += 1
            else:
                pass
        else:
            pass

    conn.commit()

    # Показываем обновленных пользователей

    all_ids = set(admin_ids + dispatcher_ids)
    cursor.execute(f"SELECT telegram_id, username, first_name, last_name, role FROM users WHERE telegram_id IN ({','.join(['?']*len(all_ids))})", tuple(all_ids))
    users = cursor.fetchall()

    if users:
        for user in users:
            f"{user['first_name'] or ''} {user['last_name'] or ''}".strip() or user["username"] or f"ID: {user['telegram_id']}"
            roles = user["role"]

            role_names = {
                "ADMIN": "👑 Администратор",
                "DISPATCHER": "📞 Диспетчер",
                "MASTER": "🔧 Мастер",
                "UNKNOWN": "❓ Неизвестно"
            }

            ", ".join([role_names.get(r.strip(), r) for r in roles.split(",")])


    conn.close()

    if updated_count > 0:
        pass
    else:
        pass

    return updated_count


if __name__ == "__main__":
    try:
        updated = sync_roles()

        if updated > 0:
            pass
    except Exception:
        import traceback
        traceback.print_exc()

