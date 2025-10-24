# 🚀 Быстрое исправление LONG_REPAIR на сервере

## Выполните эти команды на сервере:

### 1. Исправить код
```bash
# Linux/Mac
./fix_code_production.sh

# Windows PowerShell
.\fix_code_production.ps1
```

### 2. Исправить данные
```bash
python fix_long_repair_production.py
```

### 3. Перезапустить бота
```bash
# Docker
docker-compose restart

# Или напрямую
pkill -f bot.py && python bot.py &
```

## ✅ Проверка результата

```bash
python -c "
import sqlite3
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM orders WHERE status = \"LONG_REPAIR\"')
print('LONG_REPAIR заявок:', cursor.fetchone()[0])
cursor.execute('SELECT COUNT(*) FROM orders WHERE status = \"DR\"')
print('DR заявок:', cursor.fetchone()[0])
conn.close()
"
```

**Ожидаемый результат:** `LONG_REPAIR заявок: 0`

## 🔄 Откат (если нужно)

```bash
cp app/handlers/master.py.backup app/handlers/master.py
docker-compose restart
```

---
**Время выполнения:** ~2 минуты  
**Риск:** Минимальный (только изменение статуса)
