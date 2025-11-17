#!/usr/bin/env python3
"""
Проверка наличия колонки refuse_reason в таблице orders
"""

import sqlite3
from pathlib import Path


def check_column(db_path: str) -> None:
    """Проверяет наличие колонки refuse_reason"""
    
    if not Path(db_path).exists():
        print(f"⚠️  База данных не найдена: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Получаем информацию о колонках
    cursor.execute("PRAGMA table_info(orders)")
    columns = cursor.fetchall()
    
    print(f"\n📂 {db_path}")
    print("=" * 60)
    
    # Ищем refuse_reason
    refuse_reason_col = None
    for col in columns:
        if col[1] == 'refuse_reason':
            refuse_reason_col = col
            break
    
    if refuse_reason_col:
        print("✅ Колонка refuse_reason найдена!")
        print(f"   - Тип: {refuse_reason_col[2]}")
        print(f"   - Nullable: {'Да' if refuse_reason_col[3] == 0 else 'Нет'}")
        print(f"   - Default: {refuse_reason_col[4] if refuse_reason_col[4] else 'NULL'}")
        
        # Проверяем существующие данные
        cursor.execute("SELECT COUNT(*) FROM orders WHERE refuse_reason IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"   - Записей с причиной отказа: {count}")
        
    else:
        print("❌ Колонка refuse_reason НЕ найдена!")
        print("   Необходимо применить миграцию.")
    
    conn.close()


def main():
    print("🔍 Проверка колонки refuse_reason в таблице orders")
    print("=" * 60)
    
    # Проверяем все возможные базы данных
    databases = [
        "data/bot_database.db",
        "data/city1/bot_database.db",
        "data/city2/bot_database.db",
        "bot_database.db",
    ]
    
    found = False
    for db_path in databases:
        if Path(db_path).exists():
            check_column(db_path)
            found = True
    
    if not found:
        print("\n❌ Не найдено ни одной базы данных!")
    else:
        print("\n" + "=" * 60)
        print("✅ Проверка завершена")


if __name__ == "__main__":
    main()

