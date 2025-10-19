# 🔧 Исправление ошибки миграций Alembic

**Ошибка:** `Requested revision 005_add_reschedule_fields overlaps with other requested revisions 004_add_order_reports`

**Причина:** Конфликт в таблице `alembic_version` или некорректное состояние миграций

---

## ⚡ Быстрое решение (выполните на сервере)

### Шаг 1: Проверьте текущее состояние

```bash
cd ~/telegram_repair_bot

# Проверьте версию миграций
alembic current

# Проверьте таблицу alembic_version
sqlite3 bot_database.db "SELECT * FROM alembic_version;"
```

**Ожидается:**
- Либо пусто (миграции не применялись)
- Либо одна строка с version_num

---

### Шаг 2: Сбросьте состояние миграций

```bash
# Удалите таблицу alembic_version
sqlite3 bot_database.db "DROP TABLE IF EXISTS alembic_version;"

# Проверьте какие таблицы есть
sqlite3 bot_database.db ".tables"
```

**Если таблиц НЕТ или только alembic_version:**
```bash
# Примените миграции с нуля
alembic upgrade head
```

**Если таблицы УЖЕ ЕСТЬ (users, masters, orders и т.д.):**
```bash
# Пометьте текущую версию вручную
alembic stamp head

# Это установит версию без выполнения миграций
```

---

### Шаг 3: Проверьте результат

```bash
# Проверьте версию
alembic current
# Должно показать: 005_add_reschedule_fields (head)

# Проверьте таблицы
sqlite3 bot_database.db ".tables"
# Должно быть 8 таблиц

# Проверьте структуру orders (должны быть новые поля)
sqlite3 bot_database.db ".schema orders" | grep reschedule
# Должно показать: rescheduled_count, last_rescheduled_at, reschedule_reason
```

---

## 🔄 Альтернативный способ (если не помогло)

### Вариант 1: Создать БД заново (ЕСЛИ НЕТ ВАЖНЫХ ДАННЫХ)

```bash
cd ~/telegram_repair_bot

# Backup старой БД (на всякий случай)
cp bot_database.db bot_database.db.backup.$(date +%Y%m%d)

# Удалите БД
rm bot_database.db bot_database.db-wal bot_database.db-shm

# Примените миграции на свежую БД
alembic upgrade head

# Проверьте
sqlite3 bot_database.db ".tables"
```

---

### Вариант 2: Исправить через Docker (ваш случай)

```bash
cd ~/telegram_repair_bot/docker

# Зайдите в контейнер
docker-compose -f docker-compose.prod.yml exec bot bash

# Внутри контейнера:
cd /app

# Проверьте состояние
alembic current

# Сбросьте и примените заново
sqlite3 bot_database.db "DROP TABLE IF EXISTS alembic_version;"
alembic upgrade head

# Выйдите
exit

# Перезапустите бота
docker-compose -f docker-compose.prod.yml restart bot
```

---

### Вариант 3: Ручное исправление (если таблицы уже есть)

```bash
# 1. Проверьте какие таблицы есть
sqlite3 bot_database.db ".tables"

# 2. Проверьте структуру orders
sqlite3 bot_database.db "PRAGMA table_info(orders);" | grep reschedule

# Если полей reschedule НЕТ:
sqlite3 bot_database.db << EOF
ALTER TABLE orders ADD COLUMN rescheduled_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE orders ADD COLUMN last_rescheduled_at DATETIME;
ALTER TABLE orders ADD COLUMN reschedule_reason TEXT;
EOF

# 3. Установите версию миграций вручную
sqlite3 bot_database.db << EOF
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL
);
DELETE FROM alembic_version;
INSERT INTO alembic_version VALUES ('005_add_reschedule_fields');
EOF

# 4. Проверьте
alembic current
```

---

## 🎯 Рекомендуемая последовательность для ВАС

**На production сервере выполните:**

```bash
# 1. Перейдите в директорию
cd ~/telegram_repair_bot

# 2. Проверьте что есть
sqlite3 bot_database.db ".tables"

# Если таблиц НЕТ:
alembic upgrade head

# Если таблицы ЕСТЬ, но миграции ломаются:
sqlite3 bot_database.db "DROP TABLE IF EXISTS alembic_version;"
alembic stamp head

# 3. Проверьте что всё ОК
alembic current
sqlite3 bot_database.db ".tables"

# 4. Теперь можно проверить нагрузку
python3 -c "import sqlite3; conn = sqlite3.connect('bot_database.db'); c = conn.cursor(); masters = c.execute('SELECT COUNT(*) FROM masters WHERE is_active=1').fetchone()[0]; orders = c.execute('SELECT COUNT(*) FROM orders WHERE created_at > datetime(\"now\", \"-30 days\")').fetchone()[0]; print(f'Мастеров: {masters}, Заявок/месяц: {orders}, Заявок/день: {orders/30:.1f}')"
```

---

## 📞 Покажите результаты

После выполнения команд покажите:

1. Результат `sqlite3 bot_database.db ".tables"`
2. Результат `alembic current`
3. Результат проверки нагрузки (мастеров, заявок)

И я скажу **точно** насколько критично мигрировать на PostgreSQL для вашего случая! 📊
