#!/usr/bin/env python3
"""
Проверка, какая база данных используется (ORM или Raw SQL)
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Config
from app.database import Database

print("=" * 80)
print("ПРОВЕРКА КОНФИГУРАЦИИ БАЗЫ ДАННЫХ")
print("=" * 80)
print()

print(f"USE_ORM: {Config.USE_ORM}")
print(f"DATABASE_PATH: {Config.DATABASE_PATH}")
print()

print(f"Используемый класс Database: {Database.__name__}")
print(f"Модуль: {Database.__module__}")
print()

# Проверяем, какой именно класс используется
if "orm" in Database.__module__.lower():
    print("✅ Используется ORM Database (SQLAlchemy)")
else:
    print("❌ Используется Raw SQL Database (sqlite3)")

print()
print("=" * 80)
