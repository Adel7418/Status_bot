# ⚡ State Machine - Быстрая памятка

## ✅ Что сделано автоматически

- ✅ State Machine создана (`app/domain/order_state_machine.py`)
- ✅ `db.py` обновлена (валидация в `update_order_status()`)
- ✅ Middleware создан (`validation_handler.py`)
- ✅ Middleware подключён в `bot.py`

## 🚀 Готово к использованию!

Никаких дополнительных действий не требуется. State Machine уже работает.

---

## 🧪 Быстрый тест

### 1. Запустите бота

```bash
python bot.py
```

### 2. Попробуйте создать заявку и изменить статус

**Допустимые действия** (✅ Должны работать):
1. Создать заявку → статус NEW
2. Назначить мастера (диспетчер/admin) → ASSIGNED
3. Принять заявку (мастер) → ACCEPTED
4. На объекте (мастер) → ONSITE
5. Закрыть (мастер) → CLOSED

**Недопустимые действия** (❌ Должны блокироваться):
1. NEW → CLOSED напрямую
2. Мастер пытается назначить себя (нет прав)
3. Диспетчер пытается закрыть заявку (нет прав)
4. Переход из CLOSED в любой статус (терминальный)

### 3. Проверьте логи

```bash
cat logs/bot.log | grep -i "валидация"
```

**Ожидаемый вывод при успехе:**
```
✅ Валидация перехода пройдена: NEW → ASSIGNED
✅ Валидация перехода пройдена: ASSIGNED → ACCEPTED
```

**При ошибке:**
```
❌ Недопустимый переход статуса для заявки #123: Переход из 'NEW' в 'CLOSED' недопустим
```

---

## 📊 Допустимые переходы

```
NEW        → ASSIGNED, REFUSED
ASSIGNED   → ACCEPTED, REFUSED, NEW
ACCEPTED   → ONSITE, DR, REFUSED
ONSITE     → CLOSED, DR
DR         → CLOSED, ONSITE
REFUSED    → NEW
CLOSED     → (нет, терминальный)
```

---

## 💡 Примеры использования в коде

### Обновление статуса (с валидацией)

```python
# В handlers - просто передайте user_roles
await db.update_order_status(
    order_id=order_id,
    status=OrderStatus.ACCEPTED,
    changed_by=callback.from_user.id,
    user_roles=user_roles  # Middleware передаёт автоматически
)
# Валидация произойдёт автоматически!
# При ошибке - ValidationHandlerMiddleware покажет ошибку пользователю
```

### Проверка возможности перехода

```python
from app.domain.order_state_machine import OrderStateMachine

# Можно ли перейти из NEW в ASSIGNED?
can = OrderStateMachine.can_transition(
    from_state=OrderStatus.NEW,
    to_state=OrderStatus.ASSIGNED
)
print(can)  # True
```

### Получение доступных переходов

```python
# Какие переходы доступны мастеру из ASSIGNED?
available = OrderStateMachine.get_available_transitions(
    from_state=OrderStatus.ASSIGNED,
    user_roles=[UserRole.MASTER]
)
print(available)  # ['ACCEPTED', 'REFUSED']
```

---

## 🔧 Обработка ошибок

### Автоматическая (Middleware) - РЕКОМЕНДУЕТСЯ

Просто `raise` исключение - Middleware обработает:

```python
try:
    await db.update_order_status(...)
except InvalidStateTransitionError:
    raise  # Middleware поймает и покажет ошибку
```

### Ручная (опционально)

```python
from app.domain.order_state_machine import InvalidStateTransitionError

try:
    await db.update_order_status(...)
except InvalidStateTransitionError as e:
    await callback.answer(f"❌ {e}", show_alert=True)
```

---

## 📝 История переходов

Все переходы автоматически сохраняются:

```python
history = await db.get_order_status_history(order_id=123)
for entry in history:
    print(f"{entry['old_status']} → {entry['new_status']}")
    print(f"Изменил: {entry['changed_by_name']}")
```

---

## 🆘 Что-то не работает?

### 1. Проверьте импорты

```python
# В handlers должны быть:
from app.domain.order_state_machine import InvalidStateTransitionError
```

### 2. Проверьте, что Middleware подключён

```bash
# bot.py должен содержать:
grep -A 3 "ValidationHandlerMiddleware" bot.py
```

### 3. Проверьте логи

```bash
# Должны быть строки с валидацией:
cat logs/bot.log | grep -i "валидация"
```

### 4. Проверьте роли передаются

В handlers должен быть параметр `user_roles`:

```python
async def my_handler(callback: CallbackQuery, user_roles: list):
    # user_roles передаётся автоматически из RoleCheckMiddleware
    await db.update_order_status(..., user_roles=user_roles)
```

---

## 📄 Полная документация

См. **[STATE_MACHINE_GUIDE.md](STATE_MACHINE_GUIDE.md)** (10+ страниц с примерами)

---

## ✅ Чеклист

- [✅] State Machine работает
- [✅] Валидация включена
- [✅] Middleware активен
- [✅] Ошибки обрабатываются
- [ ] Тесты написаны (TODO)
- [ ] Production deployment

---

**Время тестирования:** 5 минут
**Приоритет:** P0 - Критично
**Статус:** ✅ Готово к работе
