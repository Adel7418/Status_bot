# 🔍 АУДИТ КОРРЕКТНОСТИ И УСТОЙЧИВОСТИ БОТА

**Дата:** 12 октября 2025  
**Статус:** ⚠️ **НАЙДЕНО 10 ПРОБЛЕМ**

---

## 📊 РЕЗЮМЕ АУДИТА

**Проверено:**
- ✅ aiohttp.ClientSession и ресурсы
- ✅ async/await и обработка исключений
- ✅ FSM (state, очистка)
- ⚠️ Безопасное форматирование HTML
- ✅ drop_pending_updates и allowed_updates
- ⚠️ middleware (отсутствует Throttle)
- ✅ retry/backoff для Bot API
- ✅ Валидация через pydantic

**Найдено проблем:** 10 (3 критические, 4 важные, 3 средние)

---

## 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### 1. **HTML Injection через пользовательский ввод**

**📍 Локация:** `app/handlers/dispatcher.py:502-520`, все хэндлеры

**Симптом:**  
```python
# dispatcher.py:502-520
text = (
    f"🔧 <b>Тип техники:</b> {data['equipment_type']}\n"  # ❌ Нет escape!
    f"📝 <b>Описание:</b> {data['description']}\n"        # ❌ Нет escape!
    f"👤 <b>Клиент:</b> {data['client_name']}\n"          # ❌ Нет escape!
)
await message.answer(text, parse_mode="HTML")
```

**Причина:**  
Пользовательский ввод вставляется напрямую в HTML без экранирования. Есть функция `escape_markdown()` в `utils.py`, но **нет `escape_html()`** и она нигде не используется.

**Риск:**  
🔴 **XSS атака через HTML injection**
- Пользователь может ввести `<b>test</b>` → сломает форматирование
- Пользователь может ввести `</b><i>` → сломает весь HTML
- В худшем случае: injection может сломать отображение для всех пользователей

**Рекомендация:**
```python
# Добавить в app/utils.py
from html import escape

def escape_html(text: str) -> str:
    """Экранирование HTML специальных символов"""
    if text is None:
        return ""
    return escape(str(text))

# Использовать:
text = f"👤 <b>Клиент:</b> {escape_html(data['client_name'])}\n"
```

**Затронуто файлов:** ~5 (все handlers)  
**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

### 2. **Отсутствует Throttling Middleware**

**📍 Локация:** `app/middlewares/`, `bot.py:150-152`

**Симптом:**  
```python
# bot.py - только RoleCheckMiddleware
role_middleware = RoleCheckMiddleware(db)
dp.message.middleware(role_middleware)
dp.callback_query.middleware(role_middleware)
# ❌ Нет ThrottlingMiddleware!
```

**Причина:**  
Не реализован Throttling middleware. Пользователь может спамить команды → флуд контроль со стороны Telegram (429 Too Many Requests).

**Риск:**  
🔴 **Флуд атака и бан бота**
- Злонамеренный пользователь может спамить команды
- Telegram заблокирует бота через Flood Control
- Нагрузка на БД от повторяющихся запросов
- DoS для других пользователей

**Рекомендация:**
```python
# app/middlewares/throttling.py
from aiogram import BaseMiddleware
from aiogram.types import Message
from collections import defaultdict
import time

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):  # 0.5 сек между сообщениями
        self.rate_limit = rate_limit
        self.user_timestamps = defaultdict(float)
    
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        current_time = time.time()
        
        last_time = self.user_timestamps[user_id]
        if current_time - last_time < self.rate_limit:
            # Игнорируем или отвечаем "Too many requests"
            if isinstance(event, Message):
                await event.answer("⏱ Слишком частые запросы. Подождите.")
            return
        
        self.user_timestamps[user_id] = current_time
        return await handler(event, data)
```

**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

### 3. **Bot session не закрывается при исключениях в startup**

**📍 Локация:** `bot.py:115-180`

**Симптом:**  
```python
# bot.py:115-180
async def main():
    bot = Bot(token=Config.BOT_TOKEN, ...)  # Создали
    # ... много кода ...
    
    try:
        await dp.start_polling(bot, ...)
    except Exception as e:
        logger.error("Критическая ошибка: %s", e)
    finally:
        await on_shutdown(bot, db, scheduler)
        await bot.session.close()  # ✅ Закрываем
```

**НО!** Если исключение произойдет ДО `try` блока (строки 115-164):
```python
bot = Bot(...)  # Создали
db = Database()
await db.connect()
await db.init_db()  # ❌ Если здесь ошибка → bot.session не закроется!
scheduler = TaskScheduler(bot, db)
# ... роутеры ...
await on_startup(...)  # ❌ Если здесь ошибка → bot.session не закроется!
```

**Причина:**  
`bot.session.close()` в `finally` блоке, но он не покрывает инициализацию до `try`.

**Риск:**  
🔴 **Resource leak**
- aiohttp.ClientSession остается открытой
- TCP соединения не закрываются
- Memory leak при перезапусках
- "Unclosed client session" warnings

**Рекомендация:**
```python
async def main():
    bot = None
    db = None
    scheduler = None
    
    try:
        # Инициализация Sentry
        init_sentry()
        
        # Валидация
        Config.validate()
        
        # Создаем ресурсы
        bot = Bot(...)
        db = Database()
        await db.connect()
        await db.init_db()
        
        scheduler = TaskScheduler(bot, db)
        
        # ... middleware, роутеры ...
        
        await on_startup(bot, db, scheduler)
        
        # Polling
        await dp.start_polling(bot, ...)
        
    except Exception as e:
        logger.error("Критическая ошибка: %s", e)
        
    finally:
        # Cleanup всегда выполняется
        if scheduler:
            await scheduler.stop()
        if db:
            await db.disconnect()
        if bot:
            await bot.session.close()
```

**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

## 🟠 ВАЖНЫЕ ПРОБЛЕМЫ

### 4. **FSM state не очищается при исключениях**

**📍 Локация:** Все handlers с FSM

**Симптом:**  
```python
# dispatcher.py:524-594
async def confirm_create_order(message: Message, state: FSMContext, ...):
    try:
        # Валидация
        order_data = OrderCreateSchema(**data)
    except ValidationError as e:
        logger.error(f"Order validation failed: {e}")
        await state.clear()  # ✅ Здесь очищаем
        # ...
        return
    
    db = Database()
    try:
        order = await db.create_order(...)
        # ...
    finally:
        await db.disconnect()
    
    await state.clear()  # ✅ Здесь очищаем
```

**НО!** Если исключение в `create_order()` или между операциями:
```python
try:
    order = await db.create_order(...)  # ❌ Если ошибка здесь
    # ... отправка уведомлений ...      # state не очистится!
finally:
    await db.disconnect()

await state.clear()  # ❌ Не достигнется при исключении!
```

**Причина:**  
`state.clear()` вызывается ПОСЛЕ `try-finally`, а не внутри `finally`.

**Риск:**  
🟠 **Пользователь застревает в FSM state**
- После ошибки пользователь остается в CreateOrderStates.confirm
- Следующие сообщения обрабатываются неправильно
- Нужно писать `/cancel` вручную
- Плохой UX

**Рекомендация:**
```python
async def confirm_create_order(...):
    try:
        # Валидация
        order_data = OrderCreateSchema(**data)
        
        db = Database()
        try:
            order = await db.create_order(...)
            # ... логика ...
        finally:
            await db.disconnect()
            
    except ValidationError as e:
        # Обработка ошибок валидации
        pass
    except Exception as e:
        # Обработка других ошибок
        logger.exception(...)
    finally:
        # ВСЕГДА очищаем state
        await state.clear()
```

**Затронуто файлов:** ~4 handlers  
**Приоритет:** 🟠 ВАЖНЫЙ

---

### 5. **Нет логирования middleware (Logging Middleware)**

**📍 Локация:** `app/middlewares/`

**Симптом:**  
Отсутствует middleware для централизованного логирования всех входящих update'ов.

**Причина:**  
Есть только `RoleCheckMiddleware` и `global_error_handler`. Нет middleware для логирования:
- Входящих сообщений (user_id, chat_id, text)
- Callback queries
- Времени обработки
- Статистики использования

**Риск:**  
🟠 **Сложность отладки и мониторинга**
- Нет центральной точки логирования
- Сложно отследить flow пользователя
- Нет метрик производительности
- Нет статистики по командам

**Рекомендация:**
```python
# app/middlewares/logging.py
class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        start_time = time.time()
        
        # Логируем входящее событие
        if isinstance(event, Message):
            logger.info(
                f"Message from {user.id} ({user.username}): "
                f"{event.text[:50] if event.text else '[media]'}"
            )
        elif isinstance(event, CallbackQuery):
            logger.info(
                f"Callback from {user.id} ({user.username}): {event.data}"
            )
        
        try:
            result = await handler(event, data)
            duration = time.time() - start_time
            logger.info(f"Processed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error after {duration:.2f}s: {e}")
            raise
```

**Приоритет:** 🟠 ВАЖНЫЙ

---

### 6. **Retry не применяется к scheduler уведомлениям**

**📍 Локация:** `app/services/scheduler.py:130, 187, 257`

**Симптом:**  
```python
# scheduler.py:130
await safe_send_message(
    self.bot, admin_id, text,
    parse_mode="HTML",
    max_attempts=5  # ✅ Используется retry
)

# НО в других местах:
# scheduler.py:903 (dispatcher.py)
result = await safe_send_message(bot, chat_id, text)  # ❌ max_attempts=3 (default)
```

**Причина:**  
Не везде используется увеличенный `max_attempts` для важных уведомлений.

**Риск:**  
🟠 **Потеря критичных уведомлений**
- Уведомления мастерам о назначении могут не дойти
- SLA алерты администраторам могут потеряться
- При временных сетевых проблемах - только 3 попытки

**Рекомендация:**
```python
# Для критичных уведомлений
await safe_send_message(
    bot, master_id, notification_text,
    max_attempts=5,  # Увеличенное количество
    parse_mode="HTML"
)

# Можно добавить приоритеты
class MessagePriority(Enum):
    LOW = 2      # Обычные сообщения
    NORMAL = 3   # Стандартные уведомления
    HIGH = 5     # Критичные (SLA, назначения)
    CRITICAL = 7 # Очень важные (системные алерты)
```

**Приоритет:** 🟠 ВАЖНЫЙ

---

### 7. **Pydantic ValidationError не отлавливается в некоторых handlers**

**📍 Локация:** `app/handlers/dispatcher.py`, `app/handlers/master.py`

**Симптом:**  
```python
# dispatcher.py:99-162 (process_description)
async def process_description(message: Message, state: FSMContext, ...):
    try:
        # Валидация через Pydantic
        partial_data = {"description": message.text}
        OrderCreateSchema(**partial_data)  # ❌ Упадет на missing fields
    except ValidationError as e:
        # Обработка ошибок
        errors = e.errors()
        # ...
```

**Но валидация частичных данных не имеет смысла:**
```python
OrderCreateSchema(**{"description": "test"})
# ValidationError: equipment_type, client_name, etc are required
```

**Причина:**  
Используется полная схема `OrderCreateSchema` для валидации частичных данных. Нужна отдельная схема или `model_validate()` с `partial=True`.

**Риск:**  
🟠 **Неправильная валидация**
- Валидация может не работать как ожидается
- Ложные срабатывания
- Confusing error messages для пользователя

**Рекомендация:**
```python
# Вариант 1: Частичная схема
class OrderPartialSchema(BaseModel):
    description: Optional[str] = None
    client_name: Optional[str] = None
    # ...
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v is not None:
            # Валидация только если поле заполнено
            ...

# Вариант 2: Простая валидация в handlers
async def process_description(...):
    text = message.text.strip()
    if len(text) < 10:
        await message.answer("❌ Описание слишком короткое...")
        return
    if len(text) > MAX_DESCRIPTION_LENGTH:
        await message.answer(f"❌ Максимум {MAX_DESCRIPTION_LENGTH} символов")
        return
    
    await state.update_data(description=text)
    # Полная валидация только при финальном confirm
```

**Приоритет:** 🟠 ВАЖНЫЙ

---

## 🟡 СРЕДНИЕ ПРОБЛЕМЫ

### 8. **Нет валидации allowed_updates**

**📍 Локация:** `bot.py:171`

**Симптом:**  
```python
# bot.py:171
await dp.start_polling(
    bot,
    allowed_updates=dp.resolve_used_update_types(),  # ✅ Использовано
    drop_pending_updates=True,  # ✅ Использовано
)
```

**Причина:**  
`dp.resolve_used_update_types()` автоматически определяет типы, но не проверяется что они корректны. Можно явно указать только нужные типы.

**Риск:**  
🟡 **Лишний трафик и обработка**
- Получаем update'ы которые не используем
- Лишняя нагрузка на Bot API
- Потенциальная утечка данных (например, `my_chat_member` events)

**Рекомендация:**
```python
# bot.py
from aiogram.types import AllowedUpdates

ALLOWED_UPDATES = [
    AllowedUpdates.MESSAGE,
    AllowedUpdates.CALLBACK_QUERY,
    # Добавить только то что реально используется
    # AllowedUpdates.CHAT_MEMBER,  # Если нужно
]

await dp.start_polling(
    bot,
    allowed_updates=ALLOWED_UPDATES,  # Явно указываем
    drop_pending_updates=True,
)
```

**Приоритет:** 🟡 СРЕДНИЙ

---

### 9. **escape_markdown() реализован но не используется**

**📍 Локация:** `app/utils.py:101-133`

**Симптом:**  
```python
# utils.py:101
def escape_markdown(text: str) -> str:
    """Экранирование специальных символов для Markdown"""
    special_chars = ["_", "*", "[", "]", ...]
    for char in special_chars:
        text = text.replace(char, "\\" + char)
    return text
```

Но нигде не используется! (grep показал 0 использований)

**Причина:**  
Функция реализована, но:
- Используется `parse_mode="HTML"` везде (не Markdown)
- Нет `escape_html()` функции
- `escape_markdown()` висит мертвым кодом

**Риск:**  
🟡 **Dead code и confusion**
- Разработчики думают что есть escape, но используют не тот
- Markdown mode не используется, функция не нужна
- Нет HTML escape (см. проблему #1)

**Рекомендация:**
```python
# Удалить escape_markdown() или пометить как deprecated
# Добавить escape_html():
from html import escape

def escape_html(text: str) -> str:
    """Экранирование HTML специальных символов"""
    if text is None:
        return ""
    return escape(str(text))
```

**Приоритет:** 🟡 СРЕДНИЙ

---

### 10. **Отсутствует graceful shutdown для pending FSM states**

**📍 Локация:** `bot.py:176-179`

**Симптом:**  
```python
# bot.py:176-179
finally:
    await on_shutdown(bot, db, scheduler)
    await bot.session.close()
```

**Причина:**  
При shutdown не очищаются активные FSM states пользователей. Используется `MemoryStorage()` → при перезапуске все states теряются.

**Риск:**  
🟡 **Потеря состояния пользователей**
- При перезапуске бота пользователи в середине создания заявки теряют прогресс
- С `MemoryStorage` это неизбежно
- Нужен Redis для персистентности

**Рекомендация:**
```python
# Вариант 1: Уведомление при shutdown
async def on_shutdown(bot, db, scheduler):
    # Получить список активных states (если Redis)
    # Отправить уведомления пользователям
    
    await scheduler.stop()
    await db.disconnect()
    
# Вариант 2: Использовать Redis
from aiogram.fsm.storage.redis import RedisStorage

storage = RedisStorage.from_url(Config.REDIS_URL)
dp = Dispatcher(storage=storage)

# Вариант 3: Документировать поведение
# "При перезапуске бота активные FSM states будут потеряны.
#  Используйте /cancel и начните заново."
```

**Приоритет:** 🟡 СРЕДНИЙ

---

## 📊 ИТОГОВАЯ ТАБЛИЦА

| № | Проблема | Критичность | Файлы | Усилия |
|---|----------|-------------|-------|--------|
| 1 | HTML Injection | 🔴 КРИТИЧЕСКАЯ | ~5 handlers | 4 часа |
| 2 | Нет Throttling | 🔴 КРИТИЧЕСКАЯ | middlewares | 2 часа |
| 3 | Session не закрывается | 🔴 КРИТИЧЕСКАЯ | bot.py | 1 час |
| 4 | FSM state leak | 🟠 ВАЖНАЯ | ~4 handlers | 2 часа |
| 5 | Нет Logging middleware | 🟠 ВАЖНАЯ | middlewares | 2 часа |
| 6 | Retry не везде | 🟠 ВАЖНАЯ | handlers | 1 час |
| 7 | Pydantic partial validation | 🟠 ВАЖНАЯ | handlers | 2 часа |
| 8 | allowed_updates | 🟡 СРЕДНЯЯ | bot.py | 0.5 часа |
| 9 | Dead code escape_markdown | 🟡 СРЕДНЯЯ | utils.py | 0.5 часа |
| 10 | FSM graceful shutdown | 🟡 СРЕДНЯЯ | bot.py | 1 час |

**Всего усилий:** ~16 часов

---

## ✅ ЧТО РАБОТАЕТ ХОРОШО

1. ✅ **Retry mechanism** - отлично реализован в `app/utils/retry.py`
2. ✅ **Pydantic validation** - полная валидация в `app/schemas/`
3. ✅ **drop_pending_updates=True** - правильно используется
4. ✅ **Error handling** - глобальный error handler + декораторы
5. ✅ **Async/await** - правильно используется везде
6. ✅ **Database patterns** - shared instance, правильное закрытие
7. ✅ **Structured logging** - хорошее логирование с RotatingFileHandler

---

## 🎯 ПРИОРИТЕТ ИСПРАВЛЕНИЙ

### Неделя 1 (Критичные):
1. 🔴 Добавить `escape_html()` и использовать везде
2. 🔴 Реализовать ThrottlingMiddleware
3. 🔴 Исправить bot.session cleanup

### Неделя 2 (Важные):
4. 🟠 Исправить FSM state cleanup
5. 🟠 Добавить LoggingMiddleware
6. 🟠 Увеличить retry для критичных уведомлений

### Неделя 3 (Средние):
7. 🟠 Исправить Pydantic partial validation
8. 🟡 Явно указать allowed_updates
9. 🟡 Удалить/рефакторить escape_markdown
10. 🟡 Документировать FSM behavior при shutdown

---

## 📚 ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ

### Security:
- Добавить rate limiting per user (в дополнение к throttling)
- Логировать подозрительную активность (SQL injection attempts из Pydantic)
- Добавить CSP headers если будет веб-интерфейс

### Observability:
- Интегрировать Prometheus metrics (уже упомянуто в requirements)
- Добавить health check endpoint
- Tracked metrics: requests/sec, errors/sec, FSM states count

### Testing:
- Unit тесты для HTML escape
- Integration тесты для throttling
- Load testing для флуд защиты

---

**Статус:** ⚠️ **ТРЕБУЮТСЯ ИСПРАВЛЕНИЯ**  
**Следующий шаг:** Исправить критичные проблемы (1-3) в течение недели

**Документ:** [PRODUCTION_READY_GUIDE.md](PRODUCTION_READY_GUIDE.md) - уже обновлен  
**Fixes:** Создать отдельные issues для каждой проблемы

---

_Аудит проведен с использованием Context7 docs и лучших практик aiogram 3._



