# ⚡ Быстрые команды для деплоя

Шпаргалка с готовыми командами для деплоя на VPS Linux.

---

## 🚀 Полный деплой за 5 шагов

### Шаг 1: Подготовка на локальной машине

```bash
# Переход в директорию проекта
cd C:\Bot_test\telegram_repair_bot  # Windows
cd ~/telegram_repair_bot             # Linux/Mac

# Создание и настройка .env
cp env.example .env
nano .env
# Добавьте: BOT_TOKEN, ADMIN_IDS, DISPATCHER_IDS

# Сохранение: Ctrl+O, Enter, Ctrl+X
```

### Шаг 2: Экспорт базы данных (опционально)

```bash
# Экспорт в JSON (для безопасности)
python scripts/export_db.py

# Или создание backup .db файла
python backup_db.py
```

### Шаг 3: Первоначальная настройка VPS (один раз)

```bash
# Подключение к VPS
ssh root@ваш_IP_адрес

# Загрузка и запуск скрипта настройки
wget https://raw.githubusercontent.com/Adel7418/Status_bot/main/scripts/setup_vps.sh
chmod +x setup_vps.sh
./setup_vps.sh

# Выход и повторное подключение (для применения прав Docker)
exit
ssh root@ваш_IP_адрес
```

### Шаг 4: Деплой проекта

```bash
# На локальной машине (Git Bash / WSL)
bash scripts/deploy_to_vps.sh ваш_IP root

# Пример:
bash scripts/deploy_to_vps.sh 192.168.1.100 root
```

### Шаг 5: Запуск на VPS

```bash
# Подключение к VPS
ssh root@ваш_IP_адрес

# Переход в директорию
cd ~/telegram_repair_bot

# Запуск через Docker
docker compose -f docker/docker-compose.prod.yml up -d

# Проверка логов
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

---

## 📦 Альтернатива: Ручной деплой

### Вариант A: Через GitHub (если код в репозитории)

```bash
# На VPS
cd ~
git clone https://github.com/Adel7418/Status_bot.git telegram_repair_bot
cd telegram_repair_bot

# Создание .env
cp env.example .env
nano .env  # Настройте токены

# Перенос БД (с локальной машины)
# На локальной машине:
scp bot_database.db root@ваш_IP:/root/telegram_repair_bot/data/

# На VPS - запуск
docker compose -f docker/docker-compose.prod.yml up -d
```

### Вариант B: Через SCP (прямая передача файлов)

```bash
# На локальной машине (PowerShell)
scp -r C:\Bot_test\telegram_repair_bot root@ваш_IP:/root/

# На VPS
cd ~/telegram_repair_bot
cp env.example .env
nano .env  # Настройте

docker compose -f docker/docker-compose.prod.yml up -d
```

### Вариант C: Через rsync (наиболее эффективно)

```bash
# На локальной машине (Git Bash / WSL)
rsync -avz --progress \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude 'venv' \
  /c/Bot_test/telegram_repair_bot/ \
  root@ваш_IP:/root/telegram_repair_bot/

# На VPS
cd ~/telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml up -d
```

---

## 🔄 Управление ботом на VPS

### Базовые команды

```bash
# Запуск
docker compose -f docker/docker-compose.prod.yml up -d

# Остановка
docker compose -f docker/docker-compose.prod.yml down

# Перезапуск
docker compose -f docker/docker-compose.prod.yml restart

# Только бот (без Redis)
docker compose -f docker/docker-compose.prod.yml restart bot
```

### Просмотр логов

```bash
# Логи в реальном времени
docker compose -f docker/docker-compose.prod.yml logs -f bot

# Последние 100 строк
docker compose -f docker/docker-compose.prod.yml logs --tail=100 bot

# Поиск ошибок
docker compose -f docker/docker-compose.prod.yml logs bot | grep -i error

# Логи за последний час
docker compose -f docker/docker-compose.prod.yml logs --since=1h bot
```

### Проверка статуса

```bash
# Статус контейнеров
docker compose -f docker/docker-compose.prod.yml ps

# Все контейнеры
docker ps

# Использование ресурсов
docker stats --no-stream

# Healthcheck
docker inspect telegram_repair_bot_prod | grep Health -A 10
```

---

## 🔧 Обслуживание

### Обновление бота

```bash
# Метод 1: Через Git (если используете GitHub)
cd ~/telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml down
git pull origin main
docker compose -f docker/docker-compose.prod.yml build
docker compose -f docker/docker-compose.prod.yml up -d

# Метод 2: Через повторный деплой
# На локальной машине:
bash scripts/deploy_to_vps.sh ваш_IP root
# На VPS:
cd ~/telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml down
docker compose -f docker/docker-compose.prod.yml up -d
```

### Резервное копирование

```bash
# Создание backup
docker compose -f docker/docker-compose.prod.yml exec bot python backup_db.py

# Или через скрипт на VPS
~/backup_bot_db.sh

# Список backup
ls -lh ~/telegram_repair_bot/backups/

# Загрузка backup на локальную машину
scp root@ваш_IP:~/telegram_repair_bot/backups/bot_database_*.db ./backups/
```

### Восстановление из backup

```bash
# Остановка бота
docker compose -f docker/docker-compose.prod.yml down

# Восстановление
cp backups/bot_database_2025-10-13_12-00-00.db data/bot_database.db

# Запуск
docker compose -f docker/docker-compose.prod.yml up -d
```

---

## 🛡️ Мониторинг и безопасность

### Мониторинг

```bash
# Быстрая проверка
docker ps | grep telegram
docker stats telegram_repair_bot_prod --no-stream

# Размер БД
du -h ~/telegram_repair_bot/data/bot_database.db

# Использование диска
df -h

# Использование памяти
free -h

# Процессы
htop
```

### Проверка Redis

```bash
# Подключение к Redis
docker compose -f docker/docker-compose.prod.yml exec redis redis-cli

# Внутри Redis CLI:
PING           # Проверка связи
DBSIZE         # Количество ключей
KEYS *         # Все ключи
INFO memory    # Информация о памяти
exit           # Выход
```

### Логи системы

```bash
# Логи systemd (если настроен автозапуск)
sudo journalctl -u telegram-bot.service -f
sudo journalctl -u telegram-bot.service -n 100

# Логи Docker
docker logs telegram_repair_bot_prod --tail=50 -f
```

---

## 🔄 Автозапуск (systemd)

### Создание сервиса

```bash
# Создание файла сервиса
sudo nano /etc/systemd/system/telegram-bot.service
```

Вставьте:

```ini
[Unit]
Description=Telegram Repair Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=root
WorkingDirectory=/root/telegram_repair_bot
ExecStart=/usr/bin/docker compose -f docker/docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker/docker-compose.prod.yml down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

### Активация

```bash
# Перезагрузка конфигурации
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable telegram-bot.service

# Запуск сервиса
sudo systemctl start telegram-bot.service

# Проверка статуса
sudo systemctl status telegram-bot.service
```

### Управление сервисом

```bash
# Запуск
sudo systemctl start telegram-bot

# Остановка
sudo systemctl stop telegram-bot

# Перезапуск
sudo systemctl restart telegram-bot

# Статус
sudo systemctl status telegram-bot

# Отключение автозапуска
sudo systemctl disable telegram-bot
```

---

## 📊 Миграция базы данных

### Экспорт на старом сервере

```bash
# JSON экспорт
python scripts/export_db.py -o migration_$(date +%Y%m%d).json

# Или копирование .db файла
cp bot_database.db migration_$(date +%Y%m%d).db

# Загрузка на локальную машину
scp root@старый_IP:~/migration_*.json ./
scp root@старый_IP:~/migration_*.db ./
```

### Импорт на новом сервере

```bash
# Загрузка на новый сервер
scp migration_*.json root@новый_IP:~/telegram_repair_bot/
scp migration_*.db root@новый_IP:~/telegram_repair_bot/data/bot_database.db

# На новом сервере - из JSON
cd ~/telegram_repair_bot
python scripts/import_db.py migration_*.json --backup

# Или просто использование .db файла (уже скопирован выше)
```

---

## 🆘 Troubleshooting - Быстрые решения

### Бот не запускается

```bash
# 1. Проверка логов
docker compose -f docker/docker-compose.prod.yml logs bot

# 2. Проверка .env
cat .env | grep BOT_TOKEN

# 3. Проверка контейнеров
docker ps -a

# 4. Полный перезапуск
docker compose -f docker/docker-compose.prod.yml down
docker compose -f docker/docker-compose.prod.yml up -d
```

### Database locked

```bash
# Остановка и очистка
docker compose -f docker/docker-compose.prod.yml down
rm -f data/bot_database.db-journal
rm -f data/bot_database.db-shm
rm -f data/bot_database.db-wal
docker compose -f docker/docker-compose.prod.yml up -d
```

### Недостаточно памяти

```bash
# Проверка
free -h
docker stats

# Очистка Docker
docker system prune -a

# Добавление swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Проблемы с сетью

```bash
# Проверка сети Docker
docker network ls
docker network inspect telegram_repair_bot_bot_network

# Пересоздание сети
docker compose -f docker/docker-compose.prod.yml down
docker network prune
docker compose -f docker/docker-compose.prod.yml up -d

# Проверка доступности Telegram API
ping -c 3 api.telegram.org
```

---

## 📋 Чеклист после деплоя

```bash
# 1. ✅ Проверка контейнеров
docker ps

# 2. ✅ Проверка логов (без ошибок)
docker compose -f docker/docker-compose.prod.yml logs --tail=50 bot

# 3. ✅ Проверка healthcheck
docker inspect telegram_repair_bot_prod | grep -i health

# 4. ✅ Тест в Telegram
# Откройте бота и отправьте /start

# 5. ✅ Проверка автозапуска
sudo systemctl status telegram-bot

# 6. ✅ Настройка backup
crontab -e
# Добавьте: 0 2 * * * ~/backup_bot_db.sh
```

---

## 🔗 Полезные алиасы

Добавьте в `~/.bashrc` или `~/.zshrc`:

```bash
# Алиасы для управления ботом
alias bot-start='cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml up -d'
alias bot-stop='cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml down'
alias bot-restart='cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml restart'
alias bot-logs='cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml logs -f bot'
alias bot-status='cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml ps'
alias bot-update='cd ~/telegram_repair_bot && git pull && docker compose -f docker/docker-compose.prod.yml build && docker compose -f docker/docker-compose.prod.yml up -d'
alias bot-backup='cd ~/telegram_repair_bot && python backup_db.py'
```

Применение:

```bash
source ~/.bashrc  # или source ~/.zshrc
```

Использование:

```bash
bot-start    # Запуск
bot-logs     # Просмотр логов
bot-status   # Статус
bot-backup   # Backup
```

---

## 📞 Быстрая диагностика

Одна команда для проверки всего:

```bash
echo "=== Docker Containers ===" && \
docker ps && \
echo -e "\n=== Bot Logs (last 20) ===" && \
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml logs --tail=20 bot && \
echo -e "\n=== Resource Usage ===" && \
docker stats --no-stream && \
echo -e "\n=== Disk Usage ===" && \
df -h | grep -E 'Filesystem|/$' && \
echo -e "\n=== Database Size ===" && \
ls -lh ~/telegram_repair_bot/data/bot_database.db
```

---

**Версия:** 1.0  
**Дата:** 13 октября 2025  

💡 **Совет:** Сохраните этот файл локально для быстрого доступа к командам!

