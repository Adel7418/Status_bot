# ⚡ Минимальный workflow (без автоматизации)

## ❓ Важный вопрос: Git Pull удаляет файлы?

**ДА!** Когда вы удаляете файлы локально, коммитите и пушите, то при `git pull` на сервере эти файлы **тоже удалятся**.

**Пример:**
```bash
# Локально (Cursor)
rm ненужный_файл.txt
git add -A
git commit -m "удален ненужный файл"
git push origin main

# На сервере
git pull origin main
# ← ненужный_файл.txt будет удален и здесь!
```

**Это безопасно и правильно!** Git синхронизирует состояние файлов между машинами.

---

## 🎯 Ваш простой процесс

### 1. Локальная разработка

```bash
# В Cursor
# Работаете над кодом...

# Тестирование (опционально)
make test
make lint

# Запуск локально с тестовым токеном (опционально)
make run

# Фиксация изменений
git add .
git commit -m "feat: описание изменений"
git push origin main
```

### 2. Обновление на сервере

```bash
# SSH на сервер
ssh root@ваш-IP

# Обновление (одна строка)
cd ~/telegram_repair_bot && git pull && cd docker && docker compose -f docker-compose.prod.yml restart

# Проверка логов
docker compose -f docker-compose.prod.yml logs --tail=50 bot
```

**Готово!** Это всё что нужно.

---

## 💾 Backup БД (рекомендуется периодически)

```bash
# На сервере
cd ~/telegram_repair_bot
cp data/bot_database.db data/backups/bot_database_$(date +%Y%m%d_%H%M%S).db

# Или через Docker
docker compose -f docker/docker-compose.prod.yml exec bot \
  python scripts/backup_db.py
```

---

## 🔧 Полезные команды на сервере

```bash
# Перезапуск бота
cd ~/telegram_repair_bot/docker
docker compose -f docker-compose.prod.yml restart

# Полная пересборка (если изменились зависимости)
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build

# Логи
docker compose -f docker-compose.prod.yml logs -f bot
docker compose -f docker-compose.prod.yml logs --tail=100 bot

# Статус
docker compose -f docker-compose.prod.yml ps

# Проверка БД
ls -lh ../data/bot_database.db
```

---

## 🔄 Откат при проблемах

```bash
# На сервере
cd ~/telegram_repair_bot
git log --oneline -10
git reset --hard <commit-hash>
cd docker
docker compose -f docker-compose.prod.yml restart
```

---

## 📝 Шпаргалка команд

### Локально:
```bash
make test          # Тесты
make lint          # Проверка кода
make run           # Запуск бота
git push           # Отправка в GitHub
```

### На сервере (одна команда):
```bash
cd ~/telegram_repair_bot && git pull && cd docker && docker compose -f docker-compose.prod.yml restart
```

### Или по шагам:
```bash
ssh root@IP
cd ~/telegram_repair_bot
git pull origin main
cd docker
docker compose -f docker-compose.prod.yml restart
docker compose -f docker-compose.prod.yml logs -f bot
```

---

## 🎯 Итого

**Ваш workflow:**
```
Разработка → git push → SSH на сервер → git pull + restart → Готово
```

**Не нужны:**
- ❌ Скрипты деплоя (deploy_prod.sh и т.д.)
- ❌ SSH с локальной машины (если вы SSH вручную)
- ❌ Переменная SSH_SERVER
- ❌ Makefile команды для деплоя
- ❌ Staging на сервере

**Нужны только:**
- ✅ Git
- ✅ SSH доступ к серверу
- ✅ Docker на сервере
- ✅ Знание 2-3 команд

---

**Это самый простой и понятный подход!** ✅

