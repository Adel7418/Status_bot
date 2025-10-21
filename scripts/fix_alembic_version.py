"""
Скрипт для исправления таблицы alembic_version
"""
import sqlite3
from pathlib import Path

# Путь к базе данных
DB_PATH = Path(__file__).parent.parent / "bot_database.db"

def fix_alembic_version():
    """Исправление таблицы alembic_version"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Проверяем текущее состояние
        cursor.execute("SELECT * FROM alembic_version")
        current_versions = cursor.fetchall()
        print(f"Текущие версии в БД: {current_versions}")
        
        # Очищаем таблицу
        cursor.execute("DELETE FROM alembic_version")
        print("Таблица alembic_version очищена")
        
        # Устанавливаем правильную версию
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES (?)", ("008_add_soft_delete",))
        conn.commit()
        print("Установлена версия: 008_add_soft_delete")
        
        # Проверяем результат
        cursor.execute("SELECT * FROM alembic_version")
        new_versions = cursor.fetchall()
        print(f"Новая версия в БД: {new_versions}")
        
        print("\n✅ База данных успешно исправлена!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_alembic_version()







