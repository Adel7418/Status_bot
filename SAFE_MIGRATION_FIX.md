# ✅ Безопасное исправление миграций (БЕЗ удаления данных)

**Проблема:** Таблицы уже существуют (созданы через legacy схему в `db.py`), но Alembic не знает об этом

**Решение:** Пометить БД как "миграции применены" через `alembic stamp`

---

## 🎯 БЕЗОПАСНОЕ решение (данные НЕ теряются)

### На production сервере выполните:

```bash
cd ~/telegram_repair_bot

# 1. Проверьте какие таблицы УЖЕ ЕСТЬ
docker-compose -f docker/docker-compose.prod.yml exec bot sqlite3 /app/data/bot_database.db ".tables"
```

**Ожидаемый результат:**
```
alembic_version         masters                   orders
audit_log              order_status_history      users
financial_reports      master_financial_reports
# + возможно другие
```

**Если таблицы ЕСТЬ** → переходите к Шагу 2

---

### Шаг 2: Проверьте структуру таблиц

```bash
# Проверьте есть ли новые поля из миграции 005
docker-compose -f docker/docker-compose.prod.yml exec bot sqlite3 /app/data/bot_database.db "PRAGMA table_info(orders);" | grep reschedule
```

**Вариант A: Полей НЕТ** (нужно добавить вручную)
```bash
# Добавьте поля из миграции 005 вручную
docker-compose -f docker/docker-compose.prod.yml exec bot sqlite3 /app/data/bot_database.db << 'EOF'
ALTER TABLE orders ADD COLUMN rescheduled_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE orders ADD COLUMN last_rescheduled_at DATETIME;
ALTER TABLE orders ADD COLUMN reschedule_reason TEXT;
EOF
```

**Вариант B: Поля УЖЕ ЕСТЬ** (всё ОК, пропустите)

---

### Шаг 3: Пометьте что миграции применены

```bash
# Сбросьте текущее состояние
docker-compose -f docker/docker-compose.prod.yml exec bot sqlite3 /app/data/bot_database.db "DROP TABLE IF EXISTS alembic_version;"

# Пометьте что все миграции применены (БЕЗ их выполнения)
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic stamp head
```

**Что делает `alembic stamp head`:**
- ✅ Создаёт таблицу `alembic_version`
- ✅ Записывает текущую версию = 005_add_reschedule_fields
- ✅ **НЕ** выполняет миграции (данные не трогает!)
- ✅ Alembic думает что всё уже применено

---

### Шаг 4: Проверьте результат

```bash
# Проверьте версию
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic current
# Должно показать: 005_add_reschedule_fields (head)

# Проверьте что таблицы на месте
docker-compose -f docker/docker-compose.prod.yml exec bot sqlite3 /app/data/bot_database.db ".tables"

# Проверьте количество данных (ничего не должно пропасть)
docker-compose -f docker/docker-compose.prod.yml exec bot sqlite3 /app/data/bot_database.db "SELECT COUNT(*) FROM orders;"
```

---

### Шаг 5: Теперь проверьте нагрузку

```bash
docker-compose -f docker/docker-compose.prod.yml exec bot python3 -c "import sqlite3; conn = sqlite3.connect('/app/data/bot_database.db'); c = conn.cursor(); masters = c.execute('SELECT COUNT(*) FROM masters WHERE is_active=1').fetchone()[0]; orders = c.execute('SELECT COUNT(*) FROM orders WHERE created_at > datetime(\"now\", \"-30 days\")').fetchone()[0]; print(f'Мастеров: {masters}, Заявок/месяц: {orders}, Заявок/день: {orders/30:.1f}')"
```

---

## 📋 Краткая инструкция

**Скопируйте и вставьте на сервере:**

```bash
cd ~/telegram_repair_bot

# 1. Сбросить состояние миграций
docker-compose -f docker/docker-compose.prod.yml exec bot sqlite3 /app/data/bot_database.db "DROP TABLE IF EXISTS alembic_version;"

# 2. Пометить как применённые (БЕЗ выполнения)
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic stamp head

# 3. Проверить
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic current

# 4. Проверить нагрузку
docker-compose -f docker/docker-compose.prod.yml exec bot python3 -c "import sqlite3; conn = sqlite3.connect('/app/data/bot_database.db'); c = conn.cursor(); masters = c.execute('SELECT COUNT(*) FROM masters WHERE is_active=1').fetchone()[0]; orders = c.execute('SELECT COUNT(*) FROM orders WHERE created_at > datetime(\"now\", \"-30 days\")').fetchone()[0]; print(f'Мастеров: {masters}, Заявок/месяц: {orders}, Заявок/день: {orders/30:.1f}')"
```

---

## ✅ Гарантия безопасности

**Команда `alembic stamp head`:**
- ✅ **НЕ** трогает данные
- ✅ **НЕ** изменяет структуру таблиц
- ✅ **ТОЛЬКО** обновляет таблицу `alembic_version`

**Ваши данные в безопасности!** 🔒

---

Выполните эти команды и покажите результат последней команды (проверка нагрузки) 📊
