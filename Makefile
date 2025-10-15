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

prod-migrate-stamp:  ## Пометить БД как готовую (для существующей БД без миграций)
	@echo "📌 Установка версии миграции для существующей БД..."
	cd docker && docker-compose -f docker-compose.prod.yml run --rm bot alembic stamp head
	@echo "✅ БД помечена как готовая"
	@echo "ℹ️  Теперь можете использовать: make prod-migrate"

prod-migrate-check:  ## Проверить текущую версию миграции БД
	@echo "🔍 Текущая версия миграции:"
	cd docker && docker-compose -f docker-compose.prod.yml run --rm bot alembic current

prod-backup:  ## Создать backup БД в production (Docker)
	@echo "💾 Создание backup БД..."
	cd docker && docker-compose -f docker-compose.prod.yml run --rm bot python scripts/backup_db.py
	@echo "✅ Backup создан"

prod-restart:  ## Перезапуск production бота (Docker)
	@echo "🔄 Перезапуск бота..."
	cd docker && docker-compose -f docker-compose.prod.yml restart bot
	@echo "✅ Бот перезапущен"

prod-logs:  ## Показать логи production (Docker)
	cd docker && docker-compose -f docker-compose.prod.yml logs -f bot

prod-status:  ## Статус production контейнеров (Docker)
	cd docker && docker-compose -f docker-compose.prod.yml ps

prod-rebuild:  ## Пересобрать Docker образ с новым кодом
	@echo "🔨 Пересборка Docker образа..."
	cd docker && docker-compose -f docker-compose.prod.yml build --no-cache bot
	@echo "✅ Образ пересобран"

prod-deploy:  ## Полный деплой: pull + rebuild + restart (ГЛАВНАЯ КОМАНДА ДЛЯ DOCKER!)
	@echo "🚀 Запуск полного деплоя..."
	@echo "📥 1. Получение последнего кода..."
	git pull origin main
	@echo "🔨 2. Очистка build cache..."
	docker builder prune -f
	@echo "🔨 3. Пересборка Docker образа..."
	cd docker && docker-compose -f docker-compose.prod.yml build --no-cache --pull bot
	@echo "🔄 4. Перезапуск контейнера..."
	cd docker && docker-compose -f docker-compose.prod.yml up -d bot
	@echo "✅ Деплой завершен! Проверьте логи: make prod-logs"

prod-deploy-version:  ## Деплой конкретной версии (использование: make prod-deploy-version VERSION=v1.2.3)
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ Ошибка: укажите версию"; \
		echo "Использование: make prod-deploy-version VERSION=v1.2.3"; \
		echo "Доступные версии: make git-tags"; \
		exit 1; \
	fi
	@echo "🚀 Деплой версии $(VERSION)..."
	@echo "📥 1. Получение версии $(VERSION)..."
	git fetch --tags
	git checkout tags/$(VERSION)
	@echo "🔨 2. Очистка build cache..."
	docker builder prune -f
	@echo "🔨 3. Пересборка Docker образа..."
	cd docker && docker-compose -f docker-compose.prod.yml build --no-cache --pull bot
	@echo "🔄 4. Перезапуск контейнера..."
	cd docker && docker-compose -f docker-compose.prod.yml up -d bot
	@echo "✅ Версия $(VERSION) задеплоена! Проверьте логи: make prod-logs"
	@echo "⚠️  Для возврата на main: git checkout main"

prod-deploy-script:  ## Деплой через скрипт (для non-Docker режима)
	@echo "🚀 Запуск автоматического деплоя..."
	chmod +x scripts/deploy_with_migrations.sh
	./scripts/deploy_with_migrations.sh

prod-diagnose:  ## Диагностика проблем обновления
	@echo "🔍 Запуск диагностики..."
	chmod +x scripts/diagnose_update.sh
	./scripts/diagnose_update.sh

prod-full-update:  ## [УСТАРЕЛО] Используйте prod-deploy
	@echo "⚠️  ВНИМАНИЕ: Эта команда устарела!"
	@echo "ℹ️  Используйте вместо неё: make prod-deploy"
	@echo ""
	@echo "Запускаю prod-deploy через 3 секунды..."
	@sleep 3
	@make prod-deploy

all: clean install-dev lint test  ## Выполнить всё: очистка, установка, линт, тесты

# ========================================
# GIT COMMANDS
# Команды для работы с Git
# ========================================

git-status:  ## Показать статус Git
	@git status

git-add:  ## Добавить все изменения
	@git add -A
	@echo "✅ Все изменения добавлены"
	@git status

git-commit:  ## Коммит (использование: make git-commit MSG="описание")
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Ошибка: укажите сообщение коммита"; \
		echo "Использование: make git-commit MSG=\"ваше сообщение\""; \
		exit 1; \
	fi
	@git commit -m "$(MSG)"
	@echo "✅ Коммит создан"

git-push:  ## Отправить изменения в репозиторий
	@echo "🚀 Отправка изменений в GitHub..."
	@git push origin main
	@echo "✅ Изменения отправлены"

git-pull:  ## Получить изменения из репозитория
	@echo "⬇️  Получение изменений из GitHub..."
	@git pull origin main
	@echo "✅ Изменения получены"

git-save:  ## Быстрое сохранение: add + commit + push (использование: make git-save MSG="описание")
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Ошибка: укажите сообщение коммита"; \
		echo "Использование: make git-save MSG=\"ваше сообщение\""; \
		exit 1; \
	fi
	@echo "📝 Добавление изменений..."
	@git add -A
	@echo "💾 Создание коммита..."
	@git commit -m "$(MSG)"
	@echo "🚀 Отправка в GitHub..."
	@git push origin main
	@echo "✅ Всё готово!"

git-log:  ## Показать последние 10 коммитов
	@git log --oneline -10

git-diff:  ## Показать изменения
	@git diff

git-branch:  ## Показать текущую ветку
	@git branch

git-tag:  ## Создать тэг версии (использование: make git-tag VERSION=v1.2.3)
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ Ошибка: укажите версию"; \
		echo "Использование: make git-tag VERSION=v1.2.3"; \
		exit 1; \
	fi
	@echo "🏷️  Создание тэга $(VERSION)..."
	@git tag -a $(VERSION) -m "Release $(VERSION)"
	@git push origin $(VERSION)
	@echo "✅ Тэг $(VERSION) создан и отправлен в GitHub"

git-tags:  ## Показать все тэги
	@echo "🏷️  Список версий:"
	@git tag -l

git-release:  ## Полный релиз: add + commit + push + tag (использование: make git-release VERSION=v1.2.3 MSG="описание")
	@if [ -z "$(VERSION)" ] || [ -z "$(MSG)" ]; then \
		echo "❌ Ошибка: укажите версию и сообщение"; \
		echo "Использование: make git-release VERSION=v1.2.3 MSG=\"описание релиза\""; \
		exit 1; \
	fi
	@echo "📦 Подготовка релиза $(VERSION)..."
	@git add -A
	@git commit -m "$(MSG)"
	@git push origin main
	@git tag -a $(VERSION) -m "Release $(VERSION): $(MSG)"
	@git push origin $(VERSION)
	@echo "✅ Релиз $(VERSION) готов и отправлен!"

