"""
Проверка на наличие NULL значений в timestamp колонках
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "bot_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Проверяем наличие NULL значений
checks = [
    ("users", "created_at"),
    ("masters", "created_at"),
    ("orders", "created_at"),
    ("orders", "updated_at"),
    ("audit_log", "timestamp"),
    ("order_status_history", "changed_at"),
]

print("Проверка NULL значений в timestamp колонках:")
print("=" * 60)

for table, column in checks:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")
        count = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        total = cursor.fetchone()[0]
        status = "X ЕСТЬ NULL" if count > 0 else "OK"
        print(f"{table}.{column}: {count}/{total} NULL значений - {status}")
    except Exception as e:
        print(f"{table}.{column}: ОШИБКА - {e}")

conn.close()

