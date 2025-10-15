# 🚀 Руководство по деплою Telegram Repair Bot

**Дата создания:** 15.10.2025  
**Версия:** 1.2.0

## 📋 Предварительные требования

### На сервере должно быть установлено:
- Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- Docker 20.10+
- Docker Compose 2.0+
- Git
- 2GB RAM минимум (4GB рекомендуется)
- 10GB свободного места на диске

---

## 🎯 Вариант 1: Быстрый деплой через Docker Compose (Рекомендуется)

### Шаг 1: Подготовка сервера

```bash
# Подключение к серверу
ssh user@your-server-ip

# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker (если еще не установлен)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка установки
docker --version
docker-compose --version

# Добавление текущего пользователя в группу docker
sudo usermod -aG docker $USER
# Перелогиньтесь после этого!
```

### Шаг 2: Клонирование проекта

```bash
# Создание директории для проекта
sudo mkdir -p /opt/telegram_repair_bot
sudo chown $USER:$USER /opt/telegram_repair_bot
cd /opt/telegram_repair_bot

# Клонирование репозитория
git clone https://github.com/your-username/telegram_repair_bot.git .

# Или через SSH
git clone git@github.com:your-username/telegram_repair_bot.git .
```

### Шаг 3: Настройка окружения

```bash
# Копирование example .env
cp env.example .env

# Редактирование .env
nano .env
```

**Обязательно заполните:**
```env
# CRITICAL - Обязательно заполнить!
BOT_TOKEN=your_real_bot_token_from_BotFather
ADMIN_IDS=your_telegram_id
GROUP_CHAT_ID=-100your_group_chat_id

# Режим разработки (ОБЯЗАТЕЛЬНО false для production!)
DEV_MODE=false

# Логирование
LOG_LEVEL=INFO

# База данных (оставить по умолчанию)
DATABASE_PATH=bot_database.db
```

**Как получить GROUP_CHAT_ID:**
1. Добавьте бота @userinfobot в вашу группу
2. В группе напишите любое сообщение
3. Бот ответит с ID группы (например: -1001234567890)
4. Используйте этот ID в .env

### Шаг 4: Первый запуск

```bash
# Переход в директорию docker
cd docker

# Запуск в production режиме
docker-compose -f docker-compose.prod.yml up -d

# Проверка логов
docker-compose -f docker-compose.prod.yml logs -f bot

# Если все ОК, увидите:
# "Бот успешно запущен!"
# "Планировщик задач запущен"
```

### Шаг 5: Проверка работоспособности

```bash
# Проверка статуса контейнеров
docker-compose -f docker-compose.prod.yml ps

# Должны быть запущены:
# - telegram_repair_bot_prod (healthy)
# - telegram_bot_redis_prod (healthy)

# Проверка логов
docker-compose -f docker-compose.prod.yml logs --tail=50 bot

# Тест бота в Telegram
# Отправьте /start боту
```

---

## 🔄 Вариант 2: Деплой через Systemd Service

### Шаг 1: Подготовка окружения

```bash
# Установка Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Создание директории
sudo mkdir -p /opt/telegram_repair_bot
sudo chown $USER:$USER /opt/telegram_repair_bot
cd /opt/telegram_repair_bot

# Клонирование проекта
git clone https://github.com/your-username/telegram_repair_bot.git .

# Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 2: Настройка .env

```bash
cp env.example .env
nano .env
# Заполнить как в варианте 1
```

### Шаг 3: Инициализация БД

```bash
# Применение миграций
alembic upgrade head

# Проверка БД
python scripts/check_database.py
```

### Шаг 4: Создание Systemd Service

```bash
sudo nano /etc/systemd/system/telegram-repair-bot.service
```

Содержимое файла:
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
StandardOutput=append:/var/log/telegram-bot/bot.log
StandardError=append:/var/log/telegram-bot/error.log

# Ограничения ресурсов
MemoryLimit=512M
CPUQuota=100%

[Install]
WantedBy=multi-user.target
```

### Шаг 5: Запуск сервиса

```bash
# Создание директории для логов
sudo mkdir -p /var/log/telegram-bot
sudo chown your_username:your_username /var/log/telegram-bot

# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable telegram-repair-bot

# Запуск сервиса
sudo systemctl start telegram-repair-bot

# Проверка статуса
sudo systemctl status telegram-repair-bot

# Просмотр логов
sudo journalctl -u telegram-repair-bot -f
```

---

## 📊 Мониторинг и обслуживание

### Команды управления (Docker)

```bash
# Остановка
docker-compose -f docker/docker-compose.prod.yml stop

# Перезапуск
docker-compose -f docker/docker-compose.prod.yml restart

# Просмотр логов
docker-compose -f docker/docker-compose.prod.yml logs -f bot

# Просмотр логов с фильтром
docker-compose -f docker/docker-compose.prod.yml logs -f bot | grep ERROR

# Вход в контейнер
docker-compose -f docker/docker-compose.prod.yml exec bot sh
```

### Команды управления (Systemd)

```bash
# Остановка
sudo systemctl stop telegram-repair-bot

# Перезапуск
sudo systemctl restart telegram-repair-bot

# Статус
sudo systemctl status telegram-repair-bot

# Логи
sudo journalctl -u telegram-repair-bot -f
sudo journalctl -u telegram-repair-bot --since "1 hour ago"
```

### Backup базы данных

```bash
# Через Docker
docker-compose -f docker/docker-compose.prod.yml exec bot python scripts/backup_db.py

# Через Systemd
cd /opt/telegram_repair_bot
source venv/bin/activate
python scripts/backup_db.py
```

### Настройка автоматических бэкапов (Cron)

```bash
# Редактирование crontab
crontab -e

# Добавить строку (бэкап каждый день в 3:00 утра)
0 3 * * * cd /opt/telegram_repair_bot && docker-compose -f docker/docker-compose.prod.yml exec -T bot python scripts/backup_db.py

# Для Systemd варианта:
0 3 * * * cd /opt/telegram_repair_bot && source venv/bin/activate && python scripts/backup_db.py
```

---

## 🔄 Обновление бота

### Через Docker

```bash
cd /opt/telegram_repair_bot

# 1. Сохранение текущей версии
docker-compose -f docker/docker-compose.prod.yml exec bot python scripts/backup_db.py

# 2. Получение обновлений
git pull origin main

# 3. Пересборка образа
docker-compose -f docker/docker-compose.prod.yml build --no-cache

# 4. Применение миграций
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# 5. Перезапуск
docker-compose -f docker/docker-compose.prod.yml up -d

# 6. Проверка логов
docker-compose -f docker/docker-compose.prod.yml logs -f bot
```

### Через Systemd

```bash
cd /opt/telegram_repair_bot

# 1. Остановка сервиса
sudo systemctl stop telegram-repair-bot

# 2. Backup
source venv/bin/activate
python scripts/backup_db.py

# 3. Получение обновлений
git pull origin main

# 4. Обновление зависимостей
pip install --upgrade -r requirements.txt

# 5. Применение миграций
alembic upgrade head

# 6. Запуск сервиса
sudo systemctl start telegram-repair-bot

# 7. Проверка
sudo systemctl status telegram-repair-bot
```

---

## 🔒 Безопасность

### Рекомендации по безопасности:

1. **Firewall**
```bash
# Разрешить только SSH и закрыть остальные порты
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw enable
```

2. **Обновления**
```bash
# Настройка автоматических обновлений безопасности
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

3. **Права доступа к .env**
```bash
chmod 600 .env
```

4. **Использование secrets (опционально)**
```bash
# Для Docker Swarm
docker secret create bot_token your_bot_token
```

---

## 🐛 Troubleshooting

### Бот не запускается

```bash
# Проверка логов
docker-compose -f docker/docker-compose.prod.yml logs bot

# Проверка .env файла
cat .env | grep -v "^#" | grep -v "^$"

# Проверка токена бота
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

### Ошибка подключения к БД

```bash
# Проверка файла БД
ls -lh bot_database.db

# Проверка прав
chmod 644 bot_database.db

# Пересоздание БД
rm bot_database.db
alembic upgrade head
```

### Бот не отвечает

```bash
# Проверка процесса
docker-compose -f docker/docker-compose.prod.yml ps
# или
sudo systemctl status telegram-repair-bot

# Перезапуск
docker-compose -f docker/docker-compose.prod.yml restart
# или
sudo systemctl restart telegram-repair-bot
```

---

## 📈 Мониторинг

### Базовый мониторинг

```bash
# CPU и Memory usage
docker stats telegram_repair_bot_prod

# Размер логов
du -sh logs/

# Размер БД
du -h bot_database.db
```

### Настройка Prometheus + Grafana (опционально)

1. Раскомментируйте секции в `docker-compose.prod.yml`
2. Создайте `docker/monitoring/prometheus.yml`
3. Запустите: `docker-compose -f docker-compose.prod.yml up -d`
4. Grafana будет доступна на http://your-server:3000

---

## ✅ Чеклист деплоя

### Перед деплоем
- [ ] Проверен и заполнен .env файл
- [ ] BOT_TOKEN валиден
- [ ] ADMIN_IDS корректны
- [ ] GROUP_CHAT_ID получен и добавлен
- [ ] DEV_MODE=false
- [ ] Сделан backup текущей БД (если есть)
- [ ] Проверена версия Docker/Python
- [ ] Firewall настроен

### После деплоя
- [ ] Бот отвечает на /start
- [ ] Уведомления приходят в группу
- [ ] Логи не содержат ошибок
- [ ] Все функции работают
- [ ] Настроены автоматические бэкапы
- [ ] Настроен мониторинг
- [ ] Документирован процесс деплоя

---

## 🆘 Поддержка

### Полезные ссылки
- [Основная документация](../README.md)
- [Troubleshooting](../docs/TROUBLESHOOTING.md)
- [Аудит проекта](../docs/AUDIT_REPORT_2025-10-15.md)

### Контакты
- Email: 5flora.adel5@gmail.com
- GitHub Issues: [создать issue](https://github.com/your-repo/issues)

---

**Успешного деплоя! 🚀**

