# 🚀 Настройка БД на Production сервере

**Проблема:** `OperationalError: no such table: masters`
**Причина:** Таблицы БД не созданы (миграции не применены)
**Решение:** Применить Alembic миграции

---

## ⚡ Быстрое решение (2 минуты)

### Вариант A: Применить миграции Alembic (рекомендуется)

```bash
# На сервере (SSH подключение)
cd ~/telegram_repair_bot

# Проверьте наличие Alembic
which alembic
# или
alembic --version

# Если Alembic не установлен:
pip3 install alembic

# Примените миграции
alembic upgrade head

# Проверьте таблицы
sqlite3 bot_database.db "SELECT name FROM sqlite_master WHERE type='table';"
```

**Ожидаемый результат:**
```
users
masters
orders
order_status_history
audit_log
financial_reports
master_financial_reports
alembic_version
```

---

### Вариант B: Автоматическое создание через бота (если нет Alembic)

```bash
# На сервере
cd ~/telegram_repair_bot

# Запустите бота (он создаст таблицы автоматически)
python3 bot.py

# В логах должно быть:
# "⚠️  Таблицы БД не найдены! Запустите миграции: alembic upgrade head"
# "[OK] Legacy схема создана"

# Остановите бота (Ctrl+C)

# Проверьте таблицы
sqlite3 bot_database.db "SELECT name FROM sqlite_master WHERE type='table';"
```

---

## 🔍 Диагностика текущей ситуации

### Проверьте что у вас на сервере:

```bash
# 1. Где вы находитесь?
pwd
# Должно быть: /root/telegram_repair_bot

# 2. Есть ли файл БД?
ls -lh bot_database.db
# У вас показал: 126976 байт = 124 KB (файл есть)

# 3. Какие таблицы есть?
sqlite3 bot_database.db "SELECT name FROM sqlite_master WHERE type='table';"
# У вас: пусто или старые таблицы

# 4. Есть ли Alembic?
alembic --version

# 5. Есть ли миграции?
ls -la migrations/versions/
# Должно быть 5 файлов: 001_*.py ... 005_*.py
```

---

## ✅ Пошаговая инструкция для ВАШЕГО случая

### Шаг 1: Проверьте миграции

```bash
cd ~/telegram_repair_bot

# Посмотрите текущую версию БД
alembic current
```

**Если выдаёт ошибку или пусто:**
- Миграции не применялись

**Если показывает версию (например `005_add_reschedule_fields`):**
- Миграции уже применены ✅

### Шаг 2: Примените миграции

```bash
# Применить ВСЕ миграции
alembic upgrade head

# Должны увидеть:
# INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema
# INFO  [alembic.runtime.migration] Running upgrade 001 -> 002_add_financial_reports
# ...
```

### Шаг 3: Проверьте результат

```bash
# Проверьте таблицы
sqlite3 bot_database.db ".tables"

# Должно показать:
# audit_log                 masters
# financial_reports         order_status_history
# master_financial_reports  orders
# alembic_version           users
```

### Шаг 4: Повторите проверку нагрузки

```bash
python3 -c "import sqlite3; conn = sqlite3.connect('bot_database.db'); c = conn.cursor(); masters = c.execute('SELECT COUNT(*) FROM masters WHERE is_active=1').fetchone()[0]; orders = c.execute('SELECT COUNT(*) FROM orders WHERE created_at > datetime(\"now\", \"-30 days\")').fetchone()[0]; print(f'Мастеров: {masters}, Заявок/месяц: {orders}, Заявок/день: {orders/30:.1f}')"
```

**Теперь должно работать!** ✅

---

## 🆘 Если Alembic не установлен

```bash
# Установите Alembic
pip3 install alembic

# Проверьте
alembic --version

# Примените миграции
alembic upgrade head
```

---

## 🆘 Если миграции выдают ошибку

```bash
# Проверьте alembic.ini
cat alembic.ini | grep sqlalchemy.url

# Должно быть:
# sqlalchemy.url = sqlite:///bot_database.db

# Если путь неправильный - исправьте
nano alembic.ini
# Найдите строку sqlalchemy.url и убедитесь что путь правильный
```

---

## 🎯 После применения миграций

```bash
# 1. Запустите проверку нагрузки
python3 -c "import sqlite3; conn = sqlite3.connect('bot_database.db'); c = conn.cursor(); masters = c.execute('SELECT COUNT(*) FROM masters WHERE is_active=1').fetchone()[0]; orders = c.execute('SELECT COUNT(*) FROM orders WHERE created_at > datetime(\"now\", \"-30 days\")').fetchone()[0]; print(f'Мастеров: {masters}, Заявок/месяц: {orders}, Заявок/день: {orders/30:.1f}')"

# 2. Проверьте размер БД
du -h bot_database.db

# 3. Покажите результаты
```

---

## 📝 Краткая памятка

**На production сервере:**

```bash
# 1. Подключитесь по SSH
ssh root@your-server

# 2. Перейдите в директорию бота
cd ~/telegram_repair_bot

# 3. Примените миграции
alembic upgrade head

# 4. Проверьте таблицы
sqlite3 bot_database.db ".tables"

# 5. Запустите бота
python3 bot.py
# или
docker-compose up -d
```

---

**Запустите эти команды и покажите результат - я дам точную рекомендацию по SQLite vs PostgreSQL!** 📊

Какой из вариантов хотите попробовать?
- **A) Alembic миграции** (правильный способ, рекомендуется)
- **B) Запустить бота** (он создаст legacy схему)
