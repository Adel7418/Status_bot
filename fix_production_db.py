#!/usr/bin/env python3
"""
Скрипт для исправления продакшн базы данных
Добавляет недостающие колонки deleted_at и version в таблицы users и orders
"""

import os
import sqlite3
import sys


def fix_database():
    """Исправляет структуру базы данных"""

    # Путь к базе данных
    db_path = "/app/data/bot_database.db"

    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return False

    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"✅ Подключились к базе данных: {db_path}")

        # Получаем список всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Найденные таблицы: {tables}")

        # Исправляем таблицу users
        if "users" in tables:
            print("\n🔧 Исправляем таблицу users...")
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]

            if "deleted_at" not in columns:
                print("➕ Добавляем колонку deleted_at в users...")
                cursor.execute("ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP")
                print("✅ Колонка deleted_at добавлена в users")
            else:
                print("✅ Колонка deleted_at уже существует в users")

            if "version" not in columns:
                print("➕ Добавляем колонку version в users...")
                cursor.execute("ALTER TABLE users ADD COLUMN version INTEGER DEFAULT 1")
                print("✅ Колонка version добавлена в users")
            else:
                print("✅ Колонка version уже существует в users")

            # Обновляем существующие записи
            cursor.execute("UPDATE users SET version = 1 WHERE version IS NULL")
            print("✅ Обновлены существующие записи в users")

        # Исправляем таблицу orders
        if "orders" in tables:
            print("\n🔧 Исправляем таблицу orders...")
            cursor.execute("PRAGMA table_info(orders)")
            columns = [row[1] for row in cursor.fetchall()]

            if "deleted_at" not in columns:
                print("➕ Добавляем колонку deleted_at в orders...")
                cursor.execute("ALTER TABLE orders ADD COLUMN deleted_at TIMESTAMP")
                print("✅ Колонка deleted_at добавлена в orders")
            else:
                print("✅ Колонка deleted_at уже существует в orders")

            if "version" not in columns:
                print("➕ Добавляем колонку version в orders...")
                cursor.execute("ALTER TABLE orders ADD COLUMN version INTEGER DEFAULT 1")
                print("✅ Колонка version добавлена в orders")
            else:
                print("✅ Колонка version уже существует в orders")

            # Обновляем существующие записи
            cursor.execute("UPDATE orders SET version = 1 WHERE version IS NULL")
            print("✅ Обновлены существующие записи в orders")

        # Исправляем другие таблицы если нужно
        for table in ["masters", "audit_log"]:
            if table in tables:
                print(f"\n🔧 Проверяем таблицу {table}...")
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]

                if "deleted_at" not in columns:
                    print(f"➕ Добавляем колонку deleted_at в {table}...")
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at TIMESTAMP")
                    print(f"✅ Колонка deleted_at добавлена в {table}")
                else:
                    print(f"✅ Колонка deleted_at уже существует в {table}")

                if "version" not in columns:
                    print(f"➕ Добавляем колонку version в {table}...")
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN version INTEGER DEFAULT 1")
                    print(f"✅ Колонка version добавлена в {table}")
                else:
                    print(f"✅ Колонка version уже существует в {table}")

                # Обновляем существующие записи
                cursor.execute(f"UPDATE {table} SET version = 1 WHERE version IS NULL")
                print(f"✅ Обновлены существующие записи в {table}")

        # Сохраняем изменения
        conn.commit()
        print("\n✅ Все изменения сохранены")

        # Проверяем результат
        print("\n📋 Проверяем результат...")
        for table in ["users", "orders", "masters", "audit_log"]:
            if table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                print(f"  {table}: {columns}")

        conn.close()
        print("\n🎉 База данных успешно исправлена!")
        return True

    except Exception as e:
        print(f"❌ Ошибка при исправлении базы данных: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🔧 Исправление продакшн базы данных...")
    success = fix_database()

    if success:
        print("🎉 Исправление завершено успешно!")
        sys.exit(0)
    else:
        print("💥 Исправление завершилось с ошибкой!")
        sys.exit(1)
