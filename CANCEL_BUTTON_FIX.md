# Исправление кнопки "❌ Отмена"

## Проблема
Кнопка "❌ Отмена" не работала на этапе ввода описания проблемы при создании заявки. Вместо отмены действия бот отправлял сообщение что описание слишком короткое.

## Причина
Обработчики состояний FSM в роутерах `dispatcher_router` и `admin_router` срабатывали раньше общего обработчика кнопки отмены из `common_router`, так как эти роутеры подключаются к диспетчеру раньше. Обработчики состояний перехватывали все текстовые сообщения, включая кнопку "❌ Отмена".

## Решение
Добавлены фильтры `F.text != "❌ Отмена"` ко всем обработчикам состояний, которые принимают текстовый ввод:

### Файл: `app/handlers/dispatcher.py`
- `process_description` - обработка описания проблемы (CreateOrderStates.description)
- `process_client_name` - обработка имени клиента (CreateOrderStates.client_name)
- `process_client_address` - обработка адреса клиента (CreateOrderStates.client_address)
- `process_client_phone` - обработка телефона клиента (CreateOrderStates.client_phone)
- `process_notes` - обработка заметок (CreateOrderStates.notes)

### Файл: `app/handlers/admin.py`
- `process_master_telegram_id` - обработка Telegram ID мастера (AddMasterStates.enter_telegram_id)
- `process_master_phone` - обработка телефона мастера (AddMasterStates.enter_phone)
- `process_master_specialization` - обработка специализации мастера (AddMasterStates.enter_specialization)

## Результат
Теперь кнопка "❌ Отмена" корректно работает на всех этапах создания заявки и добавления мастера. При нажатии на кнопку:
1. Очищается текущее состояние FSM
2. Отображается сообщение "❌ Действие отменено."
3. Возвращается главное меню соответствующее роли пользователя

## Дата исправления
12 октября 2025

