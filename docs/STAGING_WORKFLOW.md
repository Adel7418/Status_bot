# 🚀 Staging Workflow: Безопасная разработка и деплой

## 📋 Содержание

1. [Обзор workflow](#обзор-workflow)
2. [Настройка окружений](#настройка-окружений)
3. [Локальная разработка](#локальная-разработка)
4. [Деплой в Staging](#деплой-в-staging)
5. [Деплой в Production](#деплой-в-production)
6. [Быстрые команды](#быстрые-команды)
7. [Troubleshooting](#troubleshooting)

---

## Обзор workflow

### Схема процесса разработки

```
┌─────────────────────┐
│  Local Development  │  ← Разработка в Cursor (без Docker)
│    (Cursor IDE)     │     - Тесты: make test
│                     │     - Линтинг: make lint
└──────────┬──────────┘
           │ git push origin main
           ▼
┌─────────────────────┐
│   GitHub Repository │  ← Центральный репозиторий
└──────────┬──────────┘
           │
           ├──────────────────┬──────────────────┐
           │                  │                  │
           │ git pull         │ git pull         │
           ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     STAGING     │  │   PRODUCTION    │  │   Другие envs   │
│  (test token)   │  │  (real token)   │  │                 │
│  Test database  │  │  Real database  │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Принципы безопасного workflow

✅ **DO (Делать):**
- Разрабатывать локально в Cursor (быстро, без Docker)
- Тестировать изменения в staging перед production
- Использовать ТЕСТОВЫЙ токен бота для staging
- Делать коммиты с понятными сообщениями
- Проверять логи после деплоя

❌ **DON'T (Не делать):**
- НЕ деплоить напрямую в production без проверки
- НЕ использовать один токен для staging и production
- НЕ пропускать тесты перед push
- НЕ забывать про миграции БД

---

## Настройка окружений

### 1. Локальное окружение (Cursor)

```bash
# 1. Создать виртуальное окружение
python -m venv venv

# 2. Активировать (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# 3. Установить зависимости
pip install -r requirements-dev.txt

# 4. Настроить .env (скопировать из env.example)
cp env.example .env
# Отредактировать .env с локальными настройками
```

**Структура .env для локальной разработки:**
```env
BOT_TOKEN=your_test_bot_token
ADMIN_IDS=your_telegram_id
DATABASE_PATH=bot_database.db  # Локальная БД
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

### 2. Staging на сервере

**Первоначальная настройка staging (один раз):**

```bash
# SSH на сервер
ssh root@your-server-ip

# Создать директорию для staging
mkdir -p ~/telegram_repair_bot_staging
cd ~/telegram_repair_bot_staging

# Клонировать репозиторий
git clone https://github.com/your-username/telegram_repair_bot.git .

# Создать .env.staging (ВАЖНО: с тестовым токеном!)
cp env.staging.example .env.staging
nano .env.staging  # Отредактировать с ТЕСТОВЫМ токеном
```

**Пример .env.staging:**
```env
BOT_TOKEN=YOUR_TEST_BOT_TOKEN_HERE  # ← ТЕСТОВЫЙ токен!
ADMIN_IDS=123456789
DATABASE_PATH=/app/data/bot_database.db
LOG_LEVEL=DEBUG
ENVIRONMENT=staging
REDIS_URL=redis://redis:6379/0
```

**Запуск staging:**
```bash
cd docker
docker compose -f docker-compose.staging.yml up -d --build
```

### 3. Production на сервере

Production уже должен быть настроен. Убедитесь что структура такая:

```
/root/telegram_repair_bot/              ← PRODUCTION
/root/telegram_repair_bot_staging/      ← STAGING
```

### 4. Настройка SSH переменных (локально)

Для автоматического деплоя создайте файл `.env` в корне проекта:

```env
# Для скриптов деплоя
SSH_SERVER=root@your-server-ip
STAGING_DIR=~/telegram_repair_bot_staging
PROD_DIR=~/telegram_repair_bot
```

Или экспортируйте в PowerShell:
```powershell
$env:SSH_SERVER="root@your-server-ip"
```

---

## Локальная разработка

### Ежедневный workflow

```bash
# 1. Активировать окружение (если еще не активно)
.\venv\Scripts\Activate.ps1

# 2. Получить последние изменения
git pull origin main

# 3. Сделать изменения в коде...

# 4. Запустить тесты
make test

# 5. Проверить линтинг
make lint

# 6. Запустить бота локально для проверки
make run

# 7. Зафиксировать изменения
git add .
git commit -m "feat: добавлена новая функция X"

# 8. Отправить в GitHub
git push origin main
```

### Полезные команды для локальной разработки

```bash
make help              # Показать все доступные команды
make test              # Запустить тесты
make test-cov          # Тесты с coverage
make lint              # Проверить код линтерами
make format            # Отформатировать код
make run               # Запустить бота
make migrate           # Применить миграции БД
make migrate-create MSG="описание"  # Создать миграцию
```

---

## Деплой в Staging

### Автоматический деплой (рекомендуется)

```bash
# Одна команда для деплоя в staging
make staging-deploy
```

Эта команда:
1. ✅ Подключится к серверу по SSH
2. ✅ Перейдет в директорию staging
3. ✅ Выполнит `git pull`
4. ✅ Пересоберет Docker контейнеры
5. ✅ Применит миграции
6. ✅ Проверит статус

### Ручной деплой

```bash
# SSH на сервер
ssh root@your-server-ip

# Перейти в staging директорию
cd ~/telegram_repair_bot_staging

# Получить изменения
git pull origin main

# Пересобрать и запустить
cd docker
docker compose -f docker-compose.staging.yml down
docker compose -f docker-compose.staging.yml up -d --build

# Применить миграции
docker compose -f docker-compose.migrate.yml run --rm migrate

# Проверить логи
docker compose -f docker-compose.staging.yml logs -f bot
```

### Проверка staging

```bash
# Просмотр логов staging
make staging-logs

# Или вручную
ssh root@your-server-ip
cd ~/telegram_repair_bot_staging/docker
docker compose -f docker-compose.staging.yml logs -f bot
```

**Что проверить в staging:**
- ✅ Бот запускается без ошибок
- ✅ Все новые функции работают корректно
- ✅ Нет критических ошибок в логах
- ✅ Миграции БД применились успешно
- ✅ Взаимодействие с тестовым ботом работает

---

## Деплой в Production

### ⚠️ ВАЖНО: Чеклист перед деплоем в production

- [ ] Все изменения протестированы в staging
- [ ] Нет критических ошибок в логах staging
- [ ] Миграции БД проверены в staging
- [ ] Сделан backup production БД (автоматически в скрипте)
- [ ] Есть план отката (git commit hash)

### Автоматический деплой

```bash
# Деплой в production (с подтверждением!)
make prod-deploy
```

Скрипт попросит подтверждение:
```
⚠️  Вы собираетесь обновить PRODUCTION бота!
Вы уверены? Введите 'yes' для продолжения:
```

Введите `yes` для продолжения.

### Ручной деплой

```bash
# SSH на сервер
ssh root@your-server-ip

# Перейти в production директорию
cd ~/telegram_repair_bot

# Сохранить текущий коммит (для отката)
CURRENT_COMMIT=$(git rev-parse HEAD)
echo "Текущий коммит: $CURRENT_COMMIT"

# Получить изменения
git pull origin main

# Пересобрать и запустить
cd docker
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build

# Применить миграции
docker compose -f docker-compose.migrate.yml run --rm migrate

# Проверить логи
docker compose -f docker-compose.prod.yml logs -f bot
```

### Мониторинг production

```bash
# Просмотр логов
make prod-logs

# Проверка статуса
make prod-status
```

### Откат изменений (если что-то пошло не так)

```bash
# SSH на сервер
ssh root@your-server-ip
cd ~/telegram_repair_bot

# Откатиться на предыдущий коммит
git log --oneline -5  # Посмотреть последние коммиты
git reset --hard <commit-hash>

# Пересобрать
cd docker
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Быстрые команды

### Локальная разработка
```bash
make test              # Тесты
make lint              # Линтинг
make format            # Форматирование
make run               # Запуск бота
```

### Staging
```bash
make staging-deploy    # Деплой в staging
make staging-logs      # Логи staging
```

### Production
```bash
make prod-deploy       # Деплой в production
make prod-logs         # Логи production
make prod-status       # Статус production
```

### Docker (локально)
```bash
make docker-up         # Запуск локально в Docker
make docker-up-dev     # Запуск в dev режиме
make docker-down       # Остановка
make docker-logs       # Логи
make docker-clean      # Очистка
```

---

## Troubleshooting

### Проблема: SSH соединение не работает

**Решение:**
```bash
# Проверить соединение
ssh root@your-server-ip "echo 'OK'"

# Если нужно добавить ключ
ssh-copy-id root@your-server-ip

# Проверить переменную окружения
echo $env:SSH_SERVER  # PowerShell
```

### Проблема: Git pull не работает в staging/prod

**Решение:**
```bash
# SSH на сервер
ssh root@your-server-ip
cd ~/telegram_repair_bot_staging

# Проверить статус git
git status

# Если есть изменения, откатить их
git reset --hard origin/main

# Попробовать снова
git pull origin main
```

### Проблема: Контейнеры не запускаются

**Решение:**
```bash
# Проверить логи
docker compose -f docker-compose.staging.yml logs bot

# Проверить .env файл
cat .env.staging

# Пересоздать контейнеры
docker compose -f docker-compose.staging.yml down -v
docker compose -f docker-compose.staging.yml up -d --build
```

### Проблема: Миграции не применяются

**Решение:**
```bash
# Проверить текущую версию БД
docker compose -f docker-compose.migrate.yml run --rm migrate alembic current

# Посмотреть историю миграций
docker compose -f docker-compose.migrate.yml run --rm migrate alembic history

# Применить миграции вручную
docker compose -f docker-compose.migrate.yml run --rm migrate alembic upgrade head
```

### Проблема: Два бота конфликтуют (staging и prod)

**Причина:** Используется один токен для staging и production.

**Решение:** Создайте отдельного тестового бота у @BotFather и используйте его токен в `.env.staging`.

---

## Дополнительные ресурсы

- [README.md](../README.md) - Основная документация проекта
- [DEPLOYMENT_INSTRUCTIONS.md](deployment/DEPLOYMENT_INSTRUCTIONS.md) - Детальные инструкции по деплою
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Решение проблем
- [DOCKER_USAGE.md](DOCKER_USAGE.md) - Работа с Docker

---

## Вопросы и поддержка

Если у вас возникли вопросы или проблемы:

1. Проверьте раздел [Troubleshooting](#troubleshooting)
2. Посмотрите логи: `make staging-logs` или `make prod-logs`
3. Проверьте GitHub Issues проекта
4. Создайте новый Issue с описанием проблемы

---

**Последнее обновление:** 2025-10-13

