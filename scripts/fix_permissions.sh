#!/bin/bash
# ========================================
# Скрипт для исправления прав доступа
# Использование: ./scripts/fix_permissions.sh
# ========================================

set -e

echo "🔧 Исправление прав доступа к директориям..."

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка, что мы в корневой директории проекта
if [ ! -f "bot.py" ]; then
    echo -e "${RED}❌ Ошибка: Запустите скрипт из корневой директории проекта${NC}"
    exit 1
fi

# Создание директорий если их нет
echo -e "${YELLOW}📁 Создание директорий...${NC}"
mkdir -p data logs backups data/redis

# Проверка, нужны ли sudo права
if [ -w "logs" ] && [ -w "data" ] && [ -w "backups" ]; then
    echo -e "${GREEN}✅ Директории доступны для записи${NC}"

    # Установка прав без sudo
    chmod -R 755 data logs backups
    echo -e "${GREEN}✅ Права установлены (755)${NC}"
else
    echo -e "${YELLOW}⚠️  Требуются права sudo для изменения владельца${NC}"

    # Вариант 1: Изменить владельца на текущего пользователя
    echo -e "${YELLOW}Вариант 1: Изменить владельца на $(whoami)${NC}"
    sudo chown -R $(id -u):$(id -g) data/ logs/ backups/
    chmod -R 755 data logs backups
    echo -e "${GREEN}✅ Владелец изменен на $(whoami)${NC}"
fi

# Вывод информации о правах
echo ""
echo -e "${GREEN}📊 Текущие права доступа:${NC}"
ls -lh | grep -E "data|logs|backups"

echo ""
echo -e "${GREEN}✅ Готово!${NC}"
echo -e "${YELLOW}💡 Теперь можно запустить: make prod-start${NC}"
