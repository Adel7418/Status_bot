"""
Middleware для обработки ошибок валидации State Machine
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.domain.order_state_machine import InvalidStateTransitionError


logger = logging.getLogger(__name__)


class ValidationHandlerMiddleware(BaseMiddleware):
    """Middleware для обработки ошибок валидации переходов статусов"""

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
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
            # Логируем ошибку
            logger.warning(
                f"State transition validation error: {e} "
                f"(user: {event.from_user.id}, event: {type(event).__name__})"
            )

            # Формируем user-friendly сообщение
            error_message = (
                f"❌ <b>Недопустимое действие</b>\n\n"
                f"{str(e)}\n\n"
                f"<i>Проверьте текущий статус заявки и попробуйте снова.</i>"
            )

            # Отправляем сообщение пользователю
            if isinstance(event, CallbackQuery):
                # Для callback query - показываем alert
                await event.answer(
                    f"❌ Недопустимое действие: {e.reason if e.reason else str(e)}",
                    show_alert=True,
                )
                # И обновляем сообщение
                try:
                    await event.message.edit_text(
                        error_message,
                        parse_mode="HTML",
                    )
                except Exception as edit_error:
                    logger.error(f"Failed to edit message: {edit_error}")
            else:
                # Для обычного сообщения - просто отвечаем
                await event.answer(error_message, parse_mode="HTML")

            # Не пробрасываем исключение дальше - обработали
            return None

