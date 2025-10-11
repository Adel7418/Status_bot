"""
Конфигурация бота
"""
import os
from typing import List
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()


class Config:
    """Основная конфигурация бота"""
    
    # Telegram Bot Token
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Telegram IDs администраторов
    ADMIN_IDS: List[int] = [
        int(id_) for id_ in os.getenv("ADMIN_IDS", "").split(",") if id_.strip()
    ]
    
    # Telegram IDs диспетчеров
    DISPATCHER_IDS: List[int] = [
        int(id_) for id_ in os.getenv("DISPATCHER_IDS", "").split(",") if id_.strip()
    ]
    
    # Путь к базе данных
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_database.db")
    
    # Уровень логирования
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> bool:
        """Валидация конфигурации"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env файле")
        if not cls.ADMIN_IDS:
            raise ValueError("ADMIN_IDS не установлены в .env файле")
        return True


class UserRole:
    """Роли пользователей"""
    ADMIN = "ADMIN"
    DISPATCHER = "DISPATCHER"
    MASTER = "MASTER"
    UNKNOWN = "UNKNOWN"
    
    @classmethod
    def all_roles(cls) -> List[str]:
        """Список всех ролей"""
        return [cls.ADMIN, cls.DISPATCHER, cls.MASTER, cls.UNKNOWN]


class OrderStatus:
    """Статусы заявок"""
    NEW = "NEW"                  # Новая заявка
    ASSIGNED = "ASSIGNED"        # Назначена мастеру
    ACCEPTED = "ACCEPTED"        # Принята мастером
    ONSITE = "ONSITE"           # Мастер на объекте
    CLOSED = "CLOSED"           # Завершена
    REFUSED = "REFUSED"         # Отклонена
    DR = "DR"                   # Длительный ремонт
    
    @classmethod
    def all_statuses(cls) -> List[str]:
        """Список всех статусов"""
        return [cls.NEW, cls.ASSIGNED, cls.ACCEPTED, cls.ONSITE, cls.CLOSED, cls.REFUSED, cls.DR]
    
    @classmethod
    def get_status_emoji(cls, status: str) -> str:
        """Получение эмодзи для статуса"""
        emojis = {
            cls.NEW: "🆕",
            cls.ASSIGNED: "👨‍🔧",
            cls.ACCEPTED: "✅",
            cls.ONSITE: "🏠",
            cls.CLOSED: "💰",
            cls.REFUSED: "❌",
            cls.DR: "⏳"
        }
        return emojis.get(status, "")
    
    @classmethod
    def get_status_name(cls, status: str) -> str:
        """Получение названия статуса на русском"""
        names = {
            cls.NEW: "Новая",
            cls.ASSIGNED: "Назначена",
            cls.ACCEPTED: "Принята",
            cls.ONSITE: "На объекте",
            cls.CLOSED: "Завершена",
            cls.REFUSED: "Отклонена",
            cls.DR: "Длительный ремонт"
        }
        return names.get(status, status)


class EquipmentType:
    """Типы техники"""
    WASHING_MACHINE = "Стиральные машины"
    OVEN = "Духовой шкаф"
    DISHWASHER = "Посудомоечная машина"
    COFFEE_MACHINE = "Кофе машина"
    PLUMBING = "Сантехника"
    ELECTRICAL = "Электрика"
    WATER_HEATER = "Водонагреватели"
    TV = "Телевизоры"
    
    @classmethod
    def all_types(cls) -> List[str]:
        """Список всех типов техники"""
        return [
            cls.WASHING_MACHINE,
            cls.OVEN,
            cls.DISHWASHER,
            cls.COFFEE_MACHINE,
            cls.PLUMBING,
            cls.ELECTRICAL,
            cls.WATER_HEATER,
            cls.TV
        ]


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


# Константы
MAX_DESCRIPTION_LENGTH = 500
MAX_NOTES_LENGTH = 1000
PHONE_REGEX = r"^\+?[0-9]{10,15}$"

