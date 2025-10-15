# 🔧 Исправление проблемы миграций

## ❌ Проблема

```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) table users already exists
```

**Причина:** База данных уже существует (создана через `db.init_db()`), но Alembic не знает об этом и пытается создать таблицы заново.

---

## ✅ Решение

### Вариант 1: Пометить БД как "уже с миграциями" (БЕЗ потери данных)

**На сервере выполните:**

```bash
# Пометить БД как находящуюся на последней миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic stamp head

# Проверить версию
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current

# Теперь можно применять новые миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head
```

**Эта команда говорит Alembic:** "Таблицы уже существуют, начни отслеживать с текущей версии"

---

### Вариант 2: Пересоздать БД с нуля (ПОТЕРЯ ДАННЫХ!)

**Только если нет важных данных:**

```bash
# Удалить БД
docker compose -f docker/docker-compose.prod.yml exec bot rm /app/bot_database.db

# Применить миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# Перезапустить
docker compose -f docker/docker-compose.prod.yml restart
```

---

## 🎯 Рекомендуемое решение

**Используйте Вариант 1** - он безопасный и сохраняет данные!

```bash
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic stamp head
```

Затем можно продолжить обновление как обычно.

---

## 📋 Обновленный процесс деплоя

### Первый деплой (БД уже существует)

```bash
# 1. Запуск бота
cd docker
docker-compose -f docker-compose.prod.yml up -d --build

# 2. Пометить БД как готовую (stamp)
docker-compose -f docker-compose.prod.yml run --rm bot alembic stamp head

# 3. Проверить версию
docker-compose -f docker-compose.prod.yml run --rm bot alembic current
```

### Последующие обновления

```bash
# Теперь используйте обычные команды
make prod-full-update

# Или
make prod-migrate
```

---

## 🔍 Проверка

После выполнения `alembic stamp head`:

```bash
# Проверить версию миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current

# Должно показать последнюю миграцию
```

---

**Команда для копирования:**

```bash
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic stamp head
```

**Эта команда безопасна и НЕ изменяет данные!** ✅

