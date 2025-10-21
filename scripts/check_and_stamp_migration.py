"""
Скрипт для проверки существования таблицы и пометки миграции как примененной
"""
import sqlite3
from pathlib import Path

# Путь к базе данных
DB_PATH = Path(__file__).parent.parent / "bot_database.db"

def check_and_stamp():
    """Проверка таблицы и пометка миграции"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Проверяем существование таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='master_reports_archive'")
        table_exists = cursor.fetchone() is not None
        
        print(f"Таблица master_reports_archive существует: {table_exists}")
        
        if table_exists:
            # Проверяем, есть ли индексы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='master_reports_archive'")
            indexes = cursor.fetchall()
            print(f"Найдено индексов: {len(indexes)}")
            for idx in indexes:
                print(f"  - {idx[0]}")
            
            # Обновляем версию миграции
            cursor.execute("UPDATE alembic_version SET version_num = ?", ("010_create_master_reports_archive",))
            conn.commit()
            print("\nВерсия миграции обновлена до: 010_create_master_reports_archive")
            print("Миграция успешно применена!")
        else:
            print("\nТаблица не существует. Нужно применить миграцию.")
            
    except Exception as e:
        print(f"Ошибка: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    check_and_stamp()







