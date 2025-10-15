# 🚀 Production команды для сервера

**Быстрая справка по управлению ботом на production сервере**

---

## 📋 Обновление бота

### Вариант 1: Полное обновление (рекомендуется)

**Одна команда делает всё:**

```bash
make prod-full-update
```

**Что происходит:**
1. ✅ Создается backup БД
2. ✅ Обновляется код из GitHub
3. ✅ Пересобирается Docker образ
4. ✅ Применяются миграции БД
5. ✅ Перезапускается бот

---

### Вариант 2: Пошаговое обновление

```bash
# 1. Backup БД
make prod-backup

# 2. Обновить код из git
make prod-update

# 3. Применить миграции
make prod-migrate

# 4. Перезапустить бота
make prod-restart
```

---

## 🔄 Миграции БД

### Применить миграции

```bash
make prod-migrate
```

**Или напрямую через Docker:**

```bash
cd docker
docker-compose -f docker-compose.prod.yml run --rm bot alembic upgrade head
```

### Проверить текущую версию БД

```bash
cd docker
docker-compose -f docker-compose.prod.yml exec bot alembic current
```

### Откатить миграцию

```bash
cd docker
docker-compose -f docker-compose.prod.yml exec bot alembic downgrade -1
```

---

## 💾 Backup базы данных

### Создать backup

```bash
make prod-backup
```

**Или напрямую:**

```bash
cd docker
docker-compose -f docker-compose.prod.yml exec bot python scripts/backup_db.py
```

**Бэкапы сохраняются в:** `data/backups/`

---

## 📊 Мониторинг

### Просмотр логов

```bash
make prod-logs
```

**Или:**

```bash
cd docker
docker-compose -f docker-compose.prod.yml logs -f bot
```

### Статус контейнеров

```bash
make prod-status
```

**Или:**

```bash
cd docker
docker-compose -f docker-compose.prod.yml ps
```

---

## 🛠️ Управление ботом

### Перезапуск

```bash
make prod-restart
```

### Остановка

```bash
cd docker
docker-compose -f docker-compose.prod.yml stop
```

### Запуск

```bash
cd docker
docker-compose -f docker-compose.prod.yml start
```

### Полная перезагрузка (stop + start)

```bash
cd docker
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📝 Все команды Makefile

### Production команды

| Команда | Описание |
|---------|----------|
| `make prod-update` | Обновить код из git |
| `make prod-migrate` | Применить миграции БД |
| `make prod-backup` | Создать backup БД |
| `make prod-restart` | Перезапустить бота |
| `make prod-logs` | Показать логи |
| `make prod-status` | Статус контейнеров |
| `make prod-full-update` | **Полное обновление (всё в одной команде)** |

### Разработка

| Команда | Описание |
|---------|----------|
| `make install` | Установить зависимости |
| `make test` | Запустить тесты |
| `make lint` | Проверить код |
| `make run` | Запустить бота локально |

---

## ⚡ Быстрые сценарии

### Обновление после изменений в коде

```bash
# На вашем компьютере
git add .
git commit -m "fix: исправление бага"
git push origin main

# На сервере
make prod-full-update
```

### Применение новых миграций

```bash
# На сервере
make prod-backup
make prod-migrate
make prod-restart
```

### Откат изменений

```bash
# На сервере
cd docker
docker-compose -f docker-compose.prod.yml exec bot alembic downgrade -1
docker-compose -f docker-compose.prod.yml restart
```

---

## 🆘 Решение проблем

### Бот не запускается после обновления

```bash
# Проверить логи
make prod-logs

# Проверить статус
make prod-status

# Пересобрать образ
cd docker
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Ошибка миграции

```bash
# Откатить миграцию
cd docker
docker-compose -f docker-compose.prod.yml exec bot alembic downgrade -1

# Проверить текущую версию
docker-compose -f docker-compose.prod.yml exec bot alembic current

# Попробовать снова
make prod-migrate
```

### Восстановление из backup

```bash
# Найти backup
ls -lh data/backups/

# Остановить бота
cd docker
docker-compose -f docker-compose.prod.yml stop bot

# Восстановить БД
cp data/backups/bot_database_YYYYMMDD_HHMMSS.db bot_database.db

# Запустить бота
docker-compose -f docker-compose.prod.yml start bot
```

---

## 📖 Полная документация

- 📖 [PRODUCTION_DEPLOY.md](PRODUCTION_DEPLOY.md) - Полный деплой
- 📖 [README.md](README.md) - Основная документация
- 🔍 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Решение проблем

---

**Быстрая справка всегда под рукой!** 🚀

