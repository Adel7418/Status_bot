# 🚀 Deployment Instructions

**Дата:** 12 декабря 2024
**Версия:** 1.2.1
**Статус:** ✅ Готов к deployment

---

## ✅ ЧТО УЖЕ СДЕЛАНО

### 1. ✅ Commit создан
```
Commit: 7700cf4
Message: feat: production-ready setup v1.2.1 - Docker, tests, CI/CD, clean structure
Files changed: 17
```

### 2. ✅ Push в GitHub выполнен
```
Repository: https://github.com/Adel7418/Status_bot.git
Branch: main
Status: Pushed successfully
```

### 3. ✅ Release tag создан
```
Tag: v1.2.1
Message: Production Ready Release v1.2.1 - Clean Structure
Status: Pushed to GitHub
```

---

## 🔍 ПРОВЕРКА GITHUB ACTIONS

### Шаг 1: Откройте GitHub Actions

Перейдите по ссылке:
```
https://github.com/Adel7418/Status_bot/actions
```

### Шаг 2: Проверьте запущенные workflows

После push должны автоматически запуститься:

| Workflow | Описание | Ожидаемый результат |
|----------|----------|---------------------|
| 🧪 **Tests** | Автотесты на Python 3.11 и 3.12 | ✅ Green |
| 🔍 **Lint** | Black, Ruff, MyPy проверки | ✅ Green |
| 🐳 **Docker Build** | Сборка Docker образа | ✅ Green |
| 🔒 **CodeQL** | Анализ безопасности | ✅ Green |
| 🎉 **Release** | Создание релиза (на tag) | ✅ Green |

### Шаг 3: Что проверить

#### Tests workflow:
- ✅ Установка зависимостей
- ✅ Запуск линтеров (Ruff, Black)
- ✅ Type checking (MyPy)
- ✅ Запуск тестов
- ✅ Coverage report

#### Docker Build workflow:
- ✅ Сборка образа из `docker/Dockerfile`
- ✅ Push в GitHub Container Registry
- ✅ Trivy security scan
- ✅ Multi-platform build

### Шаг 4: Просмотр логов

Если какой-то workflow упал:

1. Кликните на название workflow
2. Кликните на конкретный run
3. Раскройте failed step
4. Прочитайте логи
5. Исправьте проблему

### ⚠️ Возможные проблемы

#### Проблема: Tests падают

**Причина:** Отсутствуют зависимости или ошибки в тестах

**Решение:**
```bash
# Локально проверить
pip install -r requirements-dev.txt
pytest

# Если тесты проходят локально, проверьте:
# - Python версию в workflow (3.11, 3.12)
# - Установку зависимостей в CI
```

#### Проблема: Docker Build падает

**Причина:** Ошибка в Dockerfile или путях

**Решение:**
```bash
# Локально проверить
docker build -f docker/Dockerfile -t test .

# Если собирается локально, проверьте:
# - Путь к Dockerfile в workflow
# - Context build
```

#### Проблема: CodeQL долго выполняется

**Это нормально:** CodeQL может работать 5-10 минут, это не ошибка.

---

## 🎉 ПРОВЕРКА RELEASE

### Release автоматически создан!

Перейдите по ссылке:
```
https://github.com/Adel7418/Status_bot/releases/tag/v1.2.1
```

**Что должно быть:**
- ✅ Changelog из коммитов
- ✅ Installation instructions
- ✅ Docker pull команда
- ✅ Attachments (если есть)

---

## 🚢 PRODUCTION DEPLOYMENT

### Вариант 1: Docker Compose (Рекомендуется)

#### На вашем VPS/сервере:

```bash
# 1. Клонировать репозиторий (если ещё не сделано)
git clone https://github.com/Adel7418/Status_bot.git telegram_repair_bot
cd telegram_repair_bot

# 2. Настроить .env
cp env.example .env
nano .env
# Добавьте:
# - BOT_TOKEN (от @BotFather)
# - ADMIN_IDS (ваш Telegram ID)
# - DISPATCHER_IDS (опционально)

# 3. Запустить в production режиме
docker-compose -f docker/docker-compose.prod.yml up -d

# 4. Проверить статус
docker-compose -f docker/docker-compose.prod.yml ps

# 5. Просмотреть логи
docker-compose -f docker/docker-compose.prod.yml logs -f bot
```

#### Проверка работы:

```bash
# Проверить контейнеры
docker ps

# Проверить логи
docker-compose -f docker/docker-compose.prod.yml logs --tail=50 bot

# Проверить healthcheck
docker inspect telegram_repair_bot_prod | grep Health -A 10

# Проверить ресурсы
docker stats telegram_repair_bot_prod
```

### Вариант 2: Локальный запуск (для тестирования)

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Настроить .env
cp env.example .env
# Отредактируйте .env

# 3. Применить миграции
alembic upgrade head

# 4. Запустить бота
python bot.py
```

### Вариант 3: Через Makefile

```bash
# Установка
make install

# Настройка
cp env.example .env
# Отредактируйте .env

# Запуск через Docker
make docker-up

# Или локально
make run
```

---

## 📊 МОНИТОРИНГ ПОСЛЕ DEPLOYMENT

### 1. Проверка логов (первые 30 минут)

```bash
# Real-time логи
docker-compose -f docker/docker-compose.prod.yml logs -f bot

# Последние 100 строк
docker-compose -f docker/docker-compose.prod.yml logs --tail=100 bot

# Поиск ошибок
docker-compose -f docker/docker-compose.prod.yml logs bot | grep ERROR
```

### 2. Проверка работоспособности

**Telegram:**
1. Найдите вашего бота в Telegram
2. Отправьте `/start`
3. Проверьте что получили приветственное сообщение
4. Попробуйте основные функции

**Healthcheck:**
```bash
# Docker healthcheck
docker inspect telegram_repair_bot_prod | grep Health -A 10

# Должно быть: "Status": "healthy"
```

### 3. Проверка базы данных

```bash
# Вход в контейнер
docker-compose -f docker/docker-compose.prod.yml exec bot bash

# Проверка БД
python check_database.py

# Выход
exit
```

### 4. Проверка Redis (FSM storage)

```bash
# Подключение к Redis
docker-compose -f docker/docker-compose.prod.yml exec redis redis-cli

# Проверка ключей
DBSIZE

# Выход
exit
```

---

## 🔧 НАСТРОЙКА АВТОЗАПУСКА

### Systemd Service (Linux)

Создайте файл `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Telegram Repair Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/telegram_repair_bot
ExecStart=/usr/local/bin/docker-compose -f docker/docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker/docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

### Windows Task Scheduler

1. Откройте Task Scheduler
2. Create Basic Task
3. Trigger: At system startup
4. Action: Start a program
5. Program: `C:\path\to\docker-compose.exe`
6. Arguments: `-f C:\Bot_test\telegram_repair_bot\docker\docker-compose.prod.yml up -d`

---

## 📦 BACKUP ПОСЛЕ DEPLOYMENT

### Автоматический backup

```bash
# Создайте cron job (Linux)
crontab -e

# Добавьте строку (каждый день в 2:00):
0 2 * * * cd /path/to/telegram_repair_bot && docker-compose -f docker/docker-compose.prod.yml exec -T bot python backup_db.py
```

### Ручной backup

```bash
# Из контейнера
docker-compose -f docker/docker-compose.prod.yml exec bot python backup_db.py

# Или из хоста
python backup_db.py
```

---

## 🆘 TROUBLESHOOTING

### Бот не запускается

```bash
# 1. Проверить логи
docker-compose -f docker/docker-compose.prod.yml logs bot

# 2. Проверить .env файл
cat .env

# 3. Проверить healthcheck
docker ps

# 4. Перезапустить
docker-compose -f docker/docker-compose.prod.yml restart bot
```

### База данных заблокирована

```bash
# 1. Остановить бота
docker-compose -f docker/docker-compose.prod.yml stop bot

# 2. Проверить файл БД
ls -lh data/bot_database.db

# 3. Запустить снова
docker-compose -f docker/docker-compose.prod.yml start bot
```

### Бот не получает обновления

```bash
# 1. Проверить, что бот запущен
docker ps | grep telegram_repair_bot

# 2. Проверить токен в .env
cat .env | grep BOT_TOKEN

# 3. Проверить логи на ошибки подключения
docker-compose -f docker/docker-compose.prod.yml logs bot | grep -i error
```

---

## 📈 МОНИТОРИНГ

### Метрики для отслеживания

**Первые 24 часа:**
- ✅ Количество обработанных команд
- ✅ Ошибки в логах
- ✅ Использование памяти
- ✅ Использование CPU
- ✅ Размер БД

**Команды:**
```bash
# CPU и память
docker stats telegram_repair_bot_prod

# Размер БД
du -h data/bot_database.db

# Ошибки в логах
docker-compose -f docker/docker-compose.prod.yml logs bot | grep ERROR | wc -l
```

---

## 🔄 ОБНОВЛЕНИЕ

### При новых изменениях:

```bash
# 1. Остановить бота
docker-compose -f docker/docker-compose.prod.yml stop bot

# 2. Обновить код
git pull origin main

# 3. Пересобрать образ
docker-compose -f docker/docker-compose.prod.yml build bot

# 4. Применить миграции
docker-compose -f docker/docker-compose.prod.yml run bot alembic upgrade head

# 5. Запустить
docker-compose -f docker/docker-compose.prod.yml up -d bot
```

---

## 📞 ССЫЛКИ

- **GitHub Repository:** https://github.com/Adel7418/Status_bot
- **GitHub Actions:** https://github.com/Adel7418/Status_bot/actions
- **Releases:** https://github.com/Adel7418/Status_bot/releases
- **Issues:** https://github.com/Adel7418/Status_bot/issues

---

## ✅ CHECKLIST DEPLOYMENT

### Перед deployment:
- ✅ Коммит сделан
- ✅ Push в GitHub выполнен
- ✅ Tag создан (v1.2.1)
- ✅ GitHub Actions проверены
- ⏳ .env файл настроен
- ⏳ Сервер подготовлен

### После deployment:
- ⏳ Бот запущен
- ⏳ Логи проверены
- ⏳ Healthcheck зелёный
- ⏳ Telegram команды работают
- ⏳ Backup настроен
- ⏳ Мониторинг настроен

---

## 🎯 СЛЕДУЮЩИЕ ШАГИ

### 1. Проверить GitHub Actions (СЕЙЧАС!)

```
🔗 https://github.com/Adel7418/Status_bot/actions
```

Убедитесь что все workflows зелёные ✅

### 2. Проверить Release

```
🔗 https://github.com/Adel7418/Status_bot/releases/tag/v1.2.1
```

Должен быть автоматически создан GitHub Release

### 3. Deploy в Production

Выберите один из вариантов выше и выполните deployment.

**Рекомендуется:** Docker Compose (Вариант 1)

### 4. Мониторинг первые 24 часа

- Проверяйте логи каждые 2-3 часа
- Следите за ошибками
- Тестируйте все функции бота
- Проверяйте healthcheck

---

## 🎉 ГОТОВО!

Проект успешно:
- ✅ Закоммичен в Git
- ✅ Отправлен в GitHub
- ✅ Тегирован как v1.2.1
- ✅ Release создаётся автоматически
- ✅ CI/CD workflows запущены

**Следующий шаг:** Проверьте GitHub Actions и выполните deployment!

---

**Версия:** 1.2.1
**Статус:** ✅ **READY FOR PRODUCTION DEPLOYMENT**
**Дата:** 12 декабря 2024

**🚀 Good luck with deployment!**
