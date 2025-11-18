"""
Middleware для обработки ошибок валидации State Machine
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.domain.order_state_machine import InvalidStateTransitionError


logger = logging.getLogger(__name__)


class ValidationHandlerMiddleware(BaseMiddleware):
    """Middleware для обработки ошибок валидации переходов статусов"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Обработка события с перехватом ошибок валидации

        Args:
            handler: Следующий handler
            event: Событие (Message или CallbackQuery)
            data: Данные

        Returns:
            Результат выполнения handler
        """
        try:
            return await handler(event, data)
        except InvalidStateTransitionError as e:
            # Обрабатываем только события, у которых есть пользователь и понятный контекст
            if isinstance(event, (Message, CallbackQuery)):
                user = event.from_user
                user_id: int | str = user.id if user else "unknown"

                logger.warning(
                    "State transition validation error: %s (user: %s, event: %s)",
                    e,
                    user_id,
                    type(event).__name__,
                )

                error_message = (
                    "❌ <b>Недопустимое действие</b>\n\n"
                    f"{e!s}\n\n"
                    "<i>Проверьте текущий статус заявки и попробуйте снова.</i>"
                )

                if isinstance(event, CallbackQuery):
                    await event.answer(
                        f"❌ Недопустимое действие: {e.reason if e.reason else str(e)}",
                        show_alert=True,
                    )
                    message = event.message
                    if isinstance(message, Message):
                        try:
                            await message.edit_text(
                                error_message,
                                parse_mode="HTML",
                            )
                        except Exception as edit_error:
                            logger.error("Failed to edit message: %s", edit_error)
                elif isinstance(event, Message):
                    await event.answer(error_message, parse_mode="HTML")
            else:
                logger.warning(
                    "InvalidStateTransitionError outside Message/CallbackQuery: %s (event=%s)",
                    e,
                    type(event).__name__,
                )

            # Не пробрасываем исключение дальше - обработали
            return None
