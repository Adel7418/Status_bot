"""
Декораторы для обработки ошибок и проверки ролей
"""

import contextlib
import functools
import inspect
import logging
from collections.abc import Callable

from aiogram.types import CallbackQuery, Message

from app.config import Messages, UserRole
from app.keyboards.reply import get_main_menu_keyboard


logger = logging.getLogger(__name__)


def handle_errors(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок в обработчиках

    Args:
        func: Функция-обработчик

    Returns:
        Обернутая функция с обработкой ошибок
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.exception("Error in %s: %s", func.__name__, e)

            # Ищем объект сообщения или callback query в аргументах
            message_or_callback = None
            user_role = "UNKNOWN"

            for arg in args:
                if isinstance(arg, Message | CallbackQuery):
                    message_or_callback = arg
                    break

            # Если есть user_role в kwargs, используем его
            if "user_role" in kwargs:
                user_role = kwargs["user_role"]

            # Определяем тип ошибки
            error_type = type(e).__name__

            # Для сетевых ошибок Telegram не пытаемся отправить сообщение
            # (т.к. это приведет к новой ошибке)
            if "TelegramNetworkError" in error_type or "ClientConnectorError" in error_type:
                logger.error("Network error, cannot send error message to user")
                return None

            # Для других ошибок показываем сообщение
            error_text = Messages.ERROR_DATABASE

            try:
                if isinstance(message_or_callback, Message):
                    await message_or_callback.answer(
                        error_text, reply_markup=get_main_menu_keyboard(user_role)
                    )
                elif isinstance(message_or_callback, CallbackQuery):
                    await message_or_callback.message.answer(
                        error_text, reply_markup=get_main_menu_keyboard(user_role)
                    )
                    await message_or_callback.answer("Произошла ошибка", show_alert=True)
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")

    return wrapper


def require_role(roles: str | list[str]):
    """
    Декоратор для проверки роли пользователя

    Args:
        roles: Роль или список допустимых ролей

    Returns:
        Декоратор
    """
    if isinstance(roles, str):
        roles = [roles]

    def decorator(func: Callable) -> Callable:
        # Получаем оригинальную сигнатуру
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        # Добавляем user_role параметр если его нет
        if "user_role" not in sig.parameters:
            user_role_param = inspect.Parameter(
                "user_role",
                inspect.Parameter.KEYWORD_ONLY,
                default=UserRole.UNKNOWN,
                annotation=str,
            )
            params.append(user_role_param)

        @functools.wraps(func)
        async def wrapper(*args, user_role: str = UserRole.UNKNOWN, **kwargs):
            # Проверяем роль
            if user_role not in roles:
                logger.debug(
                    f"Access denied for {func.__name__}: user_role={user_role}, required={roles}"
                )
                return None

            # Передаем user_role дальше в kwargs
            return await func(*args, user_role=user_role, **kwargs)

        # Создаем новую сигнатуру с user_role параметром
        wrapper.__signature__ = sig.replace(parameters=params)

        return wrapper

    return decorator


def handle_database_errors(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок базы данных

    Args:
        func: Функция-обработчик

    Returns:
        Обернутая функция с обработкой ошибок БД
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        db = None
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.exception("Database error in %s: %s", func.__name__, e)

            # Ищем объект сообщения или callback query в аргументах
            message_or_callback = None
            user_role = "UNKNOWN"

            for arg in args:
                if isinstance(arg, Message | CallbackQuery):
                    message_or_callback = arg
                    break

            # Если есть user_role в kwargs, используем его
            if "user_role" in kwargs:
                user_role = kwargs["user_role"]

            error_text = Messages.ERROR_DATABASE

            if isinstance(message_or_callback, Message):
                await message_or_callback.answer(
                    error_text, reply_markup=get_main_menu_keyboard(user_role)
                )
            elif isinstance(message_or_callback, CallbackQuery):
                await message_or_callback.message.answer(
                    error_text, reply_markup=get_main_menu_keyboard(user_role)
                )
                await message_or_callback.answer("Ошибка базы данных", show_alert=True)
        finally:
            # Закрываем соединение с БД если оно было открыто
            if db and hasattr(db, "disconnect"):
                with contextlib.suppress(Exception):
                    await db.disconnect()

    return wrapper
