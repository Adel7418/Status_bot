"""
Конфигурация бота
"""

import logging
import os
from typing import ClassVar

from dotenv import load_dotenv


# Загрузка переменных окружения
# Поддержка multibot: загружаем env файл согласно переменной окружения ENV_FILE
env_file = os.getenv("ENV_FILE", ".env")

if env_file in ("env.city1", "env.city2") or (env_file != ".env" and "city" in env_file):
    # Используем абсолютный путь для надежности
    if not os.path.isabs(env_file):
        # Сначала проверяем в текущей рабочей директории
        env_file_path = os.path.join(os.getcwd(), env_file)
        if not os.path.exists(env_file_path):
            # Если не найден, проверяем в директории проекта
            project_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            env_file_path = os.path.join(project_dir, env_file)
        env_file = env_file_path
    load_dotenv(env_file)
else:
    load_dotenv()  # По умолчанию загружаем .env


class Config:
    """Основная конфигурация бота"""

    # Telegram Bot Token
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Telegram IDs администраторов
    ADMIN_IDS: ClassVar[list[int]] = [
        int(id_) for id_ in os.getenv("ADMIN_IDS", "").split(",") if id_.strip()
    ]

    # Telegram IDs диспетчеров
    DISPATCHER_IDS: ClassVar[list[int]] = [
        int(id_) for id_ in os.getenv("DISPATCHER_IDS", "").split(",") if id_.strip()
    ]

    # ID группы диспетчеров для уведомлений
    DISPATCHER_GROUP_ID: int | None = (
        int(os.getenv("DISPATCHER_GROUP_ID")) if os.getenv("DISPATCHER_GROUP_ID") else None
    )

    # Developer Mode (режим разработчика)
    DEV_MODE: bool = os.getenv("DEV_MODE", "true").lower() in (
        "true",
        "1",
        "yes",
    )  # По умолчанию true для локальной разработки

    # Путь к базе данных
    # Используем DATABASE_PATH напрямую из .env без автоматического добавления _dev
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_database.db")

    # Уровень логирования
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Фича-флаг: использовать ли ORM (SQLAlchemy) вместо прямых SQL
    # По умолчанию выключено, чтобы не ломать прод при установке зависимостей
    USE_ORM: bool = os.getenv("USE_ORM", "false").lower() in ("true", "1", "yes")

    # Фича-флаг: бонус за отзыв (10% от чистой прибыли мастеру)
    # Включается через переменную окружения REVIEW_BONUS_ENABLED=true
    REVIEW_BONUS_ENABLED: bool = os.getenv("REVIEW_BONUS_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    # Интервал проверки SLA заявок (в минутах)
    SLA_CHECK_INTERVAL: int = int(os.getenv("SLA_CHECK_INTERVAL", "30"))

    # Интервал напоминаний о непринятых заявках (в минутах)
    REMINDER_INTERVAL: int = int(os.getenv("REMINDER_INTERVAL", "5"))

    # Ночной режим для SLA (время, когда уведомления не отправляются)
    # Часы в 24-часовом формате (например, 22 = 22:00, 6 = 06:00)
    SLA_NIGHT_START: int = int(os.getenv("SLA_NIGHT_START", "22"))
    SLA_NIGHT_END: int = int(os.getenv("SLA_NIGHT_END", "6"))

    # Автоматические бэкапы
    BACKUP_ENABLED: bool = os.getenv("BACKUP_ENABLED", "true").lower() in ("true", "1", "yes")
    BACKUP_SCHEDULE: str = os.getenv("BACKUP_SCHEDULE", "0 3 * * *")  # Cron формат

    # Telethon Parser Configuration
    TELETHON_API_ID: int | None = int(os.getenv("TELETHON_API_ID")) if os.getenv("TELETHON_API_ID") else None
    TELETHON_API_HASH: str = os.getenv("TELETHON_API_HASH", "")
    TELETHON_PHONE: str = os.getenv("TELETHON_PHONE", "")
    TELETHON_SESSION_NAME: str = os.getenv("TELETHON_SESSION_NAME", "parser_session")
    # Directory for persistent Telethon session files (Docker: /app/data/telethon)
    TELETHON_SESSION_DIR: str = os.getenv("TELETHON_SESSION_DIR", "")

    # Включение парсера (можно отключить если не нужен)
    PARSER_ENABLED: bool = os.getenv("PARSER_ENABLED", "false").lower() in ("true", "1", "yes")

    @classmethod
    def validate(cls) -> bool:
        """Валидация конфигурации"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env файле")
        if not cls.ADMIN_IDS:
            raise ValueError("ADMIN_IDS не установлены в .env файле")

        # Валидация Telethon если парсер включен
        if cls.PARSER_ENABLED:
            if not cls.TELETHON_API_ID:
                raise ValueError("TELETHON_API_ID не установлен, но PARSER_ENABLED=true")
            if not cls.TELETHON_API_HASH:
                raise ValueError("TELETHON_API_HASH не установлен, но PARSER_ENABLED=true")
            if not cls.TELETHON_PHONE:
                raise ValueError("TELETHON_PHONE не установлен, но PARSER_ENABLED=true")

        return True


class Messages:
    """Текстовые сообщения бота"""

    # Приветствия
    WELCOME_UNKNOWN = (
        "👋 Добро пожаловать в систему управления заявками на ремонт техники!\n\n"
        "Для доступа к системе необходимо, чтобы администратор добавил вас в систему."
    )

    WELCOME_ADMIN = (
        "👋 Добро пожаловать, администратор!\n\n"
        "Вы имеете полный доступ к системе управления заявками.\n"
        "Используйте меню ниже для навигации."
    )

    WELCOME_DISPATCHER = (
        "👋 Добро пожаловать, диспетчер!\n\n"
        "Вы можете создавать заявки, назначать мастеров и управлять статусами.\n"
        "Используйте меню ниже для навигации."
    )

    WELCOME_MASTER = (
        "👋 Добро пожаловать, мастер!\n\n"
        "Вы можете просматривать назначенные вам заявки и обновлять их статусы.\n"
        "Используйте меню ниже для навигации."
    )

    # Ошибки
    ERROR_NO_ACCESS = "❌ У вас нет доступа к этой функции."
    ERROR_INVALID_DATA = "❌ Некорректные данные. Попробуйте снова."
    ERROR_ORDER_NOT_FOUND = "❌ Заявка не найдена."
    ERROR_MASTER_NOT_FOUND = "❌ Мастер не найден."
    ERROR_DATABASE = "❌ Ошибка базы данных. Попробуйте позже."

    # Успешные операции
    SUCCESS_ORDER_CREATED = "✅ Заявка успешно создана!"
    SUCCESS_ORDER_UPDATED = "✅ Заявка успешно обновлена!"
    SUCCESS_MASTER_ASSIGNED = "✅ Мастер успешно назначен!"
    SUCCESS_STATUS_UPDATED = "✅ Статус успешно обновлен!"


# Константы для валидации
MAX_DESCRIPTION_LENGTH = 500
MAX_NOTES_LENGTH = 1000
PHONE_REGEX = r"^\+?[0-9]{10,15}$"
