# 🔄 Проблемы с обновлением бота на сервере

**Дата:** 15 октября 2025  
**Статус:** Руководство по решению проблем обновления

---

## 📋 Содержание

1. [Основные причины](#основные-причины)
2. [Быстрая диагностика](#быстрая-диагностика)
3. [Пошаговое решение](#пошаговое-решение)
4. [Правильная процедура обновления](#правильная-процедура-обновления)
5. [Частые ошибки](#частые-ошибки)
6. [Проверка успешного обновления](#проверка-успешного-обновления)

---

## Основные причины

### 1. ❌ Код не передан на сервер

**Симптомы:**
- Бот работает, но использует старую версию кода
- Новые функции не работают
- Исправленные баги все еще присутствуют

**Причина:**
Вы внесли изменения локально, но не передали их на сервер через `git pull` или `rsync`.

**Проверка:**
```bash
# На сервере
cd ~/telegram_repair_bot

# Проверьте последний коммит
git log -1

# Сравните с локальной версией
git status
git diff origin/main
```

**Решение:**
```bash
# На сервере
cd ~/telegram_repair_bot

# Получить последние изменения
git pull origin main

# Или если используете прямую передачу файлов
# На локальной машине:
bash scripts/deploy_to_vps.sh ваш_IP root
```

---

### 2. 🐳 Docker контейнер не пересобран

**Симптомы:**
- Код обновлен, но бот работает по-старому
- `git pull` выполнен успешно
- Изменения видны в файлах, но не применяются

**Причина:**
Docker использует закэшированный образ. Контейнер нужно пересобрать.

**Проверка:**
```bash
# Проверка времени создания образа
docker images | grep telegram_repair_bot

# Проверка запущенного контейнера
docker ps | grep telegram_repair_bot_prod
```

**Решение:**
```bash
cd ~/telegram_repair_bot

# Остановка контейнера
docker compose -f docker/docker-compose.prod.yml down

# Пересборка образа (БЕЗ кэша!)
docker compose -f docker/docker-compose.prod.yml build --no-cache

# Запуск
docker compose -f docker/docker-compose.prod.yml up -d

# Проверка логов
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

---

### 3. 🔄 Контейнер не перезапущен

**Симптомы:**
- Код обновлен
- Образ пересобран
- Но бот все равно старый

**Причина:**
Старый контейнер все еще работает. Docker Compose видит, что контейнер запущен, и не пересоздает его.

**Решение:**
```bash
cd ~/telegram_repair_bot

# Полная остановка и удаление контейнеров
docker compose -f docker/docker-compose.prod.yml down

# Проверка, что контейнеры удалены
docker ps -a | grep telegram

# Запуск заново
docker compose -f docker/docker-compose.prod.yml up -d
```

---

### 4. 💾 Проблемы с Docker volumes

**Симптомы:**
- База данных не обновляется
- Логи старые
- Конфигурация не меняется

**Причина:**
Docker volumes хранят старые данные и не обновляются автоматически.

**Проверка:**
```bash
# Список volumes
docker volume ls | grep bot

# Проверка содержимого
docker volume inspect telegram_repair_bot_bot_data
```

**Решение (ОСТОРОЖНО - удаляет данные!):**
```bash
# Только если вы уверены и сделали backup!

# 1. Остановка
docker compose -f docker/docker-compose.prod.yml down

# 2. Создание backup БД
docker compose -f docker/docker-compose.prod.yml run --rm bot python backup_db.py

# 3. Удаление volumes (ОПАСНО!)
docker compose -f docker/docker-compose.prod.yml down -v

# 4. Запуск (создаст новые volumes)
docker compose -f docker/docker-compose.prod.yml up -d
```

**Безопасное решение:**
```bash
# Обновление только кода, без удаления volumes
docker compose -f docker/docker-compose.prod.yml down
docker compose -f docker/docker-compose.prod.yml build --no-cache
docker compose -f docker/docker-compose.prod.yml up -d --force-recreate
```

---

### 5. 📝 .env файл не обновлен

**Симптомы:**
- Новые переменные окружения не работают
- Бот использует старые настройки
- Ошибки о недостающих переменных

**Причина:**
В новой версии добавлены новые переменные в `.env`, но вы не обновили файл на сервере.

**Проверка:**
```bash
# На сервере
cat ~/telegram_repair_bot/.env

# Сравните с локальным env.example
cat ~/telegram_repair_bot/env.example
```

**Решение:**
```bash
# На сервере
cd ~/telegram_repair_bot

# Редактирование .env
nano .env

# Добавьте недостающие переменные из env.example
# Сохраните: Ctrl+O, Enter, Ctrl+X

# Перезапуск бота
docker compose -f docker/docker-compose.prod.yml restart bot
```

---

### 6. 🗄️ Миграции базы данных не применены

**Симптомы:**
- Ошибки при работе с БД
- Новые поля таблиц не существуют
- SQLite errors в логах

**Причина:**
Новая версия требует изменений в структуре БД, но миграции не запущены.

**Проверка:**
```bash
# Проверка логов на ошибки БД
docker compose -f docker/docker-compose.prod.yml logs bot | grep -i "column\|table\|database"
```

**Решение:**
```bash
cd ~/telegram_repair_bot

# Применение миграций
docker compose -f docker/docker-compose.prod.yml exec bot alembic upgrade head

# Или если контейнер не запущен
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# Перезапуск
docker compose -f docker/docker-compose.prod.yml restart bot
```

---

### 7. 🔧 Systemd сервис блокирует обновление

**Симптомы:**
- Контейнеры автоматически перезапускаются со старой версией
- После `down` контейнеры снова поднимаются

**Причина:**
Systemd сервис автоматически запускает бота и перезаписывает ваши изменения.

**Проверка:**
```bash
# Проверка статуса сервиса
sudo systemctl status telegram-bot
```

**Решение:**
```bash
# 1. Остановка сервиса
sudo systemctl stop telegram-bot

# 2. Обновление бота вручную
cd ~/telegram_repair_bot
git pull origin main
docker compose -f docker/docker-compose.prod.yml build --no-cache
docker compose -f docker/docker-compose.prod.yml up -d

# 3. Перезапуск сервиса (если нужен автозапуск)
sudo systemctl start telegram-bot
```

---

### 8. 🔒 Проблемы с правами доступа

**Симптомы:**
- Permission denied при git pull
- Не удается изменить файлы
- Docker не может записать в volumes

**Проверка:**
```bash
# Проверка владельца файлов
ls -la ~/telegram_repair_bot/

# Проверка текущего пользователя
whoami

# Проверка групп пользователя
groups
```

**Решение:**
```bash
# Изменение владельца (замените username на вашего пользователя)
sudo chown -R $USER:$USER ~/telegram_repair_bot/

# Права на директории
chmod 755 ~/telegram_repair_bot/data
chmod 755 ~/telegram_repair_bot/logs
chmod 755 ~/telegram_repair_bot/backups

# Права на .env
chmod 600 ~/telegram_repair_bot/.env

# Проверка прав Docker
sudo usermod -aG docker $USER
newgrp docker
```

---

### 9. 🌐 Проблемы с Redis

**Симптомы:**
- Бот не сохраняет состояния
- FSM не работает
- Redis errors в логах

**Проверка:**
```bash
# Проверка Redis контейнера
docker ps | grep redis

# Проверка логов Redis
docker compose -f docker/docker-compose.prod.yml logs redis

# Подключение к Redis
docker compose -f docker/docker-compose.prod.yml exec redis redis-cli ping
```

**Решение:**
```bash
# Перезапуск Redis
docker compose -f docker/docker-compose.prod.yml restart redis

# Или полный перезапуск всех сервисов
docker compose -f docker/docker-compose.prod.yml restart

# Очистка Redis (если нужно)
docker compose -f docker/docker-compose.prod.yml exec redis redis-cli FLUSHALL
```

---

### 10. 📦 Кэш Python пакетов

**Симптомы:**
- Новые зависимости не установлены
- Ошибки импорта новых модулей
- ModuleNotFoundError

**Причина:**
Docker использует кэшированный слой с установленными пакетами.

**Решение:**
```bash
cd ~/telegram_repair_bot

# Пересборка БЕЗ кэша
docker compose -f docker/docker-compose.prod.yml build --no-cache

# Или удаление старого образа и пересборка
docker rmi telegram_repair_bot_bot:latest
docker compose -f docker/docker-compose.prod.yml build
docker compose -f docker/docker-compose.prod.yml up -d
```

---

## Быстрая диагностика

Запустите эту команду для полной диагностики:

```bash
#!/bin/bash
echo "=== ДИАГНОСТИКА ОБНОВЛЕНИЯ БОТА ==="
echo ""

echo "1. Последний коммит в репозитории:"
cd ~/telegram_repair_bot && git log -1 --oneline
echo ""

echo "2. Статус Git:"
git status -s
echo ""

echo "3. Docker образы:"
docker images | grep -E "REPOSITORY|telegram"
echo ""

echo "4. Запущенные контейнеры:"
docker ps | grep -E "CONTAINER|telegram"
echo ""

echo "5. Последние логи бота:"
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml logs --tail=20 bot
echo ""

echo "6. Проверка .env (без секретов):"
cat ~/telegram_repair_bot/.env | grep -v "TOKEN\|PASSWORD" | head -10
echo ""

echo "7. Systemd сервис:"
sudo systemctl status telegram-bot 2>/dev/null || echo "Сервис не настроен"
echo ""
```

Сохраните в файл `diagnose_update.sh`, сделайте исполняемым и запустите:

```bash
chmod +x diagnose_update.sh
./diagnose_update.sh
```

---

## Правильная процедура обновления

### ✅ Полная процедура обновления (рекомендуется)

```bash
# 1. Подключение к серверу
ssh user@ваш_IP

# 2. Переход в директорию
cd ~/telegram_repair_bot

# 3. Создание backup БД (ВАЖНО!)
docker compose -f docker/docker-compose.prod.yml exec bot python backup_db.py
# Или
mkdir -p backups
cp data/bot_database.db backups/bot_database_$(date +%Y%m%d_%H%M%S).db

# 4. Остановка сервиса (если используется)
sudo systemctl stop telegram-bot

# 5. Остановка контейнеров
docker compose -f docker/docker-compose.prod.yml down

# 6. Получение обновлений
git pull origin main

# 7. Обновление .env (если нужно)
nano .env
# Добавьте новые переменные из env.example

# 8. Пересборка образа БЕЗ кэша
docker compose -f docker/docker-compose.prod.yml build --no-cache

# 9. Применение миграций БД (если есть)
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head

# 10. Запуск контейнеров
docker compose -f docker/docker-compose.prod.yml up -d

# 11. Проверка логов
docker compose -f docker/docker-compose.prod.yml logs -f bot

# 12. Проверка статуса
docker compose -f docker/docker-compose.prod.yml ps

# 13. Тест в Telegram
# Отправьте /start боту

# 14. Запуск сервиса (если используется)
sudo systemctl start telegram-bot
```

---

### ⚡ Быстрая процедура (для небольших изменений)

```bash
cd ~/telegram_repair_bot
git pull origin main
docker compose -f docker/docker-compose.prod.yml restart bot
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

⚠️ **Внимание:** Быстрая процедура НЕ пересобирает образ и НЕ применяет миграции!

---

### 🔄 Через автоматический скрипт

Создайте скрипт обновления:

```bash
nano ~/update_bot.sh
```

Содержимое:

```bash
#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== ОБНОВЛЕНИЕ БОТА ===${NC}"

# Backup
echo -e "${YELLOW}Создание backup...${NC}"
cd ~/telegram_repair_bot
BACKUP_FILE="backups/bot_database_$(date +%Y%m%d_%H%M%S).db"
mkdir -p backups
docker compose -f docker/docker-compose.prod.yml exec -T bot cp /app/data/bot_database.db /app/backups/backup.db 2>/dev/null || cp data/bot_database.db "$BACKUP_FILE"
echo -e "${GREEN}✓ Backup: $BACKUP_FILE${NC}"

# Stop
echo -e "${YELLOW}Остановка контейнеров...${NC}"
docker compose -f docker/docker-compose.prod.yml down

# Update code
echo -e "${YELLOW}Получение обновлений...${NC}"
git pull origin main

# Build
echo -e "${YELLOW}Пересборка образа...${NC}"
docker compose -f docker/docker-compose.prod.yml build --no-cache

# Migrations
echo -e "${YELLOW}Применение миграций...${NC}"
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head || echo "Миграции не требуются"

# Start
echo -e "${YELLOW}Запуск контейнеров...${NC}"
docker compose -f docker/docker-compose.prod.yml up -d

# Wait
echo -e "${YELLOW}Ожидание запуска...${NC}"
sleep 5

# Check
echo -e "${YELLOW}Проверка статуса...${NC}"
docker compose -f docker/docker-compose.prod.yml ps

echo -e "${GREEN}=== ОБНОВЛЕНИЕ ЗАВЕРШЕНО ===${NC}"
echo -e "${YELLOW}Проверьте логи: docker compose -f docker/docker-compose.prod.yml logs -f bot${NC}"
```

Использование:

```bash
chmod +x ~/update_bot.sh
~/update_bot.sh
```

---

## Частые ошибки

### Ошибка 1: "Cannot connect to Docker daemon"

```bash
# Запуск Docker
sudo systemctl start docker

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### Ошибка 2: "port is already allocated"

```bash
# Проверка занятых портов
sudo netstat -tulpn | grep :8080

# Остановка конфликтующего контейнера
docker ps
docker stop <container_id>
```

### Ошибка 3: "database is locked"

```bash
# Остановка всех контейнеров
docker compose -f docker/docker-compose.prod.yml down

# Удаление lock файлов
rm -f data/bot_database.db-journal
rm -f data/bot_database.db-shm
rm -f data/bot_database.db-wal

# Запуск
docker compose -f docker/docker-compose.prod.yml up -d
```

### Ошибка 4: "Permission denied"

```bash
# Исправление прав
sudo chown -R $USER:$USER ~/telegram_repair_bot/
chmod 755 ~/telegram_repair_bot/data
```

---

## Проверка успешного обновления

### 1. Проверка версии кода

```bash
# В логах должна быть актуальная версия
docker compose -f docker/docker-compose.prod.yml logs bot | grep -i version

# Или проверьте timestamp файлов
docker compose -f docker/docker-compose.prod.yml exec bot ls -la /app/bot.py
```

### 2. Проверка работы новых функций

```bash
# Отправьте команды в Telegram, которые были добавлены в обновлении
# Например, если добавили новую команду /reports, проверьте её
```

### 3. Проверка логов на ошибки

```bash
# Ошибок быть не должно
docker compose -f docker/docker-compose.prod.yml logs bot | grep -i error
docker compose -f docker/docker-compose.prod.yml logs bot | grep -i exception
```

### 4. Проверка healthcheck

```bash
# Статус должен быть healthy
docker inspect telegram_repair_bot_prod | grep -i health -A 10
```

### 5. Мониторинг ресурсов

```bash
# Проверка, что потребление ресурсов в норме
docker stats telegram_repair_bot_prod --no-stream
```

---

## 🎯 Чеклист обновления

- [ ] Создан backup базы данных
- [ ] Остановлены контейнеры (`docker compose down`)
- [ ] Получены последние изменения (`git pull`)
- [ ] Обновлен `.env` файл (если нужно)
- [ ] Пересобран образ (`build --no-cache`)
- [ ] Применены миграции БД (`alembic upgrade head`)
- [ ] Запущены контейнеры (`up -d`)
- [ ] Проверены логи (нет ошибок)
- [ ] Протестирован в Telegram (`/start`)
- [ ] Проверен healthcheck (healthy)

---

## 📞 Если ничего не помогло

### Полный сброс и переустановка

⚠️ **ВНИМАНИЕ:** Это удалит все контейнеры и образы!

```bash
# 1. ОБЯЗАТЕЛЬНО сделайте backup!
cp ~/telegram_repair_bot/data/bot_database.db ~/bot_backup_$(date +%Y%m%d).db

# 2. Полная остановка и очистка
cd ~/telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml down -v
docker system prune -a --volumes

# 3. Удаление и повторное клонирование
cd ~
mv telegram_repair_bot telegram_repair_bot_old
git clone https://github.com/Adel7418/Status_bot.git telegram_repair_bot
cd telegram_repair_bot

# 4. Настройка .env
cp env.example .env
nano .env  # Настройте все переменные

# 5. Восстановление БД
cp ~/bot_backup_*.db data/bot_database.db

# 6. Запуск
docker compose -f docker/docker-compose.prod.yml build --no-cache
docker compose -f docker/docker-compose.prod.yml up -d

# 7. Проверка
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

---

## 📚 Связанные документы

- [Руководство по деплою](../deployment/DEPLOY_VPS_LINUX_GUIDE.md)
- [Быстрые команды](../deployment/QUICK_DEPLOY_COMMANDS.md)
- [Troubleshooting](../TROUBLESHOOTING.md)
- [Docker Usage](../DOCKER_USAGE.md)

---

**Версия:** 1.0  
**Дата:** 15 октября 2025  
**Автор:** AI Assistant  

🔄 **Всегда делайте backup перед обновлением!**

