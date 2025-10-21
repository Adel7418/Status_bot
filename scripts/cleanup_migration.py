"""
Очистка незавершенной миграции
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "bot_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Очистка незавершенной миграции...")
print("=" * 60)

# Удаляем временную таблицу, если она есть
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '_alembic_tmp_%'")
temp_tables = [row[0] for row in cursor.fetchall()]

if temp_tables:
    for table in temp_tables:
        print(f"Удаление временной таблицы: {table}")
        cursor.execute(f"DROP TABLE {table}")
    conn.commit()
    print("Временные таблицы удалены.")
else:
    print("Временных таблиц не найдено.")

# Проверяем наличие старых таблиц
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='master_reports_archive'")
if cursor.fetchone():
    print("\nНайдена старая таблица master_reports_archive")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='master_report_archives'")
    if cursor.fetchone():
        print("Найдена новая таблица master_report_archives")
        print("\nОбе таблицы существуют. Нужно перенести данные и удалить старую.")
        
        # Проверяем данные в старой таблице
        cursor.execute("SELECT COUNT(*) FROM master_reports_archive")
        old_count = cursor.fetchone()[0]
        print(f"Записей в старой таблице: {old_count}")
        
        cursor.execute("SELECT COUNT(*) FROM master_report_archives")
        new_count = cursor.fetchone()[0]
        print(f"Записей в новой таблице: {new_count}")
else:
    print("\nСтарая таблица master_reports_archive не найдена.")

# Проверяем order_reports
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_reports'")
if cursor.fetchone():
    print("\nНайдена таблица order_reports (должна быть удалена)")
    cursor.execute("SELECT COUNT(*) FROM order_reports")
    count = cursor.fetchone()[0]
    print(f"Записей в таблице: {count}")

conn.close()






