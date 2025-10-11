"""
Reply клавиатуры
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRequestChat
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from app.config import UserRole


def get_main_menu_keyboard(role: str) -> ReplyKeyboardMarkup:
    """
    Получение главного меню в зависимости от роли
    
    Args:
        role: Роль пользователя
        
    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    
    if role == UserRole.ADMIN:
        builder.row(
            KeyboardButton(text="📋 Все заявки"),
            KeyboardButton(text="➕ Создать заявку")
        )
        builder.row(
            KeyboardButton(text="👥 Мастера"),
            KeyboardButton(text="📊 Отчеты")
        )
        builder.row(
            KeyboardButton(text="👤 Пользователи"),
            KeyboardButton(text="⚙️ Настройки")
        )
    
    elif role == UserRole.DISPATCHER:
        builder.row(
            KeyboardButton(text="📋 Все заявки"),
            KeyboardButton(text="➕ Создать заявку")
        )
        builder.row(
            KeyboardButton(text="👥 Мастера"),
            KeyboardButton(text="📊 Отчеты")
        )
        builder.row(
            KeyboardButton(text="⚙️ Настройки")
        )
    
    elif role == UserRole.MASTER:
        builder.row(
            KeyboardButton(text="📋 Мои заявки"),
            KeyboardButton(text="📊 Моя статистика")
        )
        builder.row(
            KeyboardButton(text="⚙️ Настройки")
        )
    
    else:  # UNKNOWN
        builder.row(
            KeyboardButton(text="ℹ️ Информация"),
            KeyboardButton(text="📞 Связаться")
        )
    
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
    builder.row(
        KeyboardButton(text="⏭️ Пропустить"),
        KeyboardButton(text="❌ Отмена")
    )
    return builder.as_markup(resize_keyboard=True)


def get_confirm_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура подтверждения
    
    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Подтвердить"),
        KeyboardButton(text="❌ Отмена")
    )
    return builder.as_markup(resize_keyboard=True)

