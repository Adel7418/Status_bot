#!/bin/bash
set -e

echo "🐳 Миграция ORMDatabase в Docker"
echo "================================="

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
if ! command -v docker-compose &> /dev/null; then
    log_error "docker-compose не найден. Установите Docker Compose."
    exit 1
fi

# Проверка наличия docker-compose.yml
if [ ! -f "docker-compose.yml" ]; then
    log_error "Файл docker-compose.yml не найден в текущей директории."
    exit 1
fi

# 1. Создание бэкапа
log_info "Создание бэкапа базы данных..."
BACKUP_NAME="bot_database_backup_$(date +%Y%m%d_%H%M%S).db"

# Проверяем, запущен ли контейнер
if docker-compose ps bot | grep -q "Up"; then
    # Контейнер запущен, создаем бэкап внутри
    if docker-compose exec bot cp /app/data/bot_database.db /app/data/$BACKUP_NAME; then
        log_success "Бэкап создан внутри контейнера: $BACKUP_NAME"
    else
        log_error "Не удалось создать бэкап внутри контейнера"
        exit 1
    fi
else
    # Контейнер не запущен, пытаемся скопировать файл
    if [ -f "data/bot_database.db" ]; then
        cp data/bot_database.db data/$BACKUP_NAME
        log_success "Бэкап создан на хосте: data/$BACKUP_NAME"
    else
        log_warning "Файл базы данных не найден. Продолжаем без бэкапа."
    fi
fi

# 2. Остановка бота
log_info "Остановка бота..."
if docker-compose stop bot; then
    log_success "Бот остановлен"
else
    log_warning "Не удалось остановить бота (возможно, уже остановлен)"
fi

# 3. Проверка миграций
log_info "Проверка текущего состояния миграций..."
if docker-compose run --rm bot alembic current; then
    log_success "Статус миграций получен"
else
    log_error "Не удалось получить статус миграций"
    exit 1
fi

# 4. Применение миграций
log_info "Применение миграций..."
if docker-compose run --rm bot alembic upgrade head; then
    log_success "Миграции применены успешно"
else
    log_error "Ошибка при применении миграций"
    exit 1
fi

# 5. Проверка базы данных
log_info "Проверка базы данных..."
if docker-compose run --rm bot sqlite3 /app/data/bot_database.db "SELECT COUNT(*) FROM orders;" > /dev/null 2>&1; then
    log_success "База данных доступна"
else
    log_error "Проблемы с базой данных"
    exit 1
fi

# 6. Запуск бота
log_info "Запуск бота..."
if docker-compose up -d bot; then
    log_success "Бот запущен"
else
    log_error "Не удалось запустить бота"
    exit 1
fi

# 7. Ожидание запуска
log_info "Ожидание запуска бота (10 секунд)..."
sleep 10

# 8. Проверка работы
log_info "Проверка работы бота..."
if docker-compose ps bot | grep -q "Up"; then
    log_success "Бот работает"
else
    log_error "Бот не запустился"
    echo "Логи бота:"
    docker-compose logs --tail=20 bot
    exit 1
fi

# 9. Показ логов
log_info "Последние логи бота:"
docker-compose logs --tail=10 bot

echo ""
echo "🎉 Миграция завершена успешно!"
echo "📁 Бэкап: $BACKUP_NAME"
echo ""
echo "📋 Следующие шаги:"
echo "1. Проверьте логи: docker-compose logs -f bot"
echo "2. Протестируйте функции бота"
echo "3. Убедитесь, что все работает корректно"
echo ""
echo "🔍 Команды для мониторинга:"
echo "- Логи: docker-compose logs -f bot"
echo "- Статус: docker-compose ps"
echo "- Ресурсы: docker stats"
