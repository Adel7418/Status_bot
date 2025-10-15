# 📚 Документация Telegram Repair Bot

> Централизованный справочник по всей документации проекта

## 🚀 Быстрый старт

Новичок в проекте? Начните отсюда:

1. **[Установка](INSTALLATION.md)** - Установка и настройка проекта
2. **[Быстрый старт](QUICKSTART.md)** - Запуск бота за 5 минут
3. **[Деплой на сервер](../SERVER_DEPLOYMENT.md)** - Развертывание в продакшн

## 📖 Основная документация

### Разработка

- **[Contributing Guide](CONTRIBUTING.md)** - Как вносить изменения в проект
- **[Development Mode](DEV_MODE_GUIDE.md)** - Режим разработки
- **[Testing Guide](development/TESTING_GUIDE.md)** - Тестирование
- **[Debug Logging](DEBUG_LOGGING_GUIDE.md)** - Отладка и логирование

### База данных

- **[Migrations Guide](MIGRATIONS_GUIDE.md)** ⭐ - Работа с миграциями БД
- **[Database Usage](DATABASE_USAGE_GUIDE.md)** - Использование БД
- **[Backup Guide](BACKUP_GUIDE.md)** - Резервное копирование

### Развертывание

- **[Production Deploy](deployment/PRODUCTION_DEPLOY.md)** - Полное руководство по продакшн
- **[Docker Usage](DOCKER_USAGE.md)** - Работа с Docker
- **[Server Deployment](../SERVER_DEPLOYMENT.md)** ⭐ - Быстрое развертывание
- **[Quick Deploy Commands](deployment/QUICK_DEPLOY_COMMANDS.md)** - Шпаргалка команд

### Функциональность

- **[Financial Reports](FINANCIAL_REPORTS_GUIDE.md)** - Финансовые отчеты
- **[Multiple Roles](MULTIPLE_ROLES_GUIDE.md)** - Множественные роли
- **[Group Interaction](GROUP_INTERACTION_GUIDE.md)** - Работа в группах
- **[FSM State Management](FSM_STATE_MANAGEMENT.md)** - Управление состояниями

## 🆘 Помощь и устранение проблем

- **[Troubleshooting](TROUBLESHOOTING.md)** - Решение проблем
- **[Troubleshooting Directory](troubleshooting/)** - Специфичные проблемы
  - [Bot Update Issues](troubleshooting/BOT_UPDATE_ISSUES.md)
  - [Обновление бота кратко](troubleshooting/ОБНОВЛЕНИЕ_БОТА_КРАТКО.md)

## 👥 Пользовательские руководства

- **[Admin Guide](user-guides/admin_guide.md)** - Для администраторов
- **[Dispatcher Guide](user-guides/dispatcher_guide.md)** - Для диспетчеров
- **[Master Guide](user-guides/master_guide.md)** - Для мастеров

## 📊 Информация о проекте

- **[Project Info](PROJECT_INFO.md)** - Общая информация
- **[Workflow](WORKFLOW.md)** - Рабочий процесс
- **[Changelog](CHANGELOG.md)** - История изменений
- **[Summary](SUMMARY.md)** - Краткое описание

## 🔧 Для разработчиков

### Структура проекта

```
telegram_repair_bot/
├── app/                    # Код приложения
│   ├── handlers/          # Обработчики команд
│   ├── services/          # Бизнес-логика
│   ├── database/          # Работа с БД
│   └── keyboards/         # Клавиатуры
├── docs/                  # Документация
├── scripts/               # Скрипты
├── migrations/            # Миграции БД
├── docker/                # Docker конфигурация
└── tests/                 # Тесты
```

### Основные команды

```bash
# Локальная разработка
make run                    # Запустить бота
make migrate               # Применить миграции
make test                  # Запустить тесты
make lint                  # Проверить код

# Production (на сервере)
make prod-deploy           # Полный деплой с миграциями ⭐
make prod-diagnose         # Диагностика проблем
make prod-logs             # Логи
make prod-status           # Статус контейнеров
```

### Полезные ссылки

- **[Makefile](../Makefile)** - Все доступные команды
- **[Scripts README](../scripts/README.md)** - Описание скриптов
- **[Tests README](../tests/README.md)** - Информация о тестах

## 🎯 Частые задачи

### Обновить бота на сервере

```bash
ssh user@server
cd telegram_repair_bot
make prod-deploy
```

или

```bash
./scripts/deploy_with_migrations.sh
```

### Создать миграцию

```bash
make migrate-create MSG="описание изменений"
```

или

```bash
alembic revision --autogenerate -m "описание"
```

### Создать backup БД

```bash
make prod-backup
```

или

```bash
python scripts/backup_db.py
```

### Посмотреть логи

```bash
make prod-logs
```

## 🌟 Рекомендуемые документы для начала

Если вы:

### 👨‍💻 Разработчик
1. [CONTRIBUTING.md](CONTRIBUTING.md)
2. [MIGRATIONS_GUIDE.md](MIGRATIONS_GUIDE.md)
3. [DEV_MODE_GUIDE.md](DEV_MODE_GUIDE.md)

### 🚀 DevOps / Администратор сервера
1. [SERVER_DEPLOYMENT.md](../SERVER_DEPLOYMENT.md)
2. [deployment/PRODUCTION_DEPLOY.md](deployment/PRODUCTION_DEPLOY.md)
3. [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### 👤 Пользователь бота
1. [user-guides/admin_guide.md](user-guides/admin_guide.md)
2. [user-guides/dispatcher_guide.md](user-guides/dispatcher_guide.md)
3. [user-guides/master_guide.md](user-guides/master_guide.md)

## 💡 Нужна помощь?

1. Проверьте [Troubleshooting](TROUBLESHOOTING.md)
2. Посмотрите [Issues на GitHub](https://github.com/Adel7418/Status_bot/issues)
3. Создайте новый Issue с описанием проблемы

---

**Последнее обновление:** 2025-10-16  
**Версия документации:** 2.0
