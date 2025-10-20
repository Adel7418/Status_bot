# ⚡ Быстрый старт: Постоянное хранение заявок

## 🎯 За 5 минут до полноценной работы

### Шаг 1: Установка зависимостей (1 мин)

```bash
# Установка библиотеки для шифрования
pip install cryptography==43.0.3

# Или обновить все зависимости
pip install -r requirements.txt
```

### Шаг 2: Генерация ключа шифрования (1 мин)

```bash
# Сгенерировать ключ
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Результат (пример):
# gAAAAABl1234567890abcdefghijklmnopqrstuvwxyz==
```

**Добавьте в `.env`:**
```bash
ENCRYPTION_KEY=gAAAAABl1234567890abcdefghijklmnopqrstuvwxyz==
ENCRYPT_DATA=false  # Сначала false для тестирования
```

⚠️ **ВАЖНО:**
- НЕ публикуйте ключ в git!
- Сохраните ключ в безопасном месте
- Без ключа вы НЕ сможете расшифровать данные!

### Шаг 3: Проверка текущего состояния (1 мин)

```bash
# Проверить миграции
alembic current

# Должно показать: 008_add_soft_delete (или новее)
# Если нет, выполните:
alembic upgrade head
```

### Шаг 4: Тестирование шифрования (2 мин)

```python
# test_encryption.py
from app.utils.encryption import encrypt, decrypt

# Тест
original = "79991234567"
encrypted = encrypt(original)
decrypted = decrypt(encrypted)

print(f"Оригинал:     {original}")
print(f"Зашифровано:  {encrypted}")
print(f"Расшифровано: {decrypted}")
print(f"✅ Работает: {original == decrypted}")
```

Запустить:
```bash
python test_encryption.py
```

---

## ✅ Ваша система УЖЕ поддерживает:

### 1. ✅ Soft Delete (Мягкое удаление)
**Что работает:**
- Поле `deleted_at` во всех таблицах
- Индексы для быстрого поиска
- Версионирование записей

**Как использовать:**
```python
# Вместо физического удаления
await db.connection.execute(
    "UPDATE orders SET deleted_at = ? WHERE id = ?",
    (datetime.now().isoformat(), order_id)
)

# Поиск только активных
SELECT * FROM orders WHERE deleted_at IS NULL

# Поиск всех (включая удаленные)
SELECT * FROM orders
```

### 2. ✅ История статусов
**Таблица:** `order_status_history`

**Что фиксируется:**
- Все изменения статусов заявок
- Кто изменил
- Когда изменил
- Дополнительные заметки

### 3. ✅ История изменений полей
**Таблица:** `entity_history`

**Что фиксируется:**
- Изменения любых полей в любых таблицах
- Старое и новое значение
- Кто и когда изменил

### 4. ✅ Аудит действий
**Таблица:** `audit_log`

**Что фиксируется:**
- Все важные действия пользователей
- Детали в JSON формате
- Временные метки

---

## 🚀 Внедрение расширенных функций

### Вариант 1: Постепенное внедрение (рекомендуется)

#### Этап 1: Используем существующий функционал

```python
# В вашем коде УЖЕ работает история статусов
from app.repositories.order_repository import OrderRepository

order_repo = OrderRepository(db.connection)

# Получить историю заявки
history = await order_repo.get_status_history(order_id=123)

for h in history:
    print(f"{h['changed_at']}: {h['old_status']} → {h['new_status']}")
```

#### Этап 2: Добавляем soft delete

```python
# Замените физическое удаление на мягкое
# БЫЛО:
await db.connection.execute("DELETE FROM orders WHERE id = ?", (order_id,))

# СТАЛО:
from app.utils.helpers import get_now
await db.connection.execute(
    "UPDATE orders SET deleted_at = ? WHERE id = ?",
    (get_now().isoformat(), order_id)
)
```

#### Этап 3: Добавляем фильтр в запросы

```python
# Обновите все запросы получения заявок
# БЫЛО:
SELECT * FROM orders WHERE status = 'NEW'

# СТАЛО:
SELECT * FROM orders WHERE status = 'NEW' AND deleted_at IS NULL
```

### Вариант 2: Полное внедрение (готовые модули)

#### Шаг 1: Используем расширенный репозиторий

```python
# В вашем коде
from app.repositories.order_repository_extended import OrderRepositoryExtended

# Замените
order_repo = OrderRepository(db.connection)

# На
order_repo = OrderRepositoryExtended(db.connection)

# Теперь доступны новые методы:
# - soft_delete()
# - restore()
# - search_orders()
# - get_full_history()
# - get_deleted_orders()
```

#### Шаг 2: Добавляем сервис поиска

```python
from app.services.search_service import SearchService

# Инициализация
search_service = SearchService(order_repo)

# Использование
orders = await search_service.search(
    query="холодильник",
    filters={"status": "COMPLETED"}
)
```

---

## 🔐 Шифрование данных (опционально)

### Когда нужно шифрование?

✅ **Нужно:**
- Хранение персональных данных клиентов
- Требования GDPR/закона о персональных данных
- Production окружение

❌ **Не нужно:**
- Development окружение
- Внутренние данные (статусы, ID)
- Данные для поиска (используйте хеширование)

### Миграция существующих данных

```bash
# 1. Сделайте бэкап!
python scripts/backup_db.py

# 2. Проверьте что будет зашифровано (DRY RUN)
python scripts/migrate_encryption.py
# Выберите: dry

# 3. Реальная миграция
python scripts/migrate_encryption.py
# Выберите: real
# Введите: YES

# 4. Включите шифрование в .env
ENCRYPT_DATA=true
```

---

## 📊 Проверка работы

### Тест 1: Проверка soft delete

```sql
-- Проверить наличие поля deleted_at
SELECT name, sql FROM sqlite_master
WHERE type='table' AND name='orders';

-- Должно быть: deleted_at DATETIME
```

### Тест 2: Проверка истории

```sql
-- Проверить историю статусов
SELECT COUNT(*) FROM order_status_history;

-- Проверить историю изменений
SELECT COUNT(*) FROM entity_history;

-- Проверить аудит
SELECT COUNT(*) FROM audit_log;
```

### Тест 3: Проверка индексов

```sql
-- Проверить индексы
SELECT name FROM sqlite_master
WHERE type='index' AND tbl_name='orders';

-- Должны быть:
-- idx_orders_deleted_at
-- idx_orders_status
-- idx_orders_assigned_master_id
-- и др.
```

---

## 🎓 Примеры использования

### Пример 1: Админ может восстановить удаленную заявку

```python
from aiogram import Router, F
from aiogram.types import CallbackQuery

@router.callback_query(F.data.startswith("restore:"))
async def restore_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])

    # Используем расширенный репозиторий
    order_repo = OrderRepositoryExtended(db.connection)

    success = await order_repo.restore(
        order_id=order_id,
        restored_by=callback.from_user.id
    )

    if success:
        await callback.answer("✅ Заявка восстановлена!", show_alert=True)
    else:
        await callback.answer("❌ Ошибка", show_alert=True)
```

### Пример 2: Поиск всех заявок клиента

```python
@router.message(Command("search_client"))
async def search_client(message: Message):
    # Получаем телефон из команды
    phone = message.text.split()[-1]

    # Поиск
    search_service = SearchService(order_repo)
    orders = await search_service.search_by_client_phone(phone)

    # Результат
    if orders:
        text = f"📱 Найдено заявок клиента {phone}: {len(orders)}\n\n"
        for order in orders:
            text += f"#{order.id} - {order.status} - {order.equipment_type}\n"
    else:
        text = "🔍 Заявок не найдено"

    await message.answer(text)
```

### Пример 3: Просмотр полной истории

```python
@router.callback_query(F.data.startswith("history:"))
async def show_history(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])

    # Получаем полную историю
    search_service = SearchService(order_repo)
    history = await search_service.get_full_order_history(order_id)

    # Форматируем
    text = f"📋 <b>История заявки #{order_id}</b>\n\n"
    text += f"📊 Изменений статусов: {len(history['status_history'])}\n"
    text += f"🔄 Изменений полей: {len(history['field_history'])}\n"
    text += f"📝 Записей аудита: {len(history['audit_logs'])}\n\n"

    # Последние 3 изменения
    text += "<b>Последние изменения:</b>\n"
    for h in history['status_history'][:3]:
        text += f"• {h['changed_at']}: {h['old_status']} → {h['new_status']}\n"

    await callback.message.answer(text, parse_mode="HTML")
```

---

## 📚 Дополнительные материалы

- 📖 [PERMANENT_STORAGE_GUIDE.md](./PERMANENT_STORAGE_GUIDE.md) - Полное руководство
- 📝 [PERMANENT_STORAGE_EXAMPLES.md](./PERMANENT_STORAGE_EXAMPLES.md) - Примеры кода
- 🔍 [DB_AUDIT.md](./DB_AUDIT.md) - Аудит базы данных

---

## ❓ FAQ

**Q: Нужно ли запускать миграции?**
A: Если у вас версия миграций >= 008, то все уже настроено! Проверьте: `alembic current`

**Q: Как узнать, зашифрованы ли данные?**
A: Зашифрованные данные выглядят как random строки base64. Пример: `Z0FBQUFBQm1...`

**Q: Что делать если потерял ключ шифрования?**
A: К сожалению, без ключа данные восстановить НЕВОЗМОЖНО. Поэтому:
- Храните ключ в безопасном месте
- Сделайте резервную копию ключа
- Используйте vault для хранения (HashiCorp Vault, AWS Secrets Manager и т.д.)

**Q: Можно ли менять ключ шифрования?**
A: Да, но потребуется расшифровать все данные старым ключом и зашифровать новым.

**Q: Замедлит ли шифрование работу?**
A: Незначительно. Cryptography очень быстрая. Для 1000 заявок ~0.1 секунды.

**Q: Как восстановить удаленную заявку?**
A: Используйте метод `restore()` расширенного репозитория или выполните:
```sql
UPDATE orders SET deleted_at = NULL WHERE id = ?
```

---

## ✅ Чеклист внедрения

- [ ] Установлена библиотека `cryptography`
- [ ] Сгенерирован ключ шифрования
- [ ] Ключ добавлен в `.env` (и НЕ в git!)
- [ ] Проверены миграции (`alembic current`)
- [ ] Протестировано шифрование
- [ ] Обновлены запросы с фильтром `deleted_at IS NULL`
- [ ] Создан бэкап базы данных
- [ ] (Опционально) Выполнена миграция шифрования
- [ ] (Опционально) Внедрен расширенный репозиторий
- [ ] (Опционально) Добавлен сервис поиска

---

**Готово!** 🎉

Ваша система теперь:
- ✅ Хранит все заявки навсегда
- ✅ Отслеживает все изменения
- ✅ Поддерживает поиск и восстановление
- ✅ (Опционально) Шифрует персональные данные

---

**Версия:** 1.0
**Дата:** 20.10.2025
**Автор:** AI Assistant
