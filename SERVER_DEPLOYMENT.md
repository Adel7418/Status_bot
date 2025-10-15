# 🚀 Развертывание на сервере - Быстрая инструкция

## ✅ Что было исправлено

### Проблема с Alembic
- **Была:** Миграция 004 ссылалась на короткий ID `'003'`
- **Стало:** Миграция 004 ссылается на полный ID `'003_add_dr_fields'`
- **Результат:** Alembic теперь корректно применяет миграции

### Автоматизация
- Создан скрипт `scripts/deploy_with_migrations.sh`
- Скрипт применяет миграции автоматически (Alembic + Python fallback)
- Полная документация в `docs/MIGRATIONS_GUIDE.md`

## 🎯 Применение на сервере

### Вариант 1: Автоматический деплой (РЕКОМЕНДУЕТСЯ)

```bash
# Подключитесь к серверу
ssh root@your_server

# Перейдите в директорию проекта
cd ~/telegram_repair_bot

# Обновите код
git pull origin main

# Сделайте скрипт исполняемым
chmod +x scripts/deploy_with_migrations.sh

# Запустите автоматический деплой
./scripts/deploy_with_migrations.sh
```

### Вариант 2: Ручной деплой

```bash
# 1. Остановите бота
docker compose -f docker/docker-compose.prod.yml stop bot

# 2. Обновите код
git pull origin main

# 3. Пересоберите образ
docker compose -f docker/docker-compose.prod.yml build bot

# 4. Запустите бота
docker compose -f docker/docker-compose.prod.yml up -d bot

# 5. Примените миграции (автоматически определит метод)
docker compose -f docker/docker-compose.prod.yml exec bot python scripts/fix_migrations_prod.py

# 6. Перезапустите бота
docker compose -f docker/docker-compose.prod.yml restart bot

# 7. Проверьте логи
docker compose -f docker/docker-compose.prod.yml logs --tail=20 bot
```

## 🔍 Проверка результата

### Проверьте миграции

```bash
# Проверьте текущую версию миграции
docker compose -f docker/docker-compose.prod.yml exec bot alembic current

# Должно показать:
# 004_add_order_reports (head)
```

### Проверьте структуру БД

```bash
# Проверьте наличие таблиц
docker compose -f docker/docker-compose.prod.yml exec bot sqlite3 /app/data/bot_database.db "SELECT name FROM sqlite_master WHERE type='table'" 

# Должны быть:
# - financial_reports
# - master_financial_reports
# - order_reports
```

### Проверьте колонки в orders

```bash
docker compose -f docker/docker-compose.prod.yml exec bot sqlite3 /app/data/bot_database.db "PRAGMA table_info(orders)" | grep -E "out_of_city|estimated_completion_date|prepayment_amount"

# Должны быть все три колонки
```

### Протестируйте отчеты

1. Откройте бота в Telegram
2. Нажмите "📊 Отчеты"
3. Выберите любой тип отчета
4. Отчет должен сгенерироваться без ошибок

## 📊 Что делают скрипты

### `deploy_with_migrations.sh`
1. Останавливает бота
2. Обновляет код из Git
3. Пересобирает Docker образ
4. Применяет миграции через Alembic
5. Если Alembic не работает → использует Python скрипт
6. Перезапускает бота
7. Показывает логи и статус

### `fix_migrations_prod.py`
1. Проверяет текущее состояние БД
2. Пытается применить миграции через Alembic
3. Если Alembic не работает → применяет вручную через SQL:
   - Добавляет недостающие колонки
   - Создает недостающие таблицы
   - Создает индексы
   - Обновляет версию миграции

## 🐛 Устранение проблем

### "KeyError: '003'"
**Решение:** Уже исправлено в коде. Обновите и пересоберите:
```bash
git pull origin main
docker compose -f docker/docker-compose.prod.yml build bot
```

### "no such column: out_of_city"
**Решение:** Примените миграции:
```bash
docker compose -f docker/docker-compose.prod.yml exec bot python scripts/fix_migrations_prod.py
docker compose -f docker/docker-compose.prod.yml restart bot
```

### "no such table: financial_reports"
**Решение:** Тоже самое - примените миграции (см. выше)

## 📚 Дополнительные ресурсы

- **Полное руководство:** `docs/MIGRATIONS_GUIDE.md`
- **Быстрое обновление:** `БЫСТРОЕ_ОБНОВЛЕНИЕ.md`
- **Документация Alembic:** https://alembic.sqlalchemy.org/

## ✨ Результат

После применения этих изменений:
- ✅ Миграции применяются автоматически через Alembic
- ✅ Есть fallback на Python скрипт если Alembic не работает
- ✅ Отчеты работают корректно в продакшн среде
- ✅ Процесс деплоя полностью автоматизирован
- ✅ Полная документация для разработчиков
