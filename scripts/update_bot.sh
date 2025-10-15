#!/bin/bash

# ========================================
# Скрипт автоматического обновления бота
# ========================================

set -e  # Остановка при ошибке

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Функции вывода
print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}\n"
}

print_step() {
    echo -e "${GREEN}▶ $1${NC}"
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

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Обработка ошибок
error_handler() {
    print_error "Ошибка на строке $1"
    print_info "Откат изменений..."
    
    # Попытка восстановить контейнеры
    if [ -d ~/telegram_repair_bot ]; then
        cd ~/telegram_repair_bot
        docker compose -f docker/docker-compose.prod.yml up -d 2>/dev/null || true
    fi
    
    print_warning "Проверьте логи: docker compose -f docker/docker-compose.prod.yml logs bot"
    exit 1
}

trap 'error_handler $LINENO' ERR

# Начало
print_header "ОБНОВЛЕНИЕ TELEGRAM REPAIR BOT"
echo -e "${BLUE}Дата: $(date)${NC}\n"

# Проверка директории
print_step "Проверка директории проекта..."
if [ -d ~/telegram_repair_bot ]; then
    cd ~/telegram_repair_bot
    print_success "Проект найден: ~/telegram_repair_bot"
else
    print_error "Проект не найден в ~/telegram_repair_bot"
    exit 1
fi

# Проверка Git
print_step "Проверка Git репозитория..."
if [ ! -d .git ]; then
    print_warning "Не Git репозиторий. Обновление через Git невозможно."
    read -p "Продолжить обновление без Git? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    SKIP_GIT=true
else
    SKIP_GIT=false
fi

# Проверка Docker
print_step "Проверка Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker не установлен!"
    exit 1
fi

if ! docker compose version &> /dev/null && ! docker-compose --version &> /dev/null; then
    print_error "Docker Compose не установлен!"
    exit 1
fi

print_success "Docker и Docker Compose установлены"

# Создание backup
print_step "Создание резервной копии базы данных..."
BACKUP_DIR="backups"
BACKUP_FILE="$BACKUP_DIR/bot_database_$(date +%Y%m%d_%H%M%S).db"
mkdir -p "$BACKUP_DIR"

if [ -f "data/bot_database.db" ]; then
    cp data/bot_database.db "$BACKUP_FILE"
    print_success "Backup создан: $BACKUP_FILE"
    
    # Проверка размера backup
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    print_info "Размер backup: $BACKUP_SIZE"
else
    print_warning "База данных не найдена (это нормально для первого запуска)"
fi

# Остановка systemd сервиса
print_step "Проверка systemd сервиса..."
if systemctl list-unit-files | grep -q telegram-bot; then
    print_info "Найден systemd сервис, остановка..."
    sudo systemctl stop telegram-bot || print_warning "Не удалось остановить сервис"
    SYSTEMD_WAS_RUNNING=true
else
    SYSTEMD_WAS_RUNNING=false
    print_info "Systemd сервис не используется"
fi

# Остановка контейнеров
print_step "Остановка Docker контейнеров..."
docker compose -f docker/docker-compose.prod.yml down
print_success "Контейнеры остановлены"

# Обновление кода
if [ "$SKIP_GIT" = false ]; then
    print_step "Получение обновлений из Git..."
    
    # Сохранение текущей ветки
    CURRENT_BRANCH=$(git branch --show-current)
    print_info "Текущая ветка: $CURRENT_BRANCH"
    
    # Проверка изменений
    if git diff-index --quiet HEAD --; then
        print_info "Локальных изменений нет"
    else
        print_warning "Обнаружены локальные изменения!"
        git status -s
        read -p "Сохранить локальные изменения в stash? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git stash save "Auto-stash before update $(date +%Y%m%d_%H%M%S)"
            print_success "Изменения сохранены в stash"
        fi
    fi
    
    # Получение обновлений
    print_info "Выполнение git pull..."
    if git pull origin "$CURRENT_BRANCH"; then
        print_success "Код обновлен"
        
        # Показать изменения
        COMMITS_PULLED=$(git log --oneline @{1}.. 2>/dev/null | wc -l)
        if [ "$COMMITS_PULLED" -gt 0 ]; then
            print_info "Получено коммитов: $COMMITS_PULLED"
            echo "Последние изменения:"
            git log --oneline @{1}.. | head -5
        else
            print_info "Новых коммитов нет (уже актуальная версия)"
        fi
    else
        print_error "Не удалось обновить код"
        exit 1
    fi
else
    print_warning "Обновление через Git пропущено"
fi

# Проверка .env
print_step "Проверка .env файла..."
if [ -f .env ]; then
    print_success ".env файл найден"
    
    # Проверка обязательных переменных
    if ! grep -q "BOT_TOKEN=.*[^example]" .env; then
        print_error "BOT_TOKEN не установлен в .env!"
        print_info "Отредактируйте .env файл и запустите скрипт снова"
        exit 1
    fi
    
    # Проверка новых переменных из env.example
    if [ -f env.example ]; then
        print_info "Проверка наличия новых переменных..."
        NEW_VARS=$(comm -13 <(grep "^[A-Z]" .env | cut -d= -f1 | sort) <(grep "^[A-Z]" env.example | cut -d= -f1 | sort) || true)
        if [ -n "$NEW_VARS" ]; then
            print_warning "Найдены новые переменные в env.example:"
            echo "$NEW_VARS"
            print_info "Рекомендуется добавить их в .env файл"
        fi
    fi
else
    print_error ".env файл не найден!"
    print_info "Создайте .env из env.example: cp env.example .env"
    exit 1
fi

# Проверка изменений в requirements.txt
print_step "Проверка зависимостей..."
if [ "$SKIP_GIT" = false ] && git diff @{1} requirements.txt 2>/dev/null | grep -q "^[+-]"; then
    print_warning "Обнаружены изменения в requirements.txt"
    print_info "Будет выполнена пересборка образа без кэша"
    NO_CACHE="--no-cache"
else
    print_info "Зависимости не изменились"
    NO_CACHE=""
fi

# Пересборка образа
print_step "Пересборка Docker образа..."
echo "Это может занять несколько минут..."

if [ -n "$NO_CACHE" ]; then
    print_warning "Сборка БЕЗ кэша (из-за изменений в зависимостях)"
fi

if docker compose -f docker/docker-compose.prod.yml build $NO_CACHE; then
    print_success "Образ собран успешно"
else
    print_error "Ошибка при сборке образа"
    exit 1
fi

# Применение миграций
print_step "Применение миграций базы данных..."
if docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head 2>/dev/null; then
    print_success "Миграции применены"
else
    print_warning "Миграции не требуются или произошла ошибка (продолжаем)"
fi

# Запуск контейнеров
print_step "Запуск Docker контейнеров..."
if docker compose -f docker/docker-compose.prod.yml up -d; then
    print_success "Контейнеры запущены"
else
    print_error "Ошибка при запуске контейнеров"
    exit 1
fi

# Ожидание запуска
print_step "Ожидание запуска сервисов..."
sleep 5

# Проверка статуса
print_step "Проверка статуса контейнеров..."
docker compose -f docker/docker-compose.prod.yml ps

# Проверка логов
print_step "Проверка логов на ошибки..."
sleep 2
if docker compose -f docker/docker-compose.prod.yml logs bot | grep -qi "error\|exception"; then
    print_warning "Обнаружены ошибки в логах!"
    print_info "Последние 20 строк логов:"
    docker compose -f docker/docker-compose.prod.yml logs --tail=20 bot
else
    print_success "Критических ошибок в логах не обнаружено"
fi

# Проверка healthcheck
print_step "Проверка healthcheck..."
sleep 3
HEALTH_STATUS=$(docker inspect telegram_repair_bot_prod 2>/dev/null | grep -i '"Status"' | grep -i health | head -1 || echo "unknown")
if echo "$HEALTH_STATUS" | grep -qi "healthy"; then
    print_success "Healthcheck: healthy"
elif echo "$HEALTH_STATUS" | grep -qi "starting"; then
    print_info "Healthcheck: starting (подождите немного)"
else
    print_warning "Healthcheck: $HEALTH_STATUS"
fi

# Восстановление systemd сервиса
if [ "$SYSTEMD_WAS_RUNNING" = true ]; then
    print_step "Запуск systemd сервиса..."
    sudo systemctl start telegram-bot || print_warning "Не удалось запустить сервис"
fi

# Очистка старых образов
print_step "Очистка старых Docker образов..."
DANGLING=$(docker images -f "dangling=true" -q | wc -l)
if [ "$DANGLING" -gt 0 ]; then
    print_info "Найдено неиспользуемых образов: $DANGLING"
    docker image prune -f >/dev/null
    print_success "Старые образы удалены"
else
    print_info "Неиспользуемых образов не найдено"
fi

# Проверка использования ресурсов
print_step "Использование ресурсов:"
docker stats --no-stream | grep -E "CONTAINER|telegram"

# Итоговый отчет
print_header "ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО"

print_success "Бот обновлен и запущен!"
echo ""
print_info "Полезные команды:"
echo "  • Логи:          docker compose -f docker/docker-compose.prod.yml logs -f bot"
echo "  • Статус:        docker compose -f docker/docker-compose.prod.yml ps"
echo "  • Перезапуск:    docker compose -f docker/docker-compose.prod.yml restart bot"
echo "  • Остановка:     docker compose -f docker/docker-compose.prod.yml down"
echo ""
print_info "Резервная копия: $BACKUP_FILE"
echo ""

# Показать последние логи
print_info "Последние 30 строк логов:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose -f docker/docker-compose.prod.yml logs --tail=30 bot
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

print_success "✅ Протестируйте бота в Telegram, отправив /start"
print_info "📖 Документация: docs/troubleshooting/BOT_UPDATE_ISSUES.md"

print_header "ГОТОВО"

