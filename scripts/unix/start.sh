#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "===================================="
echo "  Telegram Repair Bot - Запуск"
echo "===================================="
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ОШИБКА]${NC} Python3 не найден!"
    echo "Установите Python 3.8 или выше"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Python3 найден"
echo ""

# Проверка зависимостей
echo "Проверка зависимостей..."
if ! python3 -c "import aiogram" &> /dev/null; then
    echo -e "${YELLOW}[ВНИМАНИЕ]${NC} Зависимости не установлены!"
    echo "Установка зависимостей..."
    pip3 install -r requirements.txt

    if [ $? -ne 0 ]; then
        echo -e "${RED}[ОШИБКА]${NC} Не удалось установить зависимости!"
        exit 1
    fi
fi

echo -e "${GREEN}[OK]${NC} Зависимости установлены"
echo ""

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo -e "${RED}[ОШИБКА]${NC} Файл .env не найден!"
    echo "Создайте файл .env по образцу .env.example"
    echo "и заполните необходимые параметры."
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Конфигурация найдена"
echo ""
echo "===================================="
echo "Запуск бота..."
echo "===================================="
echo ""

# Запуск бота
python3 bot.py

if [ $? -ne 0 ]; then
    echo ""
    echo "===================================="
    echo -e "${RED}[ОШИБКА]${NC} Бот остановлен с ошибкой!"
    echo "Проверьте логи в файле bot.log"
    echo "===================================="
    exit 1
fi
