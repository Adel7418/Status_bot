"""
Константы приложения - роли, статусы, типы техники
"""


class UserRole:
    """Роли пользователей"""

    ADMIN = "ADMIN"
    DISPATCHER = "DISPATCHER"
    MASTER = "MASTER"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def all_roles(cls) -> list[str]:
        """Список всех ролей"""
        return [cls.ADMIN, cls.DISPATCHER, cls.MASTER, cls.UNKNOWN]


class OrderStatus:
    """Статусы заявок"""

    NEW = "NEW"  # Новая заявка
    ASSIGNED = "ASSIGNED"  # Назначена мастеру
    ACCEPTED = "ACCEPTED"  # Принята мастером
    ONSITE = "ONSITE"  # Мастер на объекте
    CLOSED = "CLOSED"  # Завершена
    REFUSED = "REFUSED"  # Отклонена
    DR = "DR"  # Длительный ремонт

    @classmethod
    def all_statuses(cls) -> list[str]:
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
            cls.DR: "⏳",
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
            cls.DR: "Длительный ремонт",
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
    def all_types(cls) -> list[str]:
        """Список всех типов техники"""
        return [
            cls.WASHING_MACHINE,
            cls.OVEN,
            cls.DISHWASHER,
            cls.COFFEE_MACHINE,
            cls.PLUMBING,
            cls.ELECTRICAL,
            cls.WATER_HEATER,
            cls.TV,
        ]
