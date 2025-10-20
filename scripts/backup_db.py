"""
Скрипт для создания резервной копии базы данных
Использование: python backup_db.py
"""

import io
import os
import shutil
import sys
from datetime import datetime, timedelta


# Настройка кодировки для консоли Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def format_size(size_bytes):
    """Форматирование размера файла"""
    return f"{size_bytes / 1024:.2f} KB"


def backup_database(keep_days=30):
    """
    Создание резервной копии базы данных

    Args:
        keep_days: Количество дней для хранения копий (по умолчанию 30)
    """

    # Поддержка Docker: используем переменную окружения или относительный путь
    db_file = os.environ.get("DATABASE_PATH", "bot_database.db")
    
    # Если указан полный путь в DATABASE_PATH, используем его директорию для backups
    if os.path.isabs(db_file):
        # В Docker: /app/data/bot_database.db -> backups в /app/backups
        backup_dir = "/app/backups"
    else:
        # Локально: bot_database.db -> backups в ./backups
        backup_dir = "backups"

    # Проверка существования БД
    if not os.path.exists(db_file):
        return False

    # Создание директории для backup
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Получение размера БД
    os.path.getsize(db_file)

    # Создание имени файла с датой и временем
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = os.path.join(backup_dir, f"bot_database_{timestamp}.db")

    # Создание резервной копии
    try:
        shutil.copy2(db_file, backup_file)
    except Exception:
        return False

    # Подсчет всех резервных копий
    backup_files = [
        f for f in os.listdir(backup_dir) if f.startswith("bot_database_") and f.endswith(".db")
    ]
    backup_files.sort(reverse=True)

    # Удаление старых копий
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    deleted_count = 0

    for backup_filename in backup_files:
        backup_path = os.path.join(backup_dir, backup_filename)
        file_time = datetime.fromtimestamp(os.path.getmtime(backup_path))

        if file_time < cutoff_date:
            try:
                os.remove(backup_path)
                deleted_count += 1
            except Exception:
                pass

    if deleted_count > 0:
        pass
    else:
        pass

    # Список последних резервных копий

    recent_backups = backup_files[:5]
    for backup_filename in recent_backups:
        backup_path = os.path.join(backup_dir, backup_filename)
        os.path.getsize(backup_path)
        datetime.fromtimestamp(os.path.getmtime(backup_path))

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Создание резервной копии базы данных")
    parser.add_argument(
        "--keep-days",
        type=int,
        default=30,
        help="Количество дней для хранения копий (по умолчанию: 30)",
    )

    args = parser.parse_args()

    success = backup_database(keep_days=args.keep_days)

    if not success:
        sys.exit(1)
