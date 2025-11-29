# 🚀 Production Deploy - Команды для сервера

**Дата:** 15.10.2025
**Готово к деплою:** ✅ ДА

---

## 📋 Команды для деплоя на сервер

### 1️⃣ Подключение к серверу

```bash
ssh user@your-server-ip
```

---

### 2️⃣ Установка Docker (если не установлен)

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# ВАЖНО: Перелогиньтесь после этого!
exit
ssh user@your-server-ip
```

---

### 3️⃣ Клонирование проекта

```bash
# Создание директории
sudo mkdir -p /opt/telegram_repair_bot
sudo chown $USER:$USER /opt/telegram_repair_bot
cd /opt/telegram_repair_bot

# Клонирование из GitHub
git clone https://github.com/your-username/telegram_repair_bot.git .

# ИЛИ если проект уже на сервере - обновление
git pull origin main
```

---

### 4️⃣ Настройка .env файла

```bash
# Копирование example
cp env.example .env

# Для production настроек (переопределяет .env)
cp env.example env.production

# Редактирование
nano .env
nano env.production
```

**Обязательно заполните:**

```env
# Получите у @BotFather
BOT_TOKEN=ваш_реальный_токен_от_BotFather

# Получите у @userinfobot
ADMIN_IDS=ваш_telegram_id

# Получите у @userinfobot в группе
GROUP_CHAT_ID=-100ваш_group_id

# ОБЯЗАТЕЛЬНО false для production!
DEV_MODE=false

# Логирование
LOG_LEVEL=INFO
```

**Сохраните:** `Ctrl+O`, Enter, `Ctrl+X`

---

### 5️⃣ Запуск бота

```bash
# Переход в директорию docker
cd /opt/telegram_repair_bot/docker

# Сборка и запуск
docker-compose -f docker-compose.prod.yml up -d --build

# Проверка статуса
docker-compose -f docker-compose.prod.yml ps
```

**Должны быть запущены:**
- `telegram_repair_bot_prod` (healthy)
- `telegram_bot_redis_prod` (healthy)

---

### 6️⃣ Проверка логов

```bash
# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f bot

# Должны увидеть:
# "База данных инициализирована"
# "Планировщик задач запущен"
# "Бот успешно запущен!"
```

**Для выхода из логов:** `Ctrl+C`

---

### 7️⃣ Применение миграций (если нужно)

```bash
# Если есть новые миграции
docker-compose -f docker-compose.prod.yml run --rm bot alembic upgrade head

# Проверка текущей версии БД
docker-compose -f docker-compose.prod.yml exec bot alembic current
```

---

### 8️⃣ Тест бота

```bash
# В Telegram отправьте боту:
/start

# Бот должен ответить приветствием
# Проверьте, что уведомления приходят в группу
```

---

## 🔄 Команды обновления бота

### Обновление при изменениях в коде

```bash
cd /opt/telegram_repair_bot

# 1. Backup БД
docker-compose -f docker/docker-compose.prod.yml exec bot python scripts/backup_db.py

# 2. Остановка бота
docker-compose -f docker/docker-compose.prod.yml stop bot

# 3. Получение обновлений
git pull origin main

# 4. Пересборка образа
docker-compose -f docker/docker-compose.prod.yml build --no-cache bot

# 5. Применение миграций
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# 6. Запуск
docker-compose -f docker/docker-compose.prod.yml up -d

# 7. Проверка
docker-compose -f docker/docker-compose.prod.yml logs -f bot
```

---

## 📊 Команды мониторинга

### Просмотр логов

```bash
cd /opt/telegram_repair_bot/docker

# Все логи
docker-compose -f docker-compose.prod.yml logs -f bot

# Последние 100 строк
docker-compose -f docker-compose.prod.yml logs --tail=100 bot

# Только ошибки
docker-compose -f docker-compose.prod.yml logs -f bot | grep ERROR
```

### Проверка статуса

```bash
# Статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# Использование ресурсов
docker stats telegram_repair_bot_prod

# Размер БД
docker-compose -f docker-compose.prod.yml exec bot ls -lh /app/bot_database.db
```

---

## 🛠️ Команды управления

### Перезапуск

```bash
cd /opt/telegram_repair_bot/docker
docker-compose -f docker-compose.prod.yml restart
```

### Остановка

```bash
docker-compose -f docker-compose.prod.yml stop
```

### Запуск

```bash
docker-compose -f docker-compose.prod.yml start
```

### Полная остановка с удалением

```bash
docker-compose -f docker-compose.prod.yml down
# С volumes
docker-compose -f docker-compose.prod.yml down -v
```

---

## 💾 Backup базы данных

### Ручной backup

```bash
cd /opt/telegram_repair_bot/docker
docker-compose -f docker-compose.prod.yml exec bot python scripts/backup_db.py
```

### Автоматический backup (cron)

```bash
# Редактирование crontab
crontab -e

# Добавить строку (backup каждый день в 3:00 AM):
0 3 * * * cd /opt/telegram_repair_bot/docker && docker-compose -f docker-compose.prod.yml exec -T bot python scripts/backup_db.py
```

---

## 🔒 Настройка firewall (рекомендуется)

```bash
# Установка UFW
sudo apt install ufw -y

# Разрешить SSH
sudo ufw allow ssh

# Включить firewall
sudo ufw enable

# Проверка статуса
sudo ufw status
```

---

## 🆘 Решение проблем

### Бот не запускается

```bash
# Проверка логов
docker-compose -f docker-compose.prod.yml logs bot | tail -50

# Проверка .env
cat /opt/telegram_repair_bot/.env | grep -v "^#"

# Проверка токена бота
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

### Ошибка подключения к БД

```bash
# Проверка файла БД
docker-compose -f docker-compose.prod.yml exec bot ls -la /app/bot_database.db

# Пересоздание БД (ВНИМАНИЕ: удаляет данные!)
docker-compose -f docker-compose.prod.yml exec bot rm bot_database.db
docker-compose -f docker-compose.prod.yml exec bot alembic upgrade head
docker-compose -f docker-compose.prod.yml restart
```

### Контейнер постоянно перезапускается

```bash
# Просмотр полных логов
docker-compose -f docker-compose.prod.yml logs --tail=200 bot

# Проверка healthcheck
docker inspect telegram_repair_bot_prod | grep -A 10 Health
```

---

## 📝 Полезные алиасы

Добавьте в `~/.bashrc`:

```bash
# Telegram Bot Aliases
alias bot-dir='cd /opt/telegram_repair_bot/docker'
alias bot-logs='docker-compose -f /opt/telegram_repair_bot/docker/docker-compose.prod.yml logs -f bot'
alias bot-status='docker-compose -f /opt/telegram_repair_bot/docker/docker-compose.prod.yml ps'
alias bot-restart='docker-compose -f /opt/telegram_repair_bot/docker/docker-compose.prod.yml restart'
alias bot-stop='docker-compose -f /opt/telegram_repair_bot/docker/docker-compose.prod.yml stop'
alias bot-start='docker-compose -f /opt/telegram_repair_bot/docker/docker-compose.prod.yml start'
alias bot-update='cd /opt/telegram_repair_bot && git pull && cd docker && docker-compose -f docker-compose.prod.yml build --no-cache && docker-compose -f docker-compose.prod.yml up -d'
```

После добавления:
```bash
source ~/.bashrc
```

Теперь можно использовать:
```bash
bot-logs
bot-status
bot-restart
bot-update
```

---

## ✅ Чеклист деплоя

### Перед запуском
- [ ] Docker установлен
- [ ] Проект склонирован в `/opt/telegram_repair_bot`
- [ ] `.env` файл создан и заполнен
- [ ] `BOT_TOKEN` получен от @BotFather
- [ ] `ADMIN_IDS` получен от @userinfobot
- [ ] `GROUP_CHAT_ID` получен от @userinfobot
- [ ] `DEV_MODE=false` установлен

### После запуска
- [ ] `docker-compose ps` показывает healthy
- [ ] Логи не содержат ERROR
- [ ] Бот отвечает на `/start`
- [ ] Уведомления приходят в группу
- [ ] Все функции работают

### Настройка сервера
- [ ] Firewall настроен
- [ ] Автоматический backup настроен (cron)
- [ ] Алиасы добавлены в `.bashrc`

---

## 🎯 Быстрый деплой (копируй-вставляй)

```bash
# 1. На сервере (если Docker уже установлен)
cd /opt/telegram_repair_bot
git clone https://github.com/your-username/telegram_repair_bot.git .

# 2. Настройка
cp env.example .env
nano .env
# Заполнить: BOT_TOKEN, ADMIN_IDS, GROUP_CHAT_ID, DEV_MODE=false

# 3. Запуск
cd docker
docker-compose -f docker-compose.prod.yml up -d --build

# 4. Проверка
docker-compose -f docker-compose.prod.yml logs -f bot
```

**Готово! Бот запущен!** 🎉

---

**Контакты поддержки:** 5flora.adel5@gmail.com
**Документация:** [README.md](README.md)
