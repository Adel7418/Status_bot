#!/bin/bash

# ========================================
# Скрипт для деплоя бота на VPS Linux
# Использование: ./deploy_to_vps.sh <IP_адрес> <пользователь>
# ========================================

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для цветного вывода
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка аргументов
if [ $# -lt 2 ]; then
    print_error "Использование: $0 <IP_адрес> <пользователь>"
    print_info "Пример: $0 192.168.1.100 root"
    exit 1
fi

VPS_IP=$1
VPS_USER=$2
VPS_PATH="/home/$VPS_USER/telegram_repair_bot"
LOCAL_PATH="$(pwd)"

print_info "=========================================="
print_info "🚀 Деплой Telegram Repair Bot на VPS"
print_info "=========================================="
echo ""
print_info "VPS: $VPS_USER@$VPS_IP"
print_info "Удаленный путь: $VPS_PATH"
print_info "Локальный путь: $LOCAL_PATH"
echo ""

# Шаг 1: Проверка подключения к VPS
print_info "Шаг 1/7: Проверка подключения к VPS..."
if ssh -o ConnectTimeout=5 "$VPS_USER@$VPS_IP" "echo 'Connected'" &>/dev/null; then
    print_success "Подключение к VPS установлено"
else
    print_error "Не удалось подключиться к VPS"
    print_info "Проверьте: IP адрес, пользователя, SSH ключ"
    exit 1
fi

# Шаг 2: Создание резервной копии базы данных
print_info "Шаг 2/7: Создание резервной копии базы данных..."
if [ -f "bot_database.db" ]; then
    python backup_db.py 2>/dev/null || {
        TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
        mkdir -p backups
        cp bot_database.db "backups/bot_database_${TIMESTAMP}.db"
        print_success "Резервная копия создана: backups/bot_database_${TIMESTAMP}.db"
    }
else
    print_warning "Локальная база данных не найдена (это нормально для первого деплоя)"
fi

# Шаг 3: Проверка .env файла
print_info "Шаг 3/7: Проверка .env файла..."
if [ ! -f ".env" ]; then
    print_error ".env файл не найден!"
    print_info "Создайте .env файл на основе env.example"
    print_info "cp env.example .env"
    print_info "nano .env"
    exit 1
fi

# Проверка обязательных переменных
if ! grep -q "BOT_TOKEN=.*[^example]" .env; then
    print_error "BOT_TOKEN не установлен в .env файле!"
    print_info "Получите токен у @BotFather и добавьте в .env"
    exit 1
fi

if ! grep -q "ADMIN_IDS=.*[0-9]" .env; then
    print_warning "ADMIN_IDS не установлен в .env файле"
    print_info "Узнайте свой ID у @userinfobot и добавьте в .env"
fi

print_success ".env файл проверен"

# Шаг 4: Создание директорий на VPS
print_info "Шаг 4/7: Создание директорий на VPS..."
ssh "$VPS_USER@$VPS_IP" "mkdir -p $VPS_PATH/{data,logs,backups}" || {
    print_error "Не удалось создать директории на VPS"
    exit 1
}
print_success "Директории созданы"

# Шаг 5: Синхронизация файлов проекта
print_info "Шаг 5/7: Синхронизация файлов проекта..."

# Используем rsync для эффективной передачи
if command -v rsync &> /dev/null; then
    print_info "Используется rsync для передачи файлов..."
    rsync -avz --progress \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.git' \
        --exclude '.vscode' \
        --exclude 'venv' \
        --exclude '.env' \
        --exclude '*.log' \
        --exclude 'htmlcov' \
        --exclude '.pytest_cache' \
        -e "ssh" \
        "$LOCAL_PATH/" \
        "$VPS_USER@$VPS_IP:$VPS_PATH/" || {
        print_error "Ошибка при синхронизации файлов"
        exit 1
    }
else
    # Используем scp как альтернативу
    print_info "rsync не найден, используется scp..."
    scp -r \
        "$LOCAL_PATH/app" \
        "$LOCAL_PATH/docker" \
        "$LOCAL_PATH/migrations" \
        "$LOCAL_PATH/bot.py" \
        "$LOCAL_PATH/requirements.txt" \
        "$LOCAL_PATH/env.example" \
        "$VPS_USER@$VPS_IP:$VPS_PATH/" || {
        print_error "Ошибка при копировании файлов"
        exit 1
    }
fi
print_success "Файлы проекта синхронизированы"

# Шаг 6: Передача .env и базы данных
print_info "Шаг 6/7: Передача .env и базы данных..."

# Передача .env
scp ".env" "$VPS_USER@$VPS_IP:$VPS_PATH/.env" || {
    print_error "Не удалось передать .env файл"
    exit 1
}
print_success ".env файл передан"

# Передача базы данных
if [ -f "bot_database.db" ]; then
    scp "bot_database.db" "$VPS_USER@$VPS_IP:$VPS_PATH/data/bot_database.db" || {
        print_warning "Не удалось передать базу данных (продолжаем)"
    }
    print_success "База данных передана"
else
    print_warning "Локальная база данных не найдена (будет создана новая)"
fi

# Шаг 7: Настройка прав доступа
print_info "Шаг 7/7: Настройка прав доступа..."
ssh "$VPS_USER@$VPS_IP" << 'EOF'
cd ~/telegram_repair_bot
chmod 600 .env
chmod 755 data logs backups
if [ -f "data/bot_database.db" ]; then
    chmod 644 data/bot_database.db
fi
EOF
print_success "Права доступа настроены"

# Вывод итоговой информации
echo ""
print_success "=========================================="
print_success "✅ Деплой завершен успешно!"
print_success "=========================================="
echo ""
print_info "📋 Следующие шаги на VPS сервере:"
echo ""
echo "1. Подключитесь к VPS:"
echo "   ssh $VPS_USER@$VPS_IP"
echo ""
echo "2. Перейдите в директорию проекта:"
echo "   cd $VPS_PATH"
echo ""
echo "3. Запустите бота через Docker:"
echo "   docker compose -f docker/docker-compose.prod.yml up -d"
echo ""
echo "4. Проверьте логи:"
echo "   docker compose -f docker/docker-compose.prod.yml logs -f bot"
echo ""
echo "5. Проверьте статус:"
echo "   docker compose -f docker/docker-compose.prod.yml ps"
echo ""
print_info "📖 Полное руководство: DEPLOY_VPS_LINUX_GUIDE.md"
echo ""

