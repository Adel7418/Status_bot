# Docker Configuration

Эта папка содержит все файлы, связанные с Docker и контейнеризацией проекта.

## 📁 Содержимое

- **Dockerfile** — Multi-stage build конфигурация
- **.dockerignore** — Файлы для исключения из образа
- **docker-compose.yml** — Базовая конфигурация для запуска
- **docker-compose.dev.yml** — Конфигурация для разработки
- **docker-compose.prod.yml** — Production конфигурация

## 🚀 Использование

### Сборка образа

```bash
# Из корневой директории проекта
docker build -f docker/Dockerfile -t telegram-repair-bot:latest .
```

### Запуск контейнеров

```bash
# Development
docker-compose -f docker/docker-compose.dev.yml up

# Production
docker-compose -f docker/docker-compose.prod.yml up -d

# Base
docker-compose -f docker/docker-compose.yml up -d
```

### Просмотр логов

```bash
docker-compose -f docker/docker-compose.yml logs -f bot
```

### Остановка

```bash
docker-compose -f docker/docker-compose.yml down
```

## 📖 Подробная документация

См. [DOCKER_USAGE.md](../docs/DOCKER_USAGE.md) для полной документации.

## 🔧 Структура Dockerfile

- **Stage 1: Builder** — Установка зависимостей
- **Stage 2: Runtime** — Финальный образ
- Используется непривилегированный пользователь (security)
- Включены healthchecks
- Оптимизирован размер образа

## 🎯 Production Deployment

```bash
# 1. Настроить .env
cp env.example .env
# Отредактируйте .env

# 2. Запустить
docker-compose -f docker/docker-compose.prod.yml up -d

# 3. Проверить
docker-compose -f docker/docker-compose.prod.yml ps
docker-compose -f docker/docker-compose.prod.yml logs -f
```

