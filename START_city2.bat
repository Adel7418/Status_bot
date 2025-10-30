@echo off
REM Запуск только второго бота (city2)
docker-compose -f docker\docker-compose.multibot.yml up -d --build bot_city2
echo bot_city2 started
