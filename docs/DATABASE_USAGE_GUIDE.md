# Руководство по работе с базой данных

## 📊 Обзор базы данных

База данных: `bot_database.db` (SQLite)

### Текущее состояние:
- 👥 **Пользователей:** 9
- 🔧 **Мастеров:** 6
- 📋 **Заявок:** 12
  - ✅ Завершено: 6
  - ❌ Отклонено: 3
  - 🆕 Новых: 2
  - 🏠 На объекте: 1

## 🔍 Способы просмотра базы данных

### Способ 1: DB Browser for SQLite (Рекомендуется) 🌟

**Установка:**
```powershell
winget install -e --id DBBrowserForSQLite.DBBrowserForSQLite
```

**Запуск:**
```powershell
Start-Process "C:\Program Files\DB Browser for SQLite\DB Browser for SQLite.exe" -ArgumentList "C:\Bot_test\telegram_repair_bot\bot_database.db"
```

Или просто откройте программу и выберите файл `bot_database.db`.

**Возможности:**
- ✅ Графический интерфейс
- ✅ Просмотр всех таблиц
- ✅ Редактирование данных
- ✅ Выполнение SQL-запросов
- ✅ Экспорт данных (CSV, JSON, SQL)
- ✅ Импорт данных
- ✅ Создание резервных копий

### Способ 2: Python-скрипт (Быстро) ⚡

**Создан файл:** `check_database.py`

**Запуск:**
```powershell
python check_database.py
```

**Что показывает:**
- 👥 Список всех пользователей с ролями
- 🔧 Список всех мастеров с контактами
- 📋 Последние 20 заявок
- 📊 Статистика по статусам заявок
- 🎭 Пользователи с множественными ролями (DISPATCHER+MASTER)

**Преимущества:**
- ✅ Быстрый запуск
- ✅ Красивый вывод в консоли
- ✅ Автоматическая проверка множественных ролей
- ✅ Не требует дополнительных программ

### Способ 3: SQLite в консоли (Для разработчиков)

**Подключение:**
```powershell
sqlite3 bot_database.db
```

**Полезные команды:**
```sql
-- Показать все таблицы
.tables

-- Показать структуру таблицы
.schema users

-- Выборка данных
SELECT * FROM users;
SELECT * FROM masters;
SELECT * FROM orders;

-- Выход
.quit
```

### Способ 4: VS Code расширение (Если используете VS Code)

**Установка расширения:**
1. Откройте VS Code
2. Нажмите Ctrl+Shift+X
3. Найдите "SQLite Viewer" или "SQLite"
4. Установите расширение

**Использование:**
1. Откройте `bot_database.db` в VS Code
2. Расширение автоматически откроет интерфейс просмотра

## 📋 Структура базы данных

### Таблица `users`
```sql
- id: INTEGER PRIMARY KEY
- telegram_id: INTEGER UNIQUE (ID пользователя в Telegram)
- username: TEXT (Username без @)
- first_name: TEXT (Имя)
- last_name: TEXT (Фамилия)
- role: TEXT (Роли через запятую: "DISPATCHER,MASTER")
- created_at: TIMESTAMP
```

### Таблица `masters`
```sql
- id: INTEGER PRIMARY KEY
- telegram_id: INTEGER UNIQUE (связь с users)
- phone: TEXT (Телефон мастера)
- specialization: TEXT (Специализация)
- is_active: BOOLEAN (Активен ли мастер)
- is_approved: BOOLEAN (Одобрен ли администратором)
- work_chat_id: INTEGER (ID рабочей группы с мастером)
- created_at: TIMESTAMP
```

### Таблица `orders`
```sql
- id: INTEGER PRIMARY KEY
- equipment_type: TEXT (Тип техники)
- description: TEXT (Описание проблемы)
- client_name: TEXT (Имя клиента)
- client_address: TEXT (Адрес клиента)
- client_phone: TEXT (Телефон клиента)
- status: TEXT (NEW, ASSIGNED, ACCEPTED, ONSITE, CLOSED, REFUSED, DR)
- assigned_master_id: INTEGER (ID мастера из таблицы masters)
- dispatcher_id: INTEGER (Telegram ID диспетчера)
- notes: TEXT (Заметки)
- total_amount: REAL (Общая сумма)
- materials_cost: REAL (Стоимость материалов)
- master_profit: REAL (Прибыль мастера)
- company_profit: REAL (Прибыль компании)
- has_review: BOOLEAN (Взят ли отзыв)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

### Таблица `audit_log`
```sql
- id: INTEGER PRIMARY KEY
- user_id: INTEGER (Telegram ID пользователя)
- action: TEXT (Тип действия)
- details: TEXT (Детали действия)
- timestamp: TIMESTAMP
```

## 🔧 Полезные SQL-запросы

### Проверка пользователей с множественными ролями
```sql
SELECT telegram_id, username, first_name, role
FROM users
WHERE role LIKE '%,%';
```

### Мастера с их статистикой
```sql
SELECT
    m.id,
    u.first_name || ' ' || u.last_name as name,
    m.phone,
    m.specialization,
    COUNT(o.id) as total_orders,
    SUM(CASE WHEN o.status = 'CLOSED' THEN 1 ELSE 0 END) as completed_orders
FROM masters m
LEFT JOIN users u ON m.telegram_id = u.telegram_id
LEFT JOIN orders o ON o.assigned_master_id = m.id
GROUP BY m.id;
```

### Активные заявки
```sql
SELECT
    o.id,
    o.equipment_type,
    o.client_name,
    o.status,
    u.first_name as master_name
FROM orders o
LEFT JOIN masters m ON o.assigned_master_id = m.id
LEFT JOIN users u ON m.telegram_id = u.telegram_id
WHERE o.status NOT IN ('CLOSED', 'REFUSED')
ORDER BY o.created_at DESC;
```

### Финансовая статистика
```sql
SELECT
    COUNT(*) as total_closed,
    SUM(total_amount) as total_revenue,
    SUM(materials_cost) as total_materials,
    SUM(master_profit) as total_master_profit,
    SUM(company_profit) as total_company_profit
FROM orders
WHERE status = 'CLOSED' AND total_amount IS NOT NULL;
```

## 🔐 Резервное копирование

### Создание резервной копии
```powershell
# Копирование файла базы данных
Copy-Item bot_database.db -Destination "bot_database_backup_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').db"
```

### Автоматическое резервное копирование (скрипт)
```powershell
# backup_db.ps1
$BackupDir = "C:\Bot_test\telegram_repair_bot\backups"
if (!(Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir
}

$BackupFile = Join-Path $BackupDir "bot_database_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').db"
Copy-Item "C:\Bot_test\telegram_repair_bot\bot_database.db" -Destination $BackupFile

Write-Host "Резервная копия создана: $BackupFile"

# Удаление копий старше 30 дней
Get-ChildItem $BackupDir -Filter "bot_database_*.db" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item
```

## ⚠️ Важные замечания

### При работе с базой данных:

1. **Остановите бот перед прямым редактированием:**
   ```powershell
   Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
   ```

2. **Создавайте резервные копии перед изменениями:**
   ```powershell
   Copy-Item bot_database.db bot_database_backup.db
   ```

3. **Не удаляйте записи напрямую** без понимания зависимостей

4. **Для добавления мастеров** используйте интерфейс бота (сохраняет целостность)

5. **Проверяйте формат ролей:**
   - Правильно: `"DISPATCHER,MASTER"` (без пробелов, через запятую)
   - Неправильно: `"DISPATCHER, MASTER"` или `"DISPATCHER MASTER"`

## 🎯 Проверка системы множественных ролей

### Быстрая проверка через скрипт:
```powershell
python check_database.py
```

Скрипт автоматически покажет раздел "ПОЛЬЗОВАТЕЛИ С НЕСКОЛЬКИМИ РОЛЯМИ".

### Проверка через SQL:
```sql
-- Все пользователи с ролью DISPATCHER
SELECT * FROM users WHERE role LIKE '%DISPATCHER%';

-- Все пользователи с ролью MASTER
SELECT * FROM users WHERE role LIKE '%MASTER%';

-- Пользователи с обеими ролями
SELECT * FROM users WHERE role LIKE '%DISPATCHER%' AND role LIKE '%MASTER%';
```

### Добавление роли вручную (через SQL):
```sql
-- Добавить роль MASTER диспетчеру (telegram_id = 123456789)
UPDATE users
SET role = 'DISPATCHER,MASTER'
WHERE telegram_id = 123456789 AND role = 'DISPATCHER';

-- НО ЛУЧШЕ использовать интерфейс бота!
```

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте, остановлен ли бот перед редактированием БД
2. Создайте резервную копию перед изменениями
3. Используйте `check_database.py` для быстрой диагностики
4. Проверьте логи бота: `bot.log`

---

**Дата создания:** 12 октября 2025
**Версия:** 1.0
