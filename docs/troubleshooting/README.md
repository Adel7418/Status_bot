# 🔧 Troubleshooting - Решение проблем

Эта папка содержит руководства по решению различных проблем с ботом.

---

## 📚 Доступные руководства

### 🔄 Проблемы с обновлением

- **[ОБНОВЛЕНИЕ_БОТА_КРАТКО.md](ОБНОВЛЕНИЕ_БОТА_КРАТКО.md)** - Краткая инструкция (начните здесь!)
  - Быстрые решения
  - Типичные проблемы
  - Команды для копирования

- **[BOT_UPDATE_ISSUES.md](BOT_UPDATE_ISSUES.md)** - Подробное руководство
  - 10 основных причин
  - Полная диагностика
  - Пошаговые решения
  - Скрипты автоматизации

---

## 🚀 Быстрый старт

### Бот не обновляется на сервере?

```bash
# Подключитесь к серверу
ssh user@ваш_IP

# Выполните автоматическое обновление
cd ~/telegram_repair_bot
bash scripts/update_bot.sh
```

### Нужна диагностика?

```bash
# Запустите полную диагностику
bash scripts/diagnose_update.sh
```

---

## 📖 Другие полезные документы

### Деплой и установка
- [DEPLOY_VPS_LINUX_GUIDE.md](../deployment/DEPLOY_VPS_LINUX_GUIDE.md) - Полное руководство по деплою
- [QUICK_DEPLOY_COMMANDS.md](../deployment/QUICK_DEPLOY_COMMANDS.md) - Быстрые команды
- [INSTALLATION.md](../INSTALLATION.md) - Установка

### Использование
- [DOCKER_USAGE.md](../DOCKER_USAGE.md) - Работа с Docker
- [DATABASE_USAGE_GUIDE.md](../DATABASE_USAGE_GUIDE.md) - Работа с БД
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Общие проблемы

### Разработка
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Участие в разработке
- [development/](../development/) - Руководства для разработчиков

---

## 🛠️ Полезные скрипты

В папке `scripts/` доступны автоматические скрипты:

- **update_bot.sh** - Автоматическое обновление бота
- **diagnose_update.sh** - Диагностика проблем обновления
- **backup_db.py** - Резервное копирование БД
- **deploy_to_vps.sh** - Деплой на VPS

---

## 🆘 Часто задаваемые вопросы

### Q: Бот не обновляется после git pull

**A:** Нужно пересобрать Docker образ:
```bash
docker compose -f docker/docker-compose.prod.yml build --no-cache
docker compose -f docker/docker-compose.prod.yml up -d
```

### Q: Как откатиться к предыдущей версии?

**A:** Используйте backup БД и откат Git:
```bash
# Остановка
docker compose -f docker/docker-compose.prod.yml down

# Откат кода
git log --oneline  # Найдите нужный коммит
git checkout <commit-hash>

# Восстановление БД
cp backups/bot_database_<timestamp>.db data/bot_database.db

# Запуск
docker compose -f docker/docker-compose.prod.yml build --no-cache
docker compose -f docker/docker-compose.prod.yml up -d
```

### Q: Database locked ошибка

**A:** Удалите lock-файлы:
```bash
docker compose -f docker/docker-compose.prod.yml down
rm -f data/bot_database.db-journal
rm -f data/bot_database.db-shm
rm -f data/bot_database.db-wal
docker compose -f docker/docker-compose.prod.yml up -d
```

### Q: Как проверить версию бота на сервере?

**A:** Проверьте последний коммит:
```bash
cd ~/telegram_repair_bot
git log -1 --oneline
```

### Q: Systemd сервис запускает старую версию

**A:** Остановите сервис перед обновлением:
```bash
sudo systemctl stop telegram-bot
# Обновляйте бота
sudo systemctl start telegram-bot
```

---

## 📝 Добавление новых руководств

При обнаружении новых проблем и их решений:

1. Создайте новый MD файл в этой папке
2. Используйте понятную структуру
3. Добавьте примеры команд
4. Обновите этот README
5. Укажите дату и версию

---

## 🔗 Связанные ресурсы

- [Официальная документация aiogram](https://docs.aiogram.dev/)
- [Docker документация](https://docs.docker.com/)
- [SQLite документация](https://www.sqlite.org/docs.html)
- [Python Alembic](https://alembic.sqlalchemy.org/)

---

**Последнее обновление:** 15 октября 2025
**Поддержка:** Создайте issue в репозитории проекта
