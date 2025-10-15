# 🔄 Руководство по миграциям базы данных

## 📚 Что такое миграции?

**Миграции** — это версионированные изменения схемы базы данных. Они позволяют:
- Отслеживать изменения в структуре БД
- Применять изменения автоматически
- Откатывать изменения при необходимости
- Синхронизировать БД между разными средами

## 🛠️ Структура миграций

Проект использует **Alembic** — инструмент для миграций от создателей SQLAlchemy.

### Цепочка миграций

```
001_initial_schema (base)
    ↓
002_add_financial_reports
    ↓
003_add_dr_fields
    ↓
004_add_order_reports (head)
```

Каждая миграция знает о предыдущей через поле `down_revision`:

```python
# В файле 004_add_order_reports.py
revision = '004_add_order_reports'
down_revision = '003_add_dr_fields'  # Ссылка на предыдущую миграцию
```

### Важные правила

1. **Каждая миграция должна иметь уникальный ID**
2. **down_revision должен указывать на полный ID предыдущей миграции**
3. **Не изменяйте уже примененные миграции** — создавайте новые
4. **Тестируйте миграции локально** перед применением на продакшн

## 🚀 Работа с миграциями

### Локальная разработка

#### Просмотр текущей версии
```bash
alembic current
```

#### Просмотр истории миграций
```bash
alembic history --verbose
```

#### Создание новой миграции
```bash
# Автогенерация на основе изменений в моделях
alembic revision --autogenerate -m "описание изменений"

# Ручное создание миграции
alembic revision -m "описание изменений"
```

#### Применение миграций
```bash
# Применить все до последней
alembic upgrade head

# Применить конкретную миграцию
alembic upgrade 004_add_order_reports

# Применить +1 миграцию от текущей
alembic upgrade +1
```

#### Откат миграций
```bash
# Откатить на одну назад
alembic downgrade -1

# Откатить до конкретной версии
alembic downgrade 003_add_dr_fields

# Откатить все миграции
alembic downgrade base
```

### Продакшн среда (Docker)

#### Автоматическое применение (РЕКОМЕНДУЕТСЯ)
```bash
# Используйте скрипт деплоя
./scripts/deploy_with_migrations.sh
```

Этот скрипт:
1. Останавливает бота
2. Обновляет код из Git
3. Пересобирает Docker образ
4. Применяет миграции через Alembic
5. Если Alembic не работает — применяет миграции через Python скрипт
6. Перезапускает бота

#### Ручное применение через Alembic
```bash
docker compose -f docker/docker-compose.prod.yml exec bot alembic upgrade head
```

#### Ручное применение через Python скрипт
```bash
docker compose -f docker/docker-compose.prod.yml exec bot python scripts/fix_migrations_prod.py
```

## 🐛 Устранение проблем

### Проблема: "KeyError: '003'"

**Причина:** Несоответствие в ID миграций. Миграция ссылается на короткий ID (например, `'003'`), а реальная миграция имеет полный ID (`'003_add_dr_fields'`).

**Решение:**
1. Откройте файл миграции
2. Измените `down_revision` на полный ID:
   ```python
   # Было
   down_revision = '003'
   
   # Стало
   down_revision = '003_add_dr_fields'
   ```

### Проблема: "no such column: out_of_city"

**Причина:** База данных не содержит новых колонок, миграции не применены.

**Решение:**
```bash
# Применить миграции
docker compose -f docker/docker-compose.prod.yml exec bot python scripts/fix_migrations_prod.py
```

### Проблема: "Alembic can't locate the revision"

**Причина:** Файлы миграций не синхронизированы между локальной и продакшн средой.

**Решение:**
1. Убедитесь, что все миграции закоммичены в Git
2. На сервере выполните `git pull origin main`
3. Пересоберите Docker образ
4. Примените миграции

## 📝 Создание миграции: Пошаговое руководство

### Шаг 1: Изменить модель

Изменяем файл `app/database/models.py`:

```python
class Order:
    # ... существующие поля ...
    
    # Добавляем новое поле
    priority: str | None = None  # NEW, URGENT, CRITICAL
```

### Шаг 2: Создать миграцию

```bash
alembic revision --autogenerate -m "add priority field to orders"
```

Alembic создаст файл в `migrations/versions/` с примерно таким содержимым:

```python
"""add priority field to orders

Revision ID: 005_add_priority
Revises: 004_add_order_reports
Create Date: 2025-10-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_add_priority'
down_revision = '004_add_order_reports'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('priority', sa.String(), nullable=True))


def downgrade():
    op.drop_column('orders', 'priority')
```

### Шаг 3: Проверить миграцию

```bash
# Просмотреть SQL, который будет выполнен
alembic upgrade head --sql

# Применить миграцию локально
alembic upgrade head
```

### Шаг 4: Протестировать

Проверьте, что:
- База данных обновлена корректно
- Приложение работает с новой колонкой
- Откат миграции работает: `alembic downgrade -1`

### Шаг 5: Закоммитить

```bash
git add migrations/versions/005_add_priority.py
git add app/database/models.py
git commit -m "feat: add priority field to orders"
git push origin main
```

### Шаг 6: Применить на продакшн

```bash
# На сервере
./scripts/deploy_with_migrations.sh
```

## 🎯 Лучшие практики

### DO ✅

1. **Всегда тестируйте миграции локально** перед применением на продакшн
2. **Создавайте резервные копии БД** перед применением миграций
3. **Используйте понятные имена** для миграций
4. **Проверяйте откат** миграции (`downgrade`)
5. **Коммитьте миграции вместе с кодом**, который их использует

### DON'T ❌

1. **Не изменяйте уже примененные миграции** — создавайте новые
2. **Не удаляйте файлы миграций** из истории
3. **Не пропускайте миграции** — применяйте последовательно
4. **Не применяйте миграции вручную через SQL** — используйте Alembic
5. **Не коммитьте миграции с конфликтующими ID**

## 📊 Диагностика

### Проверка состояния миграций

```bash
# Локально
alembic current
alembic history

# В Docker
docker compose -f docker/docker-compose.prod.yml exec bot alembic current
docker compose -f docker/docker-compose.prod.yml exec bot alembic history
```

### Проверка структуры БД

```bash
# Локально
sqlite3 bot_database.db ".schema orders"

# В Docker
docker compose -f docker/docker-compose.prod.yml exec bot sqlite3 /app/data/bot_database.db ".schema orders"
```

### Использование диагностического скрипта

```bash
docker compose -f docker/docker-compose.prod.yml exec bot python scripts/fix_migrations_prod.py
```

Скрипт покажет:
- Текущие таблицы в БД
- Колонки в таблице orders
- Текущую версию миграции
- Применит миграции, если они не применены

## 🔗 Полезные ссылки

- [Документация Alembic](https://alembic.sqlalchemy.org/)
- [Tutorial по миграциям](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Cookbook с рецептами](https://alembic.sqlalchemy.org/en/latest/cookbook.html)

## 📞 Поддержка

Если у вас возникли проблемы с миграциями:

1. Проверьте раздел "Устранение проблем" выше
2. Запустите диагностический скрипт
3. Проверьте логи: `docker compose -f docker/docker-compose.prod.yml logs bot`
4. Создайте issue в репозитории проекта
