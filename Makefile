# ========================================
# Makefile для Telegram Repair Bot
# ========================================

.PHONY: help install test lint clean run

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

clean:  ## Очистить кэши
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ dist/ build/

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

prod-deploy:  ## Полный деплой с пересборкой
	@echo "🚀 Полный деплой..."
	git pull
	docker compose -f docker/docker-compose.prod.yml down
	docker compose -f docker/docker-compose.prod.yml up -d --build
	@echo "✅ Деплой завершен!"
	@make prod-logs

prod-clean:  ## Очистить и перезапустить
	@echo "🧹 Очистка..."
	docker compose -f docker/docker-compose.prod.yml down -v
	docker system prune -f
	@echo "✅ Очищено"

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
