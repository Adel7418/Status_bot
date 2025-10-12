"""
Скрипт для создания резервной копии базы данных
Использование: python backup_db.py
"""
import os
import shutil
from datetime import datetime, timedelta
import sys
import io

# Настройка кодировки для консоли Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def format_size(size_bytes):
    """Форматирование размера файла"""
    return f"{size_bytes / 1024:.2f} KB"


def backup_database(keep_days=30):
    """
    Создание резервной копии базы данных
    
    Args:
        keep_days: Количество дней для хранения копий (по умолчанию 30)
    """
    
    db_file = "bot_database.db"
    backup_dir = "backups"
    
    print("\n" + "="*80)
    print("  📦 РЕЗЕРВНОЕ КОПИРОВАНИЕ БАЗЫ ДАННЫХ")
    print("="*80 + "\n")
    
    # Проверка существования БД
    if not os.path.exists(db_file):
        print(f"❌ Ошибка: Файл {db_file} не найден!")
        return False
    
    # Создание директории для backup
    if not os.path.exists(backup_dir):
        print(f"📁 Создание директории: {backup_dir}")
        os.makedirs(backup_dir)
    
    # Получение размера БД
    db_size = os.path.getsize(db_file)
    print(f"📊 База данных: {db_file}")
    print(f"📏 Размер: {format_size(db_size)}\n")
    
    # Создание имени файла с датой и временем
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = os.path.join(backup_dir, f"bot_database_{timestamp}.db")
    
    # Создание резервной копии
    print("⏳ Создание резервной копии...")
    try:
        shutil.copy2(db_file, backup_file)
        print("✅ Резервная копия создана!")
        print(f"📁 Файл: {backup_file}\n")
    except Exception as e:
        print(f"❌ Ошибка при создании копии: {e}")
        return False
    
    # Подсчет всех резервных копий
    backup_files = [f for f in os.listdir(backup_dir) if f.startswith("bot_database_") and f.endswith(".db")]
    backup_files.sort(reverse=True)
    
    print(f"📊 Всего резервных копий: {len(backup_files)}")
    
    # Удаление старых копий
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    deleted_count = 0
    
    print(f"\n🗑️  Проверка старых копий (старше {keep_days} дней)...")
    
    for backup_filename in backup_files:
        backup_path = os.path.join(backup_dir, backup_filename)
        file_time = datetime.fromtimestamp(os.path.getmtime(backup_path))
        
        if file_time < cutoff_date:
            print(f"   Удаление: {backup_filename}")
            try:
                os.remove(backup_path)
                deleted_count += 1
            except Exception as e:
                print(f"   ⚠️  Не удалось удалить {backup_filename}: {e}")
    
    if deleted_count > 0:
        print(f"✅ Удалено старых копий: {deleted_count}")
    else:
        print("ℹ️  Старых копий для удаления не найдено")
    
    # Список последних резервных копий
    print("\n📋 Последние 5 резервных копий:")
    print("-" * 80)
    
    recent_backups = backup_files[:5]
    for backup_filename in recent_backups:
        backup_path = os.path.join(backup_dir, backup_filename)
        size = os.path.getsize(backup_path)
        mtime = datetime.fromtimestamp(os.path.getmtime(backup_path))
        print(f"   {backup_filename:40} {format_size(size):>12} {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "="*80)
    print("            ✅ ГОТОВО!")
    print("="*80 + "\n")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Создание резервной копии базы данных')
    parser.add_argument('--keep-days', type=int, default=30,
                       help='Количество дней для хранения копий (по умолчанию: 30)')
    
    args = parser.parse_args()
    
    success = backup_database(keep_days=args.keep_days)
    
    if not success:
        sys.exit(1)

