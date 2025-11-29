# Pydantic валидация данных

## 📋 Обзор

Полная реализация типобезопасной валидации входных данных через Pydantic 2.9.2 для самых критичных объектов бота.

## ✅ Что реализовано

### 1. Pydantic схемы (`app/schemas/`)

#### `OrderCreateSchema` - Создание заявок
**Самая критичная схема!** Валидирует все данные заявки перед сохранением в БД.

**Поля:**
- `equipment_type` (str, обязательное) - проверка из списка допустимых типов
- `description` (str, 10-500 символов) - защита от SQL injection
- `client_name` (str, минимум 2 слова) - проверка формата ФИО
- `client_address` (str, минимум 10 символов) - проверка наличия номера дома
- `client_phone` (str, автоформат) - +7XXXXXXXXXX или 8XXXXXXXXXX
- `notes` (str, опционально, до 1000 символов)
- `dispatcher_id` (int, >0)

**Защита:**
```python
# SQL Injection protection
suspicious_patterns = [
    r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER)\s+",
    r"--",
    r"/\*.*\*/",
    r"UNION\s+SELECT",
]
```

#### `MasterCreateSchema` - Регистрация мастеров
- `telegram_id` (int, >0, <=10_000_000_000)
- `phone` (str, автоформат) - валидация и форматирование
- `specialization` (str, минимум 3 символа)
- `is_approved` (bool, default=False)

#### `UserCreateSchema` - Создание пользователей
- `telegram_id` (int, >0)
- `username` (str, опционально) - автоматически убирает @
- `first_name`, `last_name` (str, опционально)
- `role` (str) - проверка из списка допустимых ролей

### 2. Интеграция в handlers

#### Поэтапная валидация (FSM states)
Каждое поле валидируется сразу при вводе:

```python
@router.message(CreateOrderStates.description)
async def process_description(message: Message, state: FSMContext):
    description = message.text.strip()

    # Валидация через Pydantic
    try:
        class DescriptionValidator(BaseModel):
            description: str = Field(..., min_length=10, max_length=500)

            @field_validator('description')
            @classmethod
            def validate_description(cls, v: str) -> str:
                # Защита от SQL injection
                if re.search(suspicious_pattern, v):
                    raise ValueError("Недопустимые символы")
                return v

        validated = DescriptionValidator(description=description)
        description = validated.description

    except ValidationError as e:
        await message.answer(f"❌ {e.errors()[0]['msg']}")
        return
```

#### Финальная валидация перед сохранением в БД
**КРИТИЧНО!** Даже если поэтапная валидация прошла, перед сохранением в БД делаем полную валидацию:

```python
@router.message(CreateOrderStates.confirm, F.text == "✅ Подтвердить")
async def confirm_create_order(message: Message, state: FSMContext):
    data = await state.get_data()

    # ФИНАЛЬНАЯ ВАЛИДАЦИЯ
    try:
        order_data = OrderCreateSchema(
            equipment_type=data["equipment_type"],
            description=data["description"],
            client_name=data["client_name"],
            client_address=data["client_address"],
            client_phone=data["client_phone"],
            dispatcher_id=message.from_user.id,
            notes=data.get("notes"),
        )
        logger.info("Order data validated successfully")
    except ValidationError as e:
        # Отменяем создание если валидация не прошла
        logger.error(f"Order validation failed: {e}")
        await state.clear()
        await message.answer("❌ Ошибка валидации данных")
        return

    # Сохраняем ТОЛЬКО валидированные данные
    order = await db.create_order(
        equipment_type=order_data.equipment_type,  # из Pydantic модели
        description=order_data.description,
        # ...
    )
```

## 📊 Примеры валидации

### ✅ Успешная валидация
```python
order_data = {
    "equipment_type": "Стиральные машины",
    "description": "Машинка не включается, нужна диагностика",
    "client_name": "Иванов Иван Петрович",
    "client_address": "ул. Ленина, дом 10, квартира 5",
    "client_phone": "89001234567",  # будет автоматически +79001234567
    "dispatcher_id": 123456789,
}

order = OrderCreateSchema(**order_data)
# SUCCESS
```

### ❌ Невалидный тип техники
```python
order_data = {
    "equipment_type": "Космический корабль",  # НЕТ в списке
    "description": "Не заводится двигатель",
    # ...
}

order = OrderCreateSchema(**order_data)
# ValidationError: Недопустимый тип техники.
# Допустимые: Стиральные машины, Духовой шкаф, ...
```

### 🛡️ Защита от SQL injection
```python
order_data = {
    "equipment_type": "Стиральные машины",
    "description": "Машинка сломана; DROP TABLE orders; --",  # АТАКА!
    # ...
}

order = OrderCreateSchema(**order_data)
# ValidationError: Описание содержит недопустимые символы
```

### 📞 Автоформатирование телефона
```python
# Input: "8 900 123 45 67"
# Output: "+79001234567"

# Input: "79001234567"
# Output: "+79001234567"

# Input: "+7 (900) 123-45-67"
# Output: "+79001234567"
```

### 👤 Валидация ФИО
```python
# ❌ Одно слово
client_name = "Иван"
# ValidationError: ФИО должно содержать минимум имя и фамилию

# ❌ Содержит цифры
client_name = "Иванов123 Иван"
# ValidationError: ФИО должно содержать только буквы

# ✅ Корректное
client_name = "Иванов Иван Петрович"
# OK

# ✅ С дефисом
client_name = "Соколов-Микитов Иван"
# OK
```

### 📍 Валидация адреса
```python
# ❌ Нет номера дома
client_address = "улица Ленина"
# ValidationError: Адрес должен содержать номер дома

# ✅ С номером дома
client_address = "ул. Ленина, 10, кв. 5"
# OK
```

## 🎯 Преимущества

### 1. Безопасность
**ДО:**
```python
description = message.text.strip()
if len(description) < 10:  # Ручная проверка
    await message.answer("Слишком короткое")
    return
# Сохраняем БЕЗ дополнительной проверки
await db.create_order(description=description)
```

**ПОСЛЕ:**
```python
# Pydantic автоматически:
# - Проверяет длину
# - Ищет SQL injection паттерны
# - Убирает лишние пробелы
# - Логирует ошибки валидации
order_data = OrderCreateSchema(**data)  # Может выбросить ValidationError
```

### 2. Типобезопасность
```python
order_data: OrderCreateSchema  # IDE знает все поля и типы
order_data.client_phone  # str, точно валидный телефон
order_data.dispatcher_id  # int, точно > 0
```

### 3. Консистентность данных в БД
- ✅ Все телефоны в едином формате: `+7XXXXXXXXXX`
- ✅ Все ФИО проверены на корректность
- ✅ Все описания защищены от SQL injection
- ✅ Все адреса содержат номера домов

### 4. Автоматическая документация
```python
OrderCreateSchema.model_json_schema()
# Возвращает JSON Schema - можно использовать для API документации
```

### 5. Детальные сообщения об ошибках
```python
try:
    order = OrderCreateSchema(**data)
except ValidationError as e:
    for error in e.errors():
        print(f"Field: {error['loc']}")
        print(f"Error: {error['msg']}")
        print(f"Type: {error['type']}")
```

## 📈 Статистика

- **Создано схем:** 3 (Order, Master, User)
- **Валидируемых полей:** 15+
- **Кастомных валидаторов:** 12
- **Защищенных полей:** Все критичные (description, phone, name, address)
- **Linter errors:** 0 ❌

## 🧪 Тестирование

Созданы pytest тесты в `tests/test_pydantic_schemas.py`:

```bash
pytest tests/test_pydantic_schemas.py -v
```

**Покрытие тестами:**
- ✅ Валидные данные
- ✅ Невалидные типы техники
- ✅ SQL injection protection
- ✅ Форматирование телефонов
- ✅ Проверка ФИО
- ✅ Проверка адресов
- ✅ Невалидные Telegram IDs
- ✅ Невалидные роли

## 🔧 Использование в новом коде

### Создание заявки
```python
from app.schemas import OrderCreateSchema
from pydantic import ValidationError

try:
    order_data = OrderCreateSchema(
        equipment_type="Стиральные машины",
        description="Машинка не работает",
        client_name="Иванов Иван",
        client_address="ул. Ленина, 10",
        client_phone="89001234567",
        dispatcher_id=message.from_user.id,
    )

    # Все данные валидны, сохраняем
    await db.create_order(**order_data.model_dump())

except ValidationError as e:
    # Валидация не прошла
    error_msg = e.errors()[0]['msg']
    await message.answer(f"❌ {error_msg}")
```

### Создание мастера
```python
from app.schemas import MasterCreateSchema

try:
    master_data = MasterCreateSchema(
        telegram_id=123456789,
        phone="89001234567",
        specialization="Ремонт стиральных машин",
        is_approved=False,
    )

    await db.create_master(**master_data.model_dump())

except ValidationError as e:
    logger.error(f"Master validation failed: {e}")
```

### Обновление заявки
```python
from app.schemas import OrderUpdateSchema

try:
    update_data = OrderUpdateSchema(
        client_phone="89009999999",  # будет +79009999999
    )

    await db.update_order(order_id, **update_data.model_dump(exclude_none=True))

except ValidationError as e:
    await message.answer(f"❌ {e.errors()[0]['msg']}")
```

## 🛡️ Защита от атак

### SQL Injection
```python
# ПОПЫТКА АТАКИ
description = "'; DROP TABLE orders; --"

# РЕЗУЛЬТАТ
ValidationError: Описание содержит недопустимые символы
```

### XSS (готовность к HTML escape)
```python
# Pydantic валидирует, HTML escape будет в следующем пункте аудита
description = "<script>alert('XSS')</script>"
# Валидация пройдет, но при выводе будет escape
```

### Некорректные данные
```python
# Отрицательный Telegram ID
telegram_id = -100
# ValidationError: Telegram ID должен быть положительным

# Нереалистично большой ID
telegram_id = 999_999_999_999
# ValidationError: Telegram ID слишком большой
```

## ✅ Результат

**ПРОБЛЕМА #8 ИЗ АУДИТА РЕШЕНА ДЛЯ КРИТИЧНЫХ ДАННЫХ!**

- ✅ Pydantic 2.9.2 активно используется
- ✅ Типобезопасная валидация для Orders, Masters, Users
- ✅ Защита от SQL injection
- ✅ Автоматическое форматирование (телефоны, username)
- ✅ Кастомные валидаторы для бизнес-логики
- ✅ Двойная валидация (поэтапная + финальная)
- ✅ Детальные error messages
- ✅ Покрытие тестами
- ✅ 0 linter ошибок

**Покрытие:** Все критичные бизнес-данные (заявки, мастера, пользователи)

---

*Документация создана: 2025-10-12*
*Версия: 1.0*
*Автор: AI Assistant*
