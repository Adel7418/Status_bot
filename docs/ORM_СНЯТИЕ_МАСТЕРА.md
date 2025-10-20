# ✅ ORM - Исправлено снятие мастера с заявки

**Дата:** 20.10.2025 23:15  
**Статус:** ✅ Исправлено

---

## 🐛 Проблема

**Ошибка при снятии мастера с заявки:**
```
AttributeError: 'ORMDatabase' object has no attribute 'connection'
```

**Место:** `app/handlers/dispatcher.py:1341`

**Код:**
```python
await db.connection.execute(
    "UPDATE orders SET status = ?, assigned_master_id = NULL WHERE id = ?",
    (OrderStatus.NEW, order_id),
)
await db.connection.commit()
```

**Причина:** В ORM нет прямого доступа к `connection`, нужно использовать методы ORM.

---

## ✅ Решение

### 1. Добавлен метод в ORMDatabase

**Файл:** `app/database/orm_database.py`

```python
async def unassign_master_from_order(self, order_id: int) -> bool:
    """Снятие мастера с заявки"""
    async with self.get_session() as session:
        # Получаем заявку
        stmt = select(Order).where(Order.id == order_id)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            logger.error(f"Заявка #{order_id} не найдена")
            return False

        # Снимаем мастера и возвращаем в NEW
        order.assigned_master_id = None
        order.status = OrderStatus.NEW
        order.updated_at = get_now()
        order.version += 1

        await session.commit()

        logger.info(f"Мастер снят с заявки #{order_id}")
        return True
```

---

### 2. Исправлены все вызовы

**Файлы:**
- `app/handlers/dispatcher.py` - снятие мастера диспетчером
- `app/handlers/master.py` - отказ мастера от заявки
- `app/handlers/group_interaction.py` - отказ мастера в группе

**Было:**
```python
await db.connection.execute(
    "UPDATE orders SET status = ?, assigned_master_id = NULL WHERE id = ?",
    (OrderStatus.NEW, order_id),
)
await db.connection.commit()
```

**Стало (ORM compatible):**
```python
if hasattr(db, 'unassign_master_from_order'):
    # ORM: используем специальный метод
    await db.unassign_master_from_order(order_id)
else:
    # Legacy: прямой SQL
    await db.connection.execute(
        "UPDATE orders SET status = ?, assigned_master_id = NULL WHERE id = ?",
        (OrderStatus.NEW, order_id),
    )
    await db.connection.commit()
```

---

## 📊 Исправленные места

### 1. Dispatcher Handler (3 сценария)
- ✅ Снятие мастера диспетчером
- ✅ Переназначение мастера
- ✅ Отмена заявки

### 2. Master Handler (2 сценария)
- ✅ Отказ мастера от заявки
- ✅ Возврат заявки в пул

### 3. Group Handler (1 сценарий)
- ✅ Отказ мастера в рабочей группе

---

## 🎯 Преимущества нового метода

**ORM метод `unassign_master_from_order`:**
- ✅ Автоматическое обновление `updated_at`
- ✅ Автоматический инкремент `version`
- ✅ Транзакционность через session
- ✅ Логирование операции
- ✅ Проверка существования заявки
- ✅ Защита от SQL injection

**Legacy SQL:**
- ⚠️ Прямой доступ к connection
- ⚠️ Ручное управление транзакциями
- ⚠️ Нет автоматического версионирования

---

## 📦 Git Коммиты

```
0c4e8d1 fix: add ORM method for unassigning master from order
406a823 fix: add ORM compatibility for unassigning master in master and group handlers
```

**Push:**
```
To https://github.com/Adel7418/Status_bot.git
   fe0900d..406a823  main -> main
```

---

## ✅ Проверка

**Тестирование:**
1. ✅ Снятие мастера диспетчером
2. ✅ Отказ мастера от заявки (личка)
3. ✅ Отказ мастера от заявки (группа)

**Все сценарии работают!**

---

## 🚀 Статус

**ORM полностью работает!**

- ✅ Назначение мастера
- ✅ Снятие мастера
- ✅ Переназначение мастера
- ✅ Отказ мастера
- ✅ Все уведомления
- ✅ Все логи

---

**Версия:** 3.1 с ORM  
**Статус:** ✅ ВСЕ РАБОТАЕТ!

