# ========================================
# Makefile для Telegram Repair Bot (Multibot)
# ========================================

.PHONY: help

# ========================================
# HELP
# ========================================

help:  ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# ========================================
# LOCAL DEVELOPMENT
# ========================================

install:  ## Установить зависимости
	pip install -r requirements.txt

install-dev:  ## Установить dev зависимости
	pip install -r requirements-dev.txt
	pre-commit install

run:  ## Запустить бота локально
	python bot.py

test:  ## Запустить тесты
	pytest

test-cov:  ## Тесты с coverage
	pytest --cov=app --cov-report=html --cov-report=term-missing

lint:  ## Проверить код
	ruff check .
	mypy app/ --ignore-missing-imports

format:  ## Отформатировать код
	ruff check --fix .
	ruff format .

pre-commit:  ## Запустить pre-commit
	pre-commit run --all-files

# ========================================
# LOCAL DEV (Docker на локальной машине)
# ========================================

DEV_COMPOSE = docker-compose.dev.yml

dev-start:  ## 🚀 Запустить dev бота (локально)
	@echo "🚀 Запуск dev бота..."
	@mkdir -p data/city1 logs/city1 backups/city1 data/redis
	@docker-compose -f $(DEV_COMPOSE) up -d
	@echo "✅ Dev бот запущен!"
	@echo "📋 Логи: make dev-logs"

dev-stop:  ## Остановить dev бота
	@echo "🛑 Остановка dev бота..."
	@docker-compose -f $(DEV_COMPOSE) down
	@echo "✅ Остановлен"

dev-restart:  ## 🔄 Перезапустить dev бота (быстро)
	@echo "🔄 Перезапуск dev бота..."
	@docker-compose -f $(DEV_COMPOSE) restart bot_city1
	@echo "✅ Перезапущен! (Логи: make dev-logs)"

dev-rebuild:  ## 🏗️ Пересобрать и запустить (если изменились зависимости)
	@echo "🏗️ Пересборка dev бота..."
	@docker-compose -f $(DEV_COMPOSE) up -d --build
	@echo "✅ Пересобран и запущен!"

dev-logs:  ## 📋 Логи dev бота (real-time)
	@docker-compose -f $(DEV_COMPOSE) logs -f --tail=30 bot_city1

dev-logs-all:  ## 📋 Все логи (с начала)
	@docker-compose -f $(DEV_COMPOSE) logs -f bot_city1

dev-status:  ## Статус dev контейнеров
	@docker-compose -f $(DEV_COMPOSE) ps

dev-shell:  ## Войти в dev контейнер
	@docker-compose -f $(DEV_COMPOSE) exec bot_city1 bash

dev-migrate:  ## Применить миграции (dev)
	@echo "🔄 Миграции dev..."
	@docker-compose -f $(DEV_COMPOSE) exec bot_city1 alembic upgrade head
	@echo "✅ Миграции применены"

dev-clean:  ## 🗑️ Удалить контейнеры и volumes
	@echo "🗑️ Очистка dev окружения..."
	@docker-compose -f $(DEV_COMPOSE) down -v
	@echo "✅ Очищено"

# ========================================
# MULTIBOT (Docker: два бота + Redis)
# ========================================

MB_COMPOSE = docker/docker-compose.multibot.yml

mb-prepare:  ## Создать директории для данных
	@mkdir -p data/city1 data/city2 logs/city1 logs/city2 backups/city1 backups/city2 data/redis
	@echo "✅ Директории подготовлены"

mb-start:  ## 🚀 Запустить оба бота
	@echo "🚀 Запуск multibot..."
	@docker compose -f $(MB_COMPOSE) up -d --build
	@echo "✅ Multibot запущен!"
	@echo "📋 Логи city1: make mb-logs-city1"
	@echo "📋 Логи city2: make mb-logs-city2"

mb-stop:  ## Остановить multibot
	@echo "🛑 Остановка multibot..."
	@docker compose -f $(MB_COMPOSE) down
	@echo "✅ Остановлен"

mb-restart:  ## Перезапустить multibot
	@echo "🔄 Перезапуск multibot..."
	@docker compose -f $(MB_COMPOSE) up -d --build
	@echo "✅ Перезапущен"

mb-status:  ## Статус контейнеров
	@docker compose -f $(MB_COMPOSE) ps

mb-logs-city1:  ## Логи city1
	@docker compose -f $(MB_COMPOSE) logs -f --tail=100 bot_city1

mb-logs-city2:  ## Логи city2
	@docker compose -f $(MB_COMPOSE) logs -f --tail=100 bot_city2

mb-logs:  ## Логи всех контейнеров
	@docker compose -f $(MB_COMPOSE) logs -f --tail=50

# ========================================
# MIGRATIONS (Multibot)
# ========================================

mb-migrate-city1:  ## Применить миграции city1
	@echo "🔄 Миграции city1..."
	@docker compose -f $(MB_COMPOSE) stop bot_city1 || true
	@docker compose -f $(MB_COMPOSE) run --rm bot_city1 alembic upgrade head
	@docker compose -f $(MB_COMPOSE) up -d bot_city1
	@echo "✅ Миграции применены для city1"

mb-migrate-city2:  ## Применить миграции city2
	@echo "🔄 Миграции city2..."
	@docker compose -f $(MB_COMPOSE) stop bot_city2 || true
	@docker compose -f $(MB_COMPOSE) run --rm bot_city2 alembic upgrade head
	@docker compose -f $(MB_COMPOSE) up -d bot_city2
	@echo "✅ Миграции применены для city2"

mb-migrate-all:  ## Применить миграции для обоих ботов
	@make mb-migrate-city1
	@make mb-migrate-city2

# ========================================
# UPDATE (Git pull + rebuild)
# ========================================

mb-update:  ## Обновить код и пересобрать
	@echo "🔄 Обновление..."
	@git pull origin main
	@docker compose -f $(MB_COMPOSE) down
	@docker compose -f $(MB_COMPOSE) build
	@docker compose -f $(MB_COMPOSE) up -d
	@echo "✅ Обновлено и запущено!"

mb-update-city1:  ## Обновить только city1
	@echo "🔄 Обновление city1..."
	@git pull origin main
	@docker compose -f $(MB_COMPOSE) stop bot_city1
	@docker compose -f $(MB_COMPOSE) build bot_city1
	@docker compose -f $(MB_COMPOSE) up -d bot_city1
	@echo "✅ city1 обновлён!"

mb-update-city2:  ## Обновить только city2
	@echo "🔄 Обновление city2..."
	@git pull origin main
	@docker compose -f $(MB_COMPOSE) stop bot_city2
	@docker compose -f $(MB_COMPOSE) build bot_city2
	@docker compose -f $(MB_COMPOSE) up -d bot_city2
	@echo "✅ city2 обновлён!"

# ========================================
# CONTROL (Управление отдельными ботами)
# ========================================

mb-restart-city1:  ## Перезапустить city1
	@docker compose -f $(MB_COMPOSE) restart bot_city1
	@echo "✅ city1 перезапущен"

mb-restart-city2:  ## Перезапустить city2
	@docker compose -f $(MB_COMPOSE) restart bot_city2
	@echo "✅ city2 перезапущен"

mb-stop-city1:  ## Остановить city1
	@docker compose -f $(MB_COMPOSE) stop bot_city1
	@echo "✅ city1 остановлен"

mb-stop-city2:  ## Остановить city2
	@docker compose -f $(MB_COMPOSE) stop bot_city2
	@echo "✅ city2 остановлен"

mb-start-city1:  ## Запустить city1
	@docker compose -f $(MB_COMPOSE) up -d bot_city1
	@echo "✅ city1 запущен"

mb-start-city2:  ## Запустить city2
	@docker compose -f $(MB_COMPOSE) up -d bot_city2
	@echo "✅ city2 запущен"

# ========================================
# BACKUP
# ========================================

mb-backup-city1:  ## Backup БД city1
	@echo "💾 Backup city1..."
	@mkdir -p backups/city1
	@docker compose -f $(MB_COMPOSE) exec bot_city1 python scripts/backup_db.py
	@docker compose -f $(MB_COMPOSE) cp bot_city1:/app/backups/. ./backups/city1/
	@echo "✅ Backup в ./backups/city1/"

mb-backup-city2:  ## Backup БД city2
	@echo "💾 Backup city2..."
	@mkdir -p backups/city2
	@docker compose -f $(MB_COMPOSE) exec bot_city2 python scripts/backup_db.py
	@docker compose -f $(MB_COMPOSE) cp bot_city2:/app/backups/. ./backups/city2/
	@echo "✅ Backup в ./backups/city2/"

mb-backup-all:  ## Backup обеих БД
	@make mb-backup-city1
	@make mb-backup-city2

# ========================================
# SHELL
# ========================================

mb-shell-city1:  ## Войти в контейнер city1
	@docker compose -f $(MB_COMPOSE) exec bot_city1 /bin/sh

mb-shell-city2:  ## Войти в контейнер city2
	@docker compose -f $(MB_COMPOSE) exec bot_city2 /bin/sh

# ========================================
# GIT SHORTCUTS
# ========================================

git-save:  ## Быстрое сохранение (make git-save MSG="текст")
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Укажите MSG=\"описание\""; \
		exit 1; \
	fi
	git add -A
	git commit -m "$(MSG)"
	git push

git-save-noverify:  ## Сохранение без хуков
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Укажите MSG=\"описание\""; \
		exit 1; \
	fi
	git add -A
	git commit --no-verify -m "$(MSG)"
	git push

git-pull:  ## Получить изменения
	git pull

git-status:  ## Статус git
	git status

# ========================================
# UTILITIES
# ========================================

backup:  ## Backup БД локально
	python scripts/backup_db.py

check-role:  ## Проверить роль (make check-role ID=123456)
	@if [ -z "$(ID)" ]; then \
		echo "❌ Укажите ID=\"telegram_id\""; \
		exit 1; \
	fi
	python scripts/check_user_role.py $(ID)

set-role:  ## Установить роль (make set-role ID=123456 ROLE=ADMIN)
	@if [ -z "$(ID)" ] || [ -z "$(ROLE)" ]; then \
		echo "❌ Укажите ID=\"telegram_id\" и ROLE=\"ADMIN|DISPATCHER|MASTER\""; \
		exit 1; \
	fi
	python scripts/set_user_role.py $(ID) $(ROLE)
