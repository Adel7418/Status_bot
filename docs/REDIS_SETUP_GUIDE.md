# 🚀 Инструкция по настройке Redis для FSM Storage

**Проблема:** MemoryStorage теряет состояния FSM при рестарте бота
**Решение:** Redis Storage для персистентности
**ETA:** 1 день
**Приоритет:** P0 (критично)

---

## ✅ Что было сделано автоматически

1. ✅ Обновлён `bot.py` - добавлена поддержка RedisStorage
2. ✅ Обновлён `requirements.txt` - раскомментирован Redis
3. ✅ Добавлено graceful shutdown для Redis соединения

---

## 📋 Шаги для запуска

### **Вариант A: Локальная разработка (без Docker)**

#### 1. Установите Redis на вашей системе

**Windows:**
```powershell
# Вариант 1: Через Chocolatey
choco install redis-64

# Вариант 2: Через WSL2
wsl --install
wsl
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# macOS (Homebrew)
brew install redis
brew services start redis
```

#### 2. Проверьте работу Redis

```bash
redis-cli ping
# Должно вернуть: PONG
```

#### 3. Установите Python зависимости

```bash
pip install -r requirements.txt
# Или только Redis:
pip install redis==5.2.1
```

#### 4. Настройте .env файл

```bash
# .env
REDIS_URL=redis://localhost:6379/0
DEV_MODE=false  # Важно! Для использования Redis
```

#### 5. Запустите бота

```bash
python bot.py
```

**Проверьте логи:**
```
... - Используется RedisStorage для FSM: redis://localhost:6379/0
... - Бот успешно запущен!
```

---

### **Вариант B: Production с Docker Compose (рекомендуется)**

#### 1. Создайте/обновите .env файл

```bash
# .env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789
DISPATCHER_IDS=987654321

# Redis configuration
REDIS_URL=redis://redis:6379/0
DEV_MODE=false

# Database
DATABASE_PATH=/app/data/bot_database.db
```

#### 2. Запустите с Redis

**Вариант 2.1: Объединённый compose (рекомендуется)**

```bash
# В корне проекта
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.redis.yml up -d
```

**Вариант 2.2: Обновите основной docker-compose.yml**

Добавьте Redis сервис в `docker/docker-compose.yml`:

```yaml
services:
  bot:
    # ... существующая конфигурация
    environment:
      - DATABASE_PATH=/app/data/bot_database.db
      - REDIS_URL=redis://redis:6379/0  # Добавить
    depends_on:
      - redis  # Добавить

  # Добавить Redis сервис
  redis:
    image: redis:7-alpine
    container_name: telegram_bot_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - bot_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: redis-server --appendonly yes
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  redis_data:
    driver: local
```

Затем запустите:

```bash
docker-compose -f docker/docker-compose.yml up -d --build
```

#### 3. Проверьте статус контейнеров

```bash
docker-compose -f docker/docker-compose.yml ps

# Должны быть запущены:
# - telegram_repair_bot (bot)
# - telegram_bot_redis (redis)
```

#### 4. Проверьте логи бота

```bash
docker logs telegram_repair_bot

# Ищите строку:
# "Используется RedisStorage для FSM: redis://redis:6379/0"
```

#### 5. Проверьте работу Redis

```bash
# Подключитесь к контейнеру Redis
docker exec -it telegram_bot_redis redis-cli

# Проверьте:
127.0.0.1:6379> PING
PONG

127.0.0.1:6379> KEYS *
# Должны появиться ключи после использования бота

127.0.0.1:6379> exit
```

---

## 🧪 Тестирование

### Тест 1: Проверка персистентности FSM

1. **Начните создание заявки:**
   - Отправьте боту `/create_order`
   - Выберите тип техники
   - Введите описание

2. **Перезапустите бота:**
   ```bash
   # Docker
   docker restart telegram_repair_bot

   # Локально
   # Ctrl+C и затем python bot.py
   ```

3. **Проверьте состояние:**
   - ✅ **С Redis:** Бот продолжит диалог с того же места
   - ❌ **Без Redis:** Бот забудет о диалоге

### Тест 2: Проверка ключей в Redis

```bash
# Подключитесь к Redis
redis-cli  # Локально
# или
docker exec -it telegram_bot_redis redis-cli  # Docker

# Проверьте ключи FSM
127.0.0.1:6379> KEYS aiogram:*
# Должны увидеть ключи вида:
# 1) "aiogram:fsm:state:123456789:123456789"
# 2) "aiogram:fsm:data:123456789:123456789"

# Посмотрите содержимое
127.0.0.1:6379> GET "aiogram:fsm:state:123456789:123456789"
# Вернёт: "OrderState:description" (или другое состояние)
```

### Тест 3: Мониторинг памяти Redis

```bash
redis-cli INFO memory

# Должны увидеть:
# used_memory_human: 1.23M
# used_memory_peak_human: 2.45M
```

---

## 🔍 Устранение неполадок

### Проблема 1: "Connection refused" при подключении к Redis

**Решение:**
```bash
# Проверьте, запущен ли Redis
# Linux/Mac:
sudo systemctl status redis

# Docker:
docker ps | grep redis

# Если не запущен - запустите:
sudo systemctl start redis  # Linux
brew services start redis   # macOS
docker-compose up -d redis  # Docker
```

### Проблема 2: Бот всё равно использует MemoryStorage

**Проверьте логи:**
```bash
docker logs telegram_repair_bot | grep -i storage
# или
cat logs/bot.log | grep -i storage
```

**Причина:** `DEV_MODE=true` в .env

**Решение:**
```bash
# В .env файле
DEV_MODE=false
```

Перезапустите бота.

### Проблема 3: Redis работает, но состояния не сохраняются

**Проверьте:**

1. Версию Redis:
```bash
redis-cli INFO | grep redis_version
# Должно быть >= 5.0
```

2. Права доступа к директории данных (Docker):
```bash
docker exec -it telegram_bot_redis ls -la /data
```

3. Логи Redis:
```bash
docker logs telegram_bot_redis
```

### Проблема 4: "ModuleNotFoundError: No module named 'redis'"

**Решение:**
```bash
pip install redis==5.2.1

# Или переустановите все зависимости:
pip install -r requirements.txt
```

---

## 📊 Производительность Redis

### Ожидаемое использование

| Метрика | Значение |
|---------|----------|
| Память | ~100MB для 1000 активных диалогов |
| CPU | <5% при нагрузке |
| Диск | ~10MB (с persistence) |
| Latency | <1ms для операций |

### Настройка persistence

Redis уже настроен с **AOF (Append Only File)** в docker-compose:

```yaml
command: redis-server --appendonly yes
```

Это гарантирует, что данные сохраняются на диск каждую секунду.

### Мониторинг

```bash
# Установите redis-cli мониторинг
redis-cli --stat

# Или используйте встроенный MONITOR
redis-cli MONITOR
```

---

## 🔐 Безопасность (для production)

### 1. Добавьте пароль для Redis

Обновите `docker-compose.yml`:

```yaml
services:
  redis:
    command: redis-server --appendonly yes --requirepass YOUR_SECURE_PASSWORD

  bot:
    environment:
      - REDIS_URL=redis://:YOUR_SECURE_PASSWORD@redis:6379/0
```

### 2. Ограничьте доступ к порту

```yaml
services:
  redis:
    ports:
      # Вместо:
      # - "6379:6379"
      # Используйте (только внутри Docker network):
      - "127.0.0.1:6379:6379"
```

### 3. Настройте firewall (Linux)

```bash
sudo ufw allow from 172.18.0.0/16 to any port 6379
sudo ufw deny 6379
```

---

## 📈 Миграция данных (опционально)

Если у вас уже есть активные пользователи в MemoryStorage:

**⚠️ Внимание:** MemoryStorage нельзя мигрировать в Redis напрямую, так как данные в RAM.

**Рекомендация:**
1. Объявите пользователям о плановом обновлении
2. Выберите время минимальной активности (ночь)
3. Перезапустите с Redis
4. Пользователи начнут новые диалоги

---

## ✅ Чеклист готовности

- [ ] Redis установлен и запущен
- [ ] `requirements.txt` обновлён (redis==5.2.1)
- [ ] Зависимости установлены (`pip install redis`)
- [ ] `.env` файл настроен (`REDIS_URL`, `DEV_MODE=false`)
- [ ] Docker compose обновлён (если используете Docker)
- [ ] Бот перезапущен
- [ ] Логи показывают "Используется RedisStorage"
- [ ] Тест персистентности пройден (перезапуск → состояние сохранено)
- [ ] Redis healthcheck работает (`redis-cli ping`)
- [ ] Мониторинг настроен (опционально)

---

## 🎯 Итог

**До:**
- ❌ Состояния в RAM (MemoryStorage)
- ❌ Потеря диалогов при рестарте
- ❌ Пользователи теряют прогресс

**После:**
- ✅ Состояния в Redis (персистентность)
- ✅ Диалоги сохраняются при рестарте
- ✅ Пользователи продолжают с того же места
- ✅ Production-ready

**Время выполнения:** ~1 час (настройка) + тестирование

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи: `docker logs telegram_repair_bot`
2. Проверьте Redis: `redis-cli ping`
3. Проверьте `.env` файл: `REDIS_URL` и `DEV_MODE`
4. См. раздел "Устранение неполадок" выше

---

**Дата:** 19 октября 2025
**Статус:** ✅ Готово к внедрению
**Приоритет:** P0 - Критично для production

