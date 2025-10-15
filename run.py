#!/usr/bin/env python3
"""
Универсальный скрипт для запуска команд проекта
Работает на Windows/Linux/Mac без установки make
"""

import sys
import subprocess
import os
from pathlib import Path

# Определяем команды
COMMANDS = {
    # Основные команды
    "run": {
        "desc": "Запустить бота",
        "cmd": ["python", "bot.py"]
    },
    "test": {
        "desc": "Запустить тесты",
        "cmd": ["pytest"]
    },
    "lint": {
        "desc": "Проверить код линтерами",
        "cmd": ["ruff", "check", "."]
    },
    "format": {
        "desc": "Отформатировать код",
        "cmd": ["black", "."]
    },
    
    # Миграции
    "migrate": {
        "desc": "Применить миграции БД",
        "cmd": ["alembic", "upgrade", "head"]
    },
    "migrate-current": {
        "desc": "Показать текущую версию БД",
        "cmd": ["alembic", "current"]
    },
    "migrate-history": {
        "desc": "Показать историю миграций",
        "cmd": ["alembic", "history"]
    },
    
    # Git команды
    "git-status": {
        "desc": "Показать статус Git",
        "cmd": ["git", "status"]
    },
    "git-add": {
        "desc": "Добавить все изменения",
        "cmd": ["git", "add", "-A"]
    },
    "git-push": {
        "desc": "Отправить в GitHub",
        "cmd": ["git", "push", "origin", "main"]
    },
    "git-pull": {
        "desc": "Получить из GitHub",
        "cmd": ["git", "pull", "origin", "main"]
    },
    "git-log": {
        "desc": "Показать последние коммиты",
        "cmd": ["git", "log", "--oneline", "-10"]
    },
    
    # Docker команды
    "docker-up": {
        "desc": "Запустить в Docker (dev)",
        "cmd": ["docker", "compose", "-f", "docker/docker-compose.yml", "up", "-d"]
    },
    "docker-down": {
        "desc": "Остановить Docker контейнеры",
        "cmd": ["docker", "compose", "-f", "docker/docker-compose.yml", "down"]
    },
    "docker-logs": {
        "desc": "Показать логи Docker",
        "cmd": ["docker", "compose", "-f", "docker/docker-compose.yml", "logs", "-f", "bot"]
    },
    
    # Production команды
    "prod-logs": {
        "desc": "Логи production",
        "cmd": ["docker", "compose", "-f", "docker/docker-compose.prod.yml", "logs", "-f", "bot"]
    },
    "prod-status": {
        "desc": "Статус production",
        "cmd": ["docker", "compose", "-f", "docker/docker-compose.prod.yml", "ps"]
    },
    "prod-restart": {
        "desc": "Перезапустить production",
        "cmd": ["docker", "compose", "-f", "docker/docker-compose.prod.yml", "restart", "bot"]
    },
}

# Специальные команды
SPECIAL_COMMANDS = {
    "help": "Показать эту справку",
    "git-commit": "Создать коммит (использование: python run.py git-commit 'сообщение')",
    "git-save": "Быстрое сохранение (add + commit + push)",
    "migrate-create": "Создать миграцию (использование: python run.py migrate-create 'описание')",
}


def print_help():
    """Показать справку"""
    print("Telegram Repair Bot - Команды")
    print("=" * 60)
    print("\nИспользование: python run.py <команда> [аргументы]\n")
    
    print("ОСНОВНЫЕ КОМАНДЫ:")
    for cmd in ["run", "test", "lint", "format"]:
        if cmd in COMMANDS:
            print(f"  {cmd:20} - {COMMANDS[cmd]['desc']}")
    
    print("\nМИГРАЦИИ:")
    for cmd in ["migrate", "migrate-current", "migrate-history", "migrate-create"]:
        if cmd in COMMANDS:
            print(f"  {cmd:20} - {COMMANDS[cmd]['desc']}")
        elif cmd in SPECIAL_COMMANDS:
            print(f"  {cmd:20} - {SPECIAL_COMMANDS[cmd]}")
    
    print("\nGIT:")
    for cmd in ["git-status", "git-add", "git-commit", "git-push", "git-pull", "git-log", "git-save"]:
        if cmd in COMMANDS:
            print(f"  {cmd:20} - {COMMANDS[cmd]['desc']}")
        elif cmd in SPECIAL_COMMANDS:
            print(f"  {cmd:20} - {SPECIAL_COMMANDS[cmd]}")
    
    print("\nDOCKER:")
    for cmd in ["docker-up", "docker-down", "docker-logs"]:
        if cmd in COMMANDS:
            print(f"  {cmd:20} - {COMMANDS[cmd]['desc']}")
    
    print("\nPRODUCTION:")
    for cmd in ["prod-logs", "prod-status", "prod-restart"]:
        if cmd in COMMANDS:
            print(f"  {cmd:20} - {COMMANDS[cmd]['desc']}")
    
    print("\nПРИМЕРЫ:")
    print("  python run.py run")
    print("  python run.py git-commit 'fix: исправил баг'")
    print("  python run.py git-save 'feat: добавил функцию'")
    print("  python run.py migrate-create 'add new field'")
    print("\n" + "=" * 60)


def run_command(cmd_list):
    """Выполнить команду"""
    try:
        result = subprocess.run(cmd_list, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Ошибка при выполнении команды: {e}")
        return False
    except FileNotFoundError:
        print(f"[ERROR] Команда не найдена: {cmd_list[0]}")
        print(f"Установите необходимые зависимости")
        return False


def git_commit(message):
    """Создать git коммит"""
    if not message:
        print("[ERROR] Укажите сообщение коммита")
        print("Использование: python run.py git-commit 'ваше сообщение'")
        return False
    
    print("[INFO] Создание коммита...")
    return run_command(["git", "commit", "-m", message])


def git_save(message):
    """Быстрое сохранение: add + commit + push"""
    if not message:
        print("[ERROR] Укажите сообщение коммита")
        print("Использование: python run.py git-save 'ваше сообщение'")
        return False
    
    print("[INFO] Добавление изменений...")
    if not run_command(["git", "add", "-A"]):
        return False
    
    print("[INFO] Создание коммита...")
    if not run_command(["git", "commit", "-m", message]):
        return False
    
    print("[INFO] Отправка в GitHub...")
    if not run_command(["git", "push", "origin", "main"]):
        return False
    
    print("[SUCCESS] Всё готово!")
    return True


def migrate_create(description):
    """Создать новую миграцию"""
    if not description:
        print("[ERROR] Укажите описание миграции")
        print("Использование: python run.py migrate-create 'описание'")
        return False
    
    print(f"[INFO] Создание миграции: {description}")
    return run_command(["alembic", "revision", "--autogenerate", "-m", description])


def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)
    
    command = sys.argv[1]
    
    # Справка
    if command in ["help", "-h", "--help"]:
        print_help()
        sys.exit(0)
    
    # Git commit
    if command == "git-commit":
        message = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        success = git_commit(message)
        sys.exit(0 if success else 1)
    
    # Git save
    if command == "git-save":
        message = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        success = git_save(message)
        sys.exit(0 if success else 1)
    
    # Migrate create
    if command == "migrate-create":
        description = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        success = migrate_create(description)
        sys.exit(0 if success else 1)
    
    # Обычные команды
    if command in COMMANDS:
        print(f"[RUN] {COMMANDS[command]['desc']}")
        success = run_command(COMMANDS[command]['cmd'])
        sys.exit(0 if success else 1)
    
    # Неизвестная команда
    print(f"[ERROR] Неизвестная команда: {command}")
    print("Используйте: python run.py help")
    sys.exit(1)


if __name__ == "__main__":
    main()

