#!/usr/bin/env python3
"""
Скрипт для исправления миграций в продакшн среде
Использует правильные методы Alembic для работы с миграциями
"""

import asyncio
import os
import sys


# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import command
from alembic.config import Config

from app.database.db import Database


async def fix_migrations_production():
    """
    Исправляет миграции в продакшн среде
    """
    print("Исправление миграций в продакшн среде...")

    try:
        # 1. Проверяем текущее состояние базы данных
        print("\n1. Проверяем текущее состояние базы данных...")

        db = Database()
        await db.connect()

        # Проверяем таблицы
        cursor = await db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in await cursor.fetchall()]
        print(f"   Таблицы: {tables}")

        # Проверяем колонки в orders
        cursor = await db.connection.execute("PRAGMA table_info(orders)")
        columns = [row[1] for row in await cursor.fetchall()]
        print(f"   Колонки в orders: {columns}")

        # Проверяем версию миграции
        try:
            cursor = await db.connection.execute("SELECT version_num FROM alembic_version")
            current_version = await cursor.fetchone()
            if current_version:
                print(f"   Текущая версия миграции: {current_version[0]}")
            else:
                print("   Таблица alembic_version пуста")
        except Exception as e:
            print(f"   Ошибка при проверке версии: {e}")

        await db.disconnect()

        # 2. Применяем миграции через Alembic
        print("\n2. Применяем миграции через Alembic...")

        # Настраиваем Alembic
        config = Config("alembic.ini")

        try:
            # Показываем текущую версию
            print("   Текущая версия в Alembic:")
            command.current(config, verbose=True)

            # Показываем историю миграций
            print("\n   История миграций:")
            command.history(config, verbose=True)

            # Пытаемся применить миграции
            print("\n   Применяем миграции...")
            command.upgrade(config, "head")
            print("   Миграции успешно применены через Alembic!")

        except Exception as e:
            print(f"   Alembic не смог применить миграции: {e}")
            print("   Применяем миграции вручную...")

            # 3. Применяем миграции вручную
            await apply_migrations_manually()

        # 4. Финальная проверка
        print("\n3. Финальная проверка...")

        db = Database()
        await db.connect()

        # Проверяем таблицы после миграций
        cursor = await db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_after = [row[0] for row in await cursor.fetchall()]
        print(f"   Таблицы после миграций: {tables_after}")

        # Проверяем колонки в orders
        cursor = await db.connection.execute("PRAGMA table_info(orders)")
        columns_after = [row[1] for row in await cursor.fetchall()]
        print(f"   Колонки в orders после миграций: {columns_after}")

        # Проверяем версию миграции
        cursor = await db.connection.execute("SELECT version_num FROM alembic_version")
        final_version = await cursor.fetchone()
        if final_version:
            print(f"   Финальная версия миграции: {final_version[0]}")

        await db.disconnect()

        print("\nМиграции успешно исправлены!")

    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


async def apply_migrations_manually():
    """
    Применяет миграции вручную, если Alembic не работает
    """
    print("   Применяем миграции вручную...")

    db = Database()
    await db.connect()

    try:
        # Проверяем текущие таблицы
        cursor = await db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in await cursor.fetchall()]

        # Проверяем колонки в orders
        cursor = await db.connection.execute("PRAGMA table_info(orders)")
        columns = [row[1] for row in await cursor.fetchall()]

        # Добавляем недостающие колонки в orders
        if "out_of_city" not in columns:
            await db.connection.execute("ALTER TABLE orders ADD COLUMN out_of_city BOOLEAN")
            print("     Добавлена колонка out_of_city")

        if "estimated_completion_date" not in columns:
            await db.connection.execute(
                "ALTER TABLE orders ADD COLUMN estimated_completion_date TEXT"
            )
            print("     Добавлена колонка estimated_completion_date")

        if "prepayment_amount" not in columns:
            await db.connection.execute("ALTER TABLE orders ADD COLUMN prepayment_amount REAL")
            print("     Добавлена колонка prepayment_amount")

        # Создаем таблицы если их нет
        if "financial_reports" not in tables:
            await db.connection.execute(
                """
                CREATE TABLE financial_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_type TEXT NOT NULL,
                    period_start TEXT,
                    period_end TEXT,
                    total_orders INTEGER NOT NULL DEFAULT 0,
                    total_amount REAL NOT NULL DEFAULT 0.0,
                    total_materials_cost REAL NOT NULL DEFAULT 0.0,
                    total_net_profit REAL NOT NULL DEFAULT 0.0,
                    total_company_profit REAL NOT NULL DEFAULT 0.0,
                    total_master_profit REAL NOT NULL DEFAULT 0.0,
                    average_check REAL NOT NULL DEFAULT 0.0,
                    created_at TEXT
                )
            """
            )
            print("     Создана таблица financial_reports")

        if "master_financial_reports" not in tables:
            await db.connection.execute(
                """
                CREATE TABLE master_financial_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    master_id INTEGER NOT NULL,
                    master_name TEXT NOT NULL,
                    orders_count INTEGER NOT NULL DEFAULT 0,
                    total_amount REAL NOT NULL DEFAULT 0.0,
                    total_materials_cost REAL NOT NULL DEFAULT 0.0,
                    total_net_profit REAL NOT NULL DEFAULT 0.0,
                    total_master_profit REAL NOT NULL DEFAULT 0.0,
                    total_company_profit REAL NOT NULL DEFAULT 0.0,
                    average_check REAL NOT NULL DEFAULT 0.0,
                    reviews_count INTEGER NOT NULL DEFAULT 0,
                    out_of_city_count INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (report_id) REFERENCES financial_reports (id) ON DELETE CASCADE,
                    FOREIGN KEY (master_id) REFERENCES masters (id) ON DELETE CASCADE
                )
            """
            )
            print("     Создана таблица master_financial_reports")

        if "order_reports" not in tables:
            await db.connection.execute(
                """
                CREATE TABLE order_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    equipment_type TEXT NOT NULL,
                    client_name TEXT NOT NULL,
                    client_address TEXT,
                    master_id INTEGER,
                    master_name TEXT,
                    dispatcher_id INTEGER,
                    dispatcher_name TEXT,
                    total_amount REAL NOT NULL,
                    materials_cost REAL NOT NULL,
                    master_profit REAL NOT NULL,
                    company_profit REAL NOT NULL,
                    out_of_city BOOLEAN,
                    has_review BOOLEAN,
                    created_at DATETIME NOT NULL,
                    closed_at DATETIME NOT NULL,
                    completion_time_hours REAL
                )
            """
            )
            print("     Создана таблица order_reports")

        # Создаем индексы
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_financial_reports_type ON financial_reports (report_type)",
            "CREATE INDEX IF NOT EXISTS idx_financial_reports_period ON financial_reports (period_start, period_end)",
            "CREATE INDEX IF NOT EXISTS idx_master_reports_report_id ON master_financial_reports (report_id)",
            "CREATE INDEX IF NOT EXISTS idx_master_reports_master_id ON master_financial_reports (master_id)",
            "CREATE INDEX IF NOT EXISTS idx_order_reports_order_id ON order_reports (order_id)",
            "CREATE INDEX IF NOT EXISTS idx_order_reports_master_id ON order_reports (master_id)",
            "CREATE INDEX IF NOT EXISTS idx_order_reports_closed_at ON order_reports (closed_at)",
        ]

        for index_sql in indexes:
            await db.connection.execute(index_sql)

        print("     Созданы индексы")

        # Устанавливаем версию миграции
        await db.connection.execute(
            "CREATE TABLE IF NOT EXISTS alembic_version (version_num TEXT NOT NULL)"
        )
        await db.connection.execute("DELETE FROM alembic_version")
        await db.connection.execute(
            "INSERT INTO alembic_version (version_num) VALUES (?)", ("004_add_order_reports",)
        )
        print("     Установлена версия миграции 004_add_order_reports")

        await db.connection.commit()
        print("   Миграции успешно применены вручную!")

    except Exception as e:
        print(f"   Ошибка при применении миграций: {e}")
        raise
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(fix_migrations_production())
