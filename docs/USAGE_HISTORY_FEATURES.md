# 📚 Использование функций истории и поиска

## 🎯 Обзор новых возможностей

После доработки системы доступны новые команды и функции для работы с историей заявок, поиском и восстановлением удаленных записей.

---

## 🔐 Доступ

### Кто может использовать:

- **ADMIN** - полный доступ ко всем функциям
- **DISPATCHER** - доступ к истории и поиску (без восстановления)
- **MASTER** - ограниченный доступ к своим заявкам

---

## 📋 Новые команды

### 1. `/history <номер>` - Просмотр истории заявки

**Доступно:** ADMIN, DISPATCHER

**Использование:**
```
/history 123
```

**Что показывает:**
- История изменений статусов
- История изменений полей
- Аудит всех действий
- Полная история заявки

**Пример:**
```
/history 15

📋 История заявки #15

🔧 Тип: Холодильник
📊 Текущий статус: COMPLETED
👤 Клиент: Иван Иванов

[Кнопки]
📊 История статусов
🔄 История изменений
📝 Аудит действий
📋 Полная история
```

---

### 2. `/deleted` - Список удаленных заявок

**Доступно:** ADMIN

**Использование:**
```
/deleted
```

**Что показывает:**
- Список всех удаленных заявок
- Дата удаления
- Возможность восстановления

**Пример:**
```
/deleted

🗑 Удаленные заявки

Всего найдено: 3

📋 #10 - Стиральная машина
   👤 Петров П.П.
   📊 CLOSED
   🗑 19.10.2025 15:30
   /restore_10

📋 #25 - Холодильник
   👤 Иванов И.И.
   📊 REFUSED
   🗑 18.10.2025 10:15
   /restore_25
```

---

### 3. `/search <запрос>` - Поиск заявок

**Доступно:** ADMIN, DISPATCHER

**Использование:**
```
/search холодильник
/search Иванов
/search 79991234567
```

**Где ищет:**
- Тип техники
- Описание проблемы
- Имя клиента
- Адрес клиента
- Телефон клиента

**Пример:**
```
/search холодильник

🔍 Найдено заявок: 3

📋 Заявка #15
📊 Статус: COMPLETED
🔧 Тип: Холодильник Samsung
👤 Клиент: Иван Иванов
👨‍🔧 Мастер: Петр Петров

📋 Заявка #28
📊 Статус: IN_PROGRESS
🔧 Тип: Холодильник LG
👤 Клиент: Мария Сидорова

📋 Заявка #42
📊 Статус: NEW
🔧 Тип: Холодильник Indesit
👤 Клиент: Алексей Смирнов
```

---

### 4. `/restore_<номер>` - Быстрое восстановление

**Доступно:** ADMIN

**Использование:**
```
/restore_123
```

**Что делает:**
- Восстанавливает удаленную заявку
- Логирует действие в аудит
- Отправляет уведомление

**Пример:**
```
/restore_10

✅ Заявка #10 успешно восстановлена!
```

---

## 🖱️ Интерактивные кнопки

### История статусов

Показывает все изменения статуса заявки:

```
📊 История статусов заявки #15

🕐 2025-10-20 14:30
   NEW → ASSIGNED
   Пользователь: @dispatcher

🕐 2025-10-20 15:45
   ASSIGNED → IN_PROGRESS
   Пользователь: @master

🕐 2025-10-21 10:15
   IN_PROGRESS → COMPLETED
   Пользователь: @master
   📝 Работа выполнена
```

### История изменений

Показывает изменения всех полей:

```
🔄 История изменений заявки #15

🕐 2025-10-20 16:00
   Поле: client_phone
   Было: 79991111111
   Стало: 79992222222
   Пользователь: @dispatcher

🕐 2025-10-20 17:30
   Поле: notes
   Было: (пусто)
   Стало: Требуются запчасти
   Пользователь: @master
```

### Аудит действий

Показывает все действия пользователей:

```
📝 Аудит заявки #15

🕐 2025-10-20 14:30
   Действие: ORDER_CREATED
   Order #15 created by dispatcher
   Пользователь: @dispatcher

🕐 2025-10-20 15:45
   Действие: ORDER_ASSIGNED
   Master assigned to order #15
   Пользователь: @dispatcher

🕐 2025-10-21 10:15
   Действие: ORDER_COMPLETED
   Order #15 marked as completed
   Пользователь: @master
```

---

## 🔍 Расширенный поиск (программный)

### В коде бота

```python
from app.database.db import Database
from app.repositories.order_repository_extended import OrderRepositoryExtended
from app.services.search_service import SearchService

# Инициализация
db = Database()
await db.connect()
order_repo = OrderRepositoryExtended(db.connection)
search_service = SearchService(order_repo)

# Простой поиск
orders = await search_service.search(query="холодильник")

# Поиск с фильтрами
orders = await search_service.search(
    query="холодильник",
    filters={
        "status": "COMPLETED",
        "date_from": datetime(2025, 10, 1),
        "date_to": datetime(2025, 10, 31)
    }
)

# Поиск по телефону
orders = await search_service.search_by_client_phone("79991234567")

# Поиск по имени
orders = await search_service.search_by_client_name("Иванов")

# Поиск за период
orders = await search_service.search_by_date_range(
    date_from=datetime(2025, 10, 1),
    date_to=datetime(2025, 10, 31),
    status="COMPLETED"
)

# Удаленные заявки
deleted = await search_service.search_deleted_orders(limit=50)

# Полная история
history = await search_service.get_full_order_history(order_id=15)

# Статистика
stats = await search_service.get_statistics(include_deleted=True)
```

---

## 📊 Работа с историей (программный)

### Получение истории статусов

```python
order_repo = OrderRepositoryExtended(db.connection)

# История статусов
status_history = await order_repo.get_status_history(order_id=15)

for h in status_history:
    print(f"{h['changed_at']}: {h['old_status']} → {h['new_status']}")
    print(f"Изменил: {h['username']}")
    if h['notes']:
        print(f"Заметка: {h['notes']}")
```

### Получение полной истории

```python
# Полная история заявки
full_history = await order_repo.get_full_history(order_id=15)

print(f"Статусов: {len(full_history['status_history'])}")
print(f"Изменений: {len(full_history['field_history'])}")
print(f"Аудит: {len(full_history['audit_logs'])}")
```

### Soft Delete

```python
# Мягкое удаление
await order_repo.soft_delete(
    order_id=15,
    deleted_by=user_id,
    reason="Дубликат заявки"
)

# Восстановление
await order_repo.restore(
    order_id=15,
    restored_by=user_id
)
```

---

## 🎯 Практические примеры

### Пример 1: Поиск всех заявок клиента

```python
async def find_client_orders(client_phone: str):
    """Найти все заявки клиента"""
    search_service = SearchService(order_repo)
    orders = await search_service.search_by_client_phone(client_phone)

    print(f"Найдено заявок: {len(orders)}")
    for order in orders:
        print(f"#{order.id} - {order.status} - {order.equipment_type}")
```

### Пример 2: Экспорт истории в текст

```python
async def export_order_history(order_id: int) -> str:
    """Экспорт истории заявки в текстовый формат"""
    search_service = SearchService(order_repo)
    history = await search_service.get_full_order_history(order_id)

    text = f"История заявки #{order_id}\n"
    text += "=" * 50 + "\n\n"

    text += "СТАТУСЫ:\n"
    for h in history['status_history']:
        text += f"{h['changed_at']}: {h['old_status']} → {h['new_status']}\n"

    text += "\nИЗМЕНЕНИЯ:\n"
    for h in history['field_history']:
        text += f"{h['changed_at']}: {h['field_name']}\n"

    return text
```

### Пример 3: Статистика по удаленным заявкам

```python
async def get_deletion_statistics():
    """Статистика удаленных заявок"""
    order_repo = OrderRepositoryExtended(db.connection)

    # Все заявки
    all_stats = await order_repo.get_statistics(include_deleted=True)

    # Только активные
    active_stats = await order_repo.get_statistics(include_deleted=False)

    deleted_count = all_stats['total'] - active_stats['total']

    print(f"Всего заявок: {all_stats['total']}")
    print(f"Активных: {active_stats['total']}")
    print(f"Удалённых: {deleted_count}")
    print(f"% удаленных: {deleted_count / all_stats['total'] * 100:.1f}%")
```

---

## 🛠️ Интеграция в существующие handlers

### Добавление истории к просмотру заявки

```python
from app.handlers.admin_history import get_history_keyboard

@router.callback_query(F.data.startswith("view_order:"))
async def view_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])

    # ... существующий код просмотра заявки ...

    # Добавляем кнопку "История"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 История", callback_data=f"history_menu:{order_id}")],
        # ... другие кнопки ...
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
```

### Добавление поиска в меню диспетчера

```python
@router.message(F.text == "🔍 Поиск")
async def show_search_menu(message: Message):
    await message.answer(
        "🔍 <b>Поиск заявок</b>\n\n"
        "Отправьте запрос для поиска:\n"
        "• Тип техники (например: холодильник)\n"
        "• Имя клиента\n"
        "• Номер телефона\n\n"
        "Или используйте команду:\n"
        "/search <запрос>",
        parse_mode="HTML"
    )
```

---

## ⚙️ Настройка

### Ограничение результатов поиска

В коде можно настроить лимиты:

```python
# В search_service.py
DEFAULT_SEARCH_LIMIT = 50  # По умолчанию
MAX_SEARCH_LIMIT = 200     # Максимум

# Использование
orders = await search_service.search(query="...", limit=100)
```

### Пагинация удаленных заявок

```python
# Страница 0 (первые 10)
page_1 = await order_repo.get_deleted_orders(limit=10, offset=0)

# Страница 1 (следующие 10)
page_2 = await order_repo.get_deleted_orders(limit=10, offset=10)

# Страница 2 (следующие 10)
page_3 = await order_repo.get_deleted_orders(limit=10, offset=20)
```

---

## 📱 Примеры использования для пользователей

### Сценарий 1: Поиск старой заявки клиента

1. Клиент звонит и говорит номер телефона
2. Диспетчер: `/search 79991234567`
3. Бот показывает все заявки этого клиента
4. Диспетчер выбирает нужную и смотрит историю: `/history 123`

### Сценарий 2: Восстановление случайно удаленной заявки

1. Администратор: `/deleted`
2. Находит нужную заявку в списке
3. Нажимает кнопку "✅ Восстановить" или `/restore_123`
4. Заявка восстановлена!

### Сценарий 3: Анализ изменений в заявке

1. Мастер говорит, что данные неверные
2. Администратор: `/history 456`
3. Выбирает "🔄 История изменений"
4. Видит, кто и когда изменил данные
5. Связывается с ответственным

---

## 🎓 Лучшие практики

### ✅ Рекомендуется

1. **Используйте поиск** перед созданием новой заявки
2. **Проверяйте историю** при спорных ситуациях
3. **Восстанавливайте**, а не создавайте заново
4. **Просматривайте аудит** для контроля действий

### ❌ Не рекомендуется

1. ❌ Не удаляйте заявки без необходимости
2. ❌ Не создавайте дубликаты (используйте поиск!)
3. ❌ Не изменяйте важные данные без записи в заметках

---

## 📚 Связанные документы

- [PERMANENT_STORAGE_GUIDE.md](./PERMANENT_STORAGE_GUIDE.md) - Полное руководство
- [PERMANENT_STORAGE_EXAMPLES.md](./PERMANENT_STORAGE_EXAMPLES.md) - Примеры кода
- [QUICKSTART_PERMANENT_STORAGE.md](./QUICKSTART_PERMANENT_STORAGE.md) - Быстрый старт

---

## ❓ FAQ

**Q: Как найти заявку, если помню только имя клиента?**
A: `/search Иванов` - поиск по имени

**Q: Можно ли восстановить заявку, удаленную месяц назад?**
A: Да! Все удаленные заявки хранятся вечно. `/deleted` → найти → восстановить

**Q: Кто может видеть историю изменений?**
A: ADMIN и DISPATCHER могут видеть полную историю

**Q: Сохраняется ли история после восстановления?**
A: Да! История сохраняется полностью

**Q: Как найти все заявки конкретного клиента?**
A: `/search <телефон>` или `/search <имя>`

---

**Версия:** 1.0
**Дата:** 20.10.2025
**Статус:** ✅ Готово к использованию
