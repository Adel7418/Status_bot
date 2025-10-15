# ⚡ Быстрые команды для деплоя

**Дата:** 15.10.2025  
**Версия:** 1.2.0

---

## 🚀 Вариант 1: Автоматический деплой (Docker)

### Одна команда для деплоя всего:

```bash
# 1. Подключение к серверу
ssh user@your-server-ip

# 2. Установка Docker (если нужно)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Перелогиньтесь!

# 3. Клонирование и деплой
git clone https://github.com/your-username/telegram_repair_bot.git
cd telegram_repair_bot
cp env.example .env
nano .env  # Заполнить BOT_TOKEN, ADMIN_IDS, GROUP_CHAT_ID, DEV_MODE=false

# 4. Запуск скрипта деплоя
chmod +x scripts/deploy_prod.sh
./scripts/deploy_prod.sh
```

**Готово!** Бот запущен в production режиме.

---

## 🔧 Вариант 2: Ручной деплой (Docker)

```bash
# На сервере
cd /opt/telegram_repair_bot

# Настройка .env
cp env.example .env
nano .env

# Запуск
cd docker
docker-compose -f docker-compose.prod.yml up -d

# Проверка
docker-compose -f docker-compose.prod.yml logs -f bot
```

---

## 📋 Вариант 3: Systemd Service

```bash
# Подготовка
cd /opt/telegram_repair_bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройка .env
cp env.example .env
nano .env

# Инициализация БД
alembic upgrade head

# Создание service
sudo nano /etc/systemd/system/telegram-repair-bot.service
```

Содержимое service файла:
```ini
[Unit]
Description=Telegram Repair Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/telegram_repair_bot
Environment="PATH=/opt/telegram_repair_bot/venv/bin"
ExecStart=/opt/telegram_repair_bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Запуск
sudo systemctl daemon-reload
sudo systemctl enable telegram-repair-bot
sudo systemctl start telegram-repair-bot
sudo systemctl status telegram-repair-bot
```

---

## 🔄 Команды обновления

### Docker

```bash
cd /opt/telegram_repair_bot

# Backup
docker-compose -f docker/docker-compose.prod.yml exec bot python scripts/backup_db.py

# Обновление
git pull origin main
cd docker
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml run --rm bot alembic upgrade head
docker-compose -f docker-compose.prod.yml up -d

# Проверка
docker-compose -f docker-compose.prod.yml logs -f bot
```

### Systemd

```bash
cd /opt/telegram_repair_bot

# Остановка
sudo systemctl stop telegram-repair-bot

# Backup
source venv/bin/activate
python scripts/backup_db.py

# Обновление
git pull origin main
pip install --upgrade -r requirements.txt
alembic upgrade head

# Запуск
sudo systemctl start telegram-repair-bot
sudo systemctl status telegram-repair-bot
```

---

## 📊 Команды мониторинга

### Docker

```bash
# Логи
docker-compose -f docker/docker-compose.prod.yml logs -f bot
docker-compose -f docker/docker-compose.prod.yml logs --tail=100 bot
docker-compose -f docker/docker-compose.prod.yml logs -f bot | grep ERROR

# Статус
docker-compose -f docker/docker-compose.prod.yml ps
docker stats telegram_repair_bot_prod

# Вход в контейнер
docker-compose -f docker/docker-compose.prod.yml exec bot sh
```

### Systemd

```bash
# Логи
sudo journalctl -u telegram-repair-bot -f
sudo journalctl -u telegram-repair-bot --since "1 hour ago"
sudo journalctl -u telegram-repair-bot | grep ERROR

# Статус
sudo systemctl status telegram-repair-bot
ps aux | grep bot.py
```

---

## 🛠️ Команды управления

### Остановка
```bash
# Docker
docker-compose -f docker/docker-compose.prod.yml stop

# Systemd
sudo systemctl stop telegram-repair-bot
```

### Перезапуск
```bash
# Docker
docker-compose -f docker/docker-compose.prod.yml restart

# Systemd
sudo systemctl restart telegram-repair-bot
```

### Полная остановка и очистка
```bash
# Docker
docker-compose -f docker/docker-compose.prod.yml down
docker-compose -f docker/docker-compose.prod.yml down -v  # С volumes

# Systemd
sudo systemctl stop telegram-repair-bot
sudo systemctl disable telegram-repair-bot
```

---

## 💾 Backup команды

### Ручной backup
```bash
# Docker
docker-compose -f docker/docker-compose.prod.yml exec bot python scripts/backup_db.py

# Systemd
cd /opt/telegram_repair_bot
source venv/bin/activate
python scripts/backup_db.py
```

### Автоматический backup (Cron)
```bash
# Редактирование crontab
crontab -e

# Добавить (каждый день в 3:00 AM):
0 3 * * * cd /opt/telegram_repair_bot && docker-compose -f docker/docker-compose.prod.yml exec -T bot python scripts/backup_db.py
```

---

## 🔍 Troubleshooting команды

### Проверка конфигурации
```bash
# Проверка .env
cat .env | grep -v "^#" | grep -v "^$"

# Проверка токена бота
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

### Проверка БД
```bash
# Docker
docker-compose -f docker/docker-compose.prod.yml exec bot python scripts/check_database.py

# Systemd
cd /opt/telegram_repair_bot
source venv/bin/activate
python scripts/check_database.py
```

### Пересоздание БД
```bash
# ВНИМАНИЕ: Удаляет все данные!
rm bot_database.db
alembic upgrade head
```

---

## 🎯 Полезные алиасы

Добавьте в `~/.bashrc` или `~/.bash_aliases`:

```bash
# Telegram Bot Aliases
alias bot-logs='docker-compose -f /opt/telegram_repair_bot/docker/docker-compose.prod.yml logs -f bot'
alias bot-status='docker-compose -f /opt/telegram_repair_bot/docker/docker-compose.prod.yml ps'
alias bot-restart='docker-compose -f /opt/telegram_repair_bot/docker/docker-compose.prod.yml restart'
alias bot-stop='docker-compose -f /opt/telegram_repair_bot/docker/docker-compose.prod.yml stop'
alias bot-start='docker-compose -f /opt/telegram_repair_bot/docker/docker-compose.prod.yml start'
alias bot-backup='docker-compose -f /opt/telegram_repair_bot/docker/docker-compose.prod.yml exec bot python scripts/backup_db.py'
```

После добавления:
```bash
source ~/.bashrc

# Теперь можно использовать:
bot-logs
bot-status
bot-restart
```

---

## ✅ Чеклист первого деплоя

### Перед деплоем
- [ ] Docker установлен
- [ ] Git настроен
- [ ] Получен BOT_TOKEN от @BotFather
- [ ] Получен ADMIN_IDS от @userinfobot
- [ ] Получен GROUP_CHAT_ID от @userinfobot в группе
- [ ] .env файл заполнен
- [ ] DEV_MODE=false в .env

### После деплоя
- [ ] `docker-compose ps` показывает healthy
- [ ] Логи не содержат ошибок
- [ ] Бот отвечает на /start
- [ ] Уведомления приходят в группу
- [ ] Все функции работают

### Настройка
- [ ] Настроен автоматический backup (cron)
- [ ] Настроен firewall
- [ ] Настроены автоматические обновления
- [ ] Документирован процесс деплоя

---

## 📚 Дополнительные ресурсы

- [Полное руководство по деплою](DEPLOY_GUIDE.md)
- [Аудит проекта](docs/AUDIT_REPORT_2025-10-15.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [README](README.md)

---

**Успешного деплоя! 🚀**

