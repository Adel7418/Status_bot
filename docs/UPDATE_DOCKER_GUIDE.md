# 🔄 Обновление бота через Docker

**Дата:** 15.10.2025

---

## 🚀 Быстрое обновление (5 минут)

### На сервере:

```bash
# 1. Подключаемся к серверу
ssh root@ваш_IP

# 2. Переходим в директорию проекта
cd ~/telegram_repair_bot

# 3. Останавливаем бота
docker compose -f docker/docker-compose.prod.yml stop bot

# 4. Делаем бэкап БД (на всякий случай!)
cp bot_database.db bot_database_backup_$(date +%Y%m%d_%H%M%S).db

# 5. Обновляем код из Git
git pull origin main

# 6. Применяем миграции (если есть новые)
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# 7. Перезапускаем бота
docker compose -f docker/docker-compose.prod.yml up -d bot

# 8. Проверяем логи
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

**Готово!** Бот обновлен и работает с новым кодом.

---

## 📋 Пошаговая инструкция с пояснениями

### Шаг 1: Подключение к серверу

```bash
ssh root@ваш_IP_адрес
```

Или если используете SSH ключ:
```bash
ssh -i ~/.ssh/id_rsa root@ваш_IP
```

---

### Шаг 2: Остановка бота

```bash
cd ~/telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml stop bot
```

**Что происходит:**
- Бот корректно завершает работу (graceful shutdown)
- Закрываются соединения с БД
- Останавливается планировщик задач

**Проверка:**
```bash
docker compose -f docker/docker-compose.prod.yml ps
# Статус бота должен быть "Exited"
```

---

### Шаг 3: Бэкап базы данных

```bash
# Создаем бэкап с датой и временем
cp bot_database.db bot_database_backup_$(date +%Y%m%d_%H%M%S).db

# Или в отдельную папку
mkdir -p backups
cp bot_database.db backups/bot_database_$(date +%Y%m%d_%H%M%S).db
```

**Зачем:**
- На случай проблем с миграциями
- Можно откатиться к предыдущей версии
- Безопасность данных

---

### Шаг 4: Обновление кода

#### Вариант A: Через Git (рекомендуется)

```bash
# Проверяем текущую ветку
git branch

# Получаем обновления
git pull origin main

# Или если есть локальные изменения:
git stash              # Сохраняем локальные изменения
git pull origin main   # Получаем обновления
git stash pop          # Восстанавливаем локальные изменения
```

#### Вариант B: Через SCP (если нет Git)

**На локальной машине:**
```bash
# Архивируем проект
tar -czf telegram_repair_bot.tar.gz telegram_repair_bot/

# Отправляем на сервер
scp telegram_repair_bot.tar.gz root@ваш_IP:/root/

# На сервере:
cd ~
tar -xzf telegram_repair_bot.tar.gz
```

---

### Шаг 5: Применение миграций

```bash
# Проверяем текущую версию БД
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current

# Применяем все новые миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# Проверяем, что миграции применились
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current
```

**Что происходит:**
- Alembic проверяет текущую версию БД
- Применяет только новые миграции
- Безопасно обновляет схему БД

**Если что-то пошло не так:**
```bash
# Откатить последнюю миграцию
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade -1

# Восстановить БД из бэкапа
cp bot_database_backup_20251015_160000.db bot_database.db
```

---

### Шаг 6: Перезапуск бота

```bash
# Пересобираем образ (если изменились зависимости)
docker compose -f docker/docker-compose.prod.yml build bot

# Запускаем бота
docker compose -f docker/docker-compose.prod.yml up -d bot

# Проверяем статус
docker compose -f docker/docker-compose.prod.yml ps
```

**Флаги:**
- `-d` - запуск в фоновом режиме (detached)
- `--build` - пересборка образа перед запуском

---

### Шаг 7: Проверка работы

```bash
# Просмотр логов в реальном времени
docker compose -f docker/docker-compose.prod.yml logs -f bot

# Последние 50 строк логов
docker compose -f docker/docker-compose.prod.yml logs --tail=50 bot

# Проверка, что бот запустился
docker compose -f docker/docker-compose.prod.yml ps bot
```

**Что проверить в логах:**
- ✅ `База данных инициализирована`
- ✅ `Планировщик задач запущен`
- ✅ `Бот успешно запущен!`
- ✅ `Start polling`
- ❌ Нет ошибок `ERROR` или `CRITICAL`

---

## 🔧 Полезные команды Docker

### Управление контейнерами:

```bash
# Остановить бота
docker compose -f docker/docker-compose.prod.yml stop bot

# Запустить бота
docker compose -f docker/docker-compose.prod.yml start bot

# Перезапустить бота
docker compose -f docker/docker-compose.prod.yml restart bot

# Удалить контейнер (с пересозданием)
docker compose -f docker/docker-compose.prod.yml down bot
docker compose -f docker/docker-compose.prod.yml up -d bot
```

### Просмотр информации:

```bash
# Статус всех контейнеров
docker compose -f docker/docker-compose.prod.yml ps

# Использование ресурсов
docker stats

# Логи с фильтром
docker compose -f docker/docker-compose.prod.yml logs bot | grep ERROR
```

### Очистка:

```bash
# Удалить неиспользуемые образы
docker image prune -a

# Удалить неиспользуемые volumes
docker volume prune

# Полная очистка (осторожно!)
docker system prune -a
```

---

## 🐛 Troubleshooting

### Проблема: Бот не запускается

```bash
# Проверяем логи
docker compose -f docker/docker-compose.prod.yml logs bot

# Проверяем .env файл
cat .env | grep BOT_TOKEN

# Проверяем права на файлы
ls -la bot_database.db
chmod 666 bot_database.db  # Если нужно
```

### Проблема: База данных заблокирована

```bash
# Останавливаем все процессы
docker compose -f docker/docker-compose.prod.yml down

# Удаляем lock файлы
rm -f bot_database.db-shm bot_database.db-wal

# Запускаем заново
docker compose -f docker/docker-compose.prod.yml up -d
```

### Проблема: Миграции не применяются

```bash
# Проверяем версию БД
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current

# Смотрим историю миграций
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic history

# Применяем конкретную миграцию
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade <revision>
```

---

## 📊 Мониторинг после обновления

### Проверка работоспособности (первые 5 минут):

```bash
# 1. Проверяем, что бот запустился
docker compose -f docker/docker-compose.prod.yml ps bot
# STATUS должен быть "Up"

# 2. Проверяем логи на ошибки
docker compose -f docker/docker-compose.prod.yml logs bot | grep -i error

# 3. Проверяем timezone ошибки (если были)
docker compose -f docker/docker-compose.prod.yml logs bot | grep "timezone\|offset-naive"

# 4. Проверяем напоминания (через 5 минут)
docker compose -f docker/docker-compose.prod.yml logs bot | grep "Reminders check"

# 5. Тестируем в Telegram
# - Отправить /start
# - Создать тестовую заявку
# - Проверить отчеты
```

---

## 🔄 Откат к предыдущей версии

Если что-то пошло не так:

```bash
# 1. Останавливаем бота
docker compose -f docker/docker-compose.prod.yml stop bot

# 2. Восстанавливаем БД из бэкапа
cp bot_database_backup_20251015_160000.db bot_database.db

# 3. Откатываем код
git log --oneline -5  # Смотрим последние коммиты
git checkout <предыдущий_коммит>

# 4. Откатываем миграции
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade -1

# 5. Запускаем бота
docker compose -f docker/docker-compose.prod.yml start bot
```

---

## 📝 Checklist обновления

Перед обновлением:
- [ ] Сделан бэкап БД
- [ ] Проверен `.env` файл
- [ ] Код протестирован локально
- [ ] Есть доступ к серверу

После обновления:
- [ ] Бот запустился (статус "Up")
- [ ] Нет ошибок в логах
- [ ] Миграции применились
- [ ] Функционал работает в Telegram
- [ ] Напоминания работают
- [ ] Отчеты генерируются

---

## 🎯 Текущие изменения (15.10.2025)

**Что добавлено:**
1. ✅ Исправлена ошибка timezone в напоминаниях
2. ✅ Система отчетов с Excel экспортом
3. ✅ Счетчики заявок в inline клавиатуре
4. ✅ Детализация по каждому заказу

**Миграции:**
- `002_add_financial_reports.py` - добавлено поле `out_of_city`
- `003_add_dr_fields.py` - добавлены поля для длительного ремонта
- `004_add_order_reports.py` - таблица для детализации заказов (создана вручную)

**Команды для применения:**
```bash
# На сервере
cd ~/telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml stop bot
cp bot_database.db bot_database_backup_$(date +%Y%m%d_%H%M%S).db
git pull origin main
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head
docker compose -f docker/docker-compose.prod.yml up -d bot
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

---

**Готово к деплою!** 🚀

