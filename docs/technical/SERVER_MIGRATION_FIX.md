# Исправление ошибки "ModuleNotFoundError: No module named 'dateparser'" при миграциях

## Проблема

При запуске миграций Alembic на сервере возникает ошибка:
```
ModuleNotFoundError: No module named 'dateparser'
```

Это происходит потому, что зависимости Python не установлены в окружении, где запускается Alembic.

## Решение

### Вариант 1: Установить зависимости на сервере (если миграции запускаются вне Docker)

```bash
# Установить зависимости
pip3 install -r requirements.txt

# Или если используете виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

После установки зависимостей запустите миграции:
```bash
alembic upgrade head
```

### Вариант 2: Использовать Docker для миграций (РЕКОМЕНДУЕТСЯ)

Если боты запущены в Docker контейнерах, используйте команды Makefile для миграций:

**Для city1:**
```bash
make mb-migrate-city1
make mb-start-city1
```

**Для city2:**
```bash
make mb-migrate-city2
make mb-start-city2
```

Эти команды запускают миграции внутри Docker контейнера, где все зависимости уже установлены.

### Вариант 3: Прямые Docker команды

Если Makefile недоступен, используйте прямые команды Docker:

**Для city1:**
```bash
docker compose -f docker/docker-compose.multibot.yml stop bot_city1
docker compose -f docker/docker-compose.multibot.yml run --rm bot_city1 alembic upgrade head
docker compose -f docker/docker-compose.multibot.yml up -d bot_city1
```

**Для city2:**
```bash
docker compose -f docker/docker-compose.multibot.yml stop bot_city2
docker compose -f docker/docker-compose.multibot.yml run --rm bot_city2 alembic upgrade head
docker compose -f docker/docker-compose.multibot.yml up -d bot_city2
```

### Вариант 4: Упрощенная миграция только для таблицы order_reports

Если нужно только создать таблицу `order_reports` без полной миграции, можно использовать Python скрипты:

**Для city1:**
```bash
docker compose -f docker/docker-compose.multibot.yml exec bot_city1 python scripts/create_order_reports_city1.py
```

**Для city2:**
```bash
docker compose -f docker/docker-compose.multibot.yml exec bot_city2 python scripts/create_order_reports_city2.py
```

## Рекомендация

**Используйте Вариант 2 (Docker через Makefile)** - это самый безопасный и надежный способ, так как:
- Все зависимости уже установлены в Docker контейнере
- Миграции применяются в правильном окружении
- Не нужно устанавливать зависимости на сервере вручную
