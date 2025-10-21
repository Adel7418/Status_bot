# 🔐 Настройка .env файла на production сервере

## ⚠️ ВАЖНО!

Файл `.env` содержит **секретные данные** (BOT_TOKEN) и **НЕ должен** храниться в Git!

---

## 📝 Как правильно настроить

### Вариант 1: Создать .env вручную (рекомендуется)

```bash
# 1. Подключитесь к серверу
ssh ваш_пользователь@ваш_сервер

# 2. Перейдите в директорию проекта
cd ~/telegram_repair_bot

# 3. Создайте .env файл с BOT_TOKEN
cat > .env << 'EOF'
# Секретные данные для production
BOT_TOKEN=ваш_реальный_токен_бота_здесь
EOF

# 4. Проверьте, что токен записался
cat .env

# 5. Установите правильные права доступа (только владелец может читать)
chmod 600 .env

# 6. Перезапустите бота
make prod-restart
```

---

### Вариант 2: Скопировать и отредактировать

```bash
# На сервере
cd ~/telegram_repair_bot

# Создайте .env на основе env.example
cp env.example .env

# Отредактируйте .env и добавьте реальный BOT_TOKEN
nano .env
# или
vim .env

# Установите права доступа
chmod 600 .env

# Перезапустите бота
make prod-restart
```

---

## 🔍 Проверка

После создания `.env` проверьте, что бот видит токен:

```bash
# 1. Запустите диагностику
bash scripts/diagnose_server.sh

# 2. Или проверьте напрямую (токен будет замаскирован в выводе)
docker exec telegram_repair_bot_prod env | grep BOT_TOKEN

# 3. Посмотрите логи бота
make prod-logs
```

---

## 📂 Структура файлов

```
telegram_repair_bot/
├── .env                    # ❌ НЕ в Git (секретные данные)
├── env.production          # ✅ В Git (публичная конфигурация)
├── env.example             # ✅ В Git (шаблон)
└── docker/
    └── docker-compose.prod.yml  # Читает env.production + .env
```

---

## 🔐 Приоритет переменных

Docker Compose читает файлы в таком порядке:

1. `env.production` - базовая конфигурация
2. `.env` - **перезаписывает** значения из env.production
3. `environment:` в docker-compose.yml - **перезаписывает** всё

**Пример:**

```
env.production:  BOT_TOKEN=       (пусто)
.env:            BOT_TOKEN=123    (реальный токен)
Результат:       BOT_TOKEN=123    ✅
```

---

## ⚠️ Безопасность

### ✅ Правильно:
- Хранить `BOT_TOKEN` только в `.env` на сервере
- Устанавливать права `chmod 600 .env`
- Не коммитить `.env` в Git

### ❌ Неправильно:
- Хранить токен в `env.production` в Git
- Делать `git add .env`
- Выкладывать токен публично

---

## 🚨 Если токен утёк

1. **Немедленно отзовите токен** через @BotFather
2. Создайте новый токен
3. Обновите `.env` на сервере
4. Перезапустите: `make prod-restart`

---

## 📋 Пример .env файла

```bash
# Секретные данные для production
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Опционально: можно перезаписать другие переменные
# LOG_LEVEL=DEBUG
# ADMIN_IDS=123456789
```

---

## ✅ Проверка корректности

```bash
# Убедитесь, что .env НЕ в Git
git status | grep .env
# Должно быть пусто или "Untracked files"

# Убедитесь, что .env в .gitignore
grep "^\.env$" .gitignore
# Должно вывести: .env
```

---

**После настройки `.env` бот должен запуститься без ошибок!** 🎉
