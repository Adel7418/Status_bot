"""Global error handler"""
import logging
from aiogram.types import ErrorEvent, Update

logger = logging.getLogger(__name__)


async def global_error_handler(event: ErrorEvent) -> bool:
    """Глобальная обработка всех необработанных исключений"""
    logger.exception(
        "Unhandled error in update %s: %s",
        event.update.update_id if event.update else "unknown",
        event.exception,
        exc_info=event.exception,
    )
    
    # Попытка уведомить пользователя
    if event.update.message:
        try:
            await event.update.message.answer(
                "❌ Произошла ошибка. Попробуйте позже или /cancel."
            )
        except Exception:
            pass
    elif event.update.callback_query:
        try:
            await event.update.callback_query.answer(
                "❌ Произошла ошибка", show_alert=True
            )
        except Exception:
            pass
    
    return True

