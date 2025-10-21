# 🔐 Руководство по шифрованию данных

## Обзор

Проект использует **симметричное шифрование Fernet** (на основе AES-128) для защиты персональных данных:
- Телефонные номера
- ФИО клиентов
- Адреса
- Другие чувствительные данные

## Проверка работы шифрования

### Быстрая проверка

Запустите тестовый скрипт:

```bash
python scripts/test_encryption.py
```

Скрипт проверит:
- ✅ Наличие ключа шифрования
- ✅ Базовое шифрование/дешифрование
- ✅ Граничные случаи (пустые строки, спецсимволы)
- ✅ Определение зашифрованных данных
- ✅ Корректность работы singleton паттерна

### Ожидаемый результат

Если всё работает правильно, вы увидите:

```
🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐
  ТЕСТИРОВАНИЕ ШИФРОВАНИЯ ДАННЫХ
🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐🔐

============================================================
  ПРОВЕРКА КЛЮЧА ШИФРОВАНИЯ
============================================================
✅ ENCRYPTION_KEY найден в переменных окружения

============================================================
  БАЗОВЫЙ ТЕСТ ШИФРОВАНИЯ
============================================================
📝 Тест: Обычная строка
   Исходные данные: Тестовый текст
   Зашифровано: Z0ZCQnlKSGN...
   Расшифровано: Тестовый текст
   ✅ УСПЕШНО: Данные совпадают

🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!
```

## Настройка ключа шифрования

### Для локальной разработки

1. Запустите скрипт генерации ключа:
   ```bash
   python scripts/test_encryption.py
   ```

2. Скопируйте сгенерированный ключ из вывода:
   ```
   🔑 Новый ключ шифрования:
      abc123def456...
   ```

3. Добавьте в `.env` файл:
   ```env
   ENCRYPTION_KEY=abc123def456...
   ```

### Для production

⚠️ **ВАЖНО**: Используйте уникальный ключ для production!

1. На сервере запустите:
   ```bash
   python scripts/test_encryption.py
   ```

2. Сохраните сгенерированный ключ в безопасном месте (password manager)

3. Добавьте в `env.production`:
   ```env
   ENCRYPTION_KEY=ваш_уникальный_ключ
   ```

4. Перезапустите бот:
   ```bash
   docker compose -f docker/docker-compose.prod.yml restart
   ```

## Проверка в базе данных

### Проверка зашифрованных данных

Если шифрование включено, данные в БД будут выглядеть так:

```sql
-- Незашифрованные данные (старые)
SELECT phone FROM orders WHERE id = 1;
-- Результат: +79991234567

-- Зашифрованные данные (новые)
SELECT phone FROM orders WHERE id = 2;
-- Результат: Z0ZCQnlKSGN5aDViS0liUWRDZz09...
```

### Проверка через скрипт

Создайте скрипт `check_encryption_in_db.py`:

```python
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from app.database import Database
from app.utils.encryption import is_encrypted

load_dotenv()

async def check_db():
    db = Database()
    await db.connect()
    
    cursor = await db.connection.execute(
        "SELECT id, phone, client_name FROM orders LIMIT 10"
    )
    rows = await cursor.fetchall()
    
    print("Проверка шифрования в БД:")
    print("-" * 60)
    
    for row in rows:
        order_id, phone, client_name = row['id'], row['phone'], row['client_name']
        
        phone_encrypted = is_encrypted(phone) if phone else None
        name_encrypted = is_encrypted(client_name) if client_name else None
        
        print(f"Заявка #{order_id}:")
        print(f"  Телефон: {'🔐 Зашифрован' if phone_encrypted else '⚠️  Не зашифрован'}")
        print(f"  Имя: {'🔐 Зашифровано' if name_encrypted else '⚠️  Не зашифровано'}")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_db())
```

## Интеграция в код

### Использование шифрования

```python
from app.utils.encryption import encrypt, decrypt, is_encrypted

# Шифрование при сохранении
encrypted_phone = encrypt(phone_number)
await db.connection.execute(
    "INSERT INTO orders (phone) VALUES (?)",
    (encrypted_phone,)
)

# Дешифрование при чтении
row = await cursor.fetchone()
phone = decrypt(row['phone'])

# Проверка, зашифрованы ли данные
if not is_encrypted(phone):
    # Данные не зашифрованы, нужно зашифровать
    encrypted = encrypt(phone)
```

### Миграция существующих данных

Для шифрования существующих данных создайте миграцию:

```python
from app.utils.encryption import encrypt, is_encrypted

async def migrate_encrypt_orders():
    """Шифрование существующих заявок"""
    db = Database()
    await db.connect()
    
    cursor = await db.connection.execute(
        "SELECT id, phone, client_name, address FROM orders"
    )
    rows = await cursor.fetchall()
    
    for row in rows:
        updates = {}
        
        # Шифруем телефон если не зашифрован
        if row['phone'] and not is_encrypted(row['phone']):
            updates['phone'] = encrypt(row['phone'])
        
        # Шифруем имя если не зашифровано
        if row['client_name'] and not is_encrypted(row['client_name']):
            updates['client_name'] = encrypt(row['client_name'])
        
        # Шифруем адрес если не зашифрован
        if row['address'] and not is_encrypted(row['address']):
            updates['address'] = encrypt(row['address'])
        
        if updates:
            set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
            await db.connection.execute(
                f"UPDATE orders SET {set_clause} WHERE id = ?",
                (*updates.values(), row['id'])
            )
    
    await db.connection.commit()
    await db.disconnect()
```

## Безопасность

### Хранение ключа

⚠️ **НИКОГДА**:
- Не коммитьте ключ в Git
- Не храните в открытом виде
- Не используйте один ключ для разных окружений

✅ **ВСЕГДА**:
- Храните ключ в переменных окружения
- Используйте разные ключи для dev/prod
- Храните резервную копию ключа в безопасном месте
- Используйте password manager для хранения

### Ротация ключей

Если ключ скомпрометирован:

1. Создайте новый ключ
2. Расшифруйте все данные старым ключом
3. Зашифруйте заново новым ключом
4. Обновите переменную окружения
5. Перезапустите приложение

### Резервное копирование

⚠️ **ВАЖНО**: Без ключа данные не могут быть расшифрованы!

- Храните резервную копию ключа отдельно от БД
- Используйте разные методы хранения (файл, password manager, vault)
- Документируйте местоположение ключа для команды

## Производительность

### Влияние на производительность

- Шифрование: ~0.1-0.5 мс на операцию
- Дешифрование: ~0.1-0.5 мс на операцию
- Влияние на пользователя: незаметно

### Оптимизация

- Шифруйте только чувствительные данные
- Используйте singleton паттерн (уже реализовано)
- Кешируйте расшифрованные данные при необходимости

## Troubleshooting

### Ошибка: "ENCRYPTION_KEY not found"

**Проблема**: Ключ не установлен в переменных окружения

**Решение**:
1. Сгенерируйте ключ: `python scripts/test_encryption.py`
2. Добавьте в `.env` или `env.production`
3. Перезапустите приложение

### Ошибка: "Invalid token" при дешифровании

**Проблема**: Данные зашифрованы другим ключом или повреждены

**Решение**:
1. Проверьте, что используется правильный ключ
2. Проверьте, не изменялся ли ключ после шифрования
3. Проверьте целостность данных в БД

### Данные не дешифруются

**Проблема**: Ключ изменился после шифрования

**Решение**:
1. Восстановите старый ключ из резервной копии
2. Расшифруйте данные
3. Зашифруйте заново новым ключом

## Дополнительная информация

### Используемые технологии

- **cryptography**: Python библиотека для криптографии
- **Fernet**: Симметричное шифрование (AES-128 CBC + HMAC)
- **base64**: Кодирование зашифрованных данных

### Ссылки

- [Документация cryptography](https://cryptography.io/)
- [Fernet specification](https://github.com/fernet/spec/)
- [ГОСТ Р 50739-95](https://docs.cntd.ru/document/1200006482) - Российский стандарт по защите информации

## Checklist для production

- [ ] Сгенерирован уникальный ключ для production
- [ ] Ключ добавлен в `env.production`
- [ ] Ключ сохранен в password manager
- [ ] Резервная копия ключа создана
- [ ] Проведено тестирование: `python scripts/test_encryption.py`
- [ ] Все тесты прошли успешно
- [ ] Документировано местоположение ключа
- [ ] Настроен процесс ротации ключей

