#!/usr/bin/env python3
"""
Скрипт для проверки работы системы постоянного хранения
"""

import asyncio
import io
import sys
from pathlib import Path


# Фикс кодировки для Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime

from app.database.db import Database


async def test_soft_delete_schema():
    """Проверка наличия полей soft delete в схеме"""
    print("\n" + "=" * 60)
    print("🔍 ТЕСТ 1: Проверка схемы БД")
    print("=" * 60)

    db = Database()
    await db.connect()

    try:
        # Проверяем наличие deleted_at в orders
        cursor = await db.connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'"
        )
        schema = await cursor.fetchone()

        if schema and "deleted_at" in schema["sql"]:
            print("✅ Поле deleted_at найдено в таблице orders")
        else:
            print("❌ Поле deleted_at НЕ найдено в таблице orders")
            print("   Выполните: alembic upgrade head")

        # Проверяем индексы
        cursor = await db.connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND tbl_name='orders'
            AND name LIKE '%deleted%'
            """
        )
        indexes = await cursor.fetchall()

        if indexes:
            print(f"✅ Найдены индексы для deleted_at: {len(indexes)} шт.")
            for idx in indexes:
                print(f"   - {idx['name']}")
        else:
            print("⚠️  Индексы для deleted_at не найдены")

    finally:
        await db.disconnect()


async def test_history_tables():
    """Проверка таблиц истории"""
    print("\n" + "=" * 60)
    print("📊 ТЕСТ 2: Проверка таблиц истории")
    print("=" * 60)

    db = Database()
    await db.connect()

    try:
        # Проверяем order_status_history
        cursor = await db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='order_status_history'"
        )
        table = await cursor.fetchone()

        if table:
            # Считаем записи
            cursor = await db.connection.execute("SELECT COUNT(*) as cnt FROM order_status_history")
            count = await cursor.fetchone()
            print(f"✅ Таблица order_status_history найдена ({count['cnt']} записей)")
        else:
            print("❌ Таблица order_status_history НЕ найдена")

        # Проверяем entity_history
        cursor = await db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entity_history'"
        )
        table = await cursor.fetchone()

        if table:
            cursor = await db.connection.execute("SELECT COUNT(*) as cnt FROM entity_history")
            count = await cursor.fetchone()
            print(f"✅ Таблица entity_history найдена ({count['cnt']} записей)")
        else:
            print("⚠️  Таблица entity_history НЕ найдена (может быть не создана)")

        # Проверяем audit_log
        cursor = await db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'"
        )
        table = await cursor.fetchone()

        if table:
            cursor = await db.connection.execute("SELECT COUNT(*) as cnt FROM audit_log")
            count = await cursor.fetchone()
            print(f"✅ Таблица audit_log найдена ({count['cnt']} записей)")
        else:
            print("❌ Таблица audit_log НЕ найдена")

    finally:
        await db.disconnect()


async def test_orders_statistics():
    """Статистика по заявкам"""
    print("\n" + "=" * 60)
    print("📈 ТЕСТ 3: Статистика заявок")
    print("=" * 60)

    db = Database()
    await db.connect()

    try:
        # Всего заявок
        cursor = await db.connection.execute("SELECT COUNT(*) as cnt FROM orders")
        total = await cursor.fetchone()
        print(f"📋 Всего заявок в базе: {total['cnt']}")

        # Активные заявки
        cursor = await db.connection.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE deleted_at IS NULL"
        )
        active = await cursor.fetchone()
        print(f"✅ Активных заявок: {active['cnt']}")

        # Удаленные заявки
        cursor = await db.connection.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE deleted_at IS NOT NULL"
        )
        deleted = await cursor.fetchone()
        print(f"🗑️  Удаленных заявок: {deleted['cnt']}")

        # По статусам (только активные)
        cursor = await db.connection.execute(
            """
            SELECT status, COUNT(*) as cnt
            FROM orders
            WHERE deleted_at IS NULL
            GROUP BY status
            ORDER BY cnt DESC
            """
        )
        statuses = await cursor.fetchall()

        if statuses:
            print("\n📊 Распределение по статусам (активные):")
            for row in statuses:
                print(f"   {row['status']}: {row['cnt']}")

    finally:
        await db.disconnect()


async def test_encryption():
    """Проверка шифрования"""
    print("\n" + "=" * 60)
    print("🔐 ТЕСТ 4: Проверка шифрования")
    print("=" * 60)

    try:
        from app.utils.encryption import decrypt, encrypt

        # Тестовые данные
        test_data = [
            "79991234567",
            "Москва, ул. Ленина 1",
            "Иван Иванович Петров",
        ]

        all_ok = True
        for data in test_data:
            encrypted = encrypt(data)
            decrypted = decrypt(encrypted)

            if data == decrypted:
                print("✅ Тест пройден:")
                print(f"   Оригинал:  {data[:30]}...")
                print(f"   Шифр:      {encrypted[:30]}...")
                print(f"   Дешифр:    {decrypted[:30]}...")
            else:
                print(f"❌ Тест НЕ пройден: {data}")
                all_ok = False

        if all_ok:
            print("\n✅ Все тесты шифрования пройдены успешно!")
        else:
            print("\n❌ Некоторые тесты не прошли проверку")

    except ImportError:
        print("⚠️  Модуль encryption не найден")
        print("   Создайте файл: app/utils/encryption.py")
    except Exception as e:
        print(f"❌ Ошибка при тестировании шифрования: {e}")
        print("   Проверьте наличие ENCRYPTION_KEY в .env")


async def test_search_performance():
    """Проверка производительности поиска"""
    print("\n" + "=" * 60)
    print("⚡ ТЕСТ 5: Производительность поиска")
    print("=" * 60)

    db = Database()
    await db.connect()

    try:
        # Тест 1: Поиск по ID (с индексом)
        start = datetime.now()
        cursor = await db.connection.execute("SELECT * FROM orders WHERE id = 1")
        await cursor.fetchone()
        time1 = (datetime.now() - start).total_seconds() * 1000

        print(f"⚡ Поиск по ID: {time1:.2f} мс")

        # Тест 2: Поиск по статусу (с индексом)
        start = datetime.now()
        cursor = await db.connection.execute(
            "SELECT * FROM orders WHERE deleted_at IS NULL AND status = 'NEW' LIMIT 10"
        )
        await cursor.fetchall()
        time2 = (datetime.now() - start).total_seconds() * 1000

        print(f"⚡ Поиск по статусу: {time2:.2f} мс")

        # Тест 3: Поиск с JOIN
        start = datetime.now()
        cursor = await db.connection.execute(
            """
            SELECT o.*, u.first_name
            FROM orders o
            LEFT JOIN users u ON o.dispatcher_id = u.telegram_id
            WHERE o.deleted_at IS NULL
            LIMIT 10
            """
        )
        await cursor.fetchall()
        time3 = (datetime.now() - start).total_seconds() * 1000

        print(f"⚡ Поиск с JOIN: {time3:.2f} мс")

        # Оценка
        if time3 < 100:
            print("\n✅ Производительность отличная!")
        elif time3 < 500:
            print("\n✅ Производительность хорошая")
        else:
            print("\n⚠️  Производительность требует оптимизации")

    finally:
        await db.disconnect()


async def test_indexes():
    """Проверка индексов"""
    print("\n" + "=" * 60)
    print("🔍 ТЕСТ 6: Проверка индексов")
    print("=" * 60)

    db = Database()
    await db.connect()

    try:
        cursor = await db.connection.execute(
            """
            SELECT name, tbl_name
            FROM sqlite_master
            WHERE type='index' AND tbl_name IN ('orders', 'users', 'masters')
            ORDER BY tbl_name, name
            """
        )
        indexes = await cursor.fetchall()

        if indexes:
            print(f"✅ Найдено индексов: {len(indexes)}\n")

            current_table = None
            for idx in indexes:
                if idx["tbl_name"] != current_table:
                    current_table = idx["tbl_name"]
                    print(f"\n📋 Таблица: {current_table}")

                print(f"   - {idx['name']}")
        else:
            print("❌ Индексы не найдены")

    finally:
        await db.disconnect()


async def main():
    """Главная функция"""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ СИСТЕМЫ ПОСТОЯННОГО ХРАНЕНИЯ")
    print("=" * 60)

    try:
        # Запускаем все тесты
        await test_soft_delete_schema()
        await test_history_tables()
        await test_orders_statistics()
        await test_encryption()
        await test_search_performance()
        await test_indexes()

        # Итоги
        print("\n" + "=" * 60)
        print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print("=" * 60)
        print("\n📚 Для подробной информации см.:")
        print("   - docs/ПОСТОЯННОЕ_ХРАНЕНИЕ_ЗАЯВОК.md")
        print("   - docs/QUICKSTART_PERMANENT_STORAGE.md")
        print("   - docs/PERMANENT_STORAGE_GUIDE.md")
        print()

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
