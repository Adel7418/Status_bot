# План миграции на ORMDatabase для Docker

## 🐳 Миграция в Docker-окружении

### Текущее состояние
- ✅ Локальная разработка с ORMDatabase готова
- ✅ Все изменения протестированы
- 🐳 Сервер работает в Docker

## 🚀 План миграции для Docker

### 1. Подготовка к миграции

#### 1.1 Создание бэкапа
```bash
# На сервере
docker-compose exec bot cp /app/data/bot_database.db /app/data/bot_database_backup_$(date +%Y%m%d_%H%M%S).db

# Или скопировать из контейнера на хост
docker cp $(docker-compose ps -q bot):/app/data/bot_database.db ./bot_database_backup_$(date +%Y%m%d_%H%M%S).db
```

#### 1.2 Проверка текущего состояния
```bash
# Проверить статус контейнеров
docker-compose ps

# Проверить логи
docker-compose logs bot

# Проверить версию миграции
docker-compose exec bot alembic current
```

### 2. Обновление кода

#### 2.1 Остановка сервисов
```bash
# Остановить бота
docker-compose stop bot

# Или остановить все сервисы
docker-compose down
```

#### 2.2 Обновление кода
```bash
# Обновить код (git pull или загрузка файлов)
git pull origin main

# Или загрузить обновленные файлы:
# - app/database/orm_database.py
# - app/handlers/admin.py
# - app/handlers/master.py
# - app/services/scheduler.py
# - app/handlers/financial_reports.py
```

#### 2.3 Пересборка образа (если нужно)
```bash
# Пересобрать образ с новым кодом
docker-compose build bot

# Или пересобрать все
docker-compose build
```

### 3. Применение миграций

#### 3.1 Запуск контейнера для миграции
```bash
# Запустить только для миграции
docker-compose run --rm bot alembic upgrade head

# Или запустить контейнер и выполнить миграцию внутри
docker-compose run --rm bot bash
# Внутри контейнера:
alembic current
alembic upgrade head
exit
```

#### 3.2 Проверка миграций
```bash
# Проверить статус
docker-compose run --rm bot alembic current

# Проверить историю
docker-compose run --rm bot alembic history
```

### 4. Запуск и проверка

#### 4.1 Запуск сервисов
```bash
# Запустить все сервисы
docker-compose up -d

# Или только бота
docker-compose up -d bot
```

#### 4.2 Проверка работы
```bash
# Проверить статус контейнеров
docker-compose ps

# Проверить логи бота
docker-compose logs -f bot

# Проверить логи всех сервисов
docker-compose logs -f
```

## 🔧 Docker-специфичные команды

### Проверка базы данных
```bash
# Подключиться к базе данных в контейнере
docker-compose exec bot sqlite3 /app/data/bot_database.db

# Выполнить SQL-запросы
docker-compose exec bot sqlite3 /app/data/bot_database.db "SELECT COUNT(*) FROM orders;"
docker-compose exec bot sqlite3 /app/data/bot_database.db "SELECT COUNT(*) FROM masters;"

# Проверить схему таблиц
docker-compose exec bot sqlite3 /app/data/bot_database.db ".schema orders"
docker-compose exec bot sqlite3 /app/data/bot_database.db ".schema masters"
```

### Управление контейнерами
```bash
# Перезапустить только бота
docker-compose restart bot

# Перезапустить все сервисы
docker-compose restart

# Остановить все
docker-compose down

# Запустить в фоне
docker-compose up -d

# Посмотреть использование ресурсов
docker stats
```

## 📋 Автоматизированный скрипт для Docker

Создайте файл `docker_migrate.sh`:

```bash
#!/bin/bash
set -e

echo "🐳 Миграция ORMDatabase в Docker"
echo "================================="

# 1. Создание бэкапа
echo "📁 Создание бэкапа..."
BACKUP_NAME="bot_database_backup_$(date +%Y%m%d_%H%M%S).db"
docker-compose exec bot cp /app/data/bot_database.db /app/data/$BACKUP_NAME
echo "✅ Бэкап создан: $BACKUP_NAME"

# 2. Остановка бота
echo "⏹️ Остановка бота..."
docker-compose stop bot

# 3. Применение миграций
echo "🔄 Применение миграций..."
docker-compose run --rm bot alembic upgrade head

# 4. Запуск бота
echo "▶️ Запуск бота..."
docker-compose up -d bot

# 5. Проверка
echo "🔍 Проверка работы..."
sleep 5
docker-compose ps
docker-compose logs --tail=20 bot

echo "🎉 Миграция завершена!"
echo "📁 Бэкап: $BACKUP_NAME"
```

## ⚠️ Возможные проблемы и решения

### Проблема 1: Контейнер не запускается
```bash
# Проверить логи
docker-compose logs bot

# Проверить конфигурацию
docker-compose config

# Пересобрать образ
docker-compose build --no-cache bot
```

### Проблема 2: Ошибки миграции
```bash
# Откатить миграцию
docker-compose run --rm bot alembic downgrade -1

# Проверить статус
docker-compose run --rm bot alembic current
```

### Проблема 3: Проблемы с базой данных
```bash
# Восстановить бэкап
docker-compose exec bot cp /app/data/bot_database_backup_YYYYMMDD_HHMMSS.db /app/data/bot_database.db

# Перезапустить
docker-compose restart bot
```

## 🔍 Мониторинг

### Логи
```bash
# Логи бота в реальном времени
docker-compose logs -f bot

# Логи всех сервисов
docker-compose logs -f

# Последние 100 строк логов
docker-compose logs --tail=100 bot
```

### Ресурсы
```bash
# Использование ресурсов
docker stats

# Информация о контейнерах
docker-compose ps
docker inspect $(docker-compose ps -q bot)
```

## ✅ Чек-лист для Docker

- [ ] Бэкап БД создан
- [ ] Код обновлен
- [ ] Образ пересобран (если нужно)
- [ ] Миграции применены
- [ ] Контейнеры запущены
- [ ] Логи проверены
- [ ] Функции протестированы

## 🆘 Откат для Docker

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
