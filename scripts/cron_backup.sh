#!/bin/bash

# ===================================================================
# Скрипт автоматического бэкапа для cron
# ===================================================================
# Использование в crontab:
#   0 */6 * * * /path/to/telegram_repair_bot/scripts/cron_backup.sh >> /var/log/bot_backup.log 2>&1
#
# Это создаёт бэкап каждые 6 часов (00:00, 06:00, 12:00, 18:00)
# ===================================================================

# Переход в директорию проекта
cd "$(dirname "$0")/.." || exit 1

# Вывод даты и времени
echo "================================================================================"
echo "АВТОМАТИЧЕСКИЙ БЭКАП БД - $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================================"

# Проверка, что Docker контейнер запущен
if ! docker ps | grep -q telegram_repair_bot_prod; then
    echo "WARNING: Контейнер telegram_repair_bot_prod не запущен!"
    echo "Попытка бэкапа с хоста..."
    
    # Бэкап напрямую с хоста
    if [ -f "data/bot_database.db" ]; then
        TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
        BACKUP_FILE="backups/bot_database_${TIMESTAMP}.db"
        
        cp data/bot_database.db "$BACKUP_FILE"
        SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        
        echo "OK: Бэкап создан с хоста: $BACKUP_FILE ($SIZE)"
    else
        echo "ERROR: База данных не найдена!"
        exit 1
    fi
else
    # Бэкап через Docker контейнер
    docker exec telegram_repair_bot_prod python /app/scripts/backup_db.py --keep-days 30
    
    if [ $? -eq 0 ]; then
        echo "OK: Бэкап создан через Docker контейнер"
    else
        echo "ERROR: Ошибка создания бэкапа"
        exit 1
    fi
fi

# Подсчёт бэкапов
BACKUP_COUNT=$(ls -1 backups/bot_database_*.db 2>/dev/null | wc -l)
echo "INFO: Всего бэкапов: $BACKUP_COUNT"

# Список последних 3 бэкапов
echo "INFO: Последние 3 бэкапа:"
ls -lht backups/bot_database_*.db 2>/dev/null | head -3 | awk '{print "  -", $9, "("$5")", $6, $7, $8}'

echo "================================================================================"
echo "БЭКАП ЗАВЕРШЁН - $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================================"
echo ""

