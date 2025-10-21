# 🆘 Инструкция по восстановлению после `make prod-clean`

## Что произошло

Команда `make prod-clean` выполнила:
```bash
docker compose -f docker/docker-compose.prod.yml down -v  # Удалены volumes
docker system prune -f  # Очищена система
```

**Удалено:**
- ❌ Docker volume `bot_data` (база данных)
- ❌ Docker volume `bot_logs` (логи)
- ❌ Docker volume `bot_backups` (бэкапы внутри контейнера)
- ❌ Docker volume `redis_data` (Redis данные)

---

## 🔍 ШАГ 1: Проверка на сервере

**Подключитесь к серверу по SSH:**
```bash
ssh user@your-server-ip
cd /path/to/telegram_repair_bot
```

**Проверьте статус Docker volumes:**
```bash
docker volume ls | grep bot
```

**Проверьте, есть ли бэкапы в локальной файловой системе сервера:**
```bash
ls -lh backups/
ls -lh data/backups/
```

⚠️ **ВАЖНО:** Если volumes удалены, бэкапы внутри контейнера тоже удалены!

---

## 🚀 ШАГ 2: Восстановление базы данных

### Вариант A: На сервере есть бэкапы

Если бэкапы сохранились в локальной файловой системе сервера:

```bash
# Проверить последний бэкап
ls -lth backups/ | head -5

# Создать директорию для восстановления
mkdir -p data/databases
```

### Вариант B: Загрузить бэкап с локальной машины

**На локальной машине Windows:**
```powershell
# Найти последний бэкап
Get-ChildItem backups\ | Sort-Object LastWriteTime -Descending | Select-Object -First 1

# Загрузить на сервер через SCP
scp backups\bot_database_2025-10-20_23-09-39.db user@server-ip:/path/to/telegram_repair_bot/
```

**Или используйте WinSCP / FileZilla для загрузки файла**

---

## 🔧 ШАГ 3: Восстановление и запуск

**На сервере:**

```bash
# 1. Создать директорию для данных
mkdir -p data/databases

# 2. Скопировать бэкап как основную БД
cp backups/bot_database_2025-10-20_23-09-39.db data/databases/bot_database.db

# ИЛИ если загрузили с локальной машины:
mv bot_database_2025-10-20_23-09-39.db data/databases/bot_database.db

# 3. Проверить права доступа
chmod 644 data/databases/bot_database.db

# 4. Запустить бота
make prod-start

# 5. Проверить логи
make prod-logs
```

---

## 📋 ШАГ 4: Проверка восстановления

```bash
# Проверить статус контейнеров
make prod-status

# Проверить логи на ошибки
docker logs telegram_repair_bot_prod --tail 100

# Войти в контейнер и проверить БД
make prod-shell
ls -lh /app/data/
exit
```

---

## ✅ ШАГ 5: Создать новый бэкап

```bash
# Сразу создайте бэкап восстановленной БД
make prod-backup
```

---

## 🛡️ Профилактика на будущее

### 1. Настроить автоматические бэкапы вне Docker

**Создать скрипт на сервере:** `/usr/local/bin/backup_bot_db.sh`
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="/root/bot_backups"
mkdir -p $BACKUP_DIR

# Копировать БД из Docker volume
docker cp telegram_repair_bot_prod:/app/data/bot_database.db $BACKUP_DIR/bot_database_$DATE.db

# Удалить старые бэкапы (старше 30 дней)
find $BACKUP_DIR -name "bot_database_*.db" -mtime +30 -delete

echo "Backup created: $BACKUP_DIR/bot_database_$DATE.db"
```

**Настроить cron:**
```bash
chmod +x /usr/local/bin/backup_bot_db.sh
crontab -e

# Добавить строку (бэкап каждые 6 часов):
0 */6 * * * /usr/local/bin/backup_bot_db.sh >> /var/log/bot_backup.log 2>&1
```

### 2. Использовать bind mount вместо volume

**Отредактировать `docker/docker-compose.prod.yml`:**
```yaml
volumes:
  - ./data:/app/data           # Bind mount вместо volume
  - ./logs:/app/logs           # Bind mount
  - ./backups:/app/backups     # Bind mount
```

Тогда данные будут храниться в локальной файловой системе сервера!

### 3. Регулярно копировать бэкапы с сервера

**На локальной машине (Windows):**
```powershell
# Создать скрипт download_backups.ps1
$SERVER = "user@server-ip"
$REMOTE_PATH = "/path/to/telegram_repair_bot/backups/"
$LOCAL_PATH = "C:\Bot_test\telegram_repair_bot\backups\"

scp -r ${SERVER}:${REMOTE_PATH}* $LOCAL_PATH
```

---

## 📞 Быстрая помощь

**Если что-то пошло не так:**
1. Проверьте логи: `make prod-logs`
2. Проверьте переменные окружения: `make prod-env`
3. Проверьте размер БД: `docker exec telegram_repair_bot_prod ls -lh /app/data/`

**Контакты для помощи:**
- Документация: `docs/BACKUP_GUIDE.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`
