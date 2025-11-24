# Инструкция по применению миграции SENIOR_MASTER на сервере

## Описание

Эта миграция добавляет поддержку роли `SENIOR_MASTER` в CheckConstraint таблицы `users`.

**Версия:** v2.6.3
**Миграция:** `f9ec1face4e2`
**Дата:** 2025-11-24

## Что изменилось

- Обновлен `CheckConstraint` в таблице `users` - добавлена роль `SENIOR_MASTER`
- Роль `SENIOR_MASTER` теперь валидируется на уровне базы данных
- Без этой миграции присвоение роли `SENIOR_MASTER` будет вызывать ошибку constraint violation

## Применение на сервере

### Вариант 1: Через Docker (Production)

```bash
# 1. Зайдите на сервер и перейдите в директорию проекта
cd /path/to/telegram_repair_bot

# 2. Получите последние изменения из GitHub
git pull origin main

# 3. Остановите бота
cd docker
docker-compose -f docker-compose.prod.yml down

# 4. Примените миграцию
docker-compose -f docker-compose.prod.yml run --rm bot alembic upgrade head

# 5. Запустите бота
docker-compose -f docker-compose.prod.yml up -d

# 6. Проверьте логи
docker-compose -f docker-compose.prod.yml logs -f bot
```

### Вариант 2: Через Make (Production)

```bash
# 1. Зайдите на сервер
cd /path/to/telegram_repair_bot

# 2. Получите изменения
git pull origin main

# 3. Примените миграцию и перезапустите бота
make prod-deploy
```

### Вариант 3: Локальная установка

```bash
# 1. Получите изменения
git pull origin main

# 2. Активируйте виртуальное окружение
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 3. Примените миграцию
alembic upgrade head

# 4. Перезапустите бота
python bot.py
```

## Проверка применения миграции

```bash
# Проверить текущую версию миграции
alembic current

# Должно вывести:
# f9ec1face4e2 (head)
```

## Откат миграции (если потребуется)

```bash
# Откатить на одну миграцию назад
alembic downgrade -1

# Или откатить к конкретной версии
alembic downgrade 62892e258c24
```

## Важно!

- ⚠️ Эта миграция **ОБЯЗАТЕЛЬНА** для работы функционала управления ролью SENIOR_MASTER
- ⚠️ Без этой миграции попытки добавить роль SENIOR_MASTER будут приводить к ошибкам БД
- ⚠️ Миграция безопасна и не удаляет/не изменяет существующие данные
- ✅ Миграция протестирована локально и работает корректно
- ✅ Поддерживается откат (downgrade)

## Связанные файлы

- `migrations/versions/f9ec1face4e2_add_senior_master_role_to_user_role_.py`
- `app/database/orm_models.py` (строки 60-66)
- `app/handlers/admin.py` (обработчики add/remove senior role)
- `app/keyboards/inline.py` (UI для управления ролью)

## Troubleshooting

### Ошибка: "constraint chk_users_role не найден"

Это нормально для некоторых баз данных. SQLite может не всегда корректно обрабатывать изменения constraint. В этом случае:

1. Проверьте, что миграция применилась: `alembic current`
2. Попробуйте создать тестового пользователя с ролью SENIOR_MASTER
3. Если ошибок нет - миграция применена успешно

### Бот не запускается после миграции

```bash
# Проверьте логи
docker-compose -f docker-compose.prod.yml logs bot

# Проверьте состояние миграций
docker-compose -f docker-compose.prod.yml run --rm bot alembic current

# Откатите миграцию и попробуйте снова
docker-compose -f docker-compose.prod.yml run --rm bot alembic downgrade -1
docker-compose -f docker-compose.prod.yml run --rm bot alembic upgrade head
```

## Поддержка

Если возникли проблемы с миграцией, проверьте:
- [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [docs/MIGRATIONS_GUIDE.md](MIGRATIONS_GUIDE.md)
