"""
Retry механизм для Bot API запросов с экспоненциальным backoff
"""
import asyncio
import logging
from functools import wraps
from typing import Any, Callable, TypeVar

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramConflictError,
    TelegramEntityTooLarge,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramServerError,
    TelegramUnauthorizedError,
)


logger = logging.getLogger(__name__)

T = TypeVar("T")

# Исключения, которые нельзя повторять (ошибки валидации/прав)
NON_RETRYABLE_EXCEPTIONS = (
    TelegramBadRequest,  # Некорректный запрос (не исправится повтором)
    TelegramNotFound,  # Чат/сообщение не найдены
    TelegramUnauthorizedError,  # Неверный токен бота
    TelegramConflictError,  # Конфликт (бот уже запущен)
    TelegramForbiddenError,  # Бот кикнут из чата
    TelegramEntityTooLarge,  # Файл слишком большой
)

# Исключения, которые можно повторять
RETRYABLE_EXCEPTIONS = (
    TelegramNetworkError,  # Сетевые ошибки
    TelegramServerError,  # Ошибки сервера Telegram (5xx)
    TelegramRetryAfter,  # Превышен лимит запросов (429)
)


def retry_on_telegram_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = RETRYABLE_EXCEPTIONS,
) -> Callable:
    """
    Декоратор для повтора Bot API запросов с экспоненциальным backoff
    
    Args:
        max_attempts: Максимальное количество попыток
        base_delay: Базовая задержка между попытками (секунды)
        max_delay: Максимальная задержка между попытками (секунды)
        exponential_base: База для экспоненциального роста задержки
        exceptions: Кортеж исключений для повтора
        
    Returns:
        Декоратор функции
        
    Example:
        @retry_on_telegram_error(max_attempts=5)
        async def send_notification(bot, chat_id, text):
            return await bot.send_message(chat_id, text)
    """
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T | None:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    # Выполняем функцию
                    return await func(*args, **kwargs)
                    
                except TelegramRetryAfter as e:
                    # Специальная обработка для 429 Too Many Requests
                    # Telegram указывает точное время ожидания
                    retry_after = e.retry_after
                    wait_time = min(retry_after, max_delay)
                    
                    logger.warning(
                        "%s: Flood control exceeded (429). "
                        "Retry after %s seconds. Attempt %d/%d",
                        func.__name__,
                        retry_after,
                        attempt,
                        max_attempts,
                    )
                    
                    if attempt < max_attempts:
                        logger.info("Waiting %s seconds before retry...", wait_time)
                        await asyncio.sleep(wait_time)
                        last_exception = e
                        continue
                    else:
                        logger.error(
                            "%s: Max attempts reached after flood control. Giving up.",
                            func.__name__,
                        )
                        return None
                        
                except exceptions as e:
                    # Обработка сетевых ошибок и ошибок сервера
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    
                    logger.warning(
                        "%s: %s occurred. Attempt %d/%d. Error: %s",
                        func.__name__,
                        type(e).__name__,
                        attempt,
                        max_attempts,
                        str(e),
                    )
                    
                    if attempt < max_attempts:
                        logger.info("Retrying in %.2f seconds...", delay)
                        await asyncio.sleep(delay)
                        last_exception = e
                        continue
                    else:
                        logger.error(
                            "%s: Max attempts reached. Giving up. Last error: %s",
                            func.__name__,
                            str(e),
                        )
                        return None
                        
                except NON_RETRYABLE_EXCEPTIONS as e:
                    # Ошибки, которые не имеет смысла повторять
                    logger.error(
                        "%s: Non-retryable error %s: %s. Not retrying.",
                        func.__name__,
                        type(e).__name__,
                        str(e),
                    )
                    return None
                    
                except TelegramAPIError as e:
                    # Другие Telegram ошибки (на всякий случай)
                    logger.error(
                        "%s: Unexpected Telegram API error %s: %s. Not retrying.",
                        func.__name__,
                        type(e).__name__,
                        str(e),
                    )
                    return None
                    
                except Exception as e:
                    # Неожиданные ошибки (не Telegram)
                    logger.exception(
                        "%s: Unexpected error %s: %s. Not retrying.",
                        func.__name__,
                        type(e).__name__,
                        str(e),
                    )
                    return None
            
            # Если дошли сюда - все попытки исчерпаны
            if last_exception:
                logger.error(
                    "%s: All %d attempts failed. Last exception: %s",
                    func.__name__,
                    max_attempts,
                    str(last_exception),
                )
            return None
            
        return wrapper
    return decorator


async def safe_send_message(
    bot,
    chat_id: int,
    text: str,
    max_attempts: int = 3,
    **kwargs: Any,
) -> Any | None:
    """
    Безопасная отправка сообщения с автоматическим retry
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        text: Текст сообщения
        max_attempts: Максимальное количество попыток
        **kwargs: Дополнительные параметры для send_message
        
    Returns:
        Message объект или None при ошибке
    """
    
    @retry_on_telegram_error(max_attempts=max_attempts)
    async def _send():
        return await bot.send_message(chat_id, text, **kwargs)
    
    return await _send()


async def safe_answer_callback(
    callback_query,
    text: str | None = None,
    max_attempts: int = 2,
    **kwargs: Any,
) -> bool:
    """
    Безопасный ответ на callback query с retry
    
    Args:
        callback_query: CallbackQuery объект
        text: Текст ответа
        max_attempts: Максимальное количество попыток
        **kwargs: Дополнительные параметры
        
    Returns:
        True при успехе, False при ошибке
    """
    
    @retry_on_telegram_error(max_attempts=max_attempts, base_delay=0.5)
    async def _answer():
        return await callback_query.answer(text, **kwargs)
    
    result = await _answer()
    return result is not None


async def safe_edit_message(
    message,
    text: str,
    max_attempts: int = 3,
    **kwargs: Any,
) -> Any | None:
    """
    Безопасное редактирование сообщения с retry
    
    Args:
        message: Message объект
        text: Новый текст
        max_attempts: Максимальное количество попыток
        **kwargs: Дополнительные параметры
        
    Returns:
        Message объект или None при ошибке
    """
    
    @retry_on_telegram_error(max_attempts=max_attempts)
    async def _edit():
        return await message.edit_text(text, **kwargs)
    
    return await _edit()


async def safe_delete_message(
    bot,
    chat_id: int,
    message_id: int,
    max_attempts: int = 2,
) -> bool:
    """
    Безопасное удаление сообщения с retry
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        message_id: ID сообщения
        max_attempts: Максимальное количество попыток
        
    Returns:
        True при успехе, False при ошибке
    """
    
    @retry_on_telegram_error(max_attempts=max_attempts, base_delay=0.5)
    async def _delete():
        return await bot.delete_message(chat_id, message_id)
    
    result = await _delete()
    return result is not None

