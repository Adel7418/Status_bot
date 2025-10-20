# 💾 Backup и Деплой на сервер - Полная инструкция

## ⚡ Быстрые команды для сервера

### Backup БД:
```bash
cd ~/telegram_repair_bot
make prod-backup
```

Или вручную:
```bash
docker exec telegram_repair_bot_prod python scripts/backup_db.py
docker exec telegram_repair_bot_prod ls -lh /app/backups/
docker cp telegram_repair_bot_prod:/app/backups/. ~/telegram_repair_bot/backups/
```

### Деплой с backup:
```bash
cd ~/telegram_repair_bot

# 1. Backup (ОБЯЗАТЕЛЬНО!)
make prod-backup

# 2. Обновить код
git pull origin main

# 3. Пересобрать и запустить
make prod-deploy
```

---

## 📋 Детальные инструкции

### 1. Backup на сервере с Docker

#### Проверить контейнеры:
```bash
docker ps
```

Должны быть запущены:
- `telegram_repair_bot_prod` (бот)
- `telegram_bot_redis_prod` (redis)

#### Создать backup:
```bash
# Прямая команда
docker exec telegram_repair_bot_prod python scripts/backup_db.py

# Проверить
docker exec telegram_repair_bot_prod ls -lh /app/backups/

# Скопировать на хост
mkdir -p ~/telegram_repair_bot/backups
docker cp telegram_repair_bot_prod:/app/backups/. ~/telegram_repair_bot/backups/
```

---

### 2. Откат git pull

Если нужно вернуться назад:

```bash
# К предыдущему состоянию
git reset --hard ORIG_HEAD

# Или к конкретному коммиту
git reflog
git reset --hard HEAD@{1}
```

---

### 3. Деплой на production

#### Полный деплой:
```bash
cd ~/telegram_repair_bot

# Используйте готовую команду
make prod-deploy
```

Эта команда делает:
1. ✅ Получает код
2. ✅ Пересобирает образ
3. ✅ Перезапускает контейнеры

#### Деплой с миграциями:
```bash
cd ~/telegram_repair_bot

# 1. Backup
docker exec telegram_repair_bot_prod python scripts/backup_db.py

# 2. Остановить
make prod-stop

# 3. Обновить код
git pull origin main

# 4. Миграции
make prod-migrate

# 5. Запустить
make prod-deploy
```

---

### 4. Проблемы и решения

#### Ошибка "can't cd to docker":
Выполняйте команды из корня проекта:
```bash
cd ~/telegram_repair_bot
```

#### Контейнер не запущен:
```bash
docker compose -f docker/docker-compose.prod.yml up -d
```

#### make команды не работают:
Используйте прямые docker команды:
```bash
# Backup
docker exec telegram_repair_bot_prod python scripts/backup_db.py

# Перезапуск
docker compose -f docker/docker-compose.prod.yml restart bot

# Логи
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

---

### 5. Отладка

#### Проверить скрипт в контейнере:
```bash
docker exec telegram_repair_bot_prod ls -la scripts/
```

#### Проверить БД:
```bash
docker exec telegram_repair_bot_prod ls -la /app/data/
docker exec telegram_repair_bot_prod printenv DATABASE_PATH
```

#### Войти в контейнер:
```bash
docker exec -it telegram_repair_bot_prod bash
# Внутри:
python scripts/backup_db.py
ls -lh /app/backups/
exit
```

---

## ✅ Чек-лист деплоя

- [ ] Backup БД создан
- [ ] Код обновлён (git pull)
- [ ] Миграции выполнены (если есть)
- [ ] Контейнеры перезапущены
- [ ] Логи проверены (нет ошибок)
- [ ] Бот отвечает в Telegram

---

## 🚀 Готовые команды Make

```bash
make prod-backup      # Backup БД
make prod-stop        # Остановить контейнеры
make prod-migrate     # Миграции
make prod-restart     # Перезапуск
make prod-deploy      # Полный деплой
make prod-logs        # Логи
```

---

## ⚠️ ВАЖНО!

**ВСЕГДА делайте backup ПЕРЕД обновлением!**

```bash
# Правильно:
backup → git pull → миграции → restart

# Неправильно:
git pull → backup → миграции
```

