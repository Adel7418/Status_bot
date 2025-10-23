# Инструкции для применения миграции на продакшене

## Проблема
В продакшене возникает ошибка:
```
table audit_log has no column named deleted_at
```

## Решение
Нужно применить новую миграцию для добавления колонки `deleted_at` в таблицу `audit_log`.

## Команды для выполнения на сервере

### 1. Остановить бота
```bash
docker-compose -f docker/docker-compose.prod.yml down
```

### 2. Применить миграцию
```bash
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head
```

### 3. Запустить бота
```bash
docker-compose -f docker/docker-compose.prod.yml up -d
```

### 4. Проверить логи
```bash
docker-compose -f docker/docker-compose.prod.yml logs -f bot
```

## Альтернативный способ (если есть доступ к контейнеру)

### 1. Войти в контейнер
```bash
docker exec -it telegram_repair_bot_prod bash
```

### 2. Применить миграцию
```bash
alembic upgrade head
```

### 3. Выйти из контейнера
```bash
exit
```

### 4. Перезапустить контейнер
```bash
docker-compose -f docker/docker-compose.prod.yml restart bot
```

## Проверка результата
После применения миграции в логах должно появиться одно из сообщений:

**Если таблица audit_log существует:**
```
[OK] Добавлена колонка deleted_at в audit_log
```
или
```
[OK] Колонка deleted_at уже существует в audit_log
```

**Если таблица audit_log не существует (что нормально):**
```
[SKIP] Таблица audit_log не существует - пропускаем миграцию
```

## Откат (если что-то пошло не так)
```bash
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade -1
```
