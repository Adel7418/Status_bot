#!/bin/bash
set -e

echo "🐳 Миграция ORMDatabase в Docker Multibot"
echo "=========================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка наличия docker-compose
if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
    log_error "docker-compose или docker не найден. Установите Docker."
    exit 1
fi

# Определяем команду docker
if command -v docker-compose &> /dev/null; then
    DOCKER_CMD="docker-compose"
elif command -v docker &> /dev/null; then
    DOCKER_CMD="docker compose"
else
    log_error "Не найдена команда для работы с docker-compose"
    exit 1
fi

# Устанавливаем путь к docker-compose для multibot
COMPOSE_FILE="docker/docker-compose.multibot.yml"

# Функция для миграции конкретного бота
migrate_bot() {
    local BOT_NAME=$1
    local CONTAINER_NAME=$2

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Обработка $BOT_NAME"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 1. Создание бэкапа
    log_info "Создание бэкапа базы данных для $BOT_NAME..."
    BACKUP_NAME="bot_database_backup_${BOT_NAME}_$(date +%Y%m%d_%H%M%S).db"

    # Проверяем, запущен ли контейнер
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        # Контейнер запущен, создаем бэкап внутри
        if docker exec $CONTAINER_NAME cp /app/data/bot_database.db /app/data/$BACKUP_NAME 2>/dev/null; then
            log_success "Бэкап создан: $BACKUP_NAME"
        else
            log_warning "Не удалось создать бэкап внутри контейнера (возможно, БД еще не существует)"
        fi
    else
        log_warning "Контейнер $CONTAINER_NAME не запущен"
    fi

    # 2. Остановка бота
    log_info "Остановка $BOT_NAME..."
    if $DOCKER_CMD -f $COMPOSE_FILE stop $BOT_NAME 2>/dev/null; then
        log_success "$BOT_NAME остановлен"
    else
        log_warning "Не удалось остановить $BOT_NAME (возможно, уже остановлен)"
    fi

    # 3. Проверка текущего состояния миграций
    log_info "Проверка текущего состояния миграций для $BOT_NAME..."
    if $DOCKER_CMD -f $COMPOSE_FILE run --rm $BOT_NAME alembic current; then
        log_success "Статус миграций получен для $BOT_NAME"
    else
        log_error "Не удалось получить статус миграций для $BOT_NAME"
        return 1
    fi

    # 4. Применение миграций
    log_info "Применение миграций для $BOT_NAME..."
    if $DOCKER_CMD -f $COMPOSE_FILE run --rm $BOT_NAME alembic upgrade head; then
        log_success "Миграции применены успешно для $BOT_NAME"
    else
        log_error "Ошибка при применении миграций для $BOT_NAME"
        return 1
    fi

    # 5. Проверка базы данных
    log_info "Проверка базы данных для $BOT_NAME..."
    if $DOCKER_CMD -f $COMPOSE_FILE run --rm $BOT_NAME sqlite3 /app/data/bot_database.db "SELECT COUNT(*) FROM orders;" > /dev/null 2>&1; then
        log_success "База данных доступна для $BOT_NAME"
    else
        log_error "Проблемы с базой данных для $BOT_NAME"
        return 1
    fi

    # 6. Запуск бота
    log_info "Запуск $BOT_NAME..."
    if $DOCKER_CMD -f $COMPOSE_FILE up -d $BOT_NAME; then
        log_success "$BOT_NAME запущен"
    else
        log_error "Не удалось запустить $BOT_NAME"
        return 1
    fi

    # 7. Ожидание запуска
    sleep 5

    # 8. Проверка работы
    log_info "Проверка работы $BOT_NAME..."
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_success "$BOT_NAME работает"
    else
        log_error "$BOT_NAME не запустился"
        log_info "Логи $BOT_NAME:"
        $DOCKER_CMD -f $COMPOSE_FILE logs --tail=20 $BOT_NAME
        return 1
    fi

    return 0
}

# Главная логика
log_info "Начало миграции multibot окружения"
echo ""

# 0. Пересборка образов с новым кодом
log_info "Пересборка Docker образов с новым кодом..."
if $DOCKER_CMD -f $COMPOSE_FILE build 2>/dev/null; then
    log_success "Образы пересобраны с новым кодом"
else
    log_warning "Не удалось пересобрать образы"
fi
echo ""

# Миграция для bot_city1
if ! migrate_bot "bot_city1" "telegram_repair_bot_city1"; then
    log_error "Ошибка при миграции bot_city1"
    exit 1
fi

# Миграция для bot_city2
if ! migrate_bot "bot_city2" "telegram_repair_bot_city2"; then
    log_error "Ошибка при миграции bot_city2"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Миграция multibot завершена успешно!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Следующие шаги:"
echo "1. Проверьте логи:"
echo "   - docker logs telegram_repair_bot_city1"
echo "   - docker logs telegram_repair_bot_city2"
echo "2. Протестируйте функции ботов"
echo "3. Убедитесь, что все работает корректно"
echo ""
echo "🔍 Команды для мониторинга:"
echo "- Логи city1: docker logs -f telegram_repair_bot_city1"
echo "- Логи city2: docker logs -f telegram_repair_bot_city2"
echo "- Статус: $DOCKER_CMD -f $COMPOSE_FILE ps"
echo "- Ресурсы: docker stats"
echo ""
