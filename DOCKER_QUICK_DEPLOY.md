# Быстрое развертывание ORMDatabase в Docker

## 🚀 Быстрая миграция (5 минут)

### 1. Подготовка
```bash
# На сервере
cd /path/to/telegram_repair_bot
```

### 2. Автоматическая миграция
```bash
# Сделать скрипт исполняемым
chmod +x docker_migrate.sh

# Запустить миграцию
./docker_migrate.sh
```

### 3. Обновление кода (если нужно)
```bash
# Остановить бота
docker-compose stop bot

# Обновить код
git pull origin main

# Пересобрать образ (если нужно)
docker-compose build bot

# Запустить бота
docker-compose up -d bot
```

### 4. Проверка
```bash
# Проверить статус
docker-compose ps

# Посмотреть логи
docker-compose logs -f bot
```

## 📋 Ручная миграция (если автоматическая не работает)

### 1. Бэкап
```bash
# Создать бэкап
docker-compose exec bot cp /app/data/bot_database.db /app/data/bot_database_backup_$(date +%Y%m%d_%H%M%S).db
```

### 2. Миграции
```bash
# Остановить бота
docker-compose stop bot

# Применить миграции
docker-compose run --rm bot alembic upgrade head

# Запустить бота
docker-compose up -d bot
```

### 3. Проверка
```bash
# Проверить таблицы
docker-compose exec bot sqlite3 /app/data/bot_database.db ".schema orders"
docker-compose exec bot sqlite3 /app/data/bot_database.db ".schema masters"
```

## 🔧 Файлы для обновления

Обязательно обновить эти файлы на сервере:
- `app/database/orm_database.py` (с методом `delete_master`)
- `app/handlers/admin.py` (с `ORMDatabase`)
- `app/handlers/master.py` (обновление SLA)
- `app/services/scheduler.py` (уведомления диспетчеру)
- `app/handlers/financial_reports.py` (удалена кнопка кастомного отчета)
- `docker_migrate.sh` (скрипт миграции)

## ⚠️ Откат (если что-то пошло не так)

```bash
# Остановить все
docker-compose down

# Восстановить бэкап
docker-compose run --rm bot cp /app/data/bot_database_backup_YYYYMMDD_HHMMSS.db /app/data/bot_database.db

# Откатить код
git checkout HEAD~1

# Пересобрать и запустить
docker-compose build bot
docker-compose up -d
```

## ✅ Проверочный список

- [ ] Бэкап создан
- [ ] Миграции применены
- [ ] Код обновлен
- [ ] Контейнеры запущены
- [ ] Логи проверены
- [ ] Функции протестированы

## 🆘 Поддержка

Если возникли проблемы:
1. Проверьте логи: `docker-compose logs -f bot`
2. Проверьте статус: `docker-compose ps`
3. Восстановите бэкап и откатите код

## 📊 Мониторинг

```bash
# Логи в реальном времени
docker-compose logs -f bot

# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats

# Информация о контейнере
docker inspect $(docker-compose ps -q bot)
```
