# 🚀 Пошаговый Деплой на VPS Linux

**Дата:** 13 октября 2025  
**Версия:** 1.2.1  
**Статус:** ✅ Production Ready

---

## 📋 Содержание

1. [Подготовка VPS сервера](#1-подготовка-vps-сервера)
2. [Установка необходимого ПО](#2-установка-необходимого-по)
3. [Перенос проекта на сервер](#3-перенос-проекта-на-сервер)
4. [Перенос базы данных](#4-перенос-базы-данных)
5. [Настройка окружения](#5-настройка-окружения)
6. [Запуск через Docker](#6-запуск-через-docker)
7. [Настройка автозапуска](#7-настройка-автозапуска)
8. [Мониторинг и поддержка](#8-мониторинг-и-поддержка)
9. [Резервное копирование](#9-резервное-копирование)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Подготовка VPS сервера

### 1.1 Требования к серверу

**Минимальные характеристики:**
- ОС: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- CPU: 1 ядро
- RAM: 1 GB (рекомендуется 2 GB)
- Диск: 10 GB
- Доступ: SSH root или sudo пользователь

**Рекомендуемые характеристики:**
- CPU: 2 ядра
- RAM: 2 GB
- Диск: 20 GB
- SSD диск

### 1.2 Подключение к серверу

```bash
# Подключение через SSH
ssh root@ваш_IP_адрес

# Или с использованием пользователя
ssh username@ваш_IP_адрес
```

### 1.3 Обновление системы

```bash
# Для Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# Для CentOS/RHEL
sudo yum update -y

# Установка базовых утилит
sudo apt install -y git curl wget nano htop
```

### 1.4 Создание пользователя для бота (рекомендуется)

```bash
# Создание пользователя
sudo useradd -m -s /bin/bash botuser

# Добавление в группу sudo (опционально)
sudo usermod -aG sudo botuser

# Установка пароля
sudo passwd botuser

# Переключение на пользователя
su - botuser
```

---

## 2. Установка необходимого ПО

### 2.1 Установка Docker

```bash
# Удаление старых версий Docker (если были)
sudo apt remove docker docker-engine docker.io containerd runc

# Установка зависимостей
sudo apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Добавление официального GPG ключа Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Добавление репозитория Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Проверка установки
sudo docker --version
sudo docker compose version
```

### 2.2 Настройка Docker для пользователя

```bash
# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Применение изменений (выход и повторный вход)
newgrp docker

# Проверка работы без sudo
docker ps
```

### 2.3 Установка Git (если не установлен)

```bash
sudo apt install -y git
git --version
```

---

## 3. Перенос проекта на сервер

### Вариант 1: Клонирование из GitHub (рекомендуется)

```bash
# Переход в домашнюю директорию
cd ~

# Клонирование репозитория
git clone https://github.com/Adel7418/Status_bot.git telegram_repair_bot

# Переход в директорию проекта
cd telegram_repair_bot

# Проверка файлов
ls -la
```

### Вариант 2: Перенос файлов через SCP (если работаете локально)

**На локальной машине (Windows PowerShell):**

```powershell
# Перенос всего проекта
scp -r C:\Bot_test\telegram_repair_bot root@ваш_IP:/home/botuser/

# Или через архив (быстрее для больших проектов)
# 1. Создать архив локально
tar -czf bot_project.tar.gz C:\Bot_test\telegram_repair_bot

# 2. Перенести архив
scp bot_project.tar.gz root@ваш_IP:/home/botuser/

# 3. На сервере распаковать
ssh root@ваш_IP
cd /home/botuser
tar -xzf bot_project.tar.gz
mv telegram_repair_bot telegram_repair_bot
```

### Вариант 3: Использование rsync (наиболее эффективно)

```bash
# На локальной машине (из WSL или Git Bash)
rsync -avz --progress \
  -e "ssh" \
  /c/Bot_test/telegram_repair_bot/ \
  root@ваш_IP:/home/botuser/telegram_repair_bot/
```

---

## 4. Перенос базы данных

### 4.1 Создание резервной копии на локальной машине

**На Windows (в PowerShell):**

```powershell
# Переход в директорию проекта
cd C:\Bot_test\telegram_repair_bot

# Создание резервной копии
python backup_db.py

# Проверка создания копии
dir backups
```

### 4.2 Экспорт данных в JSON (альтернативный метод)

Создайте скрипт экспорта:

```bash
# На локальной машине создайте export_db.py
```

**Содержимое файла export_db.py:**

```python
import sqlite3
import json
from datetime import datetime

def export_database():
    """Экспорт данных из SQLite в JSON"""
    
    conn = sqlite3.connect('bot_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    export_data = {
        'export_date': datetime.now().isoformat(),
        'tables': {}
    }
    
    # Получение списка таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    # Экспорт данных каждой таблицы
    for table in tables:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        export_data['tables'][table] = [dict(row) for row in rows]
    
    # Сохранение в JSON
    filename = f"db_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
    
    conn.close()
    print(f"✅ База данных экспортирована в {filename}")
    print(f"📊 Экспортировано таблиц: {len(tables)}")
    
    return filename

if __name__ == "__main__":
    export_database()
```

**Запуск экспорта:**

```powershell
# На локальной машине
python export_db.py
```

### 4.3 Перенос базы данных на сервер

**Метод 1: Перенос файла .db напрямую**

```bash
# На локальной машине (PowerShell)
scp C:\Bot_test\telegram_repair_bot\bot_database.db root@ваш_IP:/home/botuser/telegram_repair_bot/

# Или последнюю резервную копию
scp C:\Bot_test\telegram_repair_bot\backups\bot_database_*.db root@ваш_IP:/home/botuser/telegram_repair_bot/
```

**Метод 2: Перенос JSON экспорта**

```bash
# Перенос JSON файла
scp db_export_*.json root@ваш_IP:/home/botuser/telegram_repair_bot/
```

### 4.4 Восстановление базы данных на сервере

**Если перенесли .db файл:**

```bash
# На сервере
cd ~/telegram_repair_bot

# Если перенесли резервную копию
mv bot_database_*.db bot_database.db

# Установка правильных прав
chmod 644 bot_database.db
chown botuser:botuser bot_database.db
```

**Если используете JSON (создайте import_db.py):**

```python
import sqlite3
import json
import sys

def import_database(json_file):
    """Импорт данных из JSON в SQLite"""
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    for table_name, rows in data['tables'].items():
        if not rows:
            continue
            
        # Получение колонок
        columns = list(rows[0].keys())
        placeholders = ','.join(['?' for _ in columns])
        columns_str = ','.join(columns)
        
        # Вставка данных
        for row in rows:
            values = [row[col] for col in columns]
            try:
                cursor.execute(
                    f"INSERT OR REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})",
                    values
                )
            except Exception as e:
                print(f"⚠️  Ошибка при вставке в {table_name}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ База данных импортирована из {json_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python import_db.py <json_file>")
        sys.exit(1)
    
    import_database(sys.argv[1])
```

---

## 5. Настройка окружения

### 5.1 Создание .env файла

```bash
# На сервере
cd ~/telegram_repair_bot

# Копирование примера
cp env.example .env

# Редактирование .env
nano .env
```

### 5.2 Заполнение .env файла

**Обязательные параметры:**

```bash
# Токен бота (получите у @BotFather)
BOT_TOKEN=ваш_реальный_токен_от_BotFather

# ID администраторов (узнайте у @userinfobot)
ADMIN_IDS=123456789,987654321

# ID диспетчеров (опционально)
DISPATCHER_IDS=111222333

# База данных
DATABASE_PATH=/app/data/bot_database.db

# Redis для production
REDIS_URL=redis://redis:6379/0

# Уровень логирования
LOG_LEVEL=INFO

# Окружение
ENVIRONMENT=production
```

**Сохранение файла:**
- В nano: `Ctrl+O` (Enter) → `Ctrl+X`
- В vim: `Esc` → `:wq` → `Enter`

### 5.3 Установка прав доступа

```bash
# Защита .env файла
chmod 600 .env

# Проверка
ls -la .env
```

---

## 6. Запуск через Docker

### 6.1 Подготовка к запуску

```bash
# Переход в директорию
cd ~/telegram_repair_bot

# Создание необходимых директорий
mkdir -p data logs backups

# Проверка Docker
docker --version
docker compose version
```

### 6.2 Сборка образа

```bash
# Сборка Docker образа
docker compose -f docker/docker-compose.prod.yml build

# Проверка созданного образа
docker images | grep telegram
```

### 6.3 Первый запуск

```bash
# Запуск в режиме daemon (фоновый режим)
docker compose -f docker/docker-compose.prod.yml up -d

# Проверка статуса контейнеров
docker compose -f docker/docker-compose.prod.yml ps
```

### 6.4 Просмотр логов

```bash
# Просмотр логов бота в реальном времени
docker compose -f docker/docker-compose.prod.yml logs -f bot

# Последние 50 строк
docker compose -f docker/docker-compose.prod.yml logs --tail=50 bot

# Логи Redis
docker compose -f docker/docker-compose.prod.yml logs redis
```

### 6.5 Проверка работоспособности

```bash
# Проверка контейнеров
docker ps

# Проверка healthcheck
docker inspect telegram_repair_bot_prod | grep -A 10 Health

# Проверка использования ресурсов
docker stats telegram_repair_bot_prod --no-stream
```

**Ожидаемый вывод:**
```
CONTAINER ID   NAME                        CPU %     MEM USAGE / LIMIT   
abc123def456   telegram_repair_bot_prod    0.5%      150MiB / 512MiB
```

### 6.6 Тестирование бота в Telegram

1. Откройте Telegram
2. Найдите вашего бота
3. Отправьте `/start`
4. Проверьте, что бот отвечает

---

## 7. Настройка автозапуска

### 7.1 Создание systemd сервиса

```bash
# Создание файла сервиса
sudo nano /etc/systemd/system/telegram-bot.service
```

**Содержимое файла:**

```ini
[Unit]
Description=Telegram Repair Bot
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=botuser
Group=botuser
WorkingDirectory=/home/botuser/telegram_repair_bot

# Команды запуска
ExecStart=/usr/bin/docker compose -f docker/docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker/docker-compose.prod.yml down
ExecReload=/usr/bin/docker compose -f docker/docker-compose.prod.yml restart

# Таймауты
TimeoutStartSec=300
TimeoutStopSec=60

# Restart политика
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 7.2 Активация сервиса

```bash
# Перезагрузка конфигурации systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable telegram-bot.service

# Запуск сервиса
sudo systemctl start telegram-bot.service

# Проверка статуса
sudo systemctl status telegram-bot.service
```

### 7.3 Управление сервисом

```bash
# Запуск
sudo systemctl start telegram-bot

# Остановка
sudo systemctl stop telegram-bot

# Перезапуск
sudo systemctl restart telegram-bot

# Просмотр логов systemd
sudo journalctl -u telegram-bot.service -f

# Последние 100 строк
sudo journalctl -u telegram-bot.service -n 100
```

### 7.4 Проверка автозапуска

```bash
# Перезагрузка сервера
sudo reboot

# После перезагрузки проверить
sudo systemctl status telegram-bot
docker ps
```

---

## 8. Мониторинг и поддержка

### 8.1 Полезные команды для мониторинга

```bash
# Статус всех контейнеров
docker ps -a

# Использование ресурсов
docker stats

# Логи бота (последние 100 строк)
docker compose -f docker/docker-compose.prod.yml logs --tail=100 bot

# Логи с поиском ошибок
docker compose -f docker/docker-compose.prod.yml logs bot | grep -i error

# Логи за последний час
docker compose -f docker/docker-compose.prod.yml logs --since=1h bot

# Размер логов
docker inspect telegram_repair_bot_prod | grep -i logpath
```

### 8.2 Проверка базы данных

```bash
# Вход в контейнер
docker compose -f docker/docker-compose.prod.yml exec bot bash

# Внутри контейнера - проверка БД
python check_database.py

# Размер БД
ls -lh /app/data/bot_database.db

# Выход из контейнера
exit
```

### 8.3 Проверка Redis

```bash
# Подключение к Redis CLI
docker compose -f docker/docker-compose.prod.yml exec redis redis-cli

# Внутри Redis CLI:
# Проверка количества ключей
DBSIZE

# Просмотр всех ключей
KEYS *

# Информация о памяти
INFO memory

# Выход
exit
```

### 8.4 Настройка мониторинга метрик

**Скрипт для базового мониторинга:**

```bash
# Создание скрипта мониторинга
nano ~/monitor_bot.sh
```

**Содержимое monitor_bot.sh:**

```bash
#!/bin/bash

echo "🤖 Telegram Bot Monitoring Report"
echo "=================================="
echo "📅 Дата: $(date)"
echo ""

# Проверка контейнера
echo "📦 Статус контейнера:"
docker ps --filter "name=telegram_repair_bot_prod" --format "table {{.Names}}\t{{.Status}}\t{{.State}}"
echo ""

# Использование ресурсов
echo "💻 Использование ресурсов:"
docker stats telegram_repair_bot_prod --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
echo ""

# Размер БД
echo "💾 Размер базы данных:"
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml exec -T bot ls -lh /app/data/bot_database.db 2>/dev/null || echo "БД не найдена"
echo ""

# Последние ошибки
echo "⚠️  Последние ошибки (если есть):"
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml logs --tail=20 bot 2>/dev/null | grep -i error || echo "Ошибок не найдено"
echo ""

# Healthcheck
echo "🏥 Healthcheck:"
docker inspect telegram_repair_bot_prod | grep -A 5 '"Health"' || echo "Healthcheck не настроен"
```

**Использование:**

```bash
# Сделать исполняемым
chmod +x ~/monitor_bot.sh

# Запуск
~/monitor_bot.sh
```

---

## 9. Резервное копирование

### 9.1 Настройка автоматического резервного копирования

**Создание скрипта backup:**

```bash
nano ~/backup_bot_db.sh
```

**Содержимое backup_bot_db.sh:**

```bash
#!/bin/bash

# Директория для backup
BACKUP_DIR="/home/botuser/telegram_repair_bot/backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
DB_FILE="/home/botuser/telegram_repair_bot/data/bot_database.db"
BACKUP_FILE="${BACKUP_DIR}/bot_database_${TIMESTAMP}.db"

# Создание директории если не существует
mkdir -p "$BACKUP_DIR"

# Backup из контейнера
docker compose -f /home/botuser/telegram_repair_bot/docker/docker-compose.prod.yml exec -T bot \
    python backup_db.py

# Или копирование файла напрямую
if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_FILE"
    echo "✅ Backup создан: $BACKUP_FILE"
    
    # Удаление старых backup (старше 30 дней)
    find "$BACKUP_DIR" -name "bot_database_*.db" -mtime +30 -delete
    echo "🗑️  Старые backup удалены"
else
    echo "❌ База данных не найдена: $DB_FILE"
    exit 1
fi
```

**Сделать скрипт исполняемым:**

```bash
chmod +x ~/backup_bot_db.sh
```

### 9.2 Настройка CRON для автоматического backup

```bash
# Редактирование crontab
crontab -e

# Добавьте следующую строку для ежедневного backup в 2:00 ночи
0 2 * * * /home/botuser/backup_bot_db.sh >> /home/botuser/backup.log 2>&1

# Или для backup каждые 6 часов
0 */6 * * * /home/botuser/backup_bot_db.sh >> /home/botuser/backup.log 2>&1

# Сохраните и выйдите (в nano: Ctrl+O, Enter, Ctrl+X)
```

### 9.3 Ручное создание backup

```bash
# Запуск скрипта вручную
~/backup_bot_db.sh

# Или через Docker
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml exec bot python backup_db.py

# Список backup
ls -lh ~/telegram_repair_bot/backups/
```

### 9.4 Восстановление из backup

```bash
# Остановка бота
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml stop bot

# Восстановление из конкретного backup
cp ~/telegram_repair_bot/backups/bot_database_2025-10-13_12-00-00.db \
   ~/telegram_repair_bot/data/bot_database.db

# Запуск бота
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml start bot
```

---

## 10. Troubleshooting

### 10.1 Бот не запускается

**Проблема:** Контейнер падает сразу после запуска

```bash
# Проверка логов
docker compose -f docker/docker-compose.prod.yml logs bot

# Проверка .env файла
cat .env | grep BOT_TOKEN

# Проверка сети
docker network ls
docker network inspect telegram_repair_bot_bot_network

# Попробовать запуск без daemon режима
docker compose -f docker/docker-compose.prod.yml up
```

**Решение:** Проверьте корректность BOT_TOKEN в .env

### 10.2 Бот не получает сообщения

**Проблема:** Бот запущен, но не отвечает на команды

```bash
# Проверка healthcheck
docker inspect telegram_repair_bot_prod | grep Health -A 10

# Проверка логов на ошибки подключения
docker compose -f docker/docker-compose.prod.yml logs bot | grep -i "connection\|error\|fail"

# Проверка доступа к Telegram API
docker compose -f docker/docker-compose.prod.yml exec bot ping -c 3 api.telegram.org
```

**Решения:**
1. Проверьте интернет-подключение сервера
2. Убедитесь, что токен валиден
3. Проверьте firewall правила

### 10.3 База данных заблокирована

**Проблема:** SQLite database is locked

```bash
# Остановка всех контейнеров
docker compose -f docker/docker-compose.prod.yml down

# Проверка процессов использующих БД
lsof ~/telegram_repair_bot/data/bot_database.db

# Удаление lock файлов
rm -f ~/telegram_repair_bot/data/bot_database.db-journal
rm -f ~/telegram_repair_bot/data/bot_database.db-shm
rm -f ~/telegram_repair_bot/data/bot_database.db-wal

# Перезапуск
docker compose -f docker/docker-compose.prod.yml up -d
```

### 10.4 Недостаточно памяти

**Проблема:** OOM (Out of Memory)

```bash
# Проверка использования памяти
docker stats --no-stream

# Проверка лимитов в docker-compose.prod.yml
cat docker/docker-compose.prod.yml | grep -A 5 resources

# Увеличение swap (временно)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**Решение:** Увеличьте RAM сервера или оптимизируйте лимиты в docker-compose

### 10.5 Redis недоступен

**Проблема:** Cannot connect to Redis

```bash
# Проверка Redis контейнера
docker ps | grep redis

# Проверка логов Redis
docker compose -f docker/docker-compose.prod.yml logs redis

# Перезапуск Redis
docker compose -f docker/docker-compose.prod.yml restart redis

# Проверка связи
docker compose -f docker/docker-compose.prod.yml exec bot ping redis
```

### 10.6 Проблемы с правами доступа

**Проблема:** Permission denied

```bash
# Проверка владельца файлов
ls -la ~/telegram_repair_bot/

# Изменение владельца
sudo chown -R botuser:botuser ~/telegram_repair_bot/

# Проверка прав на директории
chmod 755 ~/telegram_repair_bot/data
chmod 755 ~/telegram_repair_bot/logs
chmod 755 ~/telegram_repair_bot/backups

# Проверка прав на БД
chmod 644 ~/telegram_repair_bot/data/bot_database.db
```

---

## 📊 Чеклист успешного деплоя

### Перед деплоем:
- [ ] VPS сервер готов и доступен по SSH
- [ ] Docker и Docker Compose установлены
- [ ] Git установлен
- [ ] Создан backup базы данных локально

### Во время деплоя:
- [ ] Проект перенесен на сервер
- [ ] База данных перенесена
- [ ] .env файл настроен с правильными токенами
- [ ] Docker образ собран успешно
- [ ] Контейнеры запущены

### После деплоя:
- [ ] Бот отвечает на /start в Telegram
- [ ] Логи не содержат критических ошибок
- [ ] Healthcheck показывает "healthy"
- [ ] Автозапуск через systemd настроен
- [ ] Автоматический backup настроен
- [ ] Мониторинг настроен

---

## 🔗 Полезные команды (шпаргалка)

```bash
# === Управление ботом ===
# Запуск
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml up -d

# Остановка
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml down

# Перезапуск
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml restart

# Логи
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml logs -f bot

# === Обновление ===
cd ~/telegram_repair_bot
git pull
docker compose -f docker/docker-compose.prod.yml build
docker compose -f docker/docker-compose.prod.yml up -d

# === Backup ===
~/backup_bot_db.sh

# === Мониторинг ===
~/monitor_bot.sh
docker stats
```

---

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте логи: `docker compose -f docker/docker-compose.prod.yml logs bot`
2. Проверьте статус: `docker ps`
3. Проверьте healthcheck: `docker inspect telegram_repair_bot_prod | grep Health -A 10`
4. Обратитесь к разделу [Troubleshooting](#10-troubleshooting)

---

**Версия:** 1.2.1  
**Дата обновления:** 13 октября 2025  
**Статус:** ✅ Production Ready

🚀 **Успешного деплоя!**

