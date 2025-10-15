# Makefile для упрощения команд разработки

.PHONY: help install install-dev test lint format clean run migrate migrate-create docker-build docker-up docker-down docker-migrate

help:  ## Показать эту справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Установить production зависимости
	pip install -r requirements.txt

install-dev:  ## Установить все зависимости (включая dev)
	pip install -r requirements-dev.txt
	pre-commit install

test:  ## Запустить тесты
	pytest

test-cov:  ## Запустить тесты с coverage
	pytest --cov=app --cov-report=html --cov-report=term-missing

lint:  ## Проверить код линтерами
	ruff check .
	black --check .
	mypy app/ --ignore-missing-imports

format:  ## Отформатировать код
	black .
	ruff check --fix .
	isort .

pre-commit:  ## Запустить pre-commit hooks
	pre-commit run --all-files

clean:  ## Очистить временные файлы
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/

run:  ## Запустить бота
	python bot.py

migrate:  ## Применить миграции БД
	alembic upgrade head

migrate-create:  ## Создать новую миграцию (использование: make migrate-create MSG="описание")
	alembic revision --autogenerate -m "$(MSG)"

migrate-history:  ## Показать историю миграций
	alembic history

migrate-current:  ## Показать текущую версию БД
	alembic current

migrate-downgrade:  ## Откатить одну миграцию
	alembic downgrade -1

backup:  ## Создать backup базы данных
	python backup_db.py

check-db:  ## Проверить базу данных
	python check_database.py

sync-roles:  ## Синхронизировать роли из .env
	python sync_roles_from_env.py

docker-build:  ## Собрать Docker образ
	docker build -f docker/Dockerfile -t telegram-repair-bot:latest .

docker-up:  ## Запустить через Docker Compose (dev)
	cd docker && docker compose -f docker-compose.yml up -d

docker-up-dev:  ## Запустить в dev режиме
	cd docker && docker compose -f docker-compose.dev.yml up

docker-down:  ## Остановить Docker контейнеры (dev)
	cd docker && docker compose -f docker-compose.yml down

docker-logs:  ## Показать логи Docker (dev)
	cd docker && docker compose -f docker-compose.yml logs -f bot

docker-restart:  ## Перезапустить Docker контейнеры (dev)
	cd docker && docker compose -f docker-compose.yml restart

docker-migrate:  ## Применить миграции через Docker
	cd docker && docker compose -f docker-compose.migrate.yml run --rm migrate

docker-clean:  ## Очистить Docker (удалить контейнеры и volumes)
	cd docker && docker compose -f docker-compose.yml down -v
	docker system prune -f

venv:  ## Создать виртуальное окружение
	python -m venv venv
	@echo "Активируйте окружение:"
	@echo "  Windows: venv\\Scripts\\activate"
	@echo "  Linux/Mac: source venv/bin/activate"

deps-update:  ## Обновить зависимости
	pip install --upgrade pip
	pip install --upgrade -r requirements.txt

deps-check:  ## Проверить устаревшие зависимости
	pip list --outdated

security-check:  ## Проверка безопасности зависимостей
	pip install safety
	safety check
	bandit -r app/

# ========================================
# PRODUCTION SERVER COMMANDS
# Команды для использования НА production сервере
# ========================================

prod-update:  ## Обновить код из git (на сервере)
	@echo "🔄 Обновление кода из GitHub..."
	git fetch origin
	git pull origin main
	@echo "✅ Код обновлен"

prod-migrate:  ## Применить миграции БД в production (Docker)
	@echo "🔄 Применение миграций БД..."
	cd docker && docker-compose -f docker-compose.prod.yml run --rm bot alembic upgrade head
	@echo "✅ Миграции применены"

prod-backup:  ## Создать backup БД в production (Docker)
	@echo "💾 Создание backup БД..."
	cd docker && docker-compose -f docker-compose.prod.yml exec bot python scripts/backup_db.py
	@echo "✅ Backup создан"

prod-restart:  ## Перезапуск production бота (Docker)
	@echo "🔄 Перезапуск бота..."
	cd docker && docker-compose -f docker-compose.prod.yml restart bot
	@echo "✅ Бот перезапущен"

prod-logs:  ## Показать логи production (Docker)
	cd docker && docker-compose -f docker-compose.prod.yml logs -f bot

prod-status:  ## Статус production контейнеров (Docker)
	cd docker && docker-compose -f docker-compose.prod.yml ps

prod-full-update:  ## Полное обновление: backup + git pull + rebuild + migrate + restart
	@echo "🚀 ПОЛНОЕ ОБНОВЛЕНИЕ PRODUCTION"
	@echo "1️⃣ Создание backup..."
	cd docker && docker-compose -f docker-compose.prod.yml exec -T bot python scripts/backup_db.py
	@echo "2️⃣ Обновление кода..."
	git pull origin main
	@echo "3️⃣ Пересборка образа..."
	cd docker && docker-compose -f docker-compose.prod.yml build --no-cache bot
	@echo "4️⃣ Применение миграций..."
	cd docker && docker-compose -f docker-compose.prod.yml run --rm bot alembic upgrade head
	@echo "5️⃣ Перезапуск..."
	cd docker && docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Обновление завершено!"
	@echo "📊 Проверьте логи: make prod-logs"

all: clean install-dev lint test  ## Выполнить всё: очистка, установка, линт, тесты

