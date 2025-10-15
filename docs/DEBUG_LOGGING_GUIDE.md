# 🔍 Руководство по DEBUG логированию

## 📋 Включение DEBUG режима

### Для локального хоста:

1. **Создайте файл `.env` в корне проекта:**
```bash
DEV_MODE=true
LOG_LEVEL=DEBUG
BOT_TOKEN=your_actual_bot_token
ADMIN_IDS=your_admin_ids
DISPATCHER_IDS=your_dispatcher_ids
```

2. **Запустите бота:**
```bash
python bot.py
```

### Для production (сервера):

**НЕ включайте DEBUG режим!** На сервере используется Sentry для отслеживания ошибок.

```bash
DEV_MODE=false
LOG_LEVEL=INFO
SENTRY_DSN=your_sentry_dsn_here
```

## 📊 Что логируется в DEBUG режиме:

### ✅ Общие ошибки:
- User ID и username
- Тип ошибки
- Текст сообщения или callback_data
- Полный traceback
- Контекст выполнения

### ✅ Длительный ремонт (DR):
- `[DR] Starting DR process` - начало процесса
- `[DR] Order found` - проверка наличия заявки
- `[DR] Input text` - введенный текст
- `[DR] Found prepayment pattern` - найденная предоплата
- `[DR] Parsed - completion_date` - результат парсинга
- `[DR] Updating order` - обновление БД
- `[DR] Order updated successfully` - успех
- `[DR] Sending notification` - отправка уведомлений
- `[DR] ✅ Success` или `[DR] ❌ Error` - итог

### ✅ Назначение мастеров:
- Попытки отправки уведомлений
- Результаты отправки (группа/личка)
- Предупреждения если work_chat_id не установлен

## 🎯 Пример использования:

### Тестирование DR функции:

1. Запустите бота в DEBUG режиме
2. Создайте заявку
3. Назначьте мастера
4. Примите заявку
5. Обновите статус "На объекте"
6. Нажмите "⏳ Длительный ремонт"
7. Введите: `20.10.2025 предоплата 2000`

### Что увидите в логах:

```
[DR] Starting DR process for order #X by user Y
[DR] Order found: True, Master found: True
[DR] Transitioning to LongRepairStates.enter_completion_date_and_prepayment
[DR] Processing DR info from user Y
[DR] Order ID from state: X, FSM data: {'order_id': X}
[DR] Input text: '20.10.2025 предоплата 2000'
[DR] Found prepayment pattern: r'предоплат[аы]?\s+(\d+(?:[.,]\d+)?)', value: 2000
[DR] Parsed - completion_date: '20.10.2025', prepayment: 2000.0
[DR] Updating order #X: completion_date='20.10.2025', prepayment=2000.0
[DR] Order #X updated to DR status successfully
[DR] Sending notification to dispatcher Z
[DR] Dispatcher notification sent successfully
[DR] ✅ Order #X successfully marked as DR
[DR] State cleared and DB disconnected for order #X
```

## 📝 Просмотр логов:

```bash
# Последние 50 строк
tail -50 logs/bot.log

# Только DEBUG логи
grep "DEBUG" logs/bot.log | tail -20

# Только DR логи
grep "\[DR\]" logs/bot.log | tail -20

# Только ошибки
grep "ERROR\|❌" logs/bot.log | tail -20

# Мониторинг в реальном времени
tail -f logs/bot.log
```

## ⚠️ Важно:

- ✅ DEBUG режим **ТОЛЬКО** для локальной разработки
- ❌ **НЕ включайте** DEV_MODE=true на production сервере
- ✅ На сервере используйте Sentry для отслеживания ошибок
- ✅ Логи ротируются автоматически (макс 10MB, 5 файлов)

## 🎉 Преимущества:

- 🔍 Детальное отслеживание каждого шага
- 🐛 Быстрое обнаружение ошибок
- 📊 Полный контекст выполнения
- 🎯 Легкая отладка сложных процессов

