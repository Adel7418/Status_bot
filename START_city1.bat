@echo off
chcp 65001 >nul
set ENV_FILE=env.city1
cd /d "C:\Bot_test\telegram_repair_bot"
python bot.py
