# 📜 Скрипты автоматизации

Эта папка содержит полезные скрипты для управления ботом.

---

## 🔄 Обновление и обслуживание

### update_bot.sh
**Автоматическое обновление бота на сервере**

```bash
bash scripts/update_bot.sh
```

**Что делает:**
- Создаёт backup базы данных
- Получает обновления из Git
- Пересобирает Docker образ
- Применяет миграции БД
- Перезапускает бота
- Показывает логи и статус

**Когда использовать:**
- После внесения изменений в код
- При получении обновлений из репозитория
- Для обновления зависимостей

---

### diagnose_update.sh
**Диагностика проблем с обновлением**

```bash
bash scripts/diagnose_update.sh
```

**Что проверяет:**
- Состояние Git репозитория
- Docker образы и контейнеры
- Конфигурацию .env
- Логи на ошибки
- Redis и БД
- Использование ресурсов
- Systemd сервис

**Когда использовать:**
- Бот не обновляется
- Появились непонятные ошибки
- Нужно понять текущее состояние

---

## 🗄️ База данных

### backup_db.py
**Резервное копирование базы данных**

```bash
python scripts/backup_db.py
```

**Параметры:**
- Автоматически сохраняет в `backups/`
- Имя файла с timestamp
- Сжатие не используется (SQLite уже эффективен)

**Автоматизация:**
```bash
# Ежедневный backup в 2:00
crontab -e
# Добавьте:
0 2 * * * cd ~/telegram_repair_bot && python scripts/backup_db.py
```

---

### export_db.py
**Экспорт данных в JSON**

```bash
python scripts/export_db.py
```

**Когда использовать:**
- Миграция на другой сервер
- Создание читаемого дампа
- Анализ данных

---

### import_db.py
**Импорт данных из JSON**

```bash
python scripts/import_db.py db_export_20251015.json
```

**Особенности:**
- Использует `INSERT OR REPLACE` (обновляет существующие записи)
- Создаёт backup перед импортом (флаг `--backup`)

---

### check_database.py
**Проверка состояния базы данных**

```bash
python scripts/check_database.py
```

**Что показывает:**
- Список таблиц
- Количество записей
- Структуру таблиц
- Проблемы (если есть)

---

## 🚀 Деплой

### deploy_to_vps.sh
**Деплой проекта на VPS сервер**

```bash
bash scripts/deploy_to_vps.sh 192.168.1.100 root
```

**Параметры:**
- `IP` - IP адрес сервера
- `user` - пользователь SSH (обычно root)

**Что делает:**
- Проверяет подключение
- Создаёт backup
- Синхронизирует файлы (rsync)
- Передаёт .env и БД
- Настраивает права доступа

---

### deploy_prod.sh
**Production деплой (локально)**

```bash
bash scripts/deploy_prod.sh
```

**Использование:**
- На самом сервере (не локально)
- Проверяет конфигурацию
- Собирает и запускает контейнеры

---

### setup_vps.sh
**Первоначальная настройка VPS**

```bash
bash scripts/setup_vps.sh
```

**Что устанавливает:**
- Docker и Docker Compose
- Git
- Необходимые утилиты
- Настраивает пользователя

**Когда использовать:**
- Первый запуск на новом сервере
- После переустановки ОС

---

## 📊 Отчёты

### orders_report.py
**Генерация отчётов по заказам**

```bash
python scripts/orders_report.py --period daily
python scripts/orders_report.py --period weekly
python scripts/orders_report.py --period monthly
```

**Параметры:**
- `--period` - период отчёта (daily/weekly/monthly)
- `--format` - формат (txt/xlsx)
- `--output` - путь для сохранения

---

### view_order_reports.py
**Просмотр существующих отчётов**

```bash
python scripts/view_order_reports.py
```

**Показывает:**
- Список всех отчётов
- Краткую статистику
- Доступные форматы

---

## 🔧 Утилиты

### sync_roles_from_env.py
**Синхронизация ролей из .env в БД**

```bash
python scripts/sync_roles_from_env.py
```

**Когда использовать:**
- После изменения ADMIN_IDS/DISPATCHER_IDS в .env
- Для синхронизации ролей
- При миграции данных

---

## 📝 Миграции

### migrate.sh
**Применение миграций Alembic**

```bash
bash scripts/migrate.sh
```

**Команды:**
- `migrate.sh upgrade` - Применить миграции
- `migrate.sh downgrade` - Откатить миграции
- `migrate.sh history` - История миграций
- `migrate.sh current` - Текущая версия

---

## 🔐 Права доступа

Все `.sh` скрипты должны быть исполняемыми:

```bash
# Сделать все скрипты исполняемыми
chmod +x scripts/*.sh

# Или по отдельности
chmod +x scripts/update_bot.sh
chmod +x scripts/diagnose_update.sh
```

---

## 🐍 Python скрипты

Python скрипты НЕ требуют `chmod +x`, запускаются через:

```bash
python scripts/script_name.py
```

Или в Docker контейнере:

```bash
docker compose -f docker/docker-compose.prod.yml exec bot python scripts/script_name.py
```

---

## 📋 Использование в production

### Ежедневные задачи

```bash
# Утренняя проверка
bash scripts/diagnose_update.sh

# Backup БД
docker compose -f docker/docker-compose.prod.yml exec bot python scripts/backup_db.py

# Проверка БД
docker compose -f docker/docker-compose.prod.yml exec bot python scripts/check_database.py
```

### При обновлении

```bash
# Автоматическое обновление
bash scripts/update_bot.sh

# Или вручную
git pull origin main
docker compose -f docker/docker-compose.prod.yml build --no-cache
docker compose -f docker/docker-compose.prod.yml up -d
```

### Мониторинг

```bash
# Создайте cron задачи
crontab -e

# Ежедневный backup в 2:00
0 2 * * * cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml exec -T bot python scripts/backup_db.py

# Еженедельный отчёт в понедельник 9:00
0 9 * * 1 cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml exec -T bot python scripts/orders_report.py --period weekly

# Ежемесячный отчёт 1-го числа в 10:00
0 10 1 * * cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml exec -T bot python scripts/orders_report.py --period monthly
```

---

## 🆘 Troubleshooting

### Скрипт не запускается

```bash
# Проверьте права
ls -la scripts/*.sh

# Сделайте исполняемым
chmod +x scripts/your_script.sh

# Проверьте окончания строк (Windows vs Linux)
dos2unix scripts/your_script.sh  # Если установлен dos2unix
```

### Python модуль не найден

```bash
# Убедитесь, что используете правильное окружение
# В Docker:
docker compose -f docker/docker-compose.prod.yml exec bot python scripts/your_script.py

# Локально (в venv):
source venv/bin/activate
python scripts/your_script.py
```

### Permission denied для БД

```bash
# Исправьте права
chmod 644 data/bot_database.db
chown $USER:$USER data/bot_database.db
```

---

## 📚 Дополнительная документация

- [Руководство по обновлению](../docs/troubleshooting/BOT_UPDATE_ISSUES.md)
- [Troubleshooting](../docs/troubleshooting/)
- [Deployment](../docs/deployment/)

---

**Последнее обновление:** 15 октября 2025
**Версия:** 1.0
