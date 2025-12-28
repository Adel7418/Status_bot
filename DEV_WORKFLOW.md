# 🚀 Workflow для разработки с Docker

## Быстрый старт

```bash
# 1. Запустить city1 для разработки
make mb-start-city1

# 2. Смотреть логи в реальном времени
make mb-logs-city1

# 3. После изменений кода - перезапустить
make mb-restart-city1
```

## Основные команды

### Запуск/Остановка
```bash
make mb-start          # Запустить оба бота
make mb-start-city1    # Только city1
make mb-start-city2    # Только city2
make mb-stop           # Остановить всё
make mb-restart-city1  # Перезапустить city1
```

### Логи
```bash
make mb-logs-city1     # Логи city1 (real-time)
make mb-logs-city2     # Логи city2
make mb-logs           # Все логи
```

### Работа с контейнером
```bash
make mb-shell-city1    # Зайти в контейнер city1
docker exec -it telegram_repair_bot_city1 bash
```

### Миграции
```bash
make mb-migrate-city1  # Применить миграции для city1
make mb-migrate-all    # Для обоих ботов
```

### Обновление кода
```bash
# После git pull:
make mb-restart-city1  # Быстрый перезапуск

# Или полная пересборка (если изменились зависимости):
make mb-update-city1
```

## Типичный цикл разработки

1. **Редактируете код** в VSCode/IDE
2. **Сохраняете изменения**
3. **Перезапускаете бот**: `make mb-restart-city1`
4. **Проверяете в Telegram**
5. **Смотрите логи**: `make mb-logs-city1`

## Отладка

```bash
# Зайти в контейнер для отладки
make mb-shell-city1

# Внутри контейнера:
python -c "from app.config import Config; print(Config.BOT_TOKEN)"
alembic current
python scripts/check_user_role.py YOUR_TELEGRAM_ID
```

## Полезные команды Docker

```bash
# Статус контейнеров
docker ps

# Логи конкретного контейнера
docker logs -f telegram_repair_bot_city1

# Перезапуск
docker restart telegram_repair_bot_city1

# Очистка (если что-то сломалось)
docker-compose -f docker/docker-compose.multibot.yml down
docker-compose -f docker/docker-compose.multibot.yml up -d --build
```

## Git workflow

```bash
# Быстрое сохранение изменений
make git-save MSG="Описание изменений"

# Получить изменения с сервера
git pull

# После pull обновить бота
make mb-update-city1
```

## Советы

- 💡 Работайте с city1 для dev, city2 для тестирования
- 💡 Всегда смотрите логи после перезапуска
- 💡 Если изменили requirements.txt - нужна пересборка (`make mb-update-city1`)
- 💡 Для быстрых правок кода достаточно `make mb-restart-city1`
