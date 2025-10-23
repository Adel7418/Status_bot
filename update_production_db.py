#!/usr/bin/env python3
"""
Скрипт для обновления продакшн базы данных
Добавляет недостающие колонки deleted_at и version в таблицы orders и masters
"""

import os
import sqlite3
import sys


def update_production_database():
    """Обновляет структуру продакшн базы данных"""

    # Путь к продакшн базе данных
    db_path = "/app/data/bot_database.db"

    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return False

    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"✅ Подключились к продакшн базе данных: {db_path}")

        # Получаем список всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Найденные таблицы: {tables}")

        # Проверяем и обновляем таблицу orders
        if "orders" in tables:
            print("\n🔧 Проверяем таблицу orders...")
            cursor.execute("PRAGMA table_info(orders)")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 Существующие колонки в orders: {columns}")

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

        # Проверяем и обновляем таблицу masters
        if "masters" in tables:
            print("\n🔧 Проверяем таблицу masters...")
            cursor.execute("PRAGMA table_info(masters)")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 Существующие колонки в masters: {columns}")

            if "deleted_at" not in columns:
                print("➕ Добавляем колонку deleted_at в masters...")
                cursor.execute("ALTER TABLE masters ADD COLUMN deleted_at TIMESTAMP")
                print("✅ Колонка deleted_at добавлена в masters")
            else:
                print("✅ Колонка deleted_at уже существует в masters")

            if "version" not in columns:
                print("➕ Добавляем колонку version в masters...")
                cursor.execute("ALTER TABLE masters ADD COLUMN version INTEGER DEFAULT 1")
                print("✅ Колонка version добавлена в masters")
            else:
                print("✅ Колонка version уже существует в masters")

            # Обновляем существующие записи
            cursor.execute("UPDATE masters SET version = 1 WHERE version IS NULL")
            print("✅ Обновлены существующие записи в masters")

        # Сохраняем изменения
        conn.commit()
        print("\n✅ Все изменения сохранены")

        # Проверяем результат
        print("\n📋 Проверяем результат...")
        for table in ["orders", "masters"]:
            if table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                print(f"  {table}: {columns}")

        conn.close()
        print("\n🎉 Продакшн база данных успешно обновлена!")
        return True

    except Exception as e:
        print(f"❌ Ошибка при обновлении базы данных: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🔧 Обновление продакшн базы данных...")
    success = update_production_database()

    if success:
        print("🎉 Обновление завершено успешно!")
        sys.exit(0)
    else:
        print("💥 Обновление завершилось с ошибкой!")
        sys.exit(1)
