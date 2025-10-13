# ⚡ Быстрое исправление: Миграции теперь работают!

**Дата:** 13 октября 2025  
**Статус:** ✅ Исправлено

---

## 🔧 Что было исправлено

### Проблема:
```bash
docker compose run --rm bot alembic upgrade head
# ❌ Запускался бот вместо миграций
```

### Решение:
Изменен `Dockerfile`: `ENTRYPOINT` → `CMD`

Теперь команды можно переопределять! ✅

---

## 🚀 Как применить миграции СЕЙЧАС

### На VPS (после git pull):

```bash
# 1. Перейти в проект
cd ~/telegram_repair_bot

# 2. Обновить код
git pull

# 3. Пересобрать образ
docker compose -f docker/docker-compose.prod.yml build

# 4. Остановить бота
docker compose -f docker/docker-compose.prod.yml down

# 5. Применить миграции (РАБОТАЕТ!)
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# 6. Запустить бота
docker compose -f docker/docker-compose.prod.yml up -d

# 7. Проверить логи
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

---

## 📋 Новые команды

### Через Docker:

```bash
# Применить миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# Текущая версия
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current

# История
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic history

# Откат на одну версию назад
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade -1
```

### Через Makefile (если есть):

```bash
# Применить миграции
make docker-migrate

# Локально (вне Docker)
make migrate

# Создать новую миграцию
make migrate-create MSG="add new field"

# Показать историю
make migrate-history
```

### Через скрипт:

```bash
# Сделать исполняемым (один раз)
chmod +x scripts/migrate.sh

# Применить миграции
./scripts/migrate.sh
```

---

## 🎯 Полный процесс деплоя с миграциями

```bash
# === НА VPS ===

cd ~/telegram_repair_bot

# 1. Обновить код
git pull

# 2. Пересобрать Docker образ
docker compose -f docker/docker-compose.prod.yml build

# 3. Остановить бота
docker compose -f docker/docker-compose.prod.yml down

# 4. Создать backup (важно!)
docker compose -f docker/docker-compose.prod.yml run --rm bot python backup_db.py

# 5. Применить миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# 6. Проверить версию БД
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current

# 7. Запустить бота
docker compose -f docker/docker-compose.prod.yml up -d

# 8. Проверить что всё работает
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

---

## 📊 Что изменилось в файлах

### 1. `docker/Dockerfile`
```diff
- ENTRYPOINT ["python", "bot.py"]
+ CMD ["python", "bot.py"]
```

### 2. Новые файлы:
- ✅ `scripts/migrate.sh` - скрипт для миграций
- ✅ `docker/docker-compose.migrate.yml` - конфиг для миграций
- ✅ `MIGRATION_GUIDE.md` - полное руководство
- ✅ `Makefile` - добавлены команды migrate

---

## 🔍 Проверка что миграции работают

```bash
# Применить миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# Ожидаемый вывод (правильный):
# INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
# INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
# INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema

# ❌ НЕ должно быть:
# "Бот успешно запущен!"
# "Start polling"
```

---

## 📚 Документация

- **MIGRATION_GUIDE.md** - Полное руководство по миграциям
- **DEPLOY_VPS_LINUX_GUIDE.md** - Деплой на VPS
- **scripts/migrate.sh** - Автоматический скрипт

---

## 💡 Совет

При первом деплое на новый VPS:

**Вариант 1: С миграциями (правильно)**
```bash
git clone https://github.com/Adel7418/Status_bot.git telegram_repair_bot
cd telegram_repair_bot
cp env.example .env
nano .env  # Настроить
docker compose -f docker/docker-compose.prod.yml build
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head
docker compose -f docker/docker-compose.prod.yml up -d
```

**Вариант 2: С готовой БД (быстро)**
```bash
# На Windows
scp bot_database.db root@IP:/root/telegram_repair_bot/data/

# На VPS
docker compose -f docker/docker-compose.prod.yml up -d
```

---

**Версия:** 1.0  
**Дата:** 13 октября 2025

✅ **Миграции теперь работают правильно!**

