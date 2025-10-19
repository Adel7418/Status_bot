# 🐳 Docker Usage Guide

## Быстрый старт

### 1. Подготовка

Создайте файл `.env` на основе `env.example`:

```bash
cp env.example .env
```

Отредактируйте `.env` и добавьте ваши данные:
- `BOT_TOKEN` - токен от @BotFather
- `ADMIN_IDS` - ваш Telegram ID
- `DISPATCHER_IDS` - ID диспетчеров (опционально)

### 2. Сборка образа

```bash
docker build -t telegram-repair-bot:latest .
```

### 3. Запуск

#### Development режим

```bash
docker-compose -f docker-compose.dev.yml up
```

#### Production режим

```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### Простой запуск (default)

```bash
docker-compose up -d
```

## Основные команды

### Управление контейнерами

```bash
# Запуск в фоновом режиме
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f bot

# Просмотр статуса
docker-compose ps
```

### Работа с образами

```bash
# Сборка без кэша
docker-compose build --no-cache

# Пересборка и запуск
docker-compose up --build -d

# Удаление старых образов
docker image prune -a
```

### Доступ к контейнеру

```bash
# Вход в bash
docker-compose exec bot bash

# Выполнение команды
docker-compose exec bot python check_database.py

# Просмотр логов в реальном времени
docker-compose logs -f --tail=100 bot
```

## Структура volumes

```
./data/          -> /app/data/        (база данных)
./logs/          -> /app/logs/        (логи)
./backups/       -> /app/backups/     (резервные копии)
```

## Режимы работы

### Development

- Hot-reload кода
- DEBUG логирование
- Монтирование всего проекта
- Без автоматического перезапуска

```bash
docker-compose -f docker-compose.dev.yml up
```

### Production

- Оптимизированный образ
- INFO логирование
- Автоматический перезапуск
- Ограничение ресурсов
- Healthcheck

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Резервное копирование

### Создание backup

```bash
# Вручную
docker-compose exec bot python backup_db.py

# Автоматическое (через cron)
0 2 * * * cd /path/to/project && docker-compose exec -T bot python backup_db.py
```

### Восстановление из backup

```bash
# Остановить бота
docker-compose stop bot

# Скопировать backup
cp backups/bot_database_YYYY-MM-DD_HH-MM-SS.db data/bot_database.db

# Запустить бота
docker-compose start bot
```

## Мониторинг

### Проверка health status

```bash
docker-compose ps
```

### Просмотр ресурсов

```bash
docker stats telegram_repair_bot
```

### Логи

```bash
# Все логи
docker-compose logs

# Последние 100 строк
docker-compose logs --tail=100 bot

# С фильтром
docker-compose logs bot | grep ERROR
```

## Redis (FSM Storage)

### Подключение к Redis

```bash
docker-compose exec redis redis-cli
```

### Проверка данных

```bash
# Количество ключей
docker-compose exec redis redis-cli DBSIZE

# Просмотр всех ключей
docker-compose exec redis redis-cli KEYS '*'

# Очистка (осторожно!)
docker-compose exec redis redis-cli FLUSHALL
```

## Troubleshooting

### Бот не запускается

```bash
# Проверить логи
docker-compose logs bot

# Проверить health
docker-compose ps

# Перезапустить
docker-compose restart bot
```

### База данных заблокирована

```bash
# Остановить все контейнеры
docker-compose down

# Удалить volume (ОСТОРОЖНО - потеря данных!)
docker volume rm telegram_repair_bot_bot_data

# Запустить заново
docker-compose up -d
```

### Нет доступа к файлам

```bash
# Проверить права
ls -la data/

# Изменить владельца (на хосте)
sudo chown -R 1000:1000 data/ logs/ backups/
```

### Out of memory

```bash
# Проверить использование памяти
docker stats

# Увеличить лимиты в docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 1G  # Увеличить с 512M
```

## Обновление

### Обновление кода

```bash
# 1. Остановить бота
docker-compose stop bot

# 2. Обновить код
git pull

# 3. Пересобрать образ
docker-compose build bot

# 4. Запустить
docker-compose up -d bot
```

### Обновление зависимостей

```bash
# 1. Обновить requirements.txt
# 2. Пересобрать без кэша
docker-compose build --no-cache bot

# 3. Перезапустить
docker-compose up -d bot
```

## Очистка

### Удалить всё

```bash
# Остановить и удалить контейнеры
docker-compose down

# Удалить volumes (ОСТОРОЖНО!)
docker-compose down -v

# Удалить образы
docker rmi telegram-repair-bot:latest

# Полная очистка Docker
docker system prune -a --volumes
```

### Удалить только старые контейнеры

```bash
docker-compose down
docker container prune
```

## Production Deployment

### На VPS/Dedicated Server

```bash
# 1. Клонировать репозиторий
git clone https://github.com/yourusername/telegram-repair-bot.git
cd telegram-repair-bot

# 2. Настроить .env
cp env.example .env
nano .env

# 3. Запустить в production режиме
docker-compose -f docker-compose.prod.yml up -d

# 4. Проверить статус
docker-compose -f docker-compose.prod.yml ps

# 5. Просмотреть логи
docker-compose -f docker-compose.prod.yml logs -f
```

### Автоматический запуск при старте системы

```bash
# Добавить в systemd
sudo nano /etc/systemd/system/telegram-bot.service
```

```ini
[Unit]
Description=Telegram Repair Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/telegram-repair-bot
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
# Активировать
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot

# Проверить статус
sudo systemctl status telegram-bot
```

## Советы по безопасности

1. **Не коммитить .env файл** - добавлен в `.gitignore`
2. **Использовать secrets** для production
3. **Ограничить сетевой доступ** через firewall
4. **Регулярно обновлять** образы и зависимости
5. **Делать backup** базы данных

## Полезные ссылки

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Aiogram Documentation](https://docs.aiogram.dev/)
