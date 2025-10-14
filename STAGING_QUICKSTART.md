# 🚀 Staging Workflow - Быстрый старт

## ✅ Что сделано

1. **Исправлен Makefile** - добавлены команды для staging/prod
2. **Создан docker-compose.staging.yml** - изолированное окружение
3. **Созданы скрипты автоматического деплоя**
4. **Написана полная документация**

## 📋 Первоначальная настройка (5 минут)

### 1. Настройка переменной окружения (локально)

**Windows PowerShell:**
```powershell
$env:SSH_SERVER="root@ваш-IP-адрес"
```

**Или добавьте в файл `.env` в корне проекта:**
```env
SSH_SERVER=root@ваш-IP-адрес
STAGING_DIR=~/telegram_repair_bot_staging
PROD_DIR=~/telegram_repair_bot
```

### 2. Создание staging на сервере (один раз)

```bash
# SSH на сервер
ssh root@ваш-IP-адрес

# Создать директорию staging
cd ~
git clone https://github.com/ваш-username/telegram_repair_bot.git telegram_repair_bot_staging
cd telegram_repair_bot_staging

# Настроить .env.staging с ТЕСТОВЫМ токеном
cp env.staging.example .env.staging
nano .env.staging
# Укажите ТЕСТОВЫЙ токен бота (создайте у @BotFather)
```

## 🔄 Ежедневное использование

### Процесс обновления бота:

```bash
# 1. Локальная разработка в Cursor
make test && make lint
git add . && git commit -m "feat: новая функция"
git push origin main

# 2. Деплой в staging (тестирование)
make staging-deploy
make staging-logs

# 3. Если всё ОК - деплой в production
make prod-deploy
make prod-status
```

## 📚 Полезные команды

```bash
# Локальная разработка
make test              # Запустить тесты
make lint              # Проверить код
make run               # Запустить бота локально

# Staging
make staging-deploy    # Деплой в staging
make staging-logs      # Просмотр логов

# Production
make prod-deploy       # Деплой в production (с подтверждением!)
make prod-logs         # Просмотр логов
make prod-status       # Статус и метрики

# Вся справка
make help              # Показать все команды
```

## 📖 Подробная документация

- **[docs/STAGING_WORKFLOW.md](docs/STAGING_WORKFLOW.md)** - Полное руководство
- **[docs/STAGING_SETUP_REPORT.md](docs/STAGING_SETUP_REPORT.md)** - Отчёт о настройке
- **[scripts/README.md](scripts/README.md)** - Документация скриптов

## ⚠️ Важно

- ✅ **Всегда** тестируйте в staging перед production
- ✅ Используйте **РАЗНЫЕ токены** для staging и production
- ✅ Команда `make prod-deploy` требует подтверждения
- ✅ Автоматически создаётся backup БД перед обновлением

## 🆘 Поддержка

Если что-то не работает:
1. Проверьте [docs/STAGING_WORKFLOW.md](docs/STAGING_WORKFLOW.md) - раздел Troubleshooting
2. Проверьте что `SSH_SERVER` правильно настроен
3. Проверьте SSH соединение: `ssh root@your-ip "echo OK"`

---

**Готово к использованию!** 🎉

