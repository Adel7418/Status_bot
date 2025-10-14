#!/bin/bash
# ========================================
# Скрипт автоматического деплоя в STAGING
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
STAGING_DIR="${STAGING_DIR:-~/telegram_repair_bot_staging}"
COMPOSE_FILE="docker/docker-compose.staging.yml"
MIGRATE_FILE="docker/docker-compose.migrate.yml"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🚀 STAGING DEPLOYMENT${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Проверка наличия переменной SSH_SERVER
if [ "$SSH_SERVER" = "root@YOUR_SERVER_IP" ]; then
    echo -e "${RED}❌ Ошибка: SSH_SERVER не настроен!${NC}"
    echo -e "${YELLOW}Установите переменную окружения:${NC}"
    echo -e "   export SSH_SERVER=root@your-server-ip"
    echo -e "${YELLOW}Или укажите в файле .env:${NC}"
    echo -e "   SSH_SERVER=root@your-server-ip"
    exit 1
fi

echo -e "${YELLOW}📡 Подключение к серверу: ${SSH_SERVER}${NC}"
echo -e "${YELLOW}📁 Директория staging: ${STAGING_DIR}${NC}"
echo ""

# Проверка доступности сервера
if ! ssh -o ConnectTimeout=10 "$SSH_SERVER" "echo 'Connection OK'" &> /dev/null; then
    echo -e "${RED}❌ Не удалось подключиться к серверу!${NC}"
    echo -e "${YELLOW}Проверьте:${NC}"
    echo -e "  1. SSH ключ настроен (ssh-copy-id)"
    echo -e "  2. Правильный IP адрес"
    echo -e "  3. Сервер доступен"
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

STAGING_DIR="${STAGING_DIR:-~/telegram_repair_bot_staging}"

echo -e "${YELLOW}1️⃣  Переход в директорию staging...${NC}"
cd "$STAGING_DIR" || {
    echo -e "${RED}❌ Директория $STAGING_DIR не найдена!${NC}"
    echo -e "${YELLOW}Создайте staging окружение:${NC}"
    echo -e "   mkdir -p $STAGING_DIR"
    echo -e "   cd $STAGING_DIR"
    echo -e "   git clone <repository-url> ."
    exit 1
}

echo -e "${YELLOW}2️⃣  Получение последних изменений из Git...${NC}"
git fetch origin
git pull origin main || {
    echo -e "${RED}❌ Ошибка при git pull${NC}"
    exit 1
}

echo -e "${YELLOW}3️⃣  Остановка текущих контейнеров...${NC}"
cd docker
docker compose -f docker-compose.staging.yml down || true

echo -e "${YELLOW}4️⃣  Пересборка и запуск контейнеров...${NC}"
docker compose -f docker-compose.staging.yml up -d --build

echo -e "${YELLOW}5️⃣  Применение миграций БД...${NC}"
docker compose -f docker-compose.migrate.yml run --rm migrate || {
    echo -e "${YELLOW}⚠️  Миграции не применены (возможно, уже актуальны)${NC}"
}

echo -e "${YELLOW}6️⃣  Проверка статуса контейнеров...${NC}"
docker compose -f docker-compose.staging.yml ps

echo ""
echo -e "${GREEN}✅ Деплой в STAGING завершен успешно!${NC}"
echo ""
echo -e "${BLUE}📋 Полезные команды:${NC}"
echo -e "   Логи:     docker compose -f docker-compose.staging.yml logs -f bot"
echo -e "   Статус:   docker compose -f docker-compose.staging.yml ps"
echo -e "   Остановить: docker compose -f docker-compose.staging.yml down"
echo ""
ENDSSH

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 STAGING DEPLOYMENT УСПЕШНО ЗАВЕРШЕН!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Для просмотра логов выполните:${NC}"
echo -e "   make staging-logs"
echo ""
echo -e "${YELLOW}После проверки в staging, деплой в production:${NC}"
echo -e "   make prod-deploy"
echo ""

