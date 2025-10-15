#!/bin/bash

# ========================================
# Скрипт диагностики проблем обновления бота
# ========================================

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
}

print_section() {
    echo -e "\n${GREEN}▶ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Начало диагностики
print_header "ДИАГНОСТИКА ОБНОВЛЕНИЯ БОТА"
echo -e "${BLUE}Дата: $(date)${NC}\n"

# 1. Проверка расположения проекта
print_section "1. Проверка директории проекта"
if [ -d ~/telegram_repair_bot ]; then
    print_success "Проект найден: ~/telegram_repair_bot"
    cd ~/telegram_repair_bot
else
    print_error "Проект не найден в ~/telegram_repair_bot"
    echo "Укажите путь к проекту:"
    read -r PROJECT_PATH
    if [ -d "$PROJECT_PATH" ]; then
        cd "$PROJECT_PATH"
        print_success "Используется: $PROJECT_PATH"
    else
        print_error "Директория не существует. Завершение."
        exit 1
    fi
fi

# 2. Проверка Git
print_section "2. Состояние Git репозитория"
if [ -d .git ]; then
    echo "Текущая ветка:"
    git branch --show-current
    
    echo -e "\nПоследний коммит:"
    git log -1 --oneline
    
    echo -e "\nСтатус:"
    git status -s
    
    echo -e "\nРазница с origin/main:"
    git fetch origin main 2>/dev/null
    COMMITS_BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null)
    if [ "$COMMITS_BEHIND" -gt 0 ]; then
        print_warning "Локальная версия отстаёт на $COMMITS_BEHIND коммитов"
        echo "Последние коммиты в origin/main:"
        git log --oneline HEAD..origin/main | head -5
    else
        print_success "Локальная версия актуальна"
    fi
else
    print_warning "Не Git репозиторий"
fi

# 3. Проверка Docker
print_section "3. Docker образы и контейнеры"
echo "Образы бота:"
docker images | grep -E "REPOSITORY|telegram_repair_bot|<none>" || print_warning "Образы не найдены"

echo -e "\nВремя создания образа:"
docker inspect telegram_repair_bot_bot:latest 2>/dev/null | grep -i "created" | head -1 || print_warning "Образ не найден"

echo -e "\nЗапущенные контейнеры:"
docker ps | grep -E "CONTAINER|telegram"

echo -e "\nВсе контейнеры (включая остановленные):"
docker ps -a | grep telegram

# 4. Проверка Docker Compose
print_section "4. Статус Docker Compose"
if [ -f docker/docker-compose.prod.yml ]; then
    docker compose -f docker/docker-compose.prod.yml ps
else
    print_error "docker-compose.prod.yml не найден"
fi

# 5. Проверка .env
print_section "5. Проверка .env файла"
if [ -f .env ]; then
    print_success ".env файл найден"
    echo "Переменные (без секретов):"
    grep -v "TOKEN\|PASSWORD\|SECRET" .env | grep -v "^#" | grep -v "^$" | head -15
    
    echo -e "\nПроверка обязательных переменных:"
    if grep -q "BOT_TOKEN=.*[^example]" .env; then
        print_success "BOT_TOKEN установлен"
    else
        print_error "BOT_TOKEN не установлен или использует example"
    fi
    
    if grep -q "ADMIN_IDS=.*[0-9]" .env; then
        print_success "ADMIN_IDS установлен"
    else
        print_warning "ADMIN_IDS не установлен"
    fi
else
    print_error ".env файл не найден!"
fi

# 6. Проверка requirements
print_section "6. Зависимости Python"
if [ -f requirements.txt ]; then
    echo "Последние изменения в requirements.txt:"
    git log -1 --oneline requirements.txt 2>/dev/null || echo "История недоступна"
else
    print_error "requirements.txt не найден"
fi

# 7. Логи контейнера
print_section "7. Последние логи бота"
if docker ps | grep -q telegram_repair_bot_prod; then
    echo "Последние 25 строк логов:"
    docker compose -f docker/docker-compose.prod.yml logs --tail=25 bot 2>/dev/null
    
    echo -e "\nОшибки в логах (если есть):"
    docker compose -f docker/docker-compose.prod.yml logs bot 2>/dev/null | grep -i "error\|exception\|traceback" | tail -10 || print_success "Ошибок не обнаружено"
else
    print_warning "Контейнер бота не запущен"
fi

# 8. Проверка healthcheck
print_section "8. Healthcheck контейнера"
if docker ps | grep -q telegram_repair_bot_prod; then
    docker inspect telegram_repair_bot_prod 2>/dev/null | grep -i '"Health"' -A 15 || print_warning "Healthcheck не настроен"
else
    print_warning "Контейнер не запущен"
fi

# 9. Проверка Redis
print_section "9. Состояние Redis"
if docker ps | grep -q redis; then
    print_success "Redis контейнер запущен"
    echo "Проверка подключения:"
    docker compose -f docker/docker-compose.prod.yml exec -T redis redis-cli ping 2>/dev/null || print_error "Redis не отвечает"
    
    echo -e "\nКоличество ключей:"
    docker compose -f docker/docker-compose.prod.yml exec -T redis redis-cli DBSIZE 2>/dev/null
else
    print_warning "Redis контейнер не запущен"
fi

# 10. Проверка systemd
print_section "10. Systemd сервис"
if systemctl list-unit-files | grep -q telegram-bot; then
    print_success "Systemd сервис найден"
    sudo systemctl status telegram-bot --no-pager 2>/dev/null || print_warning "Не удалось получить статус"
else
    print_warning "Systemd сервис не настроен (это нормально, если используете Docker Compose напрямую)"
fi

# 11. Использование ресурсов
print_section "11. Использование ресурсов"
if docker ps | grep -q telegram_repair_bot_prod; then
    docker stats --no-stream | grep -E "CONTAINER|telegram"
else
    print_warning "Контейнер не запущен"
fi

# 12. Проверка БД
print_section "12. База данных"
if [ -f data/bot_database.db ]; then
    DB_SIZE=$(du -h data/bot_database.db | cut -f1)
    print_success "База данных найдена: $DB_SIZE"
    echo "Последнее изменение:"
    ls -lh data/bot_database.db | awk '{print $6, $7, $8}'
    
    echo -e "\nПроверка БД из контейнера:"
    docker compose -f docker/docker-compose.prod.yml exec -T bot python -c "
import sqlite3
try:
    conn = sqlite3.connect('/app/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
    tables = cursor.fetchall()
    print(f'Таблиц в БД: {len(tables)}')
    conn.close()
except Exception as e:
    print(f'Ошибка: {e}')
" 2>/dev/null || print_warning "Не удалось проверить БД"
else
    print_error "База данных не найдена в data/bot_database.db"
fi

# 13. Проверка последнего backup
print_section "13. Резервные копии"
if [ -d backups ] && [ "$(ls -A backups 2>/dev/null)" ]; then
    echo "Последний backup:"
    ls -lht backups/ | head -2
    
    BACKUP_COUNT=$(ls backups/*.db 2>/dev/null | wc -l)
    print_success "Найдено backup'ов: $BACKUP_COUNT"
else
    print_warning "Backup'ы не найдены"
fi

# 14. Проверка диска
print_section "14. Использование диска"
df -h | grep -E "Filesystem|/$"

echo -e "\nРазмер директории проекта:"
du -sh ~/telegram_repair_bot 2>/dev/null || du -sh .

# 15. Сетевые подключения
print_section "15. Проверка сети Docker"
if docker ps | grep -q telegram; then
    echo "Docker networks:"
    docker network ls | grep -E "NETWORK|bot"
    
    echo -e "\nПроверка доступности Telegram API:"
    docker compose -f docker/docker-compose.prod.yml exec -T bot ping -c 3 api.telegram.org 2>/dev/null || print_warning "Не удалось проверить подключение"
else
    print_warning "Контейнеры не запущены"
fi

# Итоговый отчёт
print_header "ИТОГОВАЯ СВОДКА"

echo -e "\n${YELLOW}Рекомендации:${NC}"

# Проверяем основные проблемы
ISSUES_FOUND=0

# Проблема 1: Отстаёт от origin
if [ "${COMMITS_BEHIND:-0}" -gt 0 ]; then
    echo "• Код отстаёт от origin/main - выполните: git pull origin main"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Проблема 2: Контейнер не запущен
if ! docker ps | grep -q telegram_repair_bot_prod; then
    echo "• Контейнер бота не запущен - выполните:"
    echo "  docker compose -f docker/docker-compose.prod.yml up -d"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Проблема 3: Ошибки в логах
if docker compose -f docker/docker-compose.prod.yml logs bot 2>/dev/null | grep -qi "error\|exception"; then
    echo "• Найдены ошибки в логах - проверьте логи:"
    echo "  docker compose -f docker/docker-compose.prod.yml logs bot"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Проблема 4: .env не настроен
if [ ! -f .env ] || ! grep -q "BOT_TOKEN=.*[^example]" .env 2>/dev/null; then
    echo "• .env файл не настроен - настройте:"
    echo "  cp env.example .env && nano .env"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

if [ $ISSUES_FOUND -eq 0 ]; then
    print_success "Критических проблем не обнаружено!"
else
    print_warning "Найдено проблем: $ISSUES_FOUND"
fi

echo -e "\n${BLUE}Для обновления бота выполните:${NC}"
echo "bash scripts/update_bot.sh"

echo -e "\n${BLUE}Для просмотра полного руководства:${NC}"
echo "cat docs/troubleshooting/BOT_UPDATE_ISSUES.md"

print_header "КОНЕЦ ДИАГНОСТИКИ"

