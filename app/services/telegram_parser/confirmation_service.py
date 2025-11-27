"""
Order Confirmation Service

Управляет подтверждением создания заявок через inline-кнопки в Telegram боте.
После парсинга сообщения отправляет диспетчеру кнопки "Да/Нет" для подтверждения.
"""

import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .schemas import ConfirmationData, OrderParsed


logger = logging.getLogger(__name__)


class OrderConfirmationService:
    """
    Сервис подтверждения создания заявок через inline-кнопки.

    Workflow:
    1. Получает распарсенную заявку (OrderParsed)
    2. Отправляет сообщение с inline-кнопками "✅ Да" / "❌ Нет"
    3. При нажатии "Да" — вызывает callback для создания заявки
    4. При нажатии "Нет" — удаляет сообщение с кнопками
    """

    def __init__(
        self,
        bot: Bot,
        on_confirm_callback: Callable[[OrderParsed], Awaitable[None]] | None = None,
    ) -> None:
        """
        Инициализация сервиса подтверждения.

        Args:
            bot: Экземпляр aiogram Bot для отправки сообщений
            on_confirm_callback: Callback при подтверждении создания заявки
                                Сигнатура: async def callback(order: OrderParsed)
        """
        self.bot = bot
        self.on_confirm_callback = on_confirm_callback

        # Хранилище ожидающих подтверждения заявок
        # message_id (confirmation) → ConfirmationData
        self.pending_confirmations: dict[int, ConfirmationData] = {}

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def send_confirmation(
        self,
        chat_id: int,
        order: OrderParsed,
    ) -> ConfirmationData:
        """
        Отправляет сообщение с кнопками подтверждения создания заявки.

        Args:
            chat_id: ID чата для отправки (обычно DISPATCHER_GROUP_ID)
            order: Распарсенная заявка для подтверждения

        Returns:
            ConfirmationData с ID сообщения подтверждения

        Example:
            >>> confirmation = await service.send_confirmation(
            ...     chat_id=-1001234567890,
            ...     order=parsed_order
            ... )
        """
        # Формируем текст сообщения
        message_text = self._format_confirmation_message(order)

        # Создаём inline-кнопки
        keyboard = self._create_confirmation_keyboard(order.message_id)

        # Отправляем сообщение
        sent_message = await self.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

        # Создаём ConfirmationData
        confirmation_data = ConfirmationData(
            message_id=order.message_id,
            parsed_order=order,
            confirmation_message_id=sent_message.message_id,
        )

        # Сохраняем в pending
        self.pending_confirmations[sent_message.message_id] = confirmation_data

        self.logger.info(
            f"Отправлено подтверждение для заявки (message_id={order.message_id}, "
            f"confirmation_id={sent_message.message_id})"
        )

        return confirmation_data

    async def handle_confirmation(
        self,
        confirmation_message_id: int,
        confirmed: bool,
        user_id: int,
    ) -> bool:
        """
        Обрабатывает нажатие на кнопку подтверждения.

        Args:
            confirmation_message_id: ID сообщения с кнопками подтверждения
            confirmed: True если нажата кнопка "Да", False если "Нет"
            user_id: ID пользователя, нажавшего кнопку

        Returns:
            True если обработка успешна, False если подтверждение не найдено

        Example:
            >>> await service.handle_confirmation(
            ...     confirmation_message_id=12346,
            ...     confirmed=True,
            ...     user_id=123456789
            ... )
        """
        # Ищем подтверждение в pending
        confirmation_data = self.pending_confirmations.get(confirmation_message_id)

        if not confirmation_data:
            self.logger.warning(
                f"Подтверждение не найдено (confirmation_id={confirmation_message_id})"
            )
            return False

        if confirmed:
            # Пользователь нажал "Да" — создаём заявку
            self.logger.info(
                f"✅ Подтверждено создание заявки (message_id={confirmation_data.message_id}, "
                f"user_id={user_id})"
            )

            # Вызываем callback если установлен
            if self.on_confirm_callback:
                try:
                    await self.on_confirm_callback(confirmation_data.parsed_order)
                except Exception as e:
                    self.logger.exception(
                        f"Ошибка в callback подтверждения: {e}",
                    )
                    return False
            else:
                self.logger.warning("Callback для подтверждения не установлен")

        else:
            # Пользователь нажал "Нет" — отклоняем
            self.logger.info(
                f"❌ Отклонено создание заявки (message_id={confirmation_data.message_id}, "
                f"user_id={user_id})"
            )

        # Удаляем из pending
        del self.pending_confirmations[confirmation_message_id]

        return True

    def set_confirm_callback(self, callback: Callable[[OrderParsed], None]) -> None:
        """
        Устанавливает callback для подтверждения создания заявки.

        Args:
            callback: Async функция с сигнатурой (order: OrderParsed) -> None
        """
        self.on_confirm_callback = callback
        self.logger.debug("Callback для подтверждения установлен")

    def _format_confirmation_message(self, order: OrderParsed) -> str:
        """
        Форматирует текст сообщения для подтверждения.

        Args:
            order: Распарсенная заявка

        Returns:
            Отформатированный текст с HTML разметкой
        """
        lines = [
            "📋 <b>Создать заявку?</b>",
            "",
            f"🔧 <b>Тип:</b> {order.equipment_type}",
            f"❗ <b>Проблема:</b> {order.problem_description}",
            f"📍 <b>Адрес:</b> {order.address}",
            f"👤 <b>Клиент:</b> {order.client_name}",
        ]

        if order.phone:
            lines.append(f"📞 <b>Телефон:</b> {order.phone}")

        if order.scheduled_time:
            lines.append(f"🕐 <b>Время:</b> {order.scheduled_time}")

        return "\n".join(lines)

    def _create_confirmation_keyboard(self, message_id: int) -> InlineKeyboardMarkup:
        """
        Создаёт inline-клавиатуру с кнопками подтверждения.

        Args:
            message_id: ID исходного сообщения из группы

        Returns:
            InlineKeyboardMarkup с кнопками "Да" и "Нет"
        """
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Да",
                        callback_data=f"confirm_order:yes:{message_id}",
                    ),
                    InlineKeyboardButton(
                        text="❌ Нет",
                        callback_data=f"confirm_order:no:{message_id}",
                    ),
                ]
            ]
        )

    def get_pending_confirmation(
        self,
        confirmation_message_id: int,
    ) -> ConfirmationData | None:
        """
        Получает данные ожидающего подтверждения.

        Args:
            confirmation_message_id: ID сообщения с кнопками подтверждения

        Returns:
            ConfirmationData или None если не найдено
        """
        return self.pending_confirmations.get(confirmation_message_id)

    def get_pending_count(self) -> int:
        """
        Возвращает количество ожидающих подтверждения заявок.

        Returns:
            Количество pending confirmations
        """
        return len(self.pending_confirmations)
