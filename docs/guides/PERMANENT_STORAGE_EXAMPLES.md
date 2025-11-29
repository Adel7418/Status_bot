# 📝 Примеры использования постоянного хранения

## 🎯 Быстрый старт

### 1. Использование расширенного репозитория

```python
from app.repositories.order_repository_extended import OrderRepositoryExtended
from app.database.db import Database

# Инициализация
db = Database()
await db.connect()
order_repo = OrderRepositoryExtended(db.connection)

# Создание заявки (как обычно)
order = await order_repo.create(
    equipment_type="Холодильник",
    description="Не морозит",
    client_name="Иван Иванов",
    client_address="Москва, ул. Ленина 1",
    client_phone="79991234567",
    dispatcher_id=123456789
)
print(f"✅ Создана заявка #{order.id}")

# Получение заявки (только активные)
order = await order_repo.get_by_id(1)

# Получение заявки (включая удаленные)
order = await order_repo.get_by_id(1, include_deleted=True)

# Мягкое удаление
success = await order_repo.soft_delete(
    order_id=1,
    deleted_by=123456789,
    reason="Клиент отменил"
)

# Восстановление удаленной заявки
success = await order_repo.restore(
    order_id=1,
    restored_by=123456789
)
```

### 2. Расширенный поиск

```python
from app.services.search_service import SearchService

# Инициализация
search_service = SearchService(order_repo)

# Текстовый поиск
orders = await search_service.search(
    query="холодильник",
    limit=20
)

# Поиск с фильтрами
orders = await search_service.search(
    filters={
        "status": "COMPLETED",
        "master_id": 5,
        "date_from": datetime(2025, 1, 1),
        "date_to": datetime(2025, 12, 31)
    }
)

# Поиск по телефону клиента
orders = await search_service.search_by_client_phone("79991234567")

# Поиск удаленных заявок
deleted_orders = await search_service.search_deleted_orders(limit=50)
```

### 3. Полная история заявки

```python
# Получение полной истории
history = await search_service.get_full_order_history(order_id=1)

print(f"Заявка #{history['order_id']}")
print(f"\n📊 История статусов ({len(history['status_history'])} записей):")
for h in history['status_history']:
    print(f"  {h['changed_at']}: {h['old_status']} → {h['new_status']}")

print(f"\n🔄 История изменений ({len(history['field_history'])} записей):")
for h in history['field_history']:
    print(f"  {h['changed_at']}: {h['field_name']}")
    print(f"    Было: {h['old_value']}")
    print(f"    Стало: {h['new_value']}")

print(f"\n📝 Аудит ({len(history['audit_logs'])} записей):")
for log in history['audit_logs']:
    print(f"  {log['timestamp']}: {log['action']}")
    print(f"    {log['details']}")
```

### 4. Шифрование данных

```python
from app.utils.encryption import encrypt, decrypt

# Шифрование при создании заявки
encrypted_phone = encrypt("79991234567")
encrypted_address = encrypt("Москва, ул. Ленина 1")

await db.connection.execute(
    "INSERT INTO orders (client_phone, client_address, ...) VALUES (?, ?, ...)",
    (encrypted_phone, encrypted_address, ...)
)

# Дешифрование при чтении
cursor = await db.connection.execute("SELECT * FROM orders WHERE id = ?", (1,))
row = await cursor.fetchone()

decrypted_phone = decrypt(row['client_phone'])
decrypted_address = decrypt(row['client_address'])

print(f"📞 Телефон: {decrypted_phone}")
print(f"📍 Адрес: {decrypted_address}")
```

---

## 🔍 Продвинутые примеры

### Пример 1: Админская панель для просмотра истории

```python
from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data.startswith("view_order_history:"))
async def view_order_history(callback: CallbackQuery):
    """Просмотр полной истории заявки"""
    order_id = int(callback.data.split(":")[1])

    # Получаем историю
    search_service = get_search_service()  # Ваша функция получения сервиса
    history = await search_service.get_full_order_history(order_id)

    # Форматируем сообщение
    message = f"📋 <b>История заявки #{order_id}</b>\n\n"

    # Статусы
    message += f"📊 <b>Изменения статусов:</b>\n"
    for h in history['status_history'][:5]:  # Последние 5
        message += f"  {h['changed_at'].strftime('%d.%m %H:%M')}: "
        message += f"{h['old_status']} → {h['new_status']}\n"

    # Изменения полей
    if history['field_history']:
        message += f"\n🔄 <b>Изменения данных:</b>\n"
        for h in history['field_history'][:3]:  # Последние 3
            message += f"  {h['field_name']}: "
            message += f"{h['old_value'][:20]} → {h['new_value'][:20]}\n"

    await callback.message.edit_text(message, parse_mode="HTML")
```

### Пример 2: Восстановление удаленной заявки

```python
@router.callback_query(F.data.startswith("restore_order:"))
async def restore_deleted_order(callback: CallbackQuery):
    """Восстановление удаленной заявки"""
    order_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    # Восстанавливаем
    order_repo = get_order_repo()
    success = await order_repo.restore(order_id, restored_by=user_id)

    if success:
        await callback.answer("✅ Заявка восстановлена!", show_alert=True)

        # Отправляем уведомление в группу
        order = await order_repo.get_by_id(order_id)
        notification = f"🔄 Заявка #{order_id} восстановлена\n"
        notification += f"Восстановил: {callback.from_user.first_name}"

        await callback.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=notification
        )
    else:
        await callback.answer("❌ Ошибка восстановления", show_alert=True)
```

### Пример 3: Поиск заявок с пагинацией

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def show_search_results(
    message: Message,
    query: str,
    page: int = 0,
    page_size: int = 10
):
    """Показать результаты поиска с пагинацией"""
    search_service = get_search_service()

    # Поиск
    all_orders = await search_service.search(query=query, limit=100)

    # Пагинация
    start = page * page_size
    end = start + page_size
    orders = all_orders[start:end]

    if not orders:
        await message.answer("🔍 Ничего не найдено")
        return

    # Форматируем результаты
    text = f"🔍 <b>Результаты поиска:</b> \"{query}\"\n"
    text += f"Найдено: {len(all_orders)}, показано: {start+1}-{min(end, len(all_orders))}\n\n"

    for order in orders:
        text += f"📋 <b>#{order.id}</b> - {order.equipment_type}\n"
        text += f"  Статус: {order.status}\n"
        text += f"  Клиент: {order.client_name}\n\n"

    # Кнопки пагинации
    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"search:{query}:{page-1}"
            )
        )

    if end < len(all_orders):
        buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"search:{query}:{page+1}"
            )
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
```

### Пример 4: Экспорт истории в Excel

```python
from openpyxl import Workbook
from datetime import datetime

async def export_order_history_to_excel(order_id: int) -> str:
    """
    Экспорт полной истории заявки в Excel

    Returns:
        Путь к созданному файлу
    """
    search_service = get_search_service()
    history = await search_service.get_full_order_history(order_id)

    # Создаем книгу
    wb = Workbook()

    # Лист 1: История статусов
    ws1 = wb.active
    ws1.title = "Статусы"
    ws1.append(["Дата/Время", "Старый статус", "Новый статус", "Кто изменил", "Заметки"])

    for h in history['status_history']:
        ws1.append([
            h['changed_at'],
            h['old_status'],
            h['new_status'],
            h.get('username', 'Система'),
            h.get('notes', '')
        ])

    # Лист 2: История изменений
    ws2 = wb.create_sheet("Изменения")
    ws2.append(["Дата/Время", "Поле", "Старое значение", "Новое значение", "Кто изменил"])

    for h in history['field_history']:
        ws2.append([
            h['changed_at'],
            h['field_name'],
            h['old_value'],
            h['new_value'],
            h.get('username', 'Система')
        ])

    # Лист 3: Аудит
    ws3 = wb.create_sheet("Аудит")
    ws3.append(["Дата/Время", "Действие", "Детали", "Пользователь"])

    for log in history['audit_logs']:
        ws3.append([
            log['timestamp'],
            log['action'],
            log['details'],
            log.get('username', 'Система')
        ])

    # Сохраняем
    filename = f"order_{order_id}_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = f"reports/{filename}"
    wb.save(filepath)

    return filepath
```

---

## 🔐 Примеры шифрования

### Пример 1: Интеграция шифрования в репозиторий

```python
from app.utils.encryption import encrypt, decrypt

class OrderRepositoryWithEncryption(OrderRepositoryExtended):
    """Репозиторий с автоматическим шифрованием"""

    async def create(
        self,
        equipment_type: str,
        description: str,
        client_name: str,
        client_address: str,
        client_phone: str,
        dispatcher_id: int,
        notes: str | None = None,
        scheduled_time: str | None = None,
    ) -> Order:
        """Создание заявки с шифрованием персональных данных"""

        # Шифруем чувствительные данные
        encrypted_name = encrypt(client_name)
        encrypted_phone = encrypt(client_phone)
        encrypted_address = encrypt(client_address)

        # Создаем заявку
        now = get_now()
        cursor = await self._execute(
            """
            INSERT INTO orders (equipment_type, description, client_name, client_address,
                              client_phone, dispatcher_id, notes, scheduled_time, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                equipment_type,
                description,
                encrypted_name,
                encrypted_address,
                encrypted_phone,
                dispatcher_id,
                notes,
                scheduled_time,
                now.isoformat(),
                now.isoformat(),
            ),
        )
        await self.db.commit()

        # Возвращаем заявку с расшифрованными данными
        order = Order(
            id=cursor.lastrowid,
            equipment_type=equipment_type,
            description=description,
            client_name=client_name,  # Расшифрованное
            client_address=client_address,  # Расшифрованное
            client_phone=client_phone,  # Расшифрованное
            dispatcher_id=dispatcher_id,
            notes=notes,
            scheduled_time=scheduled_time,
            status=OrderStatus.NEW,
            created_at=now,
            updated_at=now,
        )

        logger.info(f"✅ Создана заявка #{order.id} с шифрованием")
        return order

    def _row_to_order(self, row) -> Order:
        """Преобразование строки с автоматическим дешифрованием"""
        order = super()._row_to_order(row)

        # Дешифруем персональные данные
        order.client_name = decrypt(order.client_name)
        order.client_phone = decrypt(order.client_phone)
        order.client_address = decrypt(order.client_address)

        return order
```

### Пример 2: Селективное шифрование

```python
# Шифруем только в production
import os

ENCRYPT_DATA = os.getenv("ENCRYPT_DATA", "false").lower() == "true"

def smart_encrypt(data: str) -> str:
    """Шифрование только в production"""
    if ENCRYPT_DATA:
        return encrypt(data)
    return data

def smart_decrypt(data: str) -> str:
    """Дешифрование только если нужно"""
    if ENCRYPT_DATA:
        return decrypt(data)
    return data
```

---

## 📊 Примеры статистики

### Получение статистики

```python
# Статистика по активным заявкам
stats = await order_repo.get_statistics(include_deleted=False)

print(f"Всего активных заявок: {stats['total']}")
print(f"Удаленных: {stats['deleted']}")
print("\nПо статусам:")
for status, count in stats['by_status'].items():
    print(f"  {status}: {count}")

# Результат:
# Всего активных заявок: 1523
# Удаленных: 47
# По статусам:
#   NEW: 12
#   ASSIGNED: 45
#   IN_PROGRESS: 78
#   COMPLETED: 1234
#   CLOSED: 154
```

---

## 🎯 Рекомендации по использованию

### ✅ Хорошие практики

1. **Всегда используйте `include_deleted=False` по умолчанию**
   ```python
   orders = await order_repo.get_all()  # Только активные
   ```

2. **Логируйте все важные действия**
   ```python
   await order_repo.soft_delete(1, user_id, reason="Дубликат")
   ```

3. **Ограничивайте результаты поиска**
   ```python
   orders = await search_service.search(query="...", limit=50)
   ```

4. **Используйте транзакции для критичных операций**
   ```python
   async with order_repo.transaction():
       await order_repo.soft_delete(1, user_id)
       await send_notification()
   ```

### ❌ Чего избегать

1. ❌ Не удаляйте заявки физически
2. ❌ Не делайте поиск без лимита
3. ❌ Не храните ключи шифрования в коде
4. ❌ Не забывайте про индексы при поиске

---

## 📚 Дополнительные ресурсы

- [PERMANENT_STORAGE_GUIDE.md](./PERMANENT_STORAGE_GUIDE.md) - Полное руководство
- [DB_AUDIT.md](./DB_AUDIT.md) - Аудит базы данных
- [API Reference](./API_REFERENCE.md) - Документация API

---

**Версия:** 1.0
**Дата:** 20.10.2025
