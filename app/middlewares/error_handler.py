"""Global error handler"""
import logging

from aiogram.types import ErrorEvent


logger = logging.getLogger(__name__)


async def global_error_handler(event: ErrorEvent) -> bool:
    """Глобальная обработка всех необработанных исключений"""

    # Получаем детали об ошибке
    error_details = {
        "update_id": event.update.update_id if event.update else "unknown",
        "exception_type": type(event.exception).__name__,
        "exception_message": str(event.exception),
    }

    # Добавляем информацию о пользователе
    if event.update.message:
        error_details["user_id"] = event.update.message.from_user.id
        error_details["username"] = event.update.message.from_user.username
        error_details["message_text"] = event.update.message.text
        error_details["chat_type"] = event.update.message.chat.type
    elif event.update.callback_query:
        error_details["user_id"] = event.update.callback_query.from_user.id
        error_details["username"] = event.update.callback_query.from_user.username
        error_details["callback_data"] = event.update.callback_query.data
        error_details["chat_type"] = (
            event.update.callback_query.message.chat.type
            if event.update.callback_query.message
            else "unknown"
        )

    # Логируем с полными деталями
    logger.error(
        "❌ UNHANDLED ERROR | Update: %s | User: %s (@%s) | Type: %s | Message: %s",
        error_details.get("update_id"),
        error_details.get("user_id"),
        error_details.get("username", "no_username"),
        error_details.get("exception_type"),
        error_details.get("exception_message"),
    )

    # Логируем полный traceback
    logger.exception(
        "Full traceback for update %s:",
        error_details.get("update_id"),
        exc_info=event.exception,
    )

    # Логируем детали запроса
    if "message_text" in error_details:
        logger.error("Message text: %s", error_details["message_text"])
    if "callback_data" in error_details:
        logger.error("Callback data: %s", error_details["callback_data"])

    # Попытка уведомить пользователя
    if event.update.message:
        try:
            await event.update.message.answer(
                "❌ Произошла ошибка. Попробуйте позже или /cancel.\n\n"
                f"<i>Ошибка: {error_details['exception_type']}</i>",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Failed to send error message to user: %s", e)
    elif event.update.callback_query:
        try:
            await event.update.callback_query.answer(
                f"❌ Произошла ошибка: {error_details['exception_type']}", show_alert=True
            )
        except Exception as e:
            logger.error("Failed to send error callback to user: %s", e)

    return True
