"""
Middleware для логирования входящих событий и метрик производительности

GDPR Compliance: Маскирует персональные данные в логах
"""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.utils.pii_masking import mask_username


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware для централизованного логирования всех событий

    Логирует:
    - Входящие сообщения и callback queries
    - User ID, username, chat type
    - Время обработки каждого события
    - Ошибки при обработке
    """

    def __init__(self, log_level: int = logging.INFO):
        """
        Инициализация

        Args:
            log_level: Уровень логирования (по умолчанию INFO)
        """
        super().__init__()
        self.log_level = log_level

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Обработка события с логированием

        Args:
            handler: Следующий handler
            event: Событие (Message или CallbackQuery)
            data: Данные

        Returns:
            Результат выполнения handler
        """
        # Обрабатываем только Message/CallbackQuery; прочие события просто прокидываем дальше
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        # Получаем пользователя (GDPR: маскируем username)
        user = event.from_user
        user_info = "unknown"
        if user:
            user_info = f"{user.id}"
            if user.username:
                masked_username = mask_username(user.username)
                user_info += f" (@{masked_username})"

        # Стартуем таймер
        start_time = time.time()

        # Логируем входящее событие
        if isinstance(event, Message):
            chat_type = event.chat.type
            text_preview = ""

            if event.text:
                # Показываем первые 50 символов текста
                text_preview = event.text[:50]
                if len(event.text) > 50:
                    text_preview += "..."
            elif event.photo:
                text_preview = "[photo]"
            elif event.document:
                text_preview = "[document]"
            elif event.voice:
                text_preview = "[voice]"
            elif event.video:
                text_preview = "[video]"
            else:
                text_preview = "[other media]"

            # Логируем текст с безопасной обработкой Unicode
            safe_text = text_preview.encode("ascii", "replace").decode("ascii")
            logger.log(
                self.log_level,
                f"[MSG] Message from {user_info} in {chat_type}: {safe_text}",
            )

        elif isinstance(event, CallbackQuery):
            callback_data = event.data[:100] if event.data else "[no data]"

            logger.log(
                self.log_level,
                f"[CALLBACK] Callback from {user_info}: {callback_data}",
            )

        # Выполняем handler и замеряем время
        try:
            result = await handler(event, data)

            # Время обработки
            duration = time.time() - start_time

            # Логируем успешную обработку
            if duration > 1.0:
                # Если обработка > 1 сек - логируем как WARNING
                logger.warning(f"[SLOW] Handler processed in {duration:.2f}s by {user_info}")
            else:
                logger.log(
                    logging.DEBUG,
                    f"[OK] Processed in {duration:.3f}s",
                )

            return result

        except Exception as e:
            # Логируем ошибку
            duration = time.time() - start_time
            logger.error(f"[ERROR] After {duration:.2f}s for {user_info}: {type(e).__name__}: {e}")
            # Пробрасываем исключение дальше (для global error handler)
            raise
