# 🐳 Инструкция по запуску бота через Docker

## 📋 Предварительные требования

1. ✅ Docker Desktop установлен и запущен
2. ✅ Файл `.env` настроен (уже существует)

## 🚀 Быстрый старт

### Вариант 1: Простой запуск (Development)

```powershell
# Из корневой директории проекта
docker-compose -f docker/docker-compose.yml up -d
```

### Вариант 2: Production запуск (рекомендуется для продакшена)

```powershell
docker-compose -f docker/docker-compose.prod.yml up -d
```

### Вариант 3: Development с hot-reload

```powershell
docker-compose -f docker/docker-compose.dev.yml up
```

## 📝 Пошаговая инструкция

### Шаг 1: Проверка Docker

```powershell
docker --version
docker-compose --version
```

Если не установлен - скачайте Docker Desktop для Windows: https://www.docker.com/products/docker-desktop

### Шаг 2: Проверка конфигурации

Убедитесь, что в файле `.env` указаны все необходимые параметры:
- `BOT_TOKEN` - токен вашего бота
- `ADMIN_IDS` - ваш Telegram ID
- `WORK_CHAT_ID` - ID группы для уведомлений
- `MASTER_IDS` - ID мастеров (если есть)
- `DISPATCHER_IDS` - ID диспетчеров (если есть)

### Шаг 3: Сборка образа

```powershell
# Сборка Docker образа
docker build -f docker/Dockerfile -t telegram-repair-bot:latest .
```

### Шаг 4: Запуск контейнера

```powershell
# Запуск в фоновом режиме
docker-compose -f docker/docker-compose.yml up -d

# Или для production:
docker-compose -f docker/docker-compose.prod.yml up -d
```

### Шаг 5: Проверка статуса

```powershell
# Проверить запущенные контейнеры
docker-compose -f docker/docker-compose.yml ps

# Или для production:
docker-compose -f docker/docker-compose.prod.yml ps
```

### Шаг 6: Просмотр логов

```powershell
# Просмотр логов в реальном времени
docker-compose -f docker/docker-compose.yml logs -f bot

# Последние 100 строк логов
docker-compose -f docker/docker-compose.yml logs --tail=100 bot
```

## 🔧 Основные команды

### Управление контейнером

```powershell
# Остановить бота
docker-compose -f docker/docker-compose.yml stop

# Запустить снова
docker-compose -f docker/docker-compose.yml start

# Перезапустить
docker-compose -f docker/docker-compose.yml restart

# Полностью остановить и удалить контейнеры
docker-compose -f docker/docker-compose.yml down
```

### Просмотр состояния

```powershell
# Статус контейнеров
docker-compose -f docker/docker-compose.yml ps

# Использование ресурсов
docker stats telegram_repair_bot

# Логи с фильтром по ошибкам
docker-compose -f docker/docker-compose.yml logs bot | Select-String "ERROR"
```

### Доступ к контейнеру

```powershell
# Войти в контейнер
docker-compose -f docker/docker-compose.yml exec bot bash

# Выполнить команду внутри контейнера
docker-compose -f docker/docker-compose.yml exec bot python scripts/check_database.py
```

## 📊 Структура данных

Docker монтирует следующие директории:

```
./data/          → /app/data/         (база данных)
./logs/          → /app/logs/         (логи)
./backups/       → /app/backups/      (резервные копии)
```

## 🔄 Обновление бота

```powershell
# 1. Остановить контейнер
docker-compose -f docker/docker-compose.yml stop bot

# 2. Обновить код (если используете Git)
git pull

# 3. Пересобрать образ
docker-compose -f docker/docker-compose.yml build bot

# 4. Запустить обновленный контейнер
docker-compose -f docker/docker-compose.yml up -d bot
```

## 💾 Резервное копирование

### Создание backup

```powershell
# Вручную
docker-compose -f docker/docker-compose.yml exec bot python scripts/backup_db.py

# Или из хоста
python scripts/backup_db.py
```

### Восстановление из backup

```powershell
# 1. Остановить бота
docker-compose -f docker/docker-compose.yml stop bot

# 2. Скопировать backup
copy backups\bot_database_2025-10-21_XX-XX-XX.db data\bot_database.db

# 3. Запустить бота
docker-compose -f docker/docker-compose.yml start bot
```

## 🐛 Устранение проблем

### Бот не запускается

```powershell
# Проверить логи
docker-compose -f docker/docker-compose.yml logs bot

# Проверить статус
docker-compose -f docker/docker-compose.yml ps

# Полный перезапуск
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml up -d
```

### База данных заблокирована

```powershell
# Остановить все контейнеры
docker-compose -f docker/docker-compose.yml down

# Удалить lock файлы (если есть)
del data\bot_database.db-shm
del data\bot_database.db-wal

# Запустить заново
docker-compose -f docker/docker-compose.yml up -d
```

### Нет места на диске

```powershell
# Очистить старые образы
docker image prune -a

# Очистить неиспользуемые контейнеры
docker container prune

# Полная очистка (ОСТОРОЖНО!)
docker system prune -a
```

### Не применяются изменения кода

```powershell
# Пересобрать без кэша
docker-compose -f docker/docker-compose.yml build --no-cache bot

# Запустить
docker-compose -f docker/docker-compose.yml up -d bot
```

## 📱 Проверка работы бота

После запуска:
1. Откройте Telegram
2. Найдите своего бота
3. Отправьте команду `/start`
4. Проверьте, что бот отвечает

## 🔐 Production настройки

Для production используйте `docker-compose.prod.yml`:

```powershell
# Запуск с Redis и ограничением ресурсов
docker-compose -f docker/docker-compose.prod.yml up -d

# Проверка всех сервисов (бот + Redis)
docker-compose -f docker/docker-compose.prod.yml ps

# Логи всех сервисов
docker-compose -f docker/docker-compose.prod.yml logs -f
```

## 📌 Полезные советы

1. **Всегда используйте `-d` флаг** для запуска в фоновом режиме
2. **Регулярно делайте backup** базы данных
3. **Следите за логами** через `logs -f`
4. **Проверяйте использование ресурсов** через `docker stats`
5. **Обновляйте образы** регулярно для безопасности

## 📚 Дополнительная документация

- Полная документация: `docs/DOCKER_USAGE.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`
- Production deploy: `docs/PRODUCTION_DEPLOY.md`

---

## ⚡ Самый простой способ (TL;DR)

```powershell
# Запустить
docker-compose -f docker/docker-compose.yml up -d

# Проверить логи
docker-compose -f docker/docker-compose.yml logs -f bot

# Остановить
docker-compose -f docker/docker-compose.yml down
```

🎉 **Готово! Ваш бот запущен в Docker!**

