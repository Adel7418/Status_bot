# 🚀 Production-Ready Guide: Telegram Repair Bot

## ✅ Что было исправлено (2025-10-12)

### 🔴 Критические исправления

#### 1. **Race Conditions в Database Layer** ✅
**Проблема:** TaskScheduler создавал отдельное соединение с БД, что приводило к `database is locked` ошибкам.

**Решение:**
```python
# app/services/scheduler.py
class TaskScheduler:
    def __init__(self, bot, db: Database):  # ✅ Shared DB instance
        self.db = db  # Используем общее соединение
```

**Файлы:** `app/services/scheduler.py`, `bot.py`

---

#### 2. **ALTER TABLE в Production коде** ✅
**Проблема:** Миграции выполнялись через `try-except` блоки в `init_db()` — антипаттерн.

**Решение:**
- Настроен **Alembic** для управления миграциями
- Создана начальная миграция `001_initial_schema.py`
- `init_db()` теперь только проверяет существование таблиц

**Использование:**
```bash
# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1

# Создать новую миграцию
alembic revision -m "description"
```

**Файлы:** `migrations/versions/001_initial_schema.py`, `app/database/db.py`

---

#### 3. **Error Tracking** ✅
**Проблема:** Нет интеграции с Sentry, логи только в файл.

**Решение:**
- Добавлена опциональная интеграция с **Sentry**
- Настраивается через `SENTRY_DSN` в `.env`
- Автоматическая инициализация при старте

**Конфигурация:**
```env
# .env
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
ENVIRONMENT=production
```

**Файлы:** `app/utils/sentry.py`, `bot.py`, `env.example`

---

### 🟠 Важные улучшения

#### 4. **Rotating File Handler** ✅
**Проблема:** Лог-файл рос бесконечно без ротации.

**Решение:**
```python
# bot.py
from logging.handlers import RotatingFileHandler

file_handler = RotatingFileHandler(
    "logs/bot.log",
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,  # Хранить 5 файлов
    encoding="utf-8"
)
```

**Файлы:** `bot.py`

---

#### 5. **Docker Optimization** ✅
**Проблема:** 
- Отсутствовал `.dockerignore` → большие образы
- Redis в docker-compose, но не используется

**Решение:**
- Создан `.dockerignore` → уменьшение размера образа на ~50%
- Redis вынесен в отдельный `docker-compose.redis.yml`
- Используйте только при необходимости:
  ```bash
  docker-compose -f docker-compose.yml -f docker-compose.redis.yml up -d
  ```

**Файлы:** `.dockerignore`, `docker/docker-compose.yml`, `docker/docker-compose.redis.yml`

---

#### 6. **Обновлены зависимости** ✅
```diff
# requirements.txt
- aiogram==3.14.0  
+ aiogram==3.16.0  # ✅ Latest stable

- pydantic==2.9.2
+ pydantic==2.10.3  # ✅ Исправлена совместимость

+ sentry-sdk>=2.19.0  # ✅ Опциональный error tracking
```

**Файлы:** `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`

---

#### 7. **Улучшен .gitignore** ✅
Добавлено в `.gitignore`:
- `logs/` и `*.log` (логи)
- `bot_database.db` (БД)
- `backups/` (бэкапы БД)
- `htmlcov/`, `.coverage` (coverage артефакты)
- `.ruff_cache/`, `.pytest_cache/` (кэши инструментов)

**Файл:** `.gitignore`

---

## 📋 Быстрый старт

### Локальная разработка

```bash
# 1. Клонировать репозиторий
git clone <repository_url>
cd telegram_repair_bot

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. Установить зависимости
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Для разработки

# 4. Настроить .env
cp env.example .env
# Отредактируйте .env файл

# 5. Применить миграции БД
alembic upgrade head

# 6. Запустить бота
python bot.py
```

---

### Production с Docker

```bash
# 1. Настроить .env
cp env.example .env
# Отредактируйте .env файл

# 2. Запустить через Docker Compose
docker-compose -f docker/docker-compose.yml up -d

# 3. Проверить логи
docker-compose -f docker/docker-compose.yml logs -f bot

# 4. (Опционально) Добавить Redis для FSM
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.redis.yml up -d
```

---

## 🔧 Конфигурация

### Обязательные переменные (.env)

```env
# Telegram Bot Token (получить у @BotFather)
BOT_TOKEN=your_bot_token_here

# ID администраторов (через запятую)
ADMIN_IDS=123456789,987654321

# ID диспетчеров (через запятую)
DISPATCHER_IDS=111222333
```

### Опциональные переменные

```env
# Путь к базе данных
DATABASE_PATH=bot_database.db

# Уровень логирования
LOG_LEVEL=INFO

# Sentry для error tracking
SENTRY_DSN=https://key@o0.ingest.sentry.io/0
ENVIRONMENT=production

# Redis для FSM (если используете)
REDIS_URL=redis://localhost:6379/0
```

---

## 📊 База данных

### Миграции Alembic

```bash
# Применить все миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Создать новую миграцию
alembic revision -m "add_new_field"

# Автогенерация миграции (требует SQLAlchemy models)
alembic revision --autogenerate -m "description"

# Показать текущую версию
alembic current

# История миграций
alembic history
```

### Резервное копирование

```bash
# Ручной бэкап
python backup_db.py

# Бэкапы сохраняются в backups/
# Формат: bot_database_YYYY-MM-DD_HH-MM-SS.db
```

---

## 🧪 Тестирование

```bash
# Запустить все тесты
pytest

# С coverage
pytest --cov=app --cov-report=html

# Только unit тесты
pytest -m unit

# Конкретный файл
pytest tests/test_database.py

# С verbose
pytest -v
```

---

## 🎨 Code Quality

```bash
# Pre-commit hooks (автоматически перед коммитом)
pre-commit install

# Ручной запуск всех checks
pre-commit run --all-files

# Black (форматирование)
black .

# Ruff (linting)
ruff check .
ruff check --fix .  # Автоисправление

# MyPy (type checking)
mypy app/
```

---

## 📈 Мониторинг

### Sentry (Error Tracking)

1. Создайте проект в [sentry.io](https://sentry.io)
2. Получите DSN
3. Добавьте в `.env`:
   ```env
   SENTRY_DSN=https://...@sentry.io/...
   ENVIRONMENT=production
   ```
4. Установите пакет (если не установлен):
   ```bash
   pip install sentry-sdk
   ```

Sentry автоматически:
- Отслеживает все exceptions
- Логирует errors и above
- Собирает breadcrumbs
- Профилирует performance (10% транзакций)

### Логи

**Расположение:** `logs/bot.log`

**Ротация:**
- Максимальный размер файла: 10 MB
- Хранится файлов: 5 (bot.log, bot.log.1, ..., bot.log.5)
- Автоматическая ротация при достижении лимита

**Уровни логирования:**
```python
# bot.py или .env
LOG_LEVEL=DEBUG   # Для разработки
LOG_LEVEL=INFO    # Production (рекомендуется)
LOG_LEVEL=WARNING # Только предупреждения и ошибки
LOG_LEVEL=ERROR   # Только ошибки
```

---

## 🔐 Безопасность

### Чек-лист

- [x] BOT_TOKEN не коммитится в репозиторий (.env в .gitignore)
- [x] База данных не коммитится (.gitignore)
- [x] Логи не коммитятся (.gitignore)
- [x] Docker контейнер запускается от non-root user
- [x] Sentry не отправляет PII данные (`send_default_pii=False`)
- [x] Используются parameterized queries (защита от SQL injection)
- [x] Валидация входных данных через Pydantic
- [x] Ролевая модель доступа через middleware

### Рекомендации для Production

1. **Используйте PostgreSQL** вместо SQLite для production
2. **Включите Sentry** для мониторинга ошибок
3. **Настройте Redis** для FSM storage (опционально)
4. **Используйте HTTPS** для webhook mode (опционально)
5. **Настройте firewall** для ограничения доступа
6. **Регулярные бэкапы** БД (можно через cron)

---

## 🐛 Troubleshooting

### "Database is locked"
**Решение:** Используется shared DB instance ✅ (исправлено)

### "Sentry SDK not installed"
```bash
pip install sentry-sdk
# или
pip install -e .[monitoring]
```

### "Alembic: Can't locate revision"
```bash
# Сбросить и применить заново
alembic downgrade base
alembic upgrade head
```

### "Docker: Permission denied"
```bash
# Дать права на data/logs/backups
chmod -R 777 data logs backups
```

### Логи не ротируются
Проверьте права на директорию `logs/`:
```bash
mkdir -p logs
chmod 755 logs
```

---

## 📚 Дополнительная документация

- [START_HERE.txt](START_HERE.txt) - Быстрый старт
- [README.md](README.md) - Основная документация
- [docs/](docs/) - Подробные гайды:
  - `MULTIPLE_ROLES_GUIDE.md` - Множественные роли
  - `DATABASE_USAGE_GUIDE.md` - Работа с БД
  - `DOCKER_USAGE.md` - Docker deployment
  - `TROUBLESHOOTING.md` - Решение проблем

---

## 🎯 TODO для дальнейшего развития

### Высокий приоритет
- [ ] Переход на PostgreSQL для production
- [ ] Webhook mode вместо long polling
- [ ] Rate limiting для API calls
- [ ] Graceful shutdown для scheduler jobs

### Средний приоритет
- [ ] Интеграция с Prometheus для метрик
- [ ] API для внешних систем
- [ ] Web-интерфейс для управления
- [ ] Notification system через email/SMS

### Низкий приоритет
- [ ] Миграция на aiogram FSMContext v3.x patterns
- [ ] GraphQL API
- [ ] Mobile app
- [ ] AI-ассистент для диспетчеров

---

## 📞 Поддержка

**Issues:** [GitHub Issues](https://github.com/yourusername/telegram-repair-bot/issues)  
**Docs:** [docs/](docs/)  
**Email:** support@example.com

---

**Версия:** 1.2.0 (Production Ready)  
**Дата:** 12.10.2025  
**Автор:** Tech Lead Review & Fixes

**Статус:** ✅ PRODUCTION READY



