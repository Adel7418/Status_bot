# 🔄 Руководство по миграциям базы данных

**Дата:** 13 октября 2025
**Версия:** 1.0

---

## 📋 Содержание

1. [Что такое миграции](#что-такое-миграции)
2. [Применение миграций](#применение-миграций)
3. [Создание новых миграций](#создание-новых-миграций)
4. [Миграции в production](#миграции-в-production)
5. [Troubleshooting](#troubleshooting)

---

## 🎯 Что такое миграции

**Миграции** - это версионный контроль для схемы базы данных. Они позволяют:

- ✅ Воспроизводимо создавать структуру БД
- ✅ Отслеживать изменения схемы
- ✅ Откатываться к предыдущим версиям
- ✅ Безопасно обновлять production БД

Этот проект использует **Alembic** для управления миграциями.

---

## 🚀 Применение миграций

### Вариант 1: Через Docker (рекомендуется для VPS)

```bash
# Применить все миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# Просмотреть текущую версию
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current

# История миграций
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic history
```

### Вариант 2: Через вспомогательный скрипт

```bash
# Сделать скрипт исполняемым (один раз)
chmod +x scripts/migrate.sh

# Применить миграции
./scripts/migrate.sh

# С конкретной командой
./scripts/migrate.sh "upgrade head"
./scripts/migrate.sh "current"
```

### Вариант 3: Локально (для разработки)

```bash
# Активировать venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Применить миграции
alembic upgrade head

# Деактивировать
deactivate
```

---

## 📝 Создание новых миграций

### При изменении моделей БД:

```bash
# 1. Отредактируйте модели в app/database/models.py

# 2. Создайте новую миграцию
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic revision --autogenerate -m "описание изменений"

# Или локально:
alembic revision --autogenerate -m "add new field to users"

# 3. Проверьте созданный файл в migrations/versions/

# 4. Примените миграцию
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head
```

### Пример создания миграции:

```bash
# Добавили новое поле в модель User
alembic revision --autogenerate -m "add phone_number to users"

# Файл создан: migrations/versions/002_add_phone_number_to_users.py

# Применить
alembic upgrade head
```

---

## 🏭 Миграции в production

### Полный процесс деплоя с миграциями:

```bash
# 1. На локальной машине - создать и протестировать миграцию
alembic upgrade head
# Проверить что всё работает

# 2. Коммит и push
git add migrations/versions/
git commit -m "feat: add new migration"
git push

# 3. На VPS - обновить код
cd ~/telegram_repair_bot
git pull

# 4. Остановить бота (для безопасности)
docker compose -f docker/docker-compose.prod.yml down

# 5. Создать backup БД
docker compose -f docker/docker-compose.prod.yml run --rm bot python backup_db.py

# 6. Применить миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# 7. Запустить бота
docker compose -f docker/docker-compose.prod.yml up -d

# 8. Проверить логи
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

---

## 🔄 Откат миграций

### Откатиться на одну версию назад:

```bash
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade -1
```

### Откатиться к конкретной версии:

```bash
# Посмотреть историю
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic history

# Откатиться к версии
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade <revision_id>
```

### Откатиться к начальному состоянию:

```bash
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade base
```

---

## 📊 Полезные команды

### Проверка статуса:

```bash
# Текущая версия БД
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current

# История всех миграций
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic history

# Показать SQL без применения
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head --sql
```

### Проверка схемы БД:

```bash
# Войти в контейнер
docker compose -f docker/docker-compose.prod.yml exec bot bash

# Проверить таблицы
sqlite3 /app/data/bot_database.db ".tables"

# Схема конкретной таблицы
sqlite3 /app/data/bot_database.db ".schema users"

# Версия миграции
sqlite3 /app/data/bot_database.db "SELECT * FROM alembic_version"

# Выход
exit
```

---

## 🆘 Troubleshooting

### Проблема: "Target database is not up to date"

**Причина:** БД создана вручную, а не через миграции

**Решение:**

```bash
# Вариант 1: Пометить БД как актуальную
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic stamp head

# Вариант 2: Пересоздать БД через миграции
# ВНИМАНИЕ: Удалит все данные!
rm data/bot_database.db
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head
```

### Проблема: "Can't locate revision identified by 'head'"

**Причина:** Файлы миграций отсутствуют

**Решение:**

```bash
# Проверить наличие файлов миграций
ls -la migrations/versions/

# Если пусто - создать начальную миграцию
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic revision --autogenerate -m "initial schema"
```

### Проблема: "Multiple head revisions are present"

**Причина:** Конфликт версий миграций

**Решение:**

```bash
# Посмотреть heads
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic heads

# Слить ветки
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic merge heads -m "merge migrations"
```

### Проблема: Миграция применилась, но таблицы не созданы

**Решение:**

```bash
# Проверить файл миграции
cat migrations/versions/001_initial_schema.py

# Убедиться что функции upgrade() и downgrade() не пустые

# Откатить и применить заново
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade base
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head
```

---

## 🔧 Исправление существующей БД

### Если БД создана без миграций:

```bash
# 1. Создать backup
docker compose -f docker/docker-compose.prod.yml run --rm bot python backup_db.py

# 2. Экспортировать данные
docker compose -f docker/docker-compose.prod.yml run --rm bot python scripts/export_db.py

# 3. Удалить старую БД
rm data/bot_database.db

# 4. Создать через миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# 5. Импортировать данные
docker compose -f docker/docker-compose.prod.yml run --rm bot python scripts/import_db.py db_export_*.json
```

---

## 📋 Чеклист для работы с миграциями

### При первом деплое:

- [ ] Перенести код проекта на сервер
- [ ] Настроить .env файл
- [ ] Применить миграции: `alembic upgrade head`
- [ ] Импортировать данные (если нужно)
- [ ] Запустить бота

### При обновлении схемы БД:

- [ ] Изменить модели в коде
- [ ] Создать миграцию: `alembic revision --autogenerate -m "..."`
- [ ] Проверить созданную миграцию
- [ ] Протестировать локально
- [ ] Коммит и push
- [ ] На production: создать backup → применить миграции → перезапустить бота

### При откате изменений:

- [ ] Создать backup БД
- [ ] Откатить миграцию: `alembic downgrade -1`
- [ ] Проверить состояние БД
- [ ] Перезапустить бота

---

## 🎓 Примеры

### Пример 1: Добавление нового поля

```python
# 1. Изменить модель
# app/database/models.py
class User:
    ...
    phone_number: Optional[str] = None  # Новое поле

# 2. Создать миграцию
alembic revision --autogenerate -m "add phone_number to users"

# 3. Проверить файл миграции
# migrations/versions/002_add_phone_number.py

# 4. Применить
alembic upgrade head
```

### Пример 2: Создание новой таблицы

```python
# 1. Создать модель
# app/database/models.py
class Settings:
    id: int
    key: str
    value: str

# 2. Создать миграцию
alembic revision --autogenerate -m "add settings table"

# 3. Применить
alembic upgrade head
```

---

## 📚 Дополнительные ресурсы

- **Документация Alembic:** https://alembic.sqlalchemy.org/
- **DEPLOY_VPS_LINUX_GUIDE.md** - полное руководство по деплою
- **scripts/migrate.sh** - вспомогательный скрипт
- **Makefile** - команды для разработки

---

## 💡 Best Practices

1. **Всегда создавайте backup** перед применением миграций в production
2. **Тестируйте миграции** на копии production БД перед применением
3. **Проверяйте автогенерированные миграции** - иногда нужно корректировать вручную
4. **Не изменяйте примененные миграции** - создавайте новые
5. **Коммитьте миграции вместе с кодом** - они часть проекта
6. **Используйте осмысленные сообщения** при создании миграций
7. **Документируйте сложные миграции** - добавляйте комментарии

---

**Версия:** 1.0
**Дата:** 13 октября 2025
**Статус:** ✅ Ready to use

🔄 **Успешных миграций!**
