# ========================================
# Makefile для Telegram Repair Bot
# ========================================

.PHONY: help install test lint run

# ========================================
# HELP
# ========================================

help:  ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

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
# DATABASE MIGRATIONS (local)
# ========================================

migrate:  ## Применить миграции
	alembic upgrade head

migrate-create:  ## Создать миграцию (make migrate-create MSG="описание")
	alembic revision --autogenerate -m "$(MSG)"

migrate-history:  ## История миграций
	alembic history

migrate-current:  ## Текущая версия БД
	alembic current

migrate-rollback:  ## Откатить миграцию
	alembic downgrade -1

# ========================================
# PRODUCTION (Docker на сервере)
# ========================================

prod-start:  ## 🚀 Запустить production бота
	@echo "🚀 Запуск production бота..."
	docker compose -f docker/docker-compose.prod.yml up -d --build
	@echo "✅ Бот запущен!"
	@echo "📋 Логи: make prod-logs"

prod-stop:  ## Остановить production
	@echo "🛑 Остановка бота..."
	docker compose -f docker/docker-compose.prod.yml down
	@echo "✅ Остановлен"

prod-restart:  ## Перезапустить production
	@echo "🔄 Перезапуск бота..."
	docker compose -f docker/docker-compose.prod.yml restart
	@echo "✅ Перезапущен"

prod-logs:  ## Показать логи production
	docker compose -f docker/docker-compose.prod.yml logs -f --tail=50

prod-status:  ## Статус контейнеров
	docker compose -f docker/docker-compose.prod.yml ps

prod-update:  ## Обновить код и перезапустить
	@echo "🔄 Полное обновление..."
	git pull
	docker compose -f docker/docker-compose.prod.yml up -d --build
	@echo "✅ Обновлено!"
	@echo ""
	@echo "📋 Последние строки логов:"
	@docker compose -f docker/docker-compose.prod.yml logs --tail=40
	@echo ""
	@echo "💡 Для просмотра логов в реальном времени: make prod-logs"

prod-deploy:  ## Полный деплой с пересборкой
	@echo "🚀 Полный деплой..."
	git pull
	docker compose -f docker/docker-compose.prod.yml down
	docker compose -f docker/docker-compose.prod.yml up -d --build
	@echo "✅ Деплой завершен!"
	@echo ""
	@echo "📋 Последние строки логов:"
	@docker compose -f docker/docker-compose.prod.yml logs --tail=40
	@echo ""
	@echo "💡 Для просмотра логов в реальном времени: make prod-logs"

prod-backup:  ## Создать backup БД
	@echo "💾 Создание backup..."
	docker exec telegram_repair_bot_prod python scripts/backup_db.py
	@mkdir -p backups
	docker cp telegram_repair_bot_prod:/app/backups/. ./backups/
	@echo "✅ Backup в ./backups/"

prod-shell:  ## Войти в контейнер
	docker exec -it telegram_repair_bot_prod /bin/sh

prod-env:  ## Показать переменные окружения контейнера
	@echo "🔍 Переменные окружения:"
	@docker exec telegram_repair_bot_prod env | grep -E "BOT_TOKEN|LOG_LEVEL|DEV_MODE|USE_ORM|ADMIN_IDS|DATABASE_PATH|REDIS_URL" | sort

# ========================================
# MULTIBOT (Docker: два бота + Redis)
# ========================================

MB_COMPOSE = docker/docker-compose.multibot.yml

mb-prepare:  ## Создать каталоги для данных/логов/бэкапов и Redis
	@mkdir -p data/city1 data/city2 logs/city1 logs/city2 backups/city1 backups/city2 data/redis
	@echo "✅ Каталоги подготовлены: data/city1, data/city2, logs/*, backups/*, data/redis"

mb-env-fix:  ## Закомментировать первую строку в env.city1/env.city2 (если там заголовок)
	@sed -i '1s/^/# /' env.city1 || true
	@sed -i '1s/^/# /' env.city2 || true
	@echo "✅ Первая строка в env.city1/env.city2 приведена к комментарию"

mb-start:  ## 🚀 Запустить оба бота и Redis (мультибот)
	@echo "🚀 Запуск multibot..."
	@docker compose -f $(MB_COMPOSE) up -d --build
	@echo "✅ Multibot запущен!"
	@echo "📋 Логи: make mb-logs-city1 | make mb-logs-city2"

mb-stop:  ## Остановить multibot
	@echo "🛑 Остановка multibot..."
	@docker compose -f $(MB_COMPOSE) down
	@echo "✅ Остановлен"

mb-restart:  ## Перезапустить multibot
	@echo "🔄 Перезапуск multibot..."
	@docker compose -f $(MB_COMPOSE) up -d --build
	@echo "✅ Перезапущен"

mb-status:  ## Статус контейнеров multibot
	@docker compose -f $(MB_COMPOSE) ps

mb-logs-city1:  ## Логи бота city1
	@docker compose -f $(MB_COMPOSE) logs -f --tail=80 bot_city1

mb-logs-city2:  ## Логи бота city2
	@docker compose -f $(MB_COMPOSE) logs -f --tail=80 bot_city2

mb-migrate-city1:  ## Применить миграции для БД city1
	@docker compose -f $(MB_COMPOSE) run --rm bot_city1 alembic upgrade head

mb-migrate-city2:  ## Применить миграции для БД city2
	@docker compose -f $(MB_COMPOSE) run --rm bot_city2 alembic upgrade head

mb-update:  ## Обновить код и пересобрать multibot
	@echo "🔄 Обновление кода и пересборка multibot..."
	@git pull
	@docker compose -f $(MB_COMPOSE) up -d --build
	@echo "✅ Обновлено и запущено!"
	@docker compose -f $(MB_COMPOSE) ps

mb-update-city1:  ## Обновить код и пересобрать только bot_city1
	@echo "🔄 Обновление кода и пересборка bot_city1..."
	@git pull
	@docker compose -f $(MB_COMPOSE) up -d --build bot_city1
	@echo "✅ bot_city1 обновлён и запущен!"

mb-update-city2:  ## Обновить код и пересобрать только bot_city2
	@echo "🔄 Обновление кода и пересборка bot_city2..."
	@git pull
	@docker compose -f $(MB_COMPOSE) up -d --build bot_city2
	@echo "✅ bot_city2 обновлён и запущен!"

mb-restart-city1:  ## Перезапустить только bot_city1 (без пересборки)
	@docker compose -f $(MB_COMPOSE) restart bot_city1
	@echo "✅ bot_city1 перезапущен"

mb-restart-city2:  ## Перезапустить только bot_city2 (без пересборки)
	@docker compose -f $(MB_COMPOSE) restart bot_city2
	@echo "✅ bot_city2 перезапущен"

# ========================================
# GIT SHORTCUTS
# ========================================

git-save:  ## Быстрое сохранение (make git-save MSG="описание")
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Укажите MSG=\"описание\""; \
		exit 1; \
	fi
	git add -A
	git commit -m "$(MSG)"
	git push

git-pull:  ## Получить изменения
	git pull

git-status:  ## Статус git
	git status

git-log:  ## Последние 10 коммитов
	git log --oneline -10

# ========================================
# UTILITIES
# ========================================

backup:  ## Backup БД локально
	python scripts/backup_db.py

check-db:  ## Проверить БД
	python scripts/check_database.py

check-role:  ## Проверить роль (make check-role ID=123456)
	python scripts/check_user_role.py $(ID)

set-role:  ## Установить роль (make set-role ID=123456 ROLE=ADMIN)
	python scripts/set_user_role.py $(ID) $(ROLE)

prod-install-deps:  ## Установить/обновить зависимости в контейнере
	@echo "📦 Установка зависимостей в production контейнере..."
	docker exec telegram_repair_bot_prod pip install -r /app/requirements.txt
	@echo "✅ Зависимости установлены!"
