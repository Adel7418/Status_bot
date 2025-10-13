# 🛠️ Скрипты для деплоя и управления

Набор утилит для упрощенного деплоя Telegram бота на VPS Linux.

---

## 📋 Список скриптов

### 1. `setup_vps.sh` - Первоначальная настройка VPS

**Назначение:** Автоматическая установка и настройка всего необходимого ПО на VPS сервере.

**Что делает:**
- Обновляет систему
- Устанавливает Git, Docker, Docker Compose
- Настраивает права доступа
- Создает необходимые директории
- Настраивает firewall

**Использование:**

```bash
# 1. Подключитесь к VPS
ssh root@ваш_IP

# 2. Загрузите скрипт
wget https://raw.githubusercontent.com/Adel7418/Status_bot/main/scripts/setup_vps.sh

# 3. Сделайте исполняемым
chmod +x setup_vps.sh

# 4. Запустите
./setup_vps.sh
```

**Требования:**
- Ubuntu 20.04+ / Debian 11+
- Права root или sudo

---

### 2. `deploy_to_vps.sh` - Деплой проекта на VPS

**Назначение:** Автоматический перенос всех файлов проекта и базы данных на VPS.

**Что делает:**
- Проверяет подключение к VPS
- Создает резервную копию БД
- Проверяет .env файл
- Синхронизирует файлы проекта
- Передает .env и базу данных
- Настраивает права доступа

**Использование:**

```bash
# На локальной машине (Windows/Linux/Mac)
cd C:\Bot_test\telegram_repair_bot  # Windows
# или
cd ~/telegram_repair_bot  # Linux/Mac

# Запуск деплоя
bash scripts/deploy_to_vps.sh <IP_адрес> <пользователь>

# Примеры:
bash scripts/deploy_to_vps.sh 192.168.1.100 root
bash scripts/deploy_to_vps.sh myserver.com botuser
```

**Требования:**
- SSH доступ к VPS
- Настроенный .env файл
- rsync или scp

**Что нужно сделать ДО запуска:**

1. Создать и заполнить .env файл:
```bash
cp env.example .env
nano .env  # Добавьте BOT_TOKEN, ADMIN_IDS
```

2. Убедиться что есть SSH доступ:
```bash
ssh root@ваш_IP  # проверка подключения
```

---

### 3. `export_db.py` - Экспорт базы данных в JSON

**Назначение:** Экспорт базы данных SQLite в формат JSON для переноса или бэкапа.

**Что делает:**
- Читает все таблицы из SQLite
- Экспортирует данные в JSON
- Сохраняет метаданные (схему таблиц)
- Показывает статистику экспорта

**Использование:**

```bash
# Простой экспорт (создаст db_export_<timestamp>.json)
python scripts/export_db.py

# С указанием БД
python scripts/export_db.py --database bot_database.db

# С указанием имени выходного файла
python scripts/export_db.py --output my_backup.json

# Полная форма
python scripts/export_db.py -d bot_database.db -o export.json
```

**Параметры:**
- `--database`, `-d`: Путь к файлу БД (по умолчанию: bot_database.db)
- `--output`, `-o`: Имя выходного JSON файла

**Пример вывода:**
```
📊 Найдено таблиц: 5
  📋 Экспорт таблицы: users... ✅ (15 строк)
  📋 Экспорт таблицы: requests... ✅ (47 строк)
  📋 Экспорт таблицы: user_roles... ✅ (20 строк)

✅ Экспорт завершен успешно!
  📁 Файл: db_export_20251013_120000.json
  📊 Таблиц: 5
  📝 Всего строк: 82
  💾 Размер БД: 45.32 KB
  💾 Размер JSON: 67.18 KB
```

---

### 4. `import_db.py` - Импорт базы данных из JSON

**Назначение:** Восстановление базы данных из JSON экспорта.

**Что делает:**
- Читает JSON файл с экспортом
- Проверяет существование таблиц
- Импортирует данные в SQLite
- Показывает статистику импорта

**Использование:**

```bash
# Простой импорт
python scripts/import_db.py db_export_20251013_120000.json

# С указанием БД
python scripts/import_db.py export.json --database bot_database.db

# С очисткой существующих данных
python scripts/import_db.py export.json --clear

# С автоматическим бэкапом
python scripts/import_db.py export.json --backup

# Полная форма
python scripts/import_db.py export.json -d bot_database.db -c -b
```

**Параметры:**
- `json_file`: Путь к JSON файлу (обязательно)
- `--database`, `-d`: Путь к файлу БД (по умолчанию: bot_database.db)
- `--clear`, `-c`: Очистить таблицы перед импортом
- `--backup`, `-b`: Создать резервную копию БД перед импортом

**Пример вывода:**
```
📖 Чтение JSON файла: db_export_20251013_120000.json
  📅 Дата экспорта: 2025-10-13T12:00:00
  📊 Таблиц в экспорте: 5
  📋 Импорт таблицы: users... ✅ (15 строк, ошибок: 0)
  📋 Импорт таблицы: requests... ✅ (47 строк, ошибок: 0)

✅ Импорт завершен успешно!
  📁 База данных: bot_database.db
  📊 Импортировано таблиц: 5
  📝 Всего строк: 82
  💾 Размер БД: 45.32 KB
```

---

## 🚀 Быстрый старт: Полный деплой

### Вариант 1: Автоматический деплой (рекомендуется)

**На локальной машине:**

```bash
# 1. Настройка .env
cp env.example .env
nano .env  # Добавьте токены

# 2. Экспорт БД (опционально, для безопасности)
python scripts/export_db.py

# 3. Деплой на VPS
bash scripts/deploy_to_vps.sh <IP> <user>
```

**На VPS сервере:**

```bash
# 1. Первоначальная настройка (один раз)
wget https://raw.githubusercontent.com/Adel7418/Status_bot/main/scripts/setup_vps.sh
chmod +x setup_vps.sh
./setup_vps.sh

# 2. После деплоя файлов - запуск бота
cd ~/telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml up -d
```

### Вариант 2: Ручной деплой

```bash
# 1. На локальной машине - экспорт БД
python scripts/export_db.py

# 2. Перенос на VPS
scp db_export_*.json root@IP:/home/botuser/telegram_repair_bot/
scp -r . root@IP:/home/botuser/telegram_repair_bot/

# 3. На VPS - импорт БД
cd ~/telegram_repair_bot
python scripts/import_db.py db_export_*.json --backup

# 4. Запуск
docker compose -f docker/docker-compose.prod.yml up -d
```

---

## 📊 Сценарии использования

### Сценарий 1: Первый деплой с нуля

```bash
# Локально
cp env.example .env
nano .env  # Настроить

# Деплой
bash scripts/deploy_to_vps.sh 192.168.1.100 root

# На VPS (после подключения)
cd ~/telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml up -d
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

### Сценарий 2: Миграция на новый сервер

```bash
# На старом сервере - экспорт
python scripts/export_db.py -o migration_backup.json

# Копирование на новый сервер
scp migration_backup.json root@новый_IP:/root/

# На новом сервере - настройка
./setup_vps.sh
cd ~/telegram_repair_bot

# Импорт данных
python scripts/import_db.py /root/migration_backup.json

# Запуск
docker compose -f docker/docker-compose.prod.yml up -d
```

### Сценарий 3: Обновление проекта

```bash
# Локально - новый деплой
bash scripts/deploy_to_vps.sh 192.168.1.100 root

# На VPS - перезапуск
cd ~/telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml down
docker compose -f docker/docker-compose.prod.yml build
docker compose -f docker/docker-compose.prod.yml up -d
```

### Сценарий 4: Восстановление из бэкапа

```bash
# Остановка бота
docker compose -f docker/docker-compose.prod.yml down

# Восстановление из JSON
python scripts/import_db.py backups/db_export_20251013_120000.json --backup

# Или из .db файла
cp backups/bot_database_2025-10-13_12-00-00.db data/bot_database.db

# Запуск
docker compose -f docker/docker-compose.prod.yml up -d
```

---

## 🔧 Troubleshooting

### Проблема: deploy_to_vps.sh не работает на Windows

**Решение:** Используйте Git Bash или WSL

```bash
# В Git Bash
bash scripts/deploy_to_vps.sh 192.168.1.100 root

# Или в WSL
wsl bash scripts/deploy_to_vps.sh 192.168.1.100 root
```

### Проблема: Permission denied при запуске .sh

**Решение:**

```bash
chmod +x scripts/deploy_to_vps.sh
chmod +x scripts/setup_vps.sh
```

### Проблема: rsync not found

**Решение:** Скрипт автоматически переключится на scp, но для лучшей производительности установите rsync:

```bash
# Windows (Git Bash)
pacman -S rsync

# Linux/Mac
sudo apt install rsync  # Ubuntu/Debian
brew install rsync      # macOS
```

### Проблема: Экспорт/импорт БД не работает

**Решение:**

```bash
# Проверка существования БД
ls -la bot_database.db

# Проверка формата JSON
python -m json.tool db_export_*.json > /dev/null

# Проверка прав доступа
chmod 644 bot_database.db
```

---

## 📝 Примечания

### Безопасность

1. **Никогда не коммитьте .env файл в Git**
2. **Используйте SSH ключи вместо паролей**
3. **Регулярно обновляйте систему на VPS**
4. **Создавайте резервные копии перед импортом**

### Производительность

- Для больших БД (>100MB) используйте прямой перенос .db файла вместо JSON
- JSON экспорт удобен для миграций между разными СУБД
- Используйте `--clear` при импорте только если уверены

### Автоматизация

Создайте alias для частых команд:

```bash
# Добавьте в ~/.bashrc или ~/.zshrc
alias bot-deploy='bash ~/telegram_repair_bot/scripts/deploy_to_vps.sh'
alias bot-export='python ~/telegram_repair_bot/scripts/export_db.py'
alias bot-import='python ~/telegram_repair_bot/scripts/import_db.py'
```

---

## 🔗 Связанные документы

- [DEPLOY_VPS_LINUX_GUIDE.md](../DEPLOY_VPS_LINUX_GUIDE.md) - Полное руководство по деплою
- [PRODUCTION_READY_GUIDE.md](../PRODUCTION_READY_GUIDE.md) - Production чеклист
- [README.md](../README.md) - Основная документация

---

**Версия:** 1.0  
**Дата:** 13 октября 2025

