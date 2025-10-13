#!/bin/bash

# ========================================
# Скрипт для применения миграций Alembic
# Использование: ./migrate.sh [команда]
# ========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Определение команды (по умолчанию upgrade head)
COMMAND=${1:-"upgrade head"}

print_info "=========================================="
print_info "🔄 Применение миграций Alembic"
print_info "=========================================="
echo ""

# Проверка наличия Docker
if command -v docker &> /dev/null; then
    print_info "Использование Docker для миграций..."
    
    # Проверка что Redis запущен
    if ! docker ps | grep -q telegram_bot_redis; then
        print_info "Запуск Redis..."
        docker compose -f docker/docker-compose.prod.yml up -d redis
        sleep 2
    fi
    
    # Выполнение миграций через Docker
    print_info "Выполнение: alembic $COMMAND"
    docker compose -f docker/docker-compose.prod.yml run --rm bot alembic $COMMAND
    
    print_success "Миграции применены успешно!"
else
    # Локальное выполнение
    print_info "Docker не найден, использование локального Python..."
    
    if [ ! -d "venv" ]; then
        print_error "Виртуальное окружение не найдено!"
        print_info "Создайте его: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
    
    source venv/bin/activate
    print_info "Выполнение: alembic $COMMAND"
    alembic $COMMAND
    deactivate
    
    print_success "Миграции применены успешно!"
fi

echo ""
print_info "Проверить текущую версию:"
print_info "  docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current"
echo ""

