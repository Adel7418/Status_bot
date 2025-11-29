# План реструктуризации проекта

## Текущие проблемы

### 1. Корень проекта перегружен
- 📄 ~25 MD файлов (отчеты, гайды) в корне
- 🔧 Скрипты разбросаны (`backup_db.py`, `check_database.py`, `sync_roles_from_env.py`)
- 📊 Дублирование: `app/utils.py` + `app/utils/`

### 2. Временные/генерируемые файлы
- ❌ `bot.log` в корне (должен быть в `logs/`)
- ❌ `coverage.xml`, `htmlcov/` (должны быть в .gitignore или отдельной папке)
- ❌ 16 бэкапов БД в `backups/` (старые нужно очистить)
- ❌ `__pycache__/` папки (должны быть в .gitignore)

### 3. Документация не организована
- Множество отчетов в корне
- 40 MD файлов в `docs/` без структуры

## Предлагаемая структура

```
telegram_repair_bot/
├── app/                          # Основное приложение
│   ├── core/                     # Ядро приложения (НОВОЕ)
│   │   ├── __init__.py
│   │   ├── config.py            # Из app/config.py
│   │   └── constants.py         # Константы (НОВОЕ)
│   │
│   ├── database/                # База данных
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── db.py
│   │   └── repositories/        # Репозитории (НОВОЕ)
│   │       ├── __init__.py
│   │       ├── user.py
│   │       ├── order.py
│   │       └── master.py
│   │
│   ├── handlers/                # Обработчики
│   │   ├── __init__.py
│   │   ├── admin/               # Разделить по модулям (НОВОЕ)
│   │   │   ├── __init__.py
│   │   │   └── handlers.py
│   │   ├── dispatcher/
│   │   │   ├── __init__.py
│   │   │   └── handlers.py
│   │   ├── master/
│   │   │   ├── __init__.py
│   │   │   └── handlers.py
│   │   ├── common.py
│   │   └── group_interaction.py
│   │
│   ├── keyboards/               # Клавиатуры
│   │   ├── __init__.py
│   │   ├── inline.py
│   │   └── reply.py
│   │
│   ├── middlewares/             # Middleware
│   │   ├── __init__.py
│   │   ├── error_handler.py
│   │   ├── logging.py
│   │   └── role_check.py
│   │
│   ├── schemas/                 # Pydantic схемы
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── master.py
│   │   └── order.py
│   │
│   ├── services/                # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── reports.py
│   │   ├── scheduler.py
│   │   └── validation/          # Валидация (НОВОЕ)
│   │       ├── __init__.py
│   │       └── scheduled_time.py
│   │
│   ├── filters/                 # Фильтры
│   │   ├── __init__.py
│   │   ├── group_filter.py
│   │   └── role_filter.py
│   │
│   ├── utils/                   # Утилиты (ОБЪЕДИНИТЬ)
│   │   ├── __init__.py
│   │   ├── helpers.py
│   │   ├── retry.py
│   │   ├── sentry.py
│   │   └── formatters.py        # Форматирование (НОВОЕ)
│   │
│   ├── decorators.py
│   └── states.py
│
├── tests/                       # Тесты
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/                    # Unit тесты (НОВОЕ)
│   │   ├── test_config.py
│   │   ├── test_models.py
│   │   ├── test_schemas.py
│   │   └── test_scheduled_time.py
│   ├── integration/             # Интеграционные (НОВОЕ)
│   │   ├── test_database.py
│   │   └── test_handlers.py
│   └── README.md
│
├── scripts/                     # Скрипты (ПЕРЕМЕСТИТЬ СЮДА)
│   ├── backup_db.py            # Из корня
│   ├── check_database.py       # Из корня
│   ├── sync_roles_from_env.py  # Из корня
│   ├── export_db.py
│   ├── import_db.py
│   ├── deploy_to_vps.sh
│   ├── migrate.sh
│   ├── setup_vps.sh
│   └── README.md
│
├── migrations/                  # Миграции Alembic
│   ├── versions/
│   ├── env.py
│   ├── README
│   └── script.py.mako
│
├── docker/                      # Docker конфигурация
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   ├── docker-compose.redis.yml
│   ├── docker-compose.migrate.yml
│   └── README.md
│
├── docs/                        # Документация (РЕОРГАНИЗОВАТЬ)
│   ├── README.md
│   ├── deployment/              # Деплой (НОВОЕ)
│   │   ├── vps-linux-guide.md
│   │   ├── quick-deploy.md
│   │   └── docker-guide.md
│   ├── development/             # Разработка (НОВОЕ)
│   │   ├── structure.md
│   │   ├── testing.md
│   │   └── contributing.md
│   ├── reports/                 # Отчеты (НОВОЕ)
│   │   ├── fixes/
│   │   │   ├── scheduled-time-fix.md
│   │   │   ├── stability-fixes.md
│   │   │   └── workflows-fix.md
│   │   └── audits/
│   │       └── stability-audit.md
│   ├── migration/               # Миграция (НОВОЕ)
│   │   ├── migration-guide.md
│   │   └── quick-migration.md
│   └── user-guides/             # Для пользователей (НОВОЕ)
│       ├── getting-started.md
│       └── quick-start.md
│
├── data/                        # Данные приложения
│   ├── backups/                 # Бэкапы (ПЕРЕМЕСТИТЬ)
│   ├── migrations/              # Данные миграций (ПЕРЕМЕСТИТЬ)
│   └── .gitkeep
│
├── logs/                        # Логи
│   ├── bot.log
│   └── .gitkeep
│
├── .github/                     # GitHub Actions (если есть)
│   └── workflows/
│
├── bot.py                       # Точка входа
├── bot_database.db              # БД (в .gitignore)
├── alembic.ini                  # Конфиг Alembic
├── pyproject.toml               # Конфигурация проекта
├── requirements.txt             # Зависимости
├── requirements-dev.txt         # Dev зависимости
├── Makefile                     # Команды
├── .env.example                 # Пример env
├── .gitignore                   # Git ignore
├── README.md                    # Главный README
└── START_HERE.md                # Быстрый старт (ПЕРЕИМЕНОВАТЬ из START_HERE.txt)
```

## Действия по реструктуризации

### Фаза 1: Организация документации (ПРИОРИТЕТ)
1. ✅ Создать структуру папок в `docs/`
2. ✅ Переместить отчеты в `docs/reports/`
3. ✅ Переместить гайды в соответствующие подпапки
4. ✅ Обновить главный README.md

### Фаза 2: Очистка корня
1. ✅ Переместить скрипты из корня в `scripts/`
2. ✅ Переместить старые бэкапы в `data/backups/`
3. ✅ Обновить .gitignore
4. ✅ Переместить migration_data в `data/migrations/`

### Фаза 3: Реорганизация кода (ОПЦИОНАЛЬНО)
1. ⚠️ Создать `app/core/` для конфигурации
2. ⚠️ Объединить `app/utils.py` и `app/utils/`
3. ⚠️ Разделить handlers по модулям
4. ⚠️ Создать repositories для БД

### Фаза 4: Тесты
1. ✅ Создать `tests/unit/` и `tests/integration/`
2. ✅ Переместить тесты в соответствующие папки

### Фаза 5: Обновление конфигов
1. ✅ Обновить пути импортов
2. ✅ Обновить docker конфиги
3. ✅ Обновить Makefile
4. ✅ Запустить тесты

## Преимущества новой структуры

✅ **Чистый корень** - только основные файлы конфигурации
✅ **Организованная документация** - легко найти нужный гайд
✅ **Разделение ответственности** - handlers разбиты по модулям
✅ **Масштабируемость** - легко добавлять новые модули
✅ **Профессиональная структура** - соответствует best practices
✅ **Упрощенное тестирование** - четкое разделение unit/integration

## Риски

⚠️ **Поломка импортов** - нужно обновить все пути
⚠️ **Время на рефакторинг** - может занять несколько часов
⚠️ **Тестирование** - нужно проверить все функции после

## Рекомендация

**Начать с Фазы 1 и 2** (организация документации и очистка корня) - это безопасно и сразу улучшит проект.

**Фазу 3** (реорганизация кода) делать постепенно, если есть время.
