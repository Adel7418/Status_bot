#!/usr/bin/env python3
"""
Скрипт для установки зависимостей на сервере
"""

import subprocess
import sys


def install_package(package):
    """Установка пакета через pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"[OK] {package} установлен успешно")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Ошибка установки {package}: {e}")


def main():
    """Основная функция"""
    print("Установка зависимостей для Alembic...")

    # Список необходимых пакетов
    packages = ["python-dotenv", "alembic", "sqlalchemy", "aiosqlite"]

    for package in packages:
        install_package(package)

    print("\nУстановка завершена!")
    print("Теперь можно запустить: alembic upgrade head")


if __name__ == "__main__":
    main()
