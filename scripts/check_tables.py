"""
Проверка существующих таблиц
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "bot_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Получаем список всех таблиц
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]

print("Существующие таблицы в БД:")
print("=" * 60)
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {table}: {count} записей")

conn.close()






