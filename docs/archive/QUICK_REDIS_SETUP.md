# ⚡ Быстрая настройка Redis (5 минут)

## 🎯 Цель
Исправить P0-3: MemoryStorage → RedisStorage

## ✅ Что уже сделано автоматически
- ✅ `bot.py` обновлён
- ✅ `requirements.txt` обновлён
- ✅ Redis Docker конфигурация готова

---

## 🚀 Быстрый старт

### Вариант 1: Docker (Рекомендуется)

```bash
# 1. Установите зависимости в контейнере
docker-compose -f docker/docker-compose.yml exec bot pip install redis==5.2.1

# 2. Обновите .env
echo "REDIS_URL=redis://redis:6379/0" >> .env
echo "DEV_MODE=false" >> .env

# 3. Запустите с Redis
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.redis.yml up -d --build

# 4. Проверьте логи
docker logs telegram_repair_bot | grep -i redis
# Должно быть: "Используется RedisStorage для FSM: redis://redis:6379/0"
```

### Вариант 2: Локально (Windows)

```powershell
# 1. Установите Redis через WSL2
wsl --install
wsl
sudo apt update && sudo apt install redis-server -y
sudo service redis-server start

# 2. Установите Python зависимость
pip install redis==5.2.1

# 3. Обновите .env
# Откройте .env и добавьте:
REDIS_URL=redis://localhost:6379/0
DEV_MODE=false

# 4. Запустите бота
python bot.py

# 5. Проверьте логи
# В logs/bot.log должно быть:
# "Используется RedisStorage для FSM: redis://localhost:6379/0"
```

---

## ✅ Тест работоспособности

```bash
# 1. Начните создание заявки в боте
/create_order

# 2. Перезапустите бота
docker restart telegram_repair_bot  # Docker
# или Ctrl+C и python bot.py        # Локально

# 3. Продолжите диалог
# ✅ Если работает: бот помнит состояние
# ❌ Если нет: см. REDIS_SETUP_GUIDE.md
```

---

## 🔧 Команды для проверки

```bash
# Проверить Redis работает
redis-cli ping                                    # Локально
docker exec -it telegram_bot_redis redis-cli ping # Docker
# Ожидается: PONG

# Посмотреть ключи FSM
redis-cli KEYS aiogram:*
# Ожидается: список ключей после использования бота

# Проверить логи бота
docker logs telegram_repair_bot | grep -i storage
# Ожидается: "Используется RedisStorage"
```

---

## 🆘 Быстрые решения проблем

**Проблема:** "Connection refused"
```bash
# Решение: Запустите Redis
docker-compose -f docker/docker-compose.redis.yml up -d redis
```

**Проблема:** Бот использует MemoryStorage
```bash
# Решение: Проверьте .env
cat .env | grep DEV_MODE
# Должно быть: DEV_MODE=false

cat .env | grep REDIS_URL
# Должно быть: REDIS_URL=redis://...
```

**Проблема:** "No module named 'redis'"
```bash
# Решение: Установите зависимость
pip install redis==5.2.1
```

---

## 📄 Полная документация

Для детальной информации см. **[REDIS_SETUP_GUIDE.md](REDIS_SETUP_GUIDE.md)**

---

**Время выполнения:** 5-10 минут
**Приоритет:** P0 - Критично
**Статус:** ✅ Готово к внедрению
