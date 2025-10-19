"""
Конфигурация бота
"""

import os
from typing import ClassVar

from dotenv import load_dotenv


# Загрузка переменных окружения
load_dotenv()


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

    # Интервал проверки SLA заявок (в минутах)
    SLA_CHECK_INTERVAL: int = int(os.getenv("SLA_CHECK_INTERVAL", "30"))

    # Интервал напоминаний о непринятых заявках (в минутах)
    REMINDER_INTERVAL: int = int(os.getenv("REMINDER_INTERVAL", "5"))

    @classmethod
    def validate(cls) -> bool:
        """Валидация конфигурации"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env файле")
        if not cls.ADMIN_IDS:
            raise ValueError("ADMIN_IDS не установлены в .env файле")
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
