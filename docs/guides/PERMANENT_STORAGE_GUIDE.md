# 📚 Руководство по постоянному хранению заявок

## 🎯 Обзор решения

Ваша система **УЖЕ поддерживает** постоянное хранение всех заявок через несколько механизмов:

### ✅ Реализованные механизмы

1. **Soft Delete** (мягкое удаление) - поле `deleted_at`
2. **История статусов** - таблица `order_status_history`
3. **История изменений** - таблица `entity_history`
4. **Аудит действий** - таблица `audit_log`
5. **Версионирование** - поле `version` в каждой таблице

---

## 🔍 Как это работает

### 1. Soft Delete (Мягкое удаление)

**Что это:**
- Вместо физического удаления записи из БД, мы просто ставим метку времени в поле `deleted_at`
- Запись остается в БД навсегда, но "логически" удалена
- Можно в любой момент восстановить или посмотреть удаленные записи

**Текущая структура:**
```sql
-- В таблице orders
deleted_at DATETIME NULL  -- NULL = активна, NOT NULL = удалена
version INTEGER DEFAULT 1  -- Версия записи для отслеживания изменений
```

**Пример использования:**
```python
# Вместо DELETE FROM orders WHERE id = 123
# Делаем:
UPDATE orders SET deleted_at = '2025-10-20 12:00:00' WHERE id = 123

# Поиск только активных заявок
SELECT * FROM orders WHERE deleted_at IS NULL

# Поиск всех заявок (включая удаленные)
SELECT * FROM orders

# Восстановление удаленной заявки
UPDATE orders SET deleted_at = NULL WHERE id = 123
```

---

### 2. История изменений статусов

**Таблица:** `order_status_history`

Каждое изменение статуса заявки записывается в историю:

```sql
CREATE TABLE order_status_history (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    changed_by INTEGER,  -- Telegram ID пользователя
    changed_at DATETIME NOT NULL,
    notes TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (changed_by) REFERENCES users(telegram_id)
);
```

**Что фиксируется:**
- Кто изменил статус
- Когда изменил
- Старый и новый статус
- Дополнительные заметки

**Пример запроса истории:**
```python
# Получить всю историю изменений заявки #123
SELECT * FROM order_status_history
WHERE order_id = 123
ORDER BY changed_at DESC
```

---

### 3. История изменений полей

**Таблица:** `entity_history`

Отслеживает изменения любых полей в любых таблицах:

```sql
CREATE TABLE entity_history (
    id INTEGER PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,  -- orders, users, masters
    record_id INTEGER NOT NULL,       -- ID записи
    field_name VARCHAR(50) NOT NULL,  -- Название поля
    old_value TEXT,                   -- Старое значение
    new_value TEXT,                   -- Новое значение
    changed_by INTEGER,               -- Кто изменил
    changed_at DATETIME NOT NULL      -- Когда изменил
);
```

**Примеры:**
```python
# История изменения адреса клиента
SELECT * FROM entity_history
WHERE table_name = 'orders'
  AND record_id = 123
  AND field_name = 'client_address'
ORDER BY changed_at DESC

# Все изменения заявки #123
SELECT * FROM entity_history
WHERE table_name = 'orders'
  AND record_id = 123
ORDER BY changed_at DESC
```

---

### 4. Аудит действий пользователей

**Таблица:** `audit_log`

Логирует все важные действия пользователей:

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,              -- Telegram ID
    action VARCHAR(255) NOT NULL, -- Тип действия
    details TEXT,                 -- Детали в JSON
    timestamp DATETIME NOT NULL,
    deleted_at DATETIME
);
```

**Примеры логов:**
- Создание заявки
- Назначение мастера
- Изменение финансовых данных
- Экспорт отчетов

---

## 🔧 Внедрение в код

### Текущая проблема

Ваши репозитории еще не используют soft delete. Нужно обновить методы.

### Решение: Обновленный OrderRepository

Создадим расширенную версию репозитория с soft delete:

```python
# app/repositories/order_repository_extended.py

class OrderRepositoryExtended(OrderRepository):
    """Расширенный репозиторий с soft delete и полной историей"""

    # ===== SOFT DELETE =====

    async def soft_delete(self, order_id: int, deleted_by: int, reason: str = None) -> bool:
        """
        Мягкое удаление заявки

        Args:
            order_id: ID заявки
            deleted_by: Telegram ID пользователя
            reason: Причина удаления

        Returns:
            True если успешно
        """
        now = get_now()

        async with self.transaction():
            # Помечаем заявку как удаленную
            await self._execute(
                "UPDATE orders SET deleted_at = ?, version = version + 1 WHERE id = ?",
                (now.isoformat(), order_id)
            )

            # Логируем в audit_log
            await self._execute(
                """
                INSERT INTO audit_log (user_id, action, details, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (deleted_by, "ORDER_SOFT_DELETED",
                 f"Order #{order_id} deleted. Reason: {reason or 'Not specified'}",
                 now.isoformat())
            )

            # Сохраняем в entity_history
            await self._execute(
                """
                INSERT INTO entity_history
                (table_name, record_id, field_name, old_value, new_value, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ('orders', order_id, 'deleted_at', None, now.isoformat(), deleted_by, now.isoformat())
            )

        logger.info(f"Заявка #{order_id} мягко удалена пользователем {deleted_by}")
        return True

    async def restore(self, order_id: int, restored_by: int) -> bool:
        """
        Восстановление удаленной заявки

        Args:
            order_id: ID заявки
            restored_by: Telegram ID пользователя

        Returns:
            True если успешно
        """
        now = get_now()

        async with self.transaction():
            await self._execute(
                "UPDATE orders SET deleted_at = NULL, version = version + 1 WHERE id = ?",
                (order_id,)
            )

            await self._execute(
                """
                INSERT INTO audit_log (user_id, action, details, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (restored_by, "ORDER_RESTORED", f"Order #{order_id} restored", now.isoformat())
            )

        logger.info(f"Заявка #{order_id} восстановлена пользователем {restored_by}")
        return True

    # ===== ПОИСК С УЧЕТОМ DELETED =====

    async def get_by_id(self, order_id: int, include_deleted: bool = False) -> Order | None:
        """
        Получение заявки по ID

        Args:
            order_id: ID заявки
            include_deleted: Включать удаленные заявки
        """
        query = """
            SELECT o.*,
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE o.id = ?
        """

        if not include_deleted:
            query += " AND o.deleted_at IS NULL"

        row = await self._fetch_one(query, (order_id,))
        return self._row_to_order(row) if row else None

    async def get_all(
        self,
        status: str | None = None,
        master_id: int | None = None,
        limit: int | None = None,
        include_deleted: bool = False
    ) -> list[Order]:
        """
        Получение всех заявок с фильтрацией
        """
        query = """
            SELECT o.*,
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE 1=1
        """
        params = []

        if not include_deleted:
            query += " AND o.deleted_at IS NULL"

        if status:
            query += " AND o.status = ?"
            params.append(status)

        if master_id:
            query += " AND o.assigned_master_id = ?"
            params.append(master_id)

        query += " ORDER BY o.created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = await self._fetch_all(query, params)
        return [self._row_to_order(row) for row in rows]

    # ===== РАСШИРЕННЫЙ ПОИСК =====

    async def search_orders(
        self,
        search_query: str = None,
        status: str = None,
        master_id: int = None,
        client_name: str = None,
        client_phone: str = None,
        date_from: datetime = None,
        date_to: datetime = None,
        include_deleted: bool = False,
        limit: int = 100
    ) -> list[Order]:
        """
        Расширенный поиск заявок

        Args:
            search_query: Поисковый запрос (ищет в описании, адресе, типе техники)
            status: Фильтр по статусу
            master_id: Фильтр по мастеру
            client_name: Фильтр по имени клиента
            client_phone: Фильтр по телефону
            date_from: Дата создания от
            date_to: Дата создания до
            include_deleted: Включать удаленные
            limit: Максимальное количество результатов
        """
        query = """
            SELECT o.*,
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE 1=1
        """
        params = []

        if not include_deleted:
            query += " AND o.deleted_at IS NULL"

        if search_query:
            query += """ AND (
                o.description LIKE ? OR
                o.client_address LIKE ? OR
                o.equipment_type LIKE ?
            )"""
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        if status:
            query += " AND o.status = ?"
            params.append(status)

        if master_id:
            query += " AND o.assigned_master_id = ?"
            params.append(master_id)

        if client_name:
            query += " AND o.client_name LIKE ?"
            params.append(f"%{client_name}%")

        if client_phone:
            query += " AND o.client_phone LIKE ?"
            params.append(f"%{client_phone}%")

        if date_from:
            query += " AND o.created_at >= ?"
            params.append(date_from.isoformat())

        if date_to:
            query += " AND o.created_at <= ?"
            params.append(date_to.isoformat())

        query += " ORDER BY o.created_at DESC LIMIT ?"
        params.append(limit)

        rows = await self._fetch_all(query, params)
        return [self._row_to_order(row) for row in rows]

    # ===== ПОЛНАЯ ИСТОРИЯ ЗАЯВКИ =====

    async def get_full_history(self, order_id: int) -> dict:
        """
        Получение полной истории заявки

        Returns:
            Словарь с историей статусов, изменений полей и аудитом
        """
        # История статусов
        status_history = await self.get_status_history(order_id)

        # История изменений полей
        field_history = await self._fetch_all(
            """
            SELECT * FROM entity_history
            WHERE table_name = 'orders' AND record_id = ?
            ORDER BY changed_at DESC
            """,
            (order_id,)
        )

        # Аудит действий
        audit_logs = await self._fetch_all(
            """
            SELECT * FROM audit_log
            WHERE details LIKE ?
            ORDER BY timestamp DESC
            """,
            (f"%Order #{order_id}%",)
        )

        return {
            "order_id": order_id,
            "status_history": status_history,
            "field_history": [dict(row) for row in field_history],
            "audit_logs": [dict(row) for row in audit_logs]
        }
```

---

## 📊 Оптимизация производительности

### 1. Индексы для быстрого поиска

Ваши миграции УЖЕ содержат оптимизированные индексы:

```sql
-- Основные индексы (уже созданы)
CREATE INDEX idx_orders_deleted_at ON orders(deleted_at);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- Составные индексы для сложных запросов
CREATE INDEX idx_orders_status_created ON orders(status, created_at);
CREATE INDEX idx_orders_master_status ON orders(assigned_master_id, status);

-- Частичные индексы (только для активных записей)
CREATE INDEX idx_orders_active ON orders(deleted_at) WHERE deleted_at IS NULL;
```

### 2. Оптимизация запросов

**Плохой запрос:**
```sql
-- Медленно на больших объемах
SELECT * FROM orders
WHERE client_name LIKE '%Иван%'
ORDER BY created_at DESC
```

**Хороший запрос:**
```sql
-- Быстро благодаря индексу
SELECT * FROM orders
WHERE deleted_at IS NULL
  AND status = 'COMPLETED'
  AND created_at BETWEEN '2025-01-01' AND '2025-12-31'
ORDER BY created_at DESC
LIMIT 50
```

### 3. Архивирование старых заявок

Для PostgreSQL можно использовать партиционирование:

```sql
-- Партиционирование по годам
CREATE TABLE orders_2025 PARTITION OF orders
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE orders_2024 PARTITION OF orders
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

---

## 🔐 Шифрование данных

### 1. Шифрование на уровне приложения

**Использование:** Для персональных данных клиентов

```python
# app/utils/encryption.py

from cryptography.fernet import Fernet
import base64
import os

class DataEncryptor:
    """Класс для шифрования/дешифрования данных"""

    def __init__(self):
        # Получаем ключ из переменных окружения
        key = os.getenv("ENCRYPTION_KEY")

        if not key:
            # Генерируем новый ключ (только для dev!)
            key = Fernet.generate_key()
            print(f"⚠️  ENCRYPTION_KEY not found! Generated: {key.decode()}")
            print(f"⚠️  Add to .env: ENCRYPTION_KEY={key.decode()}")

        if isinstance(key, str):
            key = key.encode()

        self.cipher = Fernet(key)

    def encrypt(self, data: str) -> str:
        """
        Шифрование строки

        Args:
            data: Исходная строка

        Returns:
            Зашифрованная строка в base64
        """
        if not data:
            return data

        encrypted = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Дешифрование строки

        Args:
            encrypted_data: Зашифрованная строка

        Returns:
            Расшифрованная строка
        """
        if not encrypted_data:
            return encrypted_data

        decoded = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = self.cipher.decrypt(decoded)
        return decrypted.decode()

# Синглтон
encryptor = DataEncryptor()
```

**Использование в коде:**

```python
from app.utils.encryption import encryptor

# При создании заявки
async def create_order(...):
    # Шифруем чувствительные данные
    encrypted_phone = encryptor.encrypt(client_phone)
    encrypted_address = encryptor.encrypt(client_address)

    cursor = await self._execute(
        """
        INSERT INTO orders (client_phone, client_address, ...)
        VALUES (?, ?, ...)
        """,
        (encrypted_phone, encrypted_address, ...)
    )

# При получении заявки
async def get_order(order_id: int):
    order = await self._fetch_one(...)

    # Дешифруем при чтении
    order.client_phone = encryptor.decrypt(order.client_phone)
    order.client_address = encryptor.decrypt(order.client_address)

    return order
```

### 2. Шифрование на уровне БД (PostgreSQL)

```sql
-- Установка pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Шифрование при вставке
INSERT INTO orders (client_phone, client_address)
VALUES (
    pgp_sym_encrypt('79991234567', 'encryption-key'),
    pgp_sym_encrypt('Москва, ул. Ленина 1', 'encryption-key')
);

-- Дешифрование при выборке
SELECT
    id,
    pgp_sym_decrypt(client_phone::bytea, 'encryption-key') as client_phone,
    pgp_sym_decrypt(client_address::bytea, 'encryption-key') as client_address
FROM orders;
```

### 3. Хеширование (для поиска)

Для возможности поиска по зашифрованным данным:

```python
import hashlib

def hash_phone(phone: str) -> str:
    """Создание хеша телефона для индексации"""
    return hashlib.sha256(phone.encode()).hexdigest()

# В таблице orders
"""
client_phone TEXT,           -- Зашифрованный номер
client_phone_hash TEXT,      -- Хеш для поиска
"""

# При создании
phone_encrypted = encryptor.encrypt(client_phone)
phone_hash = hash_phone(client_phone)

# При поиске
search_hash = hash_phone(search_phone)
query = "SELECT * FROM orders WHERE client_phone_hash = ?"
```

### 4. Шифрование файлов (бэкапы)

```bash
# Шифрование бэкапа GPG
gpg --symmetric --cipher-algo AES256 backup.db

# Расшифровка
gpg --decrypt backup.db.gpg > backup.db
```

---

## 📋 План внедрения

### Этап 1: Обновление репозиториев (1-2 дня)

1. Обновить `OrderRepository`:
   - Добавить методы soft delete
   - Обновить все get методы с фильтром `deleted_at IS NULL`
   - Добавить методы восстановления

2. Обновить `UserRepository` и `MasterRepository` аналогично

### Этап 2: Шифрование (2-3 дня)

1. Создать `encryption.py` модуль
2. Добавить `ENCRYPTION_KEY` в `.env`
3. Обновить методы создания/чтения заявок
4. Миграция существующих данных (скрипт)

### Этап 3: Расширенный поиск (1-2 дня)

1. Создать `SearchService`
2. Добавить handler для поиска
3. Создать клавиатуры для фильтров

### Этап 4: Админ-панель для истории (2-3 дня)

1. Handler для просмотра полной истории заявки
2. Handler для восстановления удаленных заявок
3. Handler для экспорта истории в Excel

---

## 🎓 Рекомендации

### ✅ Лучшие практики

1. **Всегда используйте soft delete** для важных данных
2. **Логируйте все изменения** в audit_log
3. **Шифруйте персональные данные** (телефоны, адреса)
4. **Делайте регулярные бэкапы** (уже настроено)
5. **Используйте индексы** для быстрого поиска
6. **Ограничивайте результаты поиска** (LIMIT)

### ❌ Чего избегать

1. ❌ Физическое удаление заявок
2. ❌ Хранение ключей шифрования в коде
3. ❌ Поиск без индексов
4. ❌ Шифрование без хеширования (для поиска)
5. ❌ Отсутствие аудита действий

---

## 📈 Масштабирование

### При росте до 100,000+ заявок

1. **Партиционирование таблиц** (PostgreSQL)
2. **Архивирование старых заявок** (> 2 лет)
3. **Full-text search** (PostgreSQL FTS или Elasticsearch)
4. **Read replicas** для отчетов
5. **Кеширование** частых запросов (Redis)

---

## 🔗 Связанные документы

- [DB_AUDIT.md](./DB_AUDIT.md) - Аудит базы данных
- [ORM_MIGRATION_COMPLETE.md](./ORM_MIGRATION_COMPLETE.md) - Миграция на ORM
- [BACKUP_GUIDE.md](./BACKUP_GUIDE.md) - Резервное копирование
- [DATABASE_USAGE_GUIDE.md](./DATABASE_USAGE_GUIDE.md) - Использование БД

---

## ❓ FAQ

**Q: Сколько места займут заявки?**
A: ~10KB на заявку. 100,000 заявок = ~1GB

**Q: Как найти удаленные заявки?**
A: `SELECT * FROM orders WHERE deleted_at IS NOT NULL`

**Q: Можно ли восстановить заявку?**
A: Да, через `restore()` метод

**Q: Как экспортировать всю историю?**
A: Используйте `get_full_history()` и экспортируйте в Excel

**Q: Безопасно ли шифрование на уровне приложения?**
A: Да, если ключ хранится безопасно (не в коде, не в git)

---

## 📞 Контакты

По вопросам внедрения обращайтесь к разработчику системы.

**Версия документа:** 1.0
**Дата создания:** 20.10.2025
**Автор:** AI Assistant
