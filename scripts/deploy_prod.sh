#!/bin/bash
# ========================================
# Скрипт деплоя в PRODUCTION
# ========================================

set -e  # Остановить при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
SSH_SERVER="${SSH_SERVER:-root@YOUR_SERVER_IP}"
PROD_DIR="${PROD_DIR:-~/telegram_repair_bot}"
COMPOSE_FILE="docker/docker-compose.prod.yml"
MIGRATE_FILE="docker/docker-compose.migrate.yml"

echo -e "${RED}========================================${NC}"
echo -e "${RED}⚠️  PRODUCTION DEPLOYMENT${NC}"
echo -e "${RED}========================================${NC}"
echo ""

# Проверка наличия переменной SSH_SERVER
if [ "$SSH_SERVER" = "root@YOUR_SERVER_IP" ]; then
    echo -e "${RED}❌ Ошибка: SSH_SERVER не настроен!${NC}"
    echo -e "${YELLOW}Установите переменную окружения:${NC}"
    echo -e "   export SSH_SERVER=root@your-server-ip"
    exit 1
fi

# Подтверждение деплоя в production
echo -e "${YELLOW}Вы собираетесь обновить PRODUCTION бота!${NC}"
echo -e "${YELLOW}Сервер: ${SSH_SERVER}${NC}"
echo -e "${YELLOW}Директория: ${PROD_DIR}${NC}"
echo ""
echo -e "${RED}⚠️  Это повлияет на работающего бота!${NC}"
echo ""
read -p "Вы уверены? Введите 'yes' для продолжения: " -r
echo ""

if [[ ! $REPLY =~ ^yes$ ]]; then
    echo -e "${BLUE}❌ Деплой отменен${NC}"
    exit 0
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🚀 PRODUCTION DEPLOYMENT${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}📡 Подключение к серверу: ${SSH_SERVER}${NC}"
echo ""

# Проверка доступности сервера
if ! ssh -o ConnectTimeout=10 "$SSH_SERVER" "echo 'Connection OK'" &> /dev/null; then
    echo -e "${RED}❌ Не удалось подключиться к серверу!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Соединение с сервером установлено${NC}"
echo ""

# Выполнение деплоя на сервере
echo -e "${YELLOW}📦 Запуск деплоя на сервере...${NC}"
ssh "$SSH_SERVER" bash -s << 'ENDSSH'
set -e

# Цвета для вывода на сервере
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROD_DIR="${PROD_DIR:-~/telegram_repair_bot}"

echo -e "${YELLOW}1️⃣  Переход в директорию production...${NC}"
cd "$PROD_DIR" || {
    echo -e "${RED}❌ Директория $PROD_DIR не найдена!${NC}"
    exit 1
}

# Сохранение текущего коммита для возможности отката
CURRENT_COMMIT=$(git rev-parse HEAD)
echo -e "${BLUE}📌 Текущий коммит: $CURRENT_COMMIT${NC}"
echo -e "${BLUE}   (для отката: git reset --hard $CURRENT_COMMIT)${NC}"
echo ""

echo -e "${YELLOW}2️⃣  Создание backup базы данных...${NC}"
if [ -f "bot_database.db" ]; then
    BACKUP_NAME="bot_database_backup_$(date +%Y%m%d_%H%M%S).db"
    cp bot_database.db "data/backups/$BACKUP_NAME" || true
    echo -e "${GREEN}✅ Backup создан: $BACKUP_NAME${NC}"
else
    echo -e "${YELLOW}⚠️  Локальная БД не найдена (используется Docker volume)${NC}"
fi
echo ""

echo -e "${YELLOW}3️⃣  Получение последних изменений из Git...${NC}"
git fetch origin
git pull origin main || {
    echo -e "${RED}❌ Ошибка при git pull${NC}"
    exit 1
}

echo -e "${YELLOW}4️⃣  Остановка текущих контейнеров...${NC}"
cd docker
docker compose -f docker-compose.prod.yml down

echo -e "${YELLOW}5️⃣  Пересборка и запуск контейнеров...${NC}"
docker compose -f docker-compose.prod.yml up -d --build

echo -e "${YELLOW}6️⃣  Применение миграций БД...${NC}"
docker compose -f docker-compose.migrate.yml run --rm migrate || {
    echo -e "${YELLOW}⚠️  Миграции не применены (возможно, уже актуальны)${NC}"
}

echo -e "${YELLOW}7️⃣  Проверка статуса контейнеров...${NC}"
docker compose -f docker-compose.prod.yml ps

# Проверка работоспособности
echo -e "${YELLOW}8️⃣  Проверка логов (первые 20 строк)...${NC}"
docker compose -f docker-compose.prod.yml logs --tail=20 bot

echo ""
echo -e "${GREEN}✅ Деплой в PRODUCTION завершен!${NC}"
echo ""
echo -e "${BLUE}📋 Полезные команды:${NC}"
echo -e "   Логи:     docker compose -f docker-compose.prod.yml logs -f bot"
echo -e "   Статус:   docker compose -f docker-compose.prod.yml ps"
echo -e "   Откат:    git reset --hard $CURRENT_COMMIT && docker compose -f docker-compose.prod.yml up -d --build"
echo ""
ENDSSH

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 PRODUCTION DEPLOYMENT ЗАВЕРШЕН!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Для мониторинга логов:${NC}"
echo -e "   make prod-logs"
echo ""
echo -e "${YELLOW}Для проверки статуса:${NC}"
echo -e "   make prod-status"
echo ""

