# 📁 Скрипты проекта

## 🎯 Активные скрипты

### **Бэкапы и восстановление:**

#### `backup_db.py`
Создание резервной копии базы данных.
```bash
python scripts/backup_db.py --keep-days 30
```

#### `cron_backup.sh`
Автоматический бэкап через cron (каждые 6 часов).
```bash
bash scripts/cron_backup.sh
```

#### `parse_telegram_export.py`
Восстановление заявок из экспорта Telegram.
```bash
python scripts/parse_telegram_export.py <result.json> <dispatcher_id> [start_from]
```

#### `restore_order_manually.py`
Ручное восстановление отдельных заявок.
```bash
python scripts/restore_order_manually.py
```

---

### **Управление пользователями:**

#### `set_user_role.py`
Установка роли пользователя.
```bash
python scripts/set_user_role.py <telegram_id> <role>
```

#### `check_user_role.py`
Проверка роли пользователя.
```bash
python scripts/check_user_role.py <telegram_id>
```

#### `sync_roles_from_env.py`
Синхронизация ролей из env файла.
```bash
python scripts/sync_roles_from_env.py
```

---

### **Диагностика:**

#### `diagnose_server.sh`
Полная диагностика production сервера.
```bash
bash scripts/diagnose_server.sh
```

#### `check_database.py`
Проверка базы данных и её содержимого.
```bash
python scripts/check_database.py
```

#### `check_schema.py`
Проверка схемы базы данных.
```bash
python scripts/check_schema.py
```

#### `check_tables.py`
Проверка таблиц базы данных.
```bash
python scripts/check_tables.py
```

---

### **Безопасность и шифрование:**

#### `test_encryption.py`
Проверка работы шифрования данных и генерация ключей.
```bash
python scripts/test_encryption.py
```

#### `check_encryption_in_db.py`
Проверка зашифрованных данных в базе данных.
```bash
python scripts/check_encryption_in_db.py
```

**См. также:** `КАК_ПРОВЕРИТЬ_ШИФРОВАНИЕ.md` и `docs/ENCRYPTION_GUIDE.md`

---

### **Импорт/Экспорт:**

#### `export_db.py`
Экспорт данных из базы.
```bash
python scripts/export_db.py
```

#### `import_db.py`
Импорт данных в базу.
```bash
python scripts/import_db.py
```

---

## 🗂️ Структура

```
scripts/
├── backup_db.py                    # Бэкап БД
├── cron_backup.sh                  # Автоматический бэкап (cron)
├── parse_telegram_export.py        # Парсинг Telegram экспорта
├── restore_order_manually.py       # Ручное восстановление заявок
├── diagnose_server.sh              # Диагностика сервера
├── set_user_role.py                # Установка ролей
├── check_user_role.py              # Проверка ролей
├── sync_roles_from_env.py          # Синхронизация ролей
├── check_database.py               # Проверка БД
├── check_schema.py                 # Проверка схемы
├── check_tables.py                 # Проверка таблиц
├── export_db.py                    # Экспорт данных
├── import_db.py                    # Импорт данных
├── test_encryption.py              # Тестирование шифрования
├── check_encryption_in_db.py       # Проверка шифрования в БД
└── README.md                       # Эта документация
```

---

## 🚀 Быстрые команды

### **Production сервер:**

```bash
# Полная диагностика
bash scripts/diagnose_server.sh

# Создать бэкап
docker exec telegram_repair_bot_prod python /app/scripts/backup_db.py

# Восстановить заявки из Telegram (>= #45)
docker exec -it telegram_repair_bot_prod python /app/scripts/parse_telegram_export.py \
  /app/docs/history_telegram/ChatExport_2025-10-21/result.json \
  5765136457 \
  45
```

### **Локальная разработка:**

```bash
# Установить роль админа
python scripts/set_user_role.py 123456789 ADMIN

# Проверить БД
python scripts/check_database.py

# Создать бэкап
python scripts/backup_db.py

# Проверить шифрование
python scripts/test_encryption.py

# Проверить зашифрованные данные в БД
python scripts/check_encryption_in_db.py
```

---

## 📚 Документация

- `НАСТРОЙКА_АВТОБЭКАПОВ.md` - настройка автоматических бэкапов
- `ИНСТРУКЦИЯ_ВОССТАНОВЛЕНИЕ_ЗАЯВОК.md` - восстановление из Telegram

---

**Всего скриптов: 16** (удалено 24 устаревших, добавлено 2 для шифрования)
