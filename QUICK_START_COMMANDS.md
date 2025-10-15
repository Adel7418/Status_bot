# ⚡ Быстрые команды для работы с проектом

## 🎯 Для всех ОС (Windows/Linux/Mac)

### Python скрипт `run.py`

Универсальный способ запуска команд без установки `make`:

```bash
python run.py <команда> [аргументы]
```

### 📋 Основные команды

```bash
# Справка
python run.py help

# Запуск бота
python run.py run

# Тесты
python run.py test

# Линтеры
python run.py lint

# Форматирование
python run.py format
```

### 🔄 Миграции

```bash
# Применить миграции
python run.py migrate

# Показать текущую версию
python run.py migrate-current

# История миграций
python run.py migrate-history

# Создать новую миграцию
python run.py migrate-create "описание изменений"
```

### 🔧 Git команды

```bash
# Статус
python run.py git-status

# Добавить все изменения
python run.py git-add

# Создать коммит
python run.py git-commit "сообщение коммита"

# Отправить в GitHub
python run.py git-push

# Получить из GitHub
python run.py git-pull

# История коммитов
python run.py git-log

# ⭐ Быстрое сохранение (add + commit + push)
python run.py git-save "сообщение коммита"
```

### 🐋 Docker

```bash
# Запустить в Docker
python run.py docker-up

# Остановить
python run.py docker-down

# Логи
python run.py docker-logs
```

### 🚀 Production

```bash
# Логи production
python run.py prod-logs

# Статус
python run.py prod-status

# Перезапуск
python run.py prod-restart
```

## 💻 Только для Windows

### Короткая команда `m`

Для ещё более быстрого запуска используйте `m.bat`:

```bash
# Вместо python run.py используйте просто m
m help
m run
m git-save "мой коммит"
m test
```

## 🐧 Только для Linux/Mac (если установлен make)

### Makefile

```bash
# Справка
make help

# Основные
make run
make test
make lint

# Git
make git-status
make git-save MSG="сообщение"
make git-push

# Production
make prod-deploy        # ⭐ ГЛАВНАЯ КОМАНДА для деплоя
make prod-diagnose
make prod-logs
```

## 🔥 Самые частые команды

### Локальная разработка

```bash
# Запустить бота
python run.py run
# или
m run

# Применить миграции
python run.py migrate

# Создать миграцию
python run.py migrate-create "add new field"

# Тесты
python run.py test
```

### Работа с Git

```bash
# Быстрое сохранение (add + commit + push)
python run.py git-save "fix: исправил баг"
# или
m git-save "fix: исправил баг"

# Посмотреть статус
python run.py git-status
# или
m git-status

# Получить обновления
python run.py git-pull
# или
m git-pull
```

### Production (на сервере)

```bash
# На сервере используйте make или run.py

# Полный деплой с миграциями
make prod-deploy
# или
python run.py prod-deploy  # (если добавить эту команду в run.py)

# Логи
make prod-logs
# или
python run.py prod-logs

# Статус
make prod-status
# или
python run.py prod-status
```

## 📖 Примеры сценариев

### Сценарий 1: Внесли изменения в код

```bash
# 1. Проверить что изменилось
m git-status

# 2. Протестировать
m test

# 3. Сохранить в Git
m git-save "feat: добавил новую функцию"
```

### Сценарий 2: Изменили модели БД

```bash
# 1. Создать миграцию
m migrate-create "add priority field"

# 2. Применить локально
m migrate

# 3. Проверить
m migrate-current

# 4. Сохранить в Git
m git-save "feat: add priority field to orders"
```

### Сценарий 3: Обновление на сервере

```bash
# На сервере
ssh user@server
cd telegram_repair_bot

# Вариант 1: через make (если установлен)
make prod-deploy

# Вариант 2: через run.py
python run.py git-pull
# затем перезапуск Docker вручную

# Вариант 3: через bash скрипт
./scripts/deploy_with_migrations.sh
```

## ❓ FAQ

### Какую команду использовать?

**На Windows (локально):**
- Используйте `m <команда>` - самое быстрое
- Или `python run.py <команда>`

**На Linux/Mac сервере:**
- Если `make` установлен: `make <команда>`
- Если нет: `python run.py <команда>`

### Как установить make на Windows?

Make на Windows не нужен! Используйте `python run.py` или `m.bat`.

### Можно ли использовать run.py на сервере?

Да! `run.py` работает везде где есть Python.

### Что быстрее?

- Windows: `m git-save "..."` (самое быстрое)
- Linux/Mac: `make git-save MSG="..."` (если make установлен)
- Везде: `python run.py git-save "..."`

## 🎓 Шпаргалка

| Действие | Windows | Linux/Mac (make) | Универсально |
|----------|---------|------------------|--------------|
| Запустить бота | `m run` | `make run` | `python run.py run` |
| Тесты | `m test` | `make test` | `python run.py test` |
| Git статус | `m git-status` | `make git-status` | `python run.py git-status` |
| Git сохранить | `m git-save "msg"` | `make git-save MSG="msg"` | `python run.py git-save "msg"` |
| Миграции | `m migrate` | `make migrate` | `python run.py migrate` |
| Справка | `m help` | `make help` | `python run.py help` |

---

**💡 Совет:** Добавьте алиас в ваш shell для ещё большего удобства!

**Windows (PowerShell):**
```powershell
# В профиль PowerShell (~\Documents\PowerShell\Profile.ps1)
function mr { python run.py $args }
```

**Linux/Mac (bash/zsh):**
```bash
# В ~/.bashrc или ~/.zshrc
alias mr='python run.py'
```

Теперь можно просто: `mr git-save "мой коммит"`
