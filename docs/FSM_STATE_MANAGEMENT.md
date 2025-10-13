# 📝 FSM State Management - Руководство

## 🎯 Обзор

Проект использует **aiogram FSM (Finite State Machine)** для управления состояниями диалогов с пользователями.

**Текущее хранилище:** `MemoryStorage` (в bot.py)

---

## ⚠️ ВАЖНО: Поведение при перезапуске

### Что происходит с FSM states при перезапуске бота?

**С MemoryStorage:**
```python
# bot.py
storage = MemoryStorage()  # ← Хранится в RAM
dp = Dispatcher(storage=storage)
```

**При перезапуске бота:**
- ✅ Все FSM states **очищаются** (теряются)
- ✅ Пользователи автоматически переводятся в начальное состояние
- ❌ **Потеря прогресса** - незавершенные заявки теряются

**Пример:**
1. Пользователь создает заявку (состояние: `CreateOrderStates.client_phone`)
2. Бот перезапускается
3. State теряется
4. Пользователь может начать заново через `/start` или `/cancel`

---

## 🔄 Graceful Shutdown

### Текущая реализация

```python
# bot.py
finally:
    # Гарантированная очистка ресурсов
    logger.info("Начало процедуры остановки...")
    
    if scheduler:
        await scheduler.stop()  # Останавливаем планировщик
    
    if db:
        await db.disconnect()  # Закрываем БД
    
    if bot:
        await bot.session.close()  # ✅ Закрываем aiohttp session
    
    logger.info("Бот полностью остановлен")
```

**Что НЕ делается при shutdown:**
- ❌ Не уведомляем пользователей о перезапуске
- ❌ Не сохраняем активные FSM states
- ❌ Не очищаем storage явно (MemoryStorage очистится автоматически)

**Почему так?**
- `MemoryStorage` не сохраняет данные на диск
- При перезапуске все равно все потеряется
- Уведомления затруднены (нет списка активных пользователей в FSM)

---

## 🔧 FSM State Cleanup

### Правильный паттерн

**❌ НЕПРАВИЛЬНО:**
```python
async def some_handler(message: Message, state: FSMContext):
    db = Database()
    await db.connect()
    
    try:
        order = await db.create_order(...)
    finally:
        await db.disconnect()
    
    await state.clear()  # ❌ Не вызовется при exception!
```

**✅ ПРАВИЛЬНО:**
```python
async def some_handler(message: Message, state: FSMContext):
    db = None
    
    try:
        db = Database()
        await db.connect()
        order = await db.create_order(...)
        
    finally:
        # Гарантированная очистка
        if db:
            await db.disconnect()
        # ВСЕГДА очищаем state
        await state.clear()  # ✅ Вызовется всегда!
```

### Где применено

**Исправлено в:**
- ✅ `app/handlers/dispatcher.py:confirm_create_order()`
- ✅ `app/handlers/master.py:process_review_confirmation()`
- ✅ Другие критичные handlers

**Паттерн:**
1. Инициализация `db = None` перед `try`
2. Вся логика в `try` блоке
3. `finally` блок:
   - Закрытие БД (`if db: await db.disconnect()`)
   - Очистка state (`await state.clear()`)

---

## 🚀 Миграция на Redis (Production)

### Зачем нужен Redis?

**Проблемы с MemoryStorage:**
- ❌ States теряются при перезапуске
- ❌ Не работает в multi-instance deployment
- ❌ Нет персистентности

**Преимущества Redis:**
- ✅ States сохраняются между перезапусками
- ✅ Поддержка нескольких экземпляров бота
- ✅ TTL для автоочистки старых states
- ✅ Atomicity операций

### Как включить Redis

**1. Установить зависимости:**
```bash
pip install redis aiogram[redis]
# или
pip install -e .[redis]
```

**2. Настроить .env:**
```env
REDIS_URL=redis://localhost:6379/0
```

**3. Обновить bot.py:**
```python
import os
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

# Определяем storage в зависимости от окружения
redis_url = os.getenv("REDIS_URL")

if redis_url:
    # Production: используем Redis
    storage = RedisStorage.from_url(redis_url)
    logger.info("Using RedisStorage for FSM")
else:
    # Development: используем Memory
    storage = MemoryStorage()
    logger.info("Using MemoryStorage for FSM (states will be lost on restart)")

dp = Dispatcher(storage=storage)
```

**4. Запустить Redis:**
```bash
# Локально
docker run -d -p 6379:6379 redis:7-alpine

# Или с docker-compose
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.redis.yml up -d
```

---

## 🧪 Тестирование FSM

### Проверка корректной очистки

```python
# tests/test_fsm_cleanup.py
import pytest
from aiogram.fsm.context import FSMContext

async def test_state_cleared_on_error(mock_message, mock_state):
    """FSM state должен очищаться даже при ошибках"""
    
    # Имитируем ошибку в handler
    with pytest.raises(Exception):
        await some_handler_with_error(mock_message, mock_state)
    
    # Проверяем что state очищен
    current_state = await mock_state.get_state()
    assert current_state is None
```

### Проверка persistence с Redis

```python
async def test_redis_persistence(bot, redis_storage):
    """States должны сохраняться в Redis"""
    
    # Устанавливаем state
    await redis_storage.set_state(
        bot=bot, 
        chat_id=123, 
        user_id=456, 
        state="CreateOrderStates:equipment_type"
    )
    
    # Проверяем что сохранился
    state = await redis_storage.get_state(bot=bot, chat_id=123, user_id=456)
    assert state == "CreateOrderStates:equipment_type"
```

---

## 📊 Мониторинг FSM States

### Логирование

**С LoggingMiddleware (уже добавлен):**
```python
# app/middlewares/logging.py
# Автоматически логирует:
# - Входящие сообщения
# - Callback queries
# - Время обработки
```

**Пример логов:**
```
2025-10-12 15:30:45 - app.middlewares.logging - INFO - 📨 Message from 123456789 (@username) in private: Создать заявку
2025-10-12 15:30:45 - app.middlewares.logging - DEBUG - ✓ Processed in 0.045s
```

### Метрики (TODO)

Можно добавить подсчет активных states:
```python
# С MemoryStorage
active_states_count = len(storage._data)

# С RedisStorage
active_states = await redis.keys("fsm:*")
active_states_count = len(active_states)
```

---

## 🔍 Troubleshooting

### "State не очищается после ошибки"

**Решение:** Проверьте что `state.clear()` в `finally` блоке:
```python
finally:
    await state.clear()  # ✅
```

### "States теряются при перезапуске"

**Это нормально для MemoryStorage!**

**Решение:** Используйте RedisStorage для production.

### "Пользователь застрял в state"

```bash
# Скажите пользователю написать:
/cancel

# Это очистит его state
```

---

## 📚 Дополнительные ресурсы

- [aiogram FSM docs](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/)
- [RedisStorage docs](https://docs.aiogram.dev/en/latest/api/fsm/storage/)
- `app/states.py` - все FSM states в проекте
- `PRODUCTION_READY_GUIDE.md` - общий production guide

---

**Версия:** 1.0  
**Дата:** 12.10.2025  
**Статус:** ✅ Актуально



