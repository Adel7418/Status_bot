# 📦 Руководство по резервному копированию базы данных

## 🚀 Быстрый старт

### Способ 1: Python-скрипт (Рекомендуется) 🌟

```powershell
python backup_db.py
```

**Преимущества:**
- ✅ Красивый вывод
- ✅ Показывает размер БД
- ✅ Автоматически удаляет старые копии (>30 дней)
- ✅ Показывает список последних копий

### Способ 2: PowerShell-скрипт

```powershell
.\backup_db.ps1
```

### Способ 3: Вручную (одной командой)

```powershell
Copy-Item bot_database.db -Destination "bot_database_backup_$(Get-Date -Format 'yyyy-MM-dd').db"
```

---

## 📋 Что делают скрипты

### 1. Создание копии
- Копируют `bot_database.db` в папку `backups/`
- Имя файла: `bot_database_ГГГГ-ММ-ДД_ЧЧ-ММ-СС.db`
- Пример: `bot_database_2025-10-12_15-43-55.db`

### 2. Автоматическая очистка
- Удаляют копии старше 30 дней
- Это экономит место на диске

### 3. Отчет
- Показывают размер БД
- Список последних копий
- Статистику

---

## 🎯 Когда создавать резервные копии

### Обязательно:
- ✅ **Перед обновлением бота**
- ✅ **Перед ручным редактированием БД**
- ✅ **Перед массовыми изменениями** (добавление множества пользователей)
- ✅ **Перед миграцией** на другой сервер

### Рекомендуется:
- 📅 **Ежедневно** (можно автоматизировать)
- 🔄 **После важных изменений**
- 📊 **Перед генерацией отчетов**

---

## ⚙️ Настройки

### Изменить срок хранения копий

**Python:**
```powershell
python backup_db.py --keep-days 60
```

**PowerShell:**
```powershell
.\backup_db.ps1 -KeepDays 60
```

По умолчанию: 30 дней

---

## 📁 Структура папки backups

```
backups/
├── bot_database_2025-10-12_15-43-55.db  (последняя)
├── bot_database_2025-10-12_14-30-00.db
├── bot_database_2025-10-11_18-45-22.db
├── bot_database_2025-10-10_12-00-00.db
└── ...
```

---

## 🔄 Восстановление из резервной копии

### Способ 1: Замена файла

**1. Остановите бот:**
```powershell
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
```

**2. Сделайте копию текущей БД (на всякий случай):**
```powershell
Copy-Item bot_database.db bot_database_current.db
```

**3. Восстановите из backup:**
```powershell
Copy-Item backups\bot_database_2025-10-12_15-43-55.db bot_database.db -Force
```

**4. Запустите бот:**
```powershell
python bot.py
```

### Способ 2: Переименование

```powershell
# Остановите бот
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Переименуйте текущую БД
Rename-Item bot_database.db bot_database_old.db

# Скопируйте backup
Copy-Item backups\bot_database_2025-10-12_15-43-55.db bot_database.db

# Запустите бот
python bot.py
```

---

## 🤖 Автоматизация резервного копирования

### Windows Task Scheduler (Планировщик заданий)

**1. Создайте файл `scheduled_backup.bat`:**
```batch
@echo off
cd C:\Bot_test\telegram_repair_bot
python backup_db.py
```

**2. Откройте Планировщик заданий:**
```powershell
taskschd.msc
```

**3. Создайте задание:**
- Имя: "Bot Database Backup"
- Триггер: Ежедневно в 3:00 AM
- Действие: Запуск `scheduled_backup.bat`

### Cron (Linux)

```bash
# Редактировать crontab
crontab -e

# Добавить строку (backup каждый день в 3:00)
0 3 * * * cd /path/to/bot && python backup_db.py
```

---

## 📊 Проверка резервных копий

### Посмотреть все копии:

**PowerShell:**
```powershell
Get-ChildItem backups | Format-Table Name, Length, LastWriteTime
```

**Python:**
```powershell
python -c "import os; print('\n'.join(sorted(os.listdir('backups'), reverse=True)))"
```

### Проверить размер папки:

```powershell
$size = (Get-ChildItem backups -Recurse | Measure-Object -Property Length -Sum).Sum
Write-Host "Размер папки backups: $([math]::Round($size/1MB, 2)) MB"
```

---

## 🗂️ Экспорт в другие форматы

### SQL дамп (для миграции)

```powershell
sqlite3 bot_database.db .dump > database_dump.sql
```

### CSV экспорт таблицы:

```powershell
sqlite3 bot_database.db
.mode csv
.output users_export.csv
SELECT * FROM users;
.quit
```

### JSON экспорт (через Python):

```python
import sqlite3
import json

conn = sqlite3.connect('bot_database.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM users")
users = [dict(row) for row in cursor.fetchall()]

with open('users_export.json', 'w', encoding='utf-8') as f:
    json.dump(users, f, indent=2, ensure_ascii=False, default=str)

print("Экспорт завершен: users_export.json")
```

---

## ⚠️ Важные замечания

### 1. Размер базы данных
- Текущий размер: ~72 KB
- При росте до нескольких MB следите за местом на диске
- Старые копии автоматически удаляются через 30 дней

### 2. Безопасность
- Папка `backups/` должна быть в `.gitignore` (уже добавлено)
- Не храните резервные копии в публичных репозиториях
- Содержит персональные данные пользователей

### 3. Целостность
- Создавайте копии при **остановленном боте** (если важна 100% целостность)
- Для работающего бота копии тоже безопасны (SQLite поддерживает чтение)

### 4. Хранение
- Храните важные копии вне папки проекта
- Используйте облачное хранилище (Google Drive, Dropbox)
- Делайте копии перед обновлениями

---

## 🔍 Проверка целостности резервной копии

### Проверить, можно ли открыть:

```powershell
sqlite3 backups\bot_database_2025-10-12_15-43-55.db "SELECT COUNT(*) FROM users;"
```

Должно вернуть число пользователей.

### Проверить через Python:

```python
import sqlite3

db_file = "backups/bot_database_2025-10-12_15-43-55.db"

try:
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Проверка таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    print(f"✅ База данных целая. Найдено таблиц: {len(tables)}")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"   {table[0]}: {count} записей")

    conn.close()
except Exception as e:
    print(f"❌ Ошибка: {e}")
```

---

## 📚 Связанные документы

- `DATABASE_USAGE_GUIDE.md` - работа с базой данных
- `HOW_TO_ADD_DISPATCHER_ROLE.md` - управление ролями
- `check_database.py` - проверка содержимого БД

---

## 💡 Полезные команды

### Быстрое копирование с описанием:

```powershell
# Перед важными изменениями
Copy-Item bot_database.db -Destination "bot_database_before_update.db"
```

### Сравнение двух версий БД:

```powershell
# Размеры файлов
(Get-Item bot_database.db).Length
(Get-Item backups\bot_database_2025-10-12_15-43-55.db).Length
```

### Восстановление последней копии:

```powershell
$latest = Get-ChildItem backups -Filter "bot_database_*.db" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Copy-Item $latest.FullName bot_database.db -Force
Write-Host "Восстановлено из: $($latest.Name)"
```

---

**Дата создания:** 12 октября 2025
**Версия:** 1.0

---

## ✅ Текущий статус

```
📁 Папка backups: Создана
📊 Резервных копий: 2
📏 Размер БД: 72 KB
🕐 Последний backup: 2025-10-12 15:43:55
✅ Автоочистка: Включена (30 дней)
```
