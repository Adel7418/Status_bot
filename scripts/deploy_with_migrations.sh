#!/bin/bash

# Скрипт для деплоя с правильным применением миграций
# Использует лучшие практики Alembic

set -e  # Останавливаем выполнение при ошибке

echo "🚀 Начинаем деплой с применением миграций..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Останавливаем бота
print_status "Останавливаем бота..."
docker compose -f docker/docker-compose.prod.yml stop bot

# 2. Обновляем код из репозитория
print_status "Обновляем код из репозитория..."
git pull origin main

# 3. Пересобираем контейнер
print_status "Пересобираем контейнер с обновленным кодом..."
docker compose -f docker/docker-compose.prod.yml build bot

# 4. Запускаем контейнер для применения миграций
print_status "Запускаем контейнер для применения миграций..."
docker compose -f docker/docker-compose.prod.yml up -d bot

# 5. Ждем запуска контейнера
print_status "Ждем запуска контейнера..."
sleep 5

# 6. Проверяем, что контейнер запущен
if ! docker compose -f docker/docker-compose.prod.yml ps bot | grep -q "Up"; then
    print_error "Контейнер бота не запущен!"
    exit 1
fi

print_success "Контейнер запущен"

# 7. Применяем миграции
print_status "Применяем миграции..."

# Сначала пытаемся через Alembic
print_status "Пытаемся применить миграции через Alembic..."
if docker compose -f docker/docker-compose.prod.yml exec bot alembic upgrade head; then
    print_success "Миграции успешно применены через Alembic!"
else
    print_warning "Alembic не сработал, применяем миграции через Python скрипт..."

    # Применяем миграции через Python скрипт
    if docker compose -f docker/docker-compose.prod.yml exec bot python scripts/fix_migrations_prod.py; then
        print_success "Миграции успешно применены через Python скрипт!"
    else
        print_error "Не удалось применить миграции!"
        exit 1
    fi
fi

# 8. Перезапускаем бота
print_status "Перезапускаем бота..."
docker compose -f docker/docker-compose.prod.yml restart bot

# 9. Ждем запуска
print_status "Ждем запуска бота..."
sleep 5

# 10. Проверяем логи
print_status "Проверяем логи бота..."
docker compose -f docker/docker-compose.prod.yml logs --tail=20 bot

# 11. Проверяем статус
print_status "Проверяем статус контейнеров..."
docker compose -f docker/docker-compose.prod.yml ps

print_success "🎉 Деплой завершен успешно!"
print_status "Бот должен быть доступен и отчеты должны работать корректно."
