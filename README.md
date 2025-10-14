# 🤖 Telegram Bot - Система управления заявками на ремонт техники

Telegram-бот для автоматизации процесса приема, обработки и выполнения заявок на ремонт бытовой техники.

## 📋 Описание

Система предназначена для управления заявками на ремонт техники с поддержкой нескольких ролей пользователей:
- **Администраторы** - полный доступ к системе, управление пользователями и мастерами
- **Диспетчеры** - создание заявок, назначение мастеров, управление статусами
- **Мастера** - просмотр назначенных заявок, обновление статусов выполнения

### 🆕 Новое: Множественные роли!
Пользователь может иметь несколько ролей одновременно. Например, диспетчер может быть также мастером и иметь доступ к функциям обеих ролей.

## 🚀 Быстрый старт

### Для новых пользователей
👉 **[docs/user-guides/START_HERE.txt](docs/user-guides/START_HERE.txt)** - Начните отсюда!

### Вариант 1: Docker (Рекомендуется)

```bash
# 1. Клонируйте репозиторий
git clone <repository_url>
cd telegram_repair_bot

# 2. Настройте переменные окружения
cp env.example .env
# Отредактируйте .env файл

# 3. Запустите через Docker Compose
docker-compose up -d

# 4. Проверьте логи
docker-compose logs -f bot
```

📖 Подробнее: [docs/DOCKER_USAGE.md](docs/DOCKER_USAGE.md)

### Вариант 2: Локальная установка

```bash
# 1. Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 2. Установите зависимости
pip install -r requirements.txt

# 3. Настройте .env
cp env.example .env

# 4. Инициализируйте базу данных
python -c "from app.database import Database; import asyncio; asyncio.run(Database().init_db())"

# 5. Запустите бота
python bot.py
```

## 🔄 Workflow разработки: DEV → STAGING → PROD

Для безопасной разработки без риска для production, проект использует трехуровневую систему окружений:

```
Local (Cursor) → Staging (Test) → Production (Live)
```

### Быстрые команды

```bash
# Локальная разработка
make test              # Запустить тесты
make lint              # Проверить код
make run               # Запустить бота локально

# Деплой в staging (тестирование)
make staging-deploy    # Автоматический деплой в staging
make staging-logs      # Просмотр логов staging

# Деплой в production (после проверки в staging)
make prod-deploy       # Деплой в production (с подтверждением!)
make prod-logs         # Просмотр логов production
make prod-status       # Статус production
```

### Процесс обновления бота

1. **Разработка локально** (в Cursor):
   ```bash
   # Внести изменения, протестировать
   make test && make lint
   git add . && git commit -m "feat: новая функция"
   git push origin main
   ```

2. **Деплой в Staging** (проверка):
   ```bash
   make staging-deploy  # Автоматически: SSH → git pull → rebuild → migrate
   make staging-logs    # Проверить логи
   ```

3. **Деплой в Production** (если все ОК):
   ```bash
   make prod-deploy     # С подтверждением и backup
   make prod-logs       # Проверить что все работает
   ```

📖 **Детальная документация:** [docs/STAGING_WORKFLOW.md](docs/STAGING_WORKFLOW.md)

### Настройка переменных для автоматического деплоя

Создайте `.env` в корне проекта или экспортируйте переменные:

```bash
# Windows PowerShell
$env:SSH_SERVER="root@your-server-ip"

# Linux/Mac
export SSH_SERVER="root@your-server-ip"
```

## 🏗️ Структура проекта

```
telegram_repair_bot/
├── app/                          # Основное приложение
│   ├── database/                 # База данных и модели
│   ├── handlers/                 # Обработчики команд
│   │   ├── admin.py             # Функции администратора
│   │   ├── dispatcher.py        # Функции диспетчера
│   │   ├── master.py            # Функции мастера
│   │   ├── common.py            # Общие функции
│   │   └── group_interaction.py # Групповые взаимодействия
│   ├── keyboards/               # Клавиатуры
│   ├── middlewares/             # Middleware
│   ├── schemas/                 # Pydantic схемы валидации
│   ├── services/                # Бизнес-логика
│   ├── filters/                 # Фильтры сообщений
│   └── utils/                   # Утилиты
│
├── tests/                       # Тесты
│   ├── unit/                    # Unit тесты
│   └── integration/             # Интеграционные тесты
│
├── scripts/                     # Утилитные скрипты
│   ├── backup_db.py            # Резервное копирование БД
│   ├── check_database.py       # Проверка БД
│   └── sync_roles_from_env.py  # Синхронизация ролей
│
├── migrations/                  # Миграции Alembic
├── docker/                      # Docker конфигурация
├── data/                        # Данные приложения
│   ├── backups/                # Бэкапы БД
│   └── migrations/             # Данные миграций
│
├── docs/                        # Документация
│   ├── deployment/             # Гайды по деплою
│   ├── development/            # Документация для разработчиков
│   ├── reports/                # Отчеты и аудиты
│   ├── migration/              # Гайды по миграции
│   └── user-guides/            # Руководства пользователя
│
├── bot.py                       # Точка входа
├── alembic.ini                  # Конфигурация Alembic
├── pyproject.toml               # Конфигурация проекта
└── requirements.txt             # Зависимости
```

## 🚀 Технический стек

- **Python** 3.11+
- **aiogram** 3.14.0 - асинхронный фреймворк для Telegram Bot API
- **SQLite** + aiosqlite - база данных
- **APScheduler** 3.11.0 - планировщик задач
- **openpyxl** 3.1.5 - генерация Excel отчетов
- **pydantic** 2.10.3 - валидация данных
- **Docker** - контейнеризация
- **GitHub Actions** - CI/CD
- **Alembic** - миграции БД
- **pytest** - тестирование

## 📚 Документация

### Для пользователей
- 📖 [Быстрый старт](docs/user-guides/START_HERE.txt)
- 📖 [После исправлений](docs/user-guides/README_AFTER_FIXES.md)
- 📖 [Начало работы](docs/user-guides/START_AFTER_FIXES.md)

### Деплой
- 🚀 **[Staging Workflow](docs/STAGING_WORKFLOW.md)** - Безопасная разработка DEV→STAGING→PROD
- 🚀 [Деплой на VPS Linux](docs/deployment/DEPLOY_VPS_LINUX_GUIDE.md)
- 🚀 [Инструкции по деплою](docs/deployment/DEPLOYMENT_INSTRUCTIONS.md)
- 🚀 [Production Ready Guide](docs/deployment/PRODUCTION_READY_GUIDE.md)
- 🚀 [Быстрые команды деплоя](docs/deployment/QUICK_DEPLOY_COMMANDS.md)

### Разработка
- 💻 **[Staging Workflow](docs/STAGING_WORKFLOW.md)** - Процесс разработки и деплоя
- 💻 [Структура проекта](docs/development/STRUCTURE_UPDATE.md)
- 💻 [Следующие шаги](docs/development/NEXT_STEPS.md)
- 💻 [Docker Usage](docs/DOCKER_USAGE.md)

### Миграция
- 🔄 [Гайд по миграции](docs/migration/MIGRATION_GUIDE.md)

### Отчеты
- 📊 [Исправления](docs/reports/fixes/)
- 📊 [Аудиты](docs/reports/audits/)

## 🧪 Тестирование

```bash
# Запустить все тесты
pytest

# Запустить только unit тесты
pytest tests/unit/

# Запустить только integration тесты
pytest tests/integration/

# С покрытием
pytest --cov=app --cov-report=html

# Использование Makefile
make test                # Все тесты
make test-unit          # Unit тесты
make test-integration   # Integration тесты
make coverage           # С отчетом покрытия
```

## 🛠️ Полезные команды (Makefile)

```bash
# Основные команды
make help              # Показать все команды
make install           # Установить production зависимости
make install-dev       # Установить dev зависимости
make run               # Запустить бота локально
make test              # Запустить тесты
make lint              # Проверить код
make format            # Форматировать код

# Docker (локальная разработка)
make docker-build      # Собрать Docker образ
make docker-up         # Запустить в Docker (dev)
make docker-up-dev     # Запустить в dev режиме
make docker-down       # Остановить контейнеры
make docker-logs       # Показать логи

# Деплой (staging/production)
make staging-deploy    # Деплой в staging
make staging-logs      # Логи staging
make prod-deploy       # Деплой в production
make prod-logs         # Логи production
make prod-status       # Статус production

# Базы данных
make migrate           # Применить миграции
make migrate-create    # Создать миграцию
make backup            # Создать бэкап БД
```

## 📦 Основные возможности

### Для администраторов
- ✅ Управление пользователями и ролями
- ✅ Добавление/удаление мастеров
- ✅ Просмотр статистики и отчетов
- ✅ Полный доступ ко всем функциям

### Для диспетчеров
- ✅ Создание новых заявок
- ✅ Назначение мастеров на заявки
- ✅ Управление статусами заявок
- ✅ Генерация отчетов

### Для мастеров
- ✅ Просмотр назначенных заявок
- ✅ Принятие/отклонение заявок
- ✅ Обновление статусов работ
- ✅ Завершение заявок с указанием финансовых данных

### Системные функции
- ✅ Автоматические уведомления в группу
- ✅ История изменений (audit log)
- ✅ Множественные роли пользователей
- ✅ Валидация данных через Pydantic
- ✅ Генерация Excel отчетов
- ✅ Автоматические бэкапы БД
- ✅ Планировщик задач

## 🔐 Настройка окружения

Создайте `.env` файл на основе `env.example`:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_here
GROUP_CHAT_ID=-100xxxxxxxxxx

# Admin
ADMIN_IDS=123456789,987654321

# Database
DATABASE_PATH=bot_database.db

# Logging
LOG_LEVEL=INFO

# Optional: Sentry
SENTRY_DSN=

# Backup
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 3 * * *
```

## 🔄 Миграции базы данных

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "Description"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1

# Или используйте Makefile
make migrate-create MSG="Description"
make migrate-up
make migrate-down
```

## 📊 Бэкапы

Автоматические бэкапы настраиваются через переменные окружения. Также можно создать бэкап вручную:

```bash
# Ручной бэкап
python scripts/backup_db.py

# Или через Makefile
make backup
```

Бэкапы сохраняются в `data/backups/` с временной меткой.

## 🐛 Отладка

```bash
# Проверить базу данных
python scripts/check_database.py

# Просмотр логов
tail -f logs/bot.log

# В Docker
docker-compose logs -f bot
```

## 🤝 Разработка

### Установка dev зависимостей

```bash
pip install -r requirements-dev.txt
```

### Код-стайл

Проект использует:
- `black` - форматирование кода
- `flake8` - линтинг
- `mypy` - проверка типов
- `pytest` - тестирование

```bash
make format  # Отформатировать код
make lint    # Проверить код
make test    # Запустить тесты
```

## 📝 Лицензия

[Добавьте информацию о лицензии]

## 👥 Авторы

[Добавьте информацию об авторах]

## 🆘 Поддержка

Если у вас возникли проблемы:
1. Проверьте [документацию](docs/)
2. Посмотрите [отчеты об исправлениях](docs/reports/fixes/)
3. Создайте issue в репозитории

---

**Последнее обновление структуры:** 13.10.2025  
**Статус:** ✅ Готов к production
