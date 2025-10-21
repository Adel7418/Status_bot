"""
Получение имен внешних ключей
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "bot_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Получаем список всех таблиц
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [row[0] for row in cursor.fetchall()]

print("Внешние ключи в таблицах:")
print("=" * 80)

for table in tables:
    cursor.execute(f"PRAGMA foreign_key_list({table})")
    fks = cursor.fetchall()
    if fks:
        print(f"\n{table}:")
        for fk in fks:
            print(f"  id={fk[0]}, seq={fk[1]}, table={fk[2]}, from={fk[3]}, to={fk[4]}")

conn.close()






