"""
Reply клавиатуры
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from app.config import UserRole


def get_main_menu_keyboard(role: str | list[str]) -> ReplyKeyboardMarkup:
    """
    Получение главного меню в зависимости от роли

    Args:
        role: Роль пользователя (строка или список ролей)

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()

    # Преобразуем в список ролей
    roles = [role] if isinstance(role, str) else role

    # Определяем, какие кнопки добавить
    has_admin = UserRole.ADMIN in roles
    has_dispatcher = UserRole.DISPATCHER in roles
    has_master = UserRole.MASTER in roles

    # Формируем текст кнопки "Все заявки" без счетчика
    all_orders_text = "📋 Все заявки"

    if has_admin:
        # Администратор видит все
        builder.row(KeyboardButton(text=all_orders_text), KeyboardButton(text="➕ Создать заявку"))
        builder.row(KeyboardButton(text="🔍 Поиск заказов"), KeyboardButton(text="👥 Мастера"))
        builder.row(KeyboardButton(text="📊 Отчеты"), KeyboardButton(text="👤 Пользователи"))
        builder.row(KeyboardButton(text="⚙️ Настройки"))

    elif has_dispatcher or has_master:
        # Комбинированное меню для диспетчера и/или мастера
        buttons_added = set()

        # Кнопки диспетчера
        if has_dispatcher:
            builder.row(
                KeyboardButton(text=all_orders_text), KeyboardButton(text="➕ Создать заявку")
            )
            builder.row(KeyboardButton(text="🔍 Поиск заказов"))
            buttons_added.add("dispatcher_orders")

        # Кнопки мастера
        if has_master:
            builder.row(
                KeyboardButton(text="📋 Мои заявки"), KeyboardButton(text="📊 Моя статистика")
            )
            buttons_added.add("master_orders")

        # Общие кнопки
        if has_dispatcher:
            builder.row(KeyboardButton(text="👥 Мастера"), KeyboardButton(text="📊 Отчеты"))

        builder.row(KeyboardButton(text="⚙️ Настройки"))

    else:  # UNKNOWN
        builder.row(KeyboardButton(text="ℹ️ Информация"), KeyboardButton(text="📞 Связаться"))

    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура с кнопкой отмены

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


def get_skip_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура с кнопками пропустить и отмена

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⏭️ Пропустить"), KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


def get_confirm_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура подтверждения

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="✅ Подтвердить"), KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


def get_client_data_confirm_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура подтверждения данных клиента

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Да, использовать"), KeyboardButton(text="❌ Нет, ввести заново")
    )
    return builder.as_markup(resize_keyboard=True)


def get_reschedule_confirm_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура подтверждения переноса

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="✅ Подтвердить перенос"), KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


def get_dr_confirm_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура подтверждения длительного ремонта

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="✅ Подтвердить перевод"), KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)
