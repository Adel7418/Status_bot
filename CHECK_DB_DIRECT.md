# 🔍 Проверка базы данных напрямую

## Выполните на сервере:

```bash
# 1. Проверьте work_chat_id в базе данных
docker exec telegram_repair_bot_prod sqlite3 /app/data/bot_database.db "SELECT id, telegram_id, work_chat_id FROM masters ORDER BY id;"

# 2. Проверьте схему таблицы masters
docker exec telegram_repair_bot_prod sqlite3 /app/data/bot_database.db ".schema masters"

# 3. Проверьте, какие файлы БД существуют
docker exec telegram_repair_bot_prod ls -lh /app/data/

# 4. Проверьте путь к БД в контейнере
docker exec telegram_repair_bot_prod env | grep DATABASE_PATH
```

## Возможная проблема:

❌ **Бот использует ДРУГУЮ базу данных!**

Возможно:
- Есть несколько файлов `bot_database.db`
- Путь к БД указан неправильно
- База данных не примонтирована правильно

---

## Решение:

### Вариант 1: Проверить все БД файлы

```bash
# Найти все файлы bot_database.db
docker exec telegram_repair_bot_prod find /app -name "bot_database.db*"

# Проверить work_chat_id в каждом из них
```

### Вариант 2: Применить миграции

Возможно, в базе данных старая схема без колонки `work_chat_id` или она была добавлена неправильно.

```bash
# Проверить миграции
docker exec telegram_repair_bot_prod alembic current
docker exec telegram_repair_bot_prod alembic heads
docker exec telegram_repair_bot_prod alembic upgrade head
```

### Вариант 3: Восстановить из бэкапа (если нужно)

```bash
# Проверить, что в бэкапе есть work_chat_id
sqlite3 backups/bot_database_2025-10-20_20-29-43.db "SELECT id, telegram_id, work_chat_id FROM masters;"
```

---

**Выполните команды и покажите результат!** 🔍
