@echo off
chcp 65001 >nul
title Telegram Repair Bot

echo ====================================
echo   Telegram Repair Bot - Запуск
echo ====================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python 3.8 или выше с https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python найден
echo.

REM Проверка зависимостей
echo Проверка зависимостей...
pip show aiogram >nul 2>&1
if errorlevel 1 (
    echo [ВНИМАНИЕ] Зависимости не установлены!
    echo Установка зависимостей...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось установить зависимости!
        pause
        exit /b 1
    )
)

echo [OK] Зависимости установлены
echo.

REM Проверка .env файла
if not exist ".env" (
    echo [ВНИМАНИЕ] Файл .env не найден!
    echo Создайте файл .env по образцу .env.example
    echo и заполните необходимые параметры.
    pause
    exit /b 1
)

echo [OK] Конфигурация найдена
echo.
echo ====================================
echo Запуск бота...
echo ====================================
echo.

python bot.py

if errorlevel 1 (
    echo.
    echo ====================================
    echo [ОШИБКА] Бот остановлен с ошибкой!
    echo Проверьте логи в файле bot.log
    echo ====================================
    pause
)
