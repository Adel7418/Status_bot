"""
Скрипт для создания недостающих индексов для таблицы master_reports_archive
"""
import sqlite3
from pathlib import Path

# Путь к базе данных
DB_PATH = Path(__file__).parent.parent / "bot_database.db"

def create_indexes():
    """Создание индексов для таблицы master_reports_archive"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    indexes = [
        ("idx_master_reports_master_id", "CREATE INDEX IF NOT EXISTS idx_master_reports_master_id ON master_reports_archive (master_id)"),
        ("idx_master_reports_period", "CREATE INDEX IF NOT EXISTS idx_master_reports_period ON master_reports_archive (period_start, period_end)"),
        ("idx_master_reports_created", "CREATE INDEX IF NOT EXISTS idx_master_reports_created ON master_reports_archive (created_at)"),
    ]
    
    try:
        for idx_name, sql in indexes:
            try:
                cursor.execute(sql)
                print(f"Создан индекс: {idx_name}")
            except sqlite3.OperationalError as e:
                print(f"Индекс {idx_name} уже существует или ошибка: {e}")
        
        conn.commit()
        
        # Проверяем созданные индексы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='master_reports_archive'")
        indexes = cursor.fetchall()
        print(f"\nВсего индексов: {len(indexes)}")
        for idx in indexes:
            print(f"  - {idx[0]}")
        
        print("\nИндексы успешно созданы!")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_indexes()







