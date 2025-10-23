# Чек-лист миграции на ORMDatabase для Docker

## 📋 Подготовка к миграции

### Локальная разработка ✅
- [x] ORMDatabase реализован
- [x] Метод `delete_master` добавлен
- [x] Обновление SLA при переносе заявок
- [x] Уведомления диспетчеру о непринятых заявках
- [x] Убрана надпись "[MASTER]" из предупреждений
- [x] Удалена кнопка "Кастомный отчет"
- [x] Миграции применены локально
- [x] Бот работает без ошибок

### Файлы для обновления на сервере
- [ ] `app/database/orm_database.py` - добавлен метод `delete_master`
- [ ] `app/handlers/admin.py` - заменен `Database` на `ORMDatabase`
- [ ] `app/handlers/master.py` - обновление `updated_at` при переносе
- [ ] `app/services/scheduler.py` - уведомления диспетчеру
- [ ] `app/handlers/financial_reports.py` - удалена кнопка кастомного отчета
- [ ] `docker_migrate.sh` - скрипт миграции для Docker
- [ ] `DOCKER_MIGRATION_PLAN.md` - план миграции для Docker
- [ ] `DOCKER_QUICK_DEPLOY.md` - быстрая инструкция для Docker

## 🐳 Выполнение миграции в Docker

### 1. Подготовка
- [ ] Подключиться к серверу
- [ ] Перейти в директорию проекта
- [ ] Проверить docker-compose.yml
- [ ] Создать бэкап БД: `docker-compose exec bot cp /app/data/bot_database.db /app/data/bot_database_backup_$(date +%Y%m%d_%H%M%S).db`

### 2. Обновление кода
- [ ] Остановить бота: `docker-compose stop bot`
- [ ] Обновить код (git pull или загрузка файлов)
- [ ] Пересобрать образ: `docker-compose build bot` (если нужно)

### 3. Миграция БД
- [ ] Запустить скрипт: `./docker_migrate.sh`
- [ ] ИЛИ вручную: `docker-compose run --rm bot alembic upgrade head`
- [ ] Проверить статус: `docker-compose run --rm bot alembic current`

### 4. Запуск и проверка
- [ ] Запустить бота: `docker-compose up -d bot`
- [ ] Проверить статус: `docker-compose ps`
- [ ] Проверить логи: `docker-compose logs -f bot`

## 🧪 Тестирование функций

### Основные функции
- [ ] Создание заявки
- [ ] Назначение мастера
- [ ] Принятие заявки мастером
- [ ] Перенос заявки (проверить обновление SLA)
- [ ] Завершение заявки

### Административные функции
- [ ] Увольнение мастера (проверить отсутствие ошибок)
- [ ] Активация/деактивация мастера
- [ ] Просмотр отчетов (без кастомного отчета)

### Уведомления
- [ ] Уведомления о непринятых заявках (мастеру и диспетчеру)
- [ ] SLA-уведомления (без надписи "[MASTER]")
- [ ] Напоминания о визитах

## 🔍 Мониторинг Docker

### Логи
- [ ] Нет ошибок `AttributeError: 'ORMDatabase' object has no attribute 'delete_master'`
- [ ] Нет ошибок подключения к БД
- [ ] Нет ошибок миграций
- [ ] Все функции работают корректно

### Контейнеры
- [ ] Контейнер бота запущен: `docker-compose ps`
- [ ] Нет перезапусков контейнера
- [ ] Использование ресурсов в норме: `docker stats`

### База данных
- [ ] БД доступна: `docker-compose exec bot sqlite3 /app/data/bot_database.db "SELECT 1;"`
- [ ] Таблицы существуют: `docker-compose exec bot sqlite3 /app/data/bot_database.db ".tables"`
- [ ] Данные сохранены: `docker-compose exec bot sqlite3 /app/data/bot_database.db "SELECT COUNT(*) FROM orders;"`

## 🆘 План отката для Docker

### Если что-то пошло не так
- [ ] Остановить все: `docker-compose down`
- [ ] Восстановить бэкап: `docker-compose run --rm bot cp /app/data/bot_database_backup_YYYYMMDD_HHMMSS.db /app/data/bot_database.db`
- [ ] Откатить код: `git checkout HEAD~1`
- [ ] Пересобрать образ: `docker-compose build bot`
- [ ] Запустить бота: `docker-compose up -d bot`

## 📞 Команды для поддержки

### Логи
```bash
# Логи бота в реальном времени
docker-compose logs -f bot

# Последние 100 строк логов
docker-compose logs --tail=100 bot

# Логи всех сервисов
docker-compose logs -f
```

### Статус
```bash
# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats

# Информация о контейнере
docker inspect $(docker-compose ps -q bot)
```

### База данных
```bash
# Подключиться к БД
docker-compose exec bot sqlite3 /app/data/bot_database.db

# Проверить таблицы
docker-compose exec bot sqlite3 /app/data/bot_database.db ".tables"

# Проверить схему
docker-compose exec bot sqlite3 /app/data/bot_database.db ".schema orders"
```

## ✅ Финальная проверка

- [ ] Все функции работают
- [ ] Нет ошибок в логах
- [ ] Контейнеры работают стабильно
- [ ] Производительность в норме
- [ ] Пользователи не жалуются
- [ ] Бэкап сохранен
- [ ] Документация обновлена

## 🐳 Docker-специфичные проверки

- [ ] Образ пересобран (если нужно)
- [ ] Том с данными монтирован корректно
- [ ] Переменные окружения настроены
- [ ] Сеть между контейнерами работает
- [ ] Порты проброшены правильно

---

**Дата миграции:** ___________
**Ответственный:** ___________
**Статус:** ___________
**Docker версия:** ___________
