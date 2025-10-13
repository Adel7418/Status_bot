# 🚀 Деплой на VPS - Краткое резюме

**Дата:** 13 октября 2025  
**Версия:** 1.2.1

---

## ✅ Что подготовлено

Для вас созданы все необходимые инструменты для деплоя бота на VPS Linux:

### 📚 Документация

1. **`DEPLOY_VPS_LINUX_GUIDE.md`** - Полное пошаговое руководство
   - 10 детальных разделов
   - Все команды и примеры
   - Troubleshooting
   - Мониторинг и безопасность

2. **`QUICK_DEPLOY_COMMANDS.md`** - Шпаргалка с готовыми командами
   - Быстрые команды
   - Алиасы для удобства
   - Чеклисты

3. **`scripts/README.md`** - Документация по скриптам
   - Описание каждого скрипта
   - Примеры использования
   - Сценарии применения

### 🛠️ Скрипты автоматизации

1. **`scripts/setup_vps.sh`** - Настройка VPS сервера
   - Устанавливает Docker, Git
   - Настраивает права
   - Создает директории

2. **`scripts/deploy_to_vps.sh`** - Автоматический деплой
   - Проверяет подключение
   - Передает файлы
   - Настраивает .env

3. **`scripts/export_db.py`** - Экспорт БД в JSON
   - Для безопасного переноса
   - С метаданными

4. **`scripts/import_db.py`** - Импорт БД из JSON
   - Восстановление данных
   - Автоматический backup

---

## 🎯 Как использовать (3 способа)

### Способ 1: Автоматический (рекомендуется) ⭐

**На локальной машине (Windows):**

```powershell
# 1. Настройка .env
cd C:\Bot_test\telegram_repair_bot
cp env.example .env
notepad .env
# Добавьте: BOT_TOKEN, ADMIN_IDS

# 2. Экспорт БД (для безопасности)
python scripts/export_db.py

# 3. Деплой (из Git Bash)
bash scripts/deploy_to_vps.sh ваш_IP root
```

**На VPS (Linux):**

```bash
# 1. Первоначальная настройка (один раз)
ssh root@ваш_IP
wget https://raw.githubusercontent.com/Adel7418/Status_bot/main/scripts/setup_vps.sh
chmod +x setup_vps.sh
./setup_vps.sh
exit

# 2. После деплоя файлов
ssh root@ваш_IP
cd ~/telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml up -d

# 3. Проверка
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

### Способ 2: Через GitHub

```bash
# На VPS
ssh root@ваш_IP

# Установка Docker (если нужно)
wget https://raw.githubusercontent.com/Adel7418/Status_bot/main/scripts/setup_vps.sh
chmod +x setup_vps.sh
./setup_vps.sh

# Клонирование проекта
git clone https://github.com/Adel7418/Status_bot.git telegram_repair_bot
cd telegram_repair_bot

# Настройка .env
cp env.example .env
nano .env  # Добавьте токены

# Перенос БД с локальной машины
exit
scp C:\Bot_test\telegram_repair_bot\bot_database.db root@ваш_IP:/root/telegram_repair_bot/data/

# На VPS - запуск
ssh root@ваш_IP
cd telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml up -d
```

### Способ 3: Ручной через SCP

```powershell
# На Windows
cd C:\Bot_test\telegram_repair_bot

# Создание архива (если нужно)
# Или прямая передача:
scp -r . root@ваш_IP:/root/telegram_repair_bot/

# На VPS
ssh root@ваш_IP
cd telegram_repair_bot
cp env.example .env
nano .env  # Настройте
docker compose -f docker/docker-compose.prod.yml up -d
```

---

## 📋 Пошаговый чеклист

### Перед деплоем на локальной машине:

- [ ] Создан и настроен `.env` файл (BOT_TOKEN, ADMIN_IDS)
- [ ] Создан backup базы данных (`python backup_db.py`)
- [ ] Экспортирована БД в JSON (`python scripts/export_db.py`)
- [ ] Проверен SSH доступ к VPS (`ssh root@IP`)

### На VPS сервере:

- [ ] Выполнена первоначальная настройка (`setup_vps.sh`)
- [ ] Docker установлен и работает (`docker --version`)
- [ ] Проект перенесен на сервер
- [ ] Файл `.env` настроен с правильными токенами
- [ ] База данных перенесена

### После деплоя:

- [ ] Контейнеры запущены (`docker ps`)
- [ ] Логи без критических ошибок (`docker logs`)
- [ ] Бот отвечает на `/start` в Telegram
- [ ] Healthcheck зеленый
- [ ] Настроен автозапуск через systemd
- [ ] Настроено автоматическое резервное копирование

---

## 🔧 Основные команды для управления

### На VPS после деплоя:

```bash
# Переход в директорию
cd ~/telegram_repair_bot

# === Управление ботом ===
# Запуск
docker compose -f docker/docker-compose.prod.yml up -d

# Остановка
docker compose -f docker/docker-compose.prod.yml down

# Перезапуск
docker compose -f docker/docker-compose.prod.yml restart

# Логи
docker compose -f docker/docker-compose.prod.yml logs -f bot

# Статус
docker compose -f docker/docker-compose.prod.yml ps

# === Резервное копирование ===
# Создание backup
docker compose -f docker/docker-compose.prod.yml exec bot python backup_db.py

# Список backup
ls -lh backups/

# === Обновление ===
# Через Git
git pull
docker compose -f docker/docker-compose.prod.yml build
docker compose -f docker/docker-compose.prod.yml up -d
```

---

## 🆘 Быстрая помощь

### Бот не запускается

```bash
# Просмотр логов
docker compose -f docker/docker-compose.prod.yml logs bot

# Проверка .env
cat .env | grep BOT_TOKEN

# Полный перезапуск
docker compose -f docker/docker-compose.prod.yml down
docker compose -f docker/docker-compose.prod.yml up -d
```

### База данных заблокирована

```bash
docker compose -f docker/docker-compose.prod.yml down
rm -f data/bot_database.db-journal
docker compose -f docker/docker-compose.prod.yml up -d
```

### Проверка всего статуса одной командой

```bash
docker ps && \
docker stats --no-stream && \
docker compose -f ~/telegram_repair_bot/docker/docker-compose.prod.yml logs --tail=20 bot
```

---

## 📊 Что читать дальше

### Для первого деплоя:
1. **`DEPLOY_VPS_LINUX_GUIDE.md`** - читайте последовательно
2. **`QUICK_DEPLOY_COMMANDS.md`** - держите открытым для копирования команд

### Если есть опыт с Docker:
1. **`QUICK_DEPLOY_COMMANDS.md`** - быстрый старт
2. **`scripts/README.md`** - автоматизация через скрипты

### Для миграции с другого сервера:
1. **`scripts/README.md`** - раздел "Сценарий 2: Миграция"
2. **`QUICK_DEPLOY_COMMANDS.md`** - раздел "Миграция базы данных"

---

## 🎯 Следующие шаги

### 1. Прямо сейчас:

```bash
# Убедитесь что .env настроен
cat .env | grep BOT_TOKEN

# Экспортируйте БД для безопасности
python scripts/export_db.py
```

### 2. Подключитесь к VPS:

```bash
ssh root@ваш_IP_адрес
```

### 3. Выполните настройку (если первый раз):

```bash
wget https://raw.githubusercontent.com/Adel7418/Status_bot/main/scripts/setup_vps.sh
chmod +x setup_vps.sh
./setup_vps.sh
```

### 4. Деплой проекта (выберите способ выше)

### 5. Запуск и проверка:

```bash
cd ~/telegram_repair_bot
docker compose -f docker/docker-compose.prod.yml up -d
docker compose -f docker/docker-compose.prod.yml logs -f bot
```

### 6. Тест в Telegram:
- Найдите бота
- Отправьте `/start`
- Проверьте функционал

---

## 📁 Структура созданных файлов

```
telegram_repair_bot/
├── DEPLOY_VPS_LINUX_GUIDE.md       # Полное руководство (детальное)
├── QUICK_DEPLOY_COMMANDS.md        # Шпаргалка с командами
├── ДЕПЛОЙ_НА_VPS_РЕЗЮМЕ.md        # Этот файл (краткое резюме)
│
└── scripts/
    ├── README.md                    # Документация по скриптам
    ├── setup_vps.sh                # Настройка VPS сервера
    ├── deploy_to_vps.sh            # Автоматический деплой
    ├── export_db.py                # Экспорт БД в JSON
    └── import_db.py                # Импорт БД из JSON
```

---

## ✅ Готово к деплою!

Все инструменты подготовлены. Выберите один из способов выше и начинайте деплой.

**Рекомендуемый порядок:**

1. 📖 Прочитайте `DEPLOY_VPS_LINUX_GUIDE.md` (раздел 1-3)
2. 🛠️ Запустите `setup_vps.sh` на VPS
3. 🚀 Используйте `deploy_to_vps.sh` для переноса файлов
4. ▶️ Запустите бота через Docker
5. ✅ Проверьте работу в Telegram

---

## 💡 Полезные советы

1. **Используйте SSH ключи** вместо паролей для безопасности
2. **Создавайте backup** перед любыми изменениями
3. **Проверяйте логи** регулярно: `docker logs -f`
4. **Настройте мониторинг** через systemd
5. **Автоматизируйте backup** через cron

---

## 📞 Где искать помощь

- **Ошибки при деплое** → `DEPLOY_VPS_LINUX_GUIDE.md` раздел 10 (Troubleshooting)
- **Команды забыл** → `QUICK_DEPLOY_COMMANDS.md`
- **Проблемы со скриптами** → `scripts/README.md` раздел Troubleshooting
- **Вопросы по Docker** → `docker/README.md`

---

**Версия:** 1.0  
**Дата создания:** 13 октября 2025  
**Статус:** ✅ Готово к использованию

🚀 **Успешного деплоя!**

---

## 🎁 Бонус: Полезные алиасы

После деплоя добавьте в `~/.bashrc` на VPS:

```bash
# Алиасы для управления ботом
alias bot='cd ~/telegram_repair_bot'
alias bot-start='cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml up -d'
alias bot-stop='cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml down'
alias bot-logs='cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml logs -f bot'
alias bot-status='docker ps | grep telegram'
alias bot-backup='cd ~/telegram_repair_bot && docker compose -f docker/docker-compose.prod.yml exec bot python backup_db.py'
```

Применить: `source ~/.bashrc`

Использовать:
```bash
bot-start   # Запуск
bot-logs    # Логи
bot-status  # Статус
```

🎉 **Готово! Можете начинать деплой!**

