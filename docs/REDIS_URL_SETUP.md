# Как настроить REDIS_URL

## 📋 Формат REDIS_URL

```
redis://[username:password@]host:port[/database]
```

---

## 🔧 Варианты подключения

### 1️⃣ **Локальный Redis (на том же сервере)**

Если Redis установлен на том же сервере, где работает бот:

```bash
# В файле .env
REDIS_URL=redis://localhost:6379/0
```

**Пояснение:**
- `redis://` - протокол
- `localhost` - адрес (локальный сервер)
- `6379` - порт по умолчанию для Redis
- `/0` - номер базы данных (0-15, по умолчанию 0)

---

### 2️⃣ **Redis на другом сервере**

Если Redis на отдельном сервере:

```bash
# В файле .env
REDIS_URL=redis://192.168.1.100:6379/0
```

Замените `192.168.1.100` на IP-адрес вашего Redis сервера.

---

### 3️⃣ **Redis с паролем (рекомендуется для production)**

Если настроили пароль в Redis:

```bash
# В файле .env
REDIS_URL=redis://:your_password@localhost:6379/0
```

Замените `your_password` на ваш пароль Redis.

---

### 4️⃣ **Redis Cloud / Managed Service**

Если используете облачный Redis (Redis Cloud, AWS ElastiCache, и т.д.):

```bash
# Пример для Redis Cloud
REDIS_URL=redis://username:password@redis-12345.cloud.redislabs.com:12345/0

# Пример для AWS ElastiCache
REDIS_URL=redis://my-cluster.abc123.0001.use1.cache.amazonaws.com:6379/0
```

URL предоставит ваш провайдер облачных услуг.

---

## 🛠️ Как узнать параметры вашего Redis

### Проверка, что Redis работает:

```bash
# 1. Проверить статус Redis
sudo systemctl status redis

# 2. Подключиться к Redis CLI
redis-cli ping
# Должно вернуть: PONG

# 3. Проверить порт
sudo netstat -tulpn | grep redis
# или
sudo ss -tulpn | grep redis
```

### Проверка конфигурации Redis:

```bash
# Посмотреть конфиг
redis-cli CONFIG GET port
redis-cli CONFIG GET bind
redis-cli CONFIG GET requirepass
```

**Вывод:**
- `port` - порт Redis (обычно 6379)
- `bind` - на каком IP слушает (127.0.0.1 = только локально, 0.0.0.0 = все интерфейсы)
- `requirepass` - пароль (если настроен)

---

## ✅ Настройка для вашего случая

### Для локального сервера (самый простой вариант):

**1. В файле `.env` (или `env.production`):**
```bash
REDIS_URL=redis://localhost:6379/0
DEV_MODE=false
```

**2. Перезапустите бота:**
```bash
# Если через Docker
docker-compose down
docker-compose up -d

# Если напрямую
systemctl restart telegram-bot
```

**3. Проверьте логи:**
```bash
# Должны увидеть:
# "Используется RedisStorage для FSM: redis://localhost:6379/0"

# В Docker
docker-compose logs -f bot

# В systemd
journalctl -u telegram-bot -f
```

---

## 🔐 Безопасность (рекомендации)

### 1. Настройте пароль для Redis:

```bash
# Откройте конфиг Redis
sudo nano /etc/redis/redis.conf

# Найдите и раскомментируйте строку:
# requirepass your_strong_password_here
requirepass MyStr0ng!P@ssw0rd

# Перезапустите Redis
sudo systemctl restart redis
```

### 2. Обновите REDIS_URL:

```bash
# В .env
REDIS_URL=redis://:MyStr0ng!P@ssw0rd@localhost:6379/0
```

### 3. Ограничьте доступ по сети:

```bash
# В /etc/redis/redis.conf
# Если бот на том же сервере:
bind 127.0.0.1

# Если на другом сервере:
bind 0.0.0.0
# И настройте firewall!
```

---

## 🧪 Тестирование подключения

### Тест 1: Из командной строки

```bash
# Без пароля
redis-cli -h localhost -p 6379 ping

# С паролем
redis-cli -h localhost -p 6379 -a "MyStr0ng!P@ssw0rd" ping
```

### Тест 2: Через Python

```python
# test_redis.py
import asyncio
from aiogram.fsm.storage.redis import RedisStorage

async def test():
    storage = RedisStorage.from_url("redis://localhost:6379/0")
    # Если подключение успешно, ошибки не будет
    print("✅ Redis подключен успешно!")
    await storage.close()

asyncio.run(test())
```

```bash
python test_redis.py
```

---

## ❓ Частые проблемы

### Ошибка: "Connection refused"

**Причина:** Redis не запущен или слушает на другом порту

**Решение:**
```bash
# Проверьте статус
sudo systemctl status redis

# Запустите если не работает
sudo systemctl start redis

# Включите автозапуск
sudo systemctl enable redis
```

### Ошибка: "NOAUTH Authentication required"

**Причина:** Redis требует пароль, но вы его не указали

**Решение:**
```bash
# Добавьте пароль в URL
REDIS_URL=redis://:ваш_пароль@localhost:6379/0
```

### Ошибка: "Could not connect to Redis at 127.0.0.1:6379"

**Причина:** Неверный хост или порт

**Решение:**
```bash
# Проверьте какой порт использует Redis
redis-cli CONFIG GET port

# Обновите URL с правильным портом
REDIS_URL=redis://localhost:ПРАВИЛЬНЫЙ_ПОРТ/0
```

---

## 📝 Итоговая проверка

После настройки REDIS_URL проверьте:

✅ Redis запущен: `sudo systemctl status redis`
✅ Бот может подключиться: проверьте логи при запуске
✅ В логах написано: `"Используется RedisStorage для FSM"`
✅ DEV_MODE=false в .env

**Готово!** 🎉 Ваши FSM состояния теперь сохраняются в Redis!

---

## 🆘 Нужна помощь?

Если Redis не работает, проверьте:
1. Установлен ли Redis: `redis-cli --version`
2. Запущен ли: `sudo systemctl status redis`
3. Доступен ли по сети: `redis-cli ping`

Если нужна установка Redis, см. `QUICK_REDIS_SETUP.md`

