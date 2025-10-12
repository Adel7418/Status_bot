# ========================================
# Multi-stage build для оптимизации размера
# ========================================

# Stage 1: Builder
FROM python:3.14-slim AS builder

# Установка зависимостей для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ========================================
# Stage 2: Runtime
# ========================================

FROM python:3.14-slim

# Метаданные образа
LABEL maintainer="your.email@example.com"
LABEL version="1.1.0"
LABEL description="Telegram бот для управления заявками на ремонт техники"

# Установка runtime зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя для запуска приложения (security best practice)
RUN useradd -m -u 1000 botuser && \
    mkdir -p /app /app/data && \
    chown -R botuser:botuser /app

# Копирование виртуального окружения из builder
COPY --from=builder /opt/venv /opt/venv

# Установка рабочей директории
WORKDIR /app

# Копирование файлов приложения
COPY --chown=botuser:botuser . .

# Установка переменной PATH для venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Переключение на непривилегированного пользователя
USER botuser

# Создание volume для базы данных
VOLUME ["/app/data"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('bot_database.db') else 1)"

# Точка входа
ENTRYPOINT ["python", "bot.py"]

