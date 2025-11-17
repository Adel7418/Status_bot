@echo off
chcp 65001 >nul
title Telegram Repair Bot - Restart City1

echo ====================================
echo   Перезапуск бота City1
echo ====================================
echo.

REM Поиск и остановка процесса бота city1
echo Поиск запущенного процесса бота city1...
setlocal enabledelayedexpansion
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST 2^>nul ^| findstr /C:"PID:"') do (
    set PID=%%i
    REM Проверяем, является ли это процессом бота
    wmic process where "ProcessId=!PID!" get CommandLine 2^>nul | findstr /C:"bot.py" >nul
    if not errorlevel 1 (
        echo Остановка процесса бота (PID: !PID!)...
        taskkill /PID !PID! /F >nul 2>&1
        if errorlevel 1 (
            echo [ВНИМАНИЕ] Не удалось остановить процесс !PID!
        ) else (
            echo [OK] Процесс !PID! остановлен
        )
    )
)
endlocal

echo.
echo Ожидание завершения процессов...
timeout /t 2 /nobreak >nul

echo.
echo ====================================
echo Запуск бота city1...
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

REM Проверка файла env.city1
if not exist "env.city1" (
    echo [ОШИБКА] Файл env.city1 не найден!
    pause
    exit /b 1
)

echo [OK] Конфигурация найдена

REM Проверка BOT_TOKEN в env.city1
findstr /C:"BOT_TOKEN=" env.city1 >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] BOT_TOKEN не найден в env.city1!
    echo Добавьте строку: BOT_TOKEN=ваш_токен
    pause
    exit /b 1
)

REM Проверка, что BOT_TOKEN не пустой
for /f "tokens=2 delims==" %%a in ('findstr /C:"BOT_TOKEN=" env.city1') do set BOT_TOKEN_VALUE=%%a
if "%BOT_TOKEN_VALUE%"=="" (
    echo [ОШИБКА] BOT_TOKEN пустой в env.city1!
    echo Укажите токен бота
    pause
    exit /b 1
)

echo [OK] BOT_TOKEN настроен

REM Проверка Redis (опционально, если используется)
findstr /C:"REDIS_URL=" env.city1 >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Redis настроен, проверка подключения...
    REM Можно добавить ping к Redis, но это опционально
)

echo.

REM Запуск бота с переменной окружения ENV_FILE=env.city1
echo Запуск бота city1...
start "Telegram Repair Bot City1" /MIN cmd /c "set ENV_FILE=env.city1 && python bot.py"

if errorlevel 1 (
    echo.
    echo ====================================
    echo [ОШИБКА] Не удалось запустить бота!
    echo Проверьте логи в файле logs/city1/bot.log
    echo ====================================
    pause
    exit /b 1
) else (
    echo.
    echo ====================================
    echo [OK] Бот city1 перезапущен!
    echo ====================================
    echo.
    echo Бот запущен в отдельном окне.
    echo Для просмотра логов откройте: logs\city1\bot.log
    echo.
)

timeout /t 3 /nobreak >nul

