# 🔐 Команды Makefile для работы с шифрованием

## Новые команды

### Локальная разработка

```bash
# Проверить работу шифрования
make test-encryption

# Проверить зашифрованные данные в БД
make check-encryption-db
```

### Production (Docker)

```bash
# Установить/обновить зависимости в контейнере
make prod-install-deps

# Проверить шифрование в production
make prod-test-encryption

# Проверить зашифрованные данные в production БД
make prod-check-encryption
```

## Примеры использования

### 1. Первая настройка шифрования (локально)

```bash
# Проверить шифрование и сгенерировать ключ
make test-encryption

# Скопировать ключ из вывода и добавить в .env
# ENCRYPTION_KEY=ваш_ключ

# Проверить работу с БД
make check-encryption-db
```

### 2. Настройка шифрования в production

```bash
# 1. Сгенерировать ключ локально
make test-encryption

# 2. Добавить ключ в env.production на сервере
# ENCRYPTION_KEY=уникальный_ключ_для_production

# 3. Перезапустить production
make prod-restart

# 4. Проверить шифрование в production
make prod-test-encryption

# 5. Проверить данные в БД
make prod-check-encryption
```

### 3. Обновление зависимостей в production

Если вы обновили requirements.txt (например, добавили новую библиотеку):

```bash
# Установить новые зависимости без перезапуска
make prod-install-deps

# ИЛИ полный деплой с пересборкой образа
make prod-deploy
```

### 4. Диагностика проблем с шифрованием

```bash
# Локально
make test-encryption          # Проверка работы шифрования
make check-encryption-db      # Проверка данных в БД
make check-db                 # Общая проверка БД

# Production
make prod-test-encryption     # Проверка в production
make prod-check-encryption    # Проверка данных
make prod-logs                # Логи для отладки
make prod-env                 # Проверка переменных окружения
```

## Полный список команд

Чтобы увидеть все доступные команды Makefile:

```bash
make help
```

Или просто:

```bash
make
```

## Автоматизация

### Скрипт для полной проверки безопасности

Создайте файл `check-security.sh`:

```bash
#!/bin/bash
echo "🔐 Полная проверка безопасности"
echo "================================"

echo ""
echo "1️⃣ Проверка шифрования..."
make test-encryption

echo ""
echo "2️⃣ Проверка данных в БД..."
make check-encryption-db

echo ""
echo "3️⃣ Проверка базы данных..."
make check-db

echo ""
echo "✅ Проверка завершена!"
```

Использование:

```bash
chmod +x check-security.sh
./check-security.sh
```

## Интеграция в CI/CD

Добавьте в ваш CI/CD pipeline:

```yaml
# .github/workflows/security-check.yml
security-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Test encryption
      run: make test-encryption
```

## Troubleshooting

### Команда не работает

```bash
# Проверьте, что вы в правильной директории
pwd

# Должно быть: /path/to/telegram_repair_bot
cd /path/to/telegram_repair_bot

# Попробуйте снова
make test-encryption
```

### Docker контейнер не найден

```bash
# Проверьте статус контейнеров
make prod-status

# Если контейнер не запущен
make prod-start
```

### Ошибка "command not found"

В Windows используйте:
- **Git Bash** (рекомендуется)
- **WSL** (Ubuntu)
- **MinGW**

PowerShell и CMD не поддерживают make напрямую.

## Связанные файлы

- `КАК_ПРОВЕРИТЬ_ШИФРОВАНИЕ.md` - краткая инструкция
- `docs/ENCRYPTION_GUIDE.md` - полное руководство
- `Makefile` - все команды проекта
- `scripts/README.md` - документация скриптов

## Быстрые команды

| Задача | Команда |
|--------|---------|
| Проверить шифрование локально | `make test-encryption` |
| Проверить БД локально | `make check-encryption-db` |
| Проверить шифрование в prod | `make prod-test-encryption` |
| Установить зависимости в prod | `make prod-install-deps` |
| Полный деплой | `make prod-deploy` |
| Показать все команды | `make help` |

