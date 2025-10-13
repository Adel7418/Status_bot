#!/bin/bash

# ========================================
# Скрипт для первоначальной настройки VPS
# Запускать ВНУТРИ VPS сервера
# Использование: ./setup_vps.sh
# ========================================

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_info "=========================================="
print_info "🔧 Настройка VPS для Telegram Bot"
print_info "=========================================="
echo ""

# Проверка прав суперпользователя
if [ "$EUID" -eq 0 ]; then 
    print_warning "Скрипт запущен от root"
    IS_ROOT=true
else
    print_info "Скрипт запущен от пользователя $USER"
    IS_ROOT=false
fi

# Шаг 1: Обновление системы
print_info "Шаг 1/6: Обновление системы..."
if [ "$IS_ROOT" = true ]; then
    apt update && apt upgrade -y
else
    sudo apt update && sudo apt upgrade -y
fi
print_success "Система обновлена"

# Шаг 2: Установка базовых утилит
print_info "Шаг 2/6: Установка базовых утилит..."
if [ "$IS_ROOT" = true ]; then
    apt install -y git curl wget nano htop net-tools
else
    sudo apt install -y git curl wget nano htop net-tools
fi
print_success "Базовые утилиты установлены"

# Шаг 3: Установка Docker
print_info "Шаг 3/6: Установка Docker..."

# Проверка, установлен ли Docker
if command -v docker &> /dev/null; then
    print_warning "Docker уже установлен (версия $(docker --version))"
else
    print_info "Установка Docker..."
    
    # Удаление старых версий
    if [ "$IS_ROOT" = true ]; then
        apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    else
        sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    fi
    
    # Установка зависимостей
    if [ "$IS_ROOT" = true ]; then
        apt install -y ca-certificates curl gnupg lsb-release
    else
        sudo apt install -y ca-certificates curl gnupg lsb-release
    fi
    
    # Добавление официального GPG ключа Docker
    if [ "$IS_ROOT" = true ]; then
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
    else
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
    fi
    
    # Добавление репозитория
    if [ "$IS_ROOT" = true ]; then
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    else
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    fi
    
    # Установка Docker
    if [ "$IS_ROOT" = true ]; then
        apt update
        apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    else
        sudo apt update
        sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi
    
    print_success "Docker установлен"
fi

# Проверка версии
docker --version
docker compose version

# Шаг 4: Настройка Docker для пользователя
print_info "Шаг 4/6: Настройка Docker для пользователя..."
if [ "$IS_ROOT" = false ]; then
    if groups $USER | grep &>/dev/null '\bdocker\b'; then
        print_warning "Пользователь $USER уже в группе docker"
    else
        sudo usermod -aG docker $USER
        print_success "Пользователь $USER добавлен в группу docker"
        print_warning "⚠️  ВАЖНО: Необходимо выйти и зайти заново для применения изменений группы!"
        print_info "Выполните: exit, затем снова подключитесь по SSH"
    fi
fi

# Шаг 5: Создание директории для проекта
print_info "Шаг 5/6: Создание директории для проекта..."
mkdir -p ~/telegram_repair_bot/{data,logs,backups}
print_success "Директории созданы в ~/telegram_repair_bot"

# Шаг 6: Настройка firewall (опционально)
print_info "Шаг 6/6: Настройка firewall..."
if command -v ufw &> /dev/null; then
    if [ "$IS_ROOT" = true ]; then
        # Разрешить SSH
        ufw allow OpenSSH
        # Включить firewall
        ufw --force enable
        ufw status
    else
        sudo ufw allow OpenSSH 2>/dev/null || true
        sudo ufw --force enable 2>/dev/null || true
        sudo ufw status
    fi
    print_success "Firewall настроен"
else
    print_warning "ufw не установлен (firewall не настроен)"
fi

# Итоговая информация
echo ""
print_success "=========================================="
print_success "✅ VPS настроен успешно!"
print_success "=========================================="
echo ""
print_info "📋 Установленное ПО:"
echo "  • Git: $(git --version)"
echo "  • Docker: $(docker --version)"
echo "  • Docker Compose: $(docker compose version)"
echo ""
print_info "📂 Директория проекта: ~/telegram_repair_bot"
echo ""
print_warning "⚠️  ВАЖНО:"
if [ "$IS_ROOT" = false ]; then
    echo "1. Если добавлялись права Docker, выполните:"
    echo "   exit"
    echo "   (затем подключитесь заново по SSH)"
    echo ""
fi
echo "2. Следующий шаг: перенос файлов проекта"
echo "   • Используйте скрипт deploy_to_vps.sh с локальной машины"
echo "   • Или клонируйте из GitHub:"
echo "     git clone https://github.com/Adel7418/Status_bot.git ~/telegram_repair_bot"
echo ""
print_info "📖 Полное руководство: DEPLOY_VPS_LINUX_GUIDE.md"
echo ""

