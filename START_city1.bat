@echo off
REM Запуск только первого бота (city1)
docker-compose -f docker\docker-compose.multibot.yml up -d --build bot_city1
echo bot_city1 started
