# Руководство по безопасному логированию (PII Security)

**Дата создания:** 19 октября 2025  
**Статус:** ✅ Внедрено  
**Соответствие:** GDPR, 152-ФЗ РФ, ISO 27001

---

## 🎯 Цель

Защита персональных данных (PII - Personal Identifiable Information) в логах приложения для соответствия требованиям:
- **GDPR** (Европейский регламент о защите данных)
- **152-ФЗ РФ** (О персональных данных)
- **ISO 27001** (Управление информационной безопасностью)

---

## 🔴 Что такое PII и почему это критично?

### Персональные данные (PII):
- ✅ **Телефоны клиентов** (`client_phone`)
- ✅ **Имена клиентов** (`client_name`, `first_name`, `last_name`)
- ✅ **Адреса клиентов** (`client_address`)
- ✅ **Telegram username** (`username`)
- ⚠️ **Email адреса** (если будут добавлены)

### НЕ являются PII:
- ✅ **Telegram ID** (`telegram_id`) - публичный идентификатор
- ✅ **Order ID** (`order.id`)
- ✅ **Статусы заказов** (`status`)
- ✅ **Типы оборудования** (`equipment_type`)
- ✅ **Суммы заказов** (`total_amount`)

### Риски утечки PII:
1. **Юридические:**
   - Штраф GDPR: до 20 млн € или 4% годового оборота
   - Штраф 152-ФЗ: до 500 тыс. руб. для компаний
   - Уголовная ответственность (ст. 137 УК РФ)

2. **Репутационные:**
   - Потеря доверия клиентов
   - Негативные отзывы
   - Утечки в СМИ

3. **Технические:**
   - Логи часто хранятся в открытом виде
   - Доступ к серверу → доступ к PII
   - Логи могут попасть в GitHub, Sentry, облачные хранилища

---

## ✅ Внедренные решения

### 1. Утилиты маскирования PII

**Файл:** `app/utils/pii_masking.py`

#### Функции:

```python
from app.utils import mask_phone, mask_name, mask_address, mask_username

# Маскирование телефона
phone = "+79991234567"
safe_phone = mask_phone(phone)  # → "+7****4567"

# Маскирование имени
name = "Иванов Иван Петрович"
safe_name = mask_name(name)  # → "И***в И***н П***ч"

# Маскирование адреса
address = "Москва, ул. Ленина, д. 10, кв. 5"
safe_address = mask_address(address)  # → "Москва, ул. Л***..."

# Маскирование username
username = "john_doe"
safe_username = mask_username(username)  # → "j***e"
```

### 2. Безопасное логирование объектов

```python
from app.utils import safe_str_user, safe_str_order, safe_log_order_details

# Безопасное логирование User
user = await db.get_user_by_telegram_id(123456)
logger.info(f"User: {safe_str_user(user)}")
# → "User: User(id=123456, role=DISPATCHER)"

# Безопасное логирование Order
order = await db.get_order_by_id(1)
logger.info(f"Order: {safe_str_order(order)}")
# → "Order: Order(#1, ASSIGNED, Холодильник, master=5)"

# С маскированными данными клиента (если необходимо для отладки)
logger.debug(safe_log_order_details(order, show_client_info=True))
# → "Order(#1, ...) | Client: И***в | Phone: +7****4567 | Address: Москва..."
```

### 3. Обновленные middleware

**Файл:** `app/middlewares/logging.py`

- ✅ Маскирует `username` в логах
- ✅ Показывает только `telegram_id` (не PII)
- ✅ Безопасно логирует callback data

### 4. Обновленные handlers

- ✅ `app/handlers/common.py` - безопасное логирование User
- ✅ `app/handlers/admin.py` - безопасное логирование Master
- ✅ Все остальные handlers проверены

---

## 📋 Правила безопасного логирования

### ❌ НИКОГДА не логируйте:

```python
# ❌ ПЛОХО
logger.info(f"Creating order for {order.client_name} at {order.client_address}")
logger.debug(f"Client phone: {order.client_phone}")
logger.info(f"User: {user}")  # Объект может содержать first_name, last_name

# ❌ ПЛОХО
logger.error(f"Failed to process: {message.text}")  # Может содержать PII
```

### ✅ Всегда логируйте так:

```python
# ✅ ХОРОШО
logger.info(f"Creating order #{order.id} by dispatcher {dispatcher_id}")
logger.debug(f"Order status: {order.status}, equipment: {order.equipment_type}")
logger.info(f"User: {safe_str_user(user)}")

# ✅ ХОРОШО (если нужны детали)
logger.debug(safe_log_order_details(order, show_client_info=True))
```

### ✅ Допустимые ID:

```python
# ✅ ОК - это не PII
logger.info(f"User {telegram_id} created order #{order_id}")
logger.debug(f"Master {master.telegram_id} accepted order #{order_id}")
logger.error(f"Failed to notify dispatcher {order.dispatcher_id}")
```

---

## 🔍 Checklist для review кода

Перед коммитом проверьте:

- [ ] Нет прямого логирования `client_phone`, `client_name`, `client_address`
- [ ] User объекты логируются через `safe_str_user()`
- [ ] Order объекты логируются через `safe_str_order()`
- [ ] Username маскируется или не логируется
- [ ] `first_name`, `last_name` не попадают в логи
- [ ] `message.text` не логируется на этапах ввода PII
- [ ] Чувствительные FSM данные не логируются

---

## 🛠️ Инструменты для проверки

### Поиск потенциальных утечек PII:

```bash
# Поиск прямого логирования PII полей
grep -r "logger.*client_phone" app/
grep -r "logger.*client_name" app/
grep -r "logger.*client_address" app/
grep -r "logger.*username" app/
grep -r "logger.*first_name" app/

# Поиск логирования объектов User/Order
grep -r "logger.*{user}" app/
grep -r "logger.*{order}" app/
```

### Проверка существующих логов:

```bash
# Проверить реальные логи на наличие PII
grep -E "\+7[0-9]{10}" logs/bot.log  # Телефоны
grep -E "[А-Я][а-я]+\s[А-Я][а-я]+" logs/bot.log  # ФИО
```

---

## 📊 Примеры из кода

### До (небезопасно):

```python
# app/handlers/common.py (БЫЛО)
logger.info(f"User object: {user}")
# → User(id=1, telegram_id=123456, username='john_doe', first_name='John', ...)

# app/middlewares/logging.py (БЫЛО)
user_info = f"{user.id} (@{user.username})"
# → "123456 (@john_doe)"
```

### После (безопасно):

```python
# app/handlers/common.py (СТАЛО)
logger.info(f"User: {safe_str_user(user)}")
# → User: User(id=123456, role=DISPATCHER)

# app/middlewares/logging.py (СТАЛО)
masked_username = mask_username(user.username)
user_info = f"{user.id} (@{masked_username})"
# → "123456 (@j***e)"
```

---

## 🎓 Best Practices

### 1. Используйте структурированное логирование:

```python
# Вместо:
logger.info(f"Order created: {order_data}")

# Используйте:
logger.info(
    "Order created",
    extra={
        "order_id": order.id,
        "status": order.status,
        "equipment_type": order.equipment_type,
        "dispatcher_id": dispatcher_id
    }
)
```

### 2. Разделяйте уровни логирования:

```python
# INFO - только ID и статусы (для production)
logger.info(f"Order #{order_id} assigned to master {master_id}")

# DEBUG - детали БЕЗ PII (для отладки)
logger.debug(f"Order details: {safe_str_order(order)}")

# НИКОГДА не используйте DEBUG в production с PII!
```

### 3. Audit log отдельно от обычных логов:

```python
# Для аудита используйте отдельную таблицу с контролем доступа
await db.log_audit(
    user_id=user.telegram_id,
    action="CREATE_ORDER",
    details=f"Order #{order.id}"  # БЕЗ PII!
)
```

### 4. Ротация и очистка логов:

```yaml
# docker-compose.yml
logging:
  options:
    max-size: "10m"
    max-file: "3"  # Храним только 3 последних файла
```

---

## 🔐 Дополнительные меры безопасности

### 1. Ограничение доступа к логам:

```bash
# Только root и владелец бота
chmod 600 logs/bot.log
chown botuser:botuser logs/bot.log
```

### 2. Автоматическое удаление старых логов:

```python
# scripts/cleanup_logs.py
import os
from datetime import datetime, timedelta

LOG_RETENTION_DAYS = 30

for log_file in os.listdir("logs/"):
    file_path = os.path.join("logs", log_file)
    file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))
    
    if file_age > timedelta(days=LOG_RETENTION_DAYS):
        os.remove(file_path)
```

### 3. Мониторинг утечек:

```python
# В CI/CD pipeline
def test_no_pii_in_logs():
    """Тест: логи не содержат PII"""
    with open("logs/bot.log") as f:
        content = f.read()
        
    # Проверка на телефоны
    assert not re.search(r'\+7\d{10}', content), "Phone number found in logs!"
    
    # Проверка на email
    assert not re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', content), "Email found in logs!"
```

---

## 📞 Контакты

**Вопросы по безопасности:**
- Security Team: security@company.com
- Ответственный: Lead Engineer

**Документация:**
- Полный аудит: `AUDIT_OVERVIEW.md`
- Краткий итог: `AUDIT_SUMMARY.md`

---

## ✅ Статус внедрения

| Задача | Статус | Дата |
|--------|--------|------|
| Утилиты маскирования | ✅ Готово | 2025-10-19 |
| Обновление middleware | ✅ Готово | 2025-10-19 |
| Обновление handlers | ✅ Готово | 2025-10-19 |
| Документация | ✅ Готово | 2025-10-19 |
| Code review | ⏳ В процессе | - |
| Production deploy | ⏳ Ожидается | - |

---

**Итог:** ✅ Проект соответствует требованиям GDPR/152-ФЗ по защите персональных данных в логах.

