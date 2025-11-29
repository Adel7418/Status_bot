"""
Telethon Client для мониторинга Telegram-группы

Обрабатывает входящие сообщения из группы через Telethon (MTProto).
Работает параллельно с aiogram ботом.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from telethon import TelegramClient, events
from telethon.tl.types import Message

from app.core.config import Config


logger = logging.getLogger(__name__)


class TelethonClient:
    """
    Клиент для мониторинга Telegram-группы через Telethon.

    Использует MTProto API для получения сообщений из группы.
    Работает параллельно с aiogram ботом (разные Telegram clients).
    """

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        session_name: str = "parser_session",
        on_message_callback: Callable[[str, int, int | None], Awaitable[None]] | None = None,
    ) -> None:
        """
        Инициализация Telethon клиента.

        Args:
            api_id: API ID от my.telegram.org
            api_hash: API Hash от my.telegram.org
            phone: Номер телефона для авторизации
            session_name: Имя session файла (default: "parser_session")
            on_message_callback: Callback для обработки новых сообщений
                                Сигнатура: async def callback(text: str, message_id: int, sender_id: int | None)
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_name = session_name
        self.on_message_callback = on_message_callback

        # Создаём клиент
        self.client = TelegramClient(
            session=self.session_name,
            api_id=self.api_id,
            api_hash=self.api_hash,
        )

        self.group_id: int | None = None
        self.is_running = False

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def start(
        self,
        group_id: int | None = None,
        code_callback: Callable[[], Awaitable[str]] | None = None,
        password_callback: Callable[[], Awaitable[str]] | None = None,
    ) -> None:
        """
        Запускает Telethon клиент и начинает мониторинг группы.

        Args:
            group_id: ID Telegram-группы для мониторинга (опционально)
            code_callback: Callback для получения кода авторизации (если требуется)
            password_callback: Callback для получения пароля 2FA (если требуется)

        Raises:
            ValueError: Если group_id не указан и не был установлен ранее
        """
        if group_id is not None:
            self.group_id = group_id

        if self.group_id is None:
            raise ValueError("group_id должен быть установлен перед запуском")

        self.logger.info(
            f"Запуск Telethon клиента для группы {self.group_id} (сессия: {self.session_name})"
        )

        # Подключаемся к Telegram
        if code_callback:
            # Интерактивный режим (аутентификация)
            await self.client.start(
                phone=self.phone,
                code_callback=code_callback,
                password=password_callback
            )
        else:
            # Фоновый режим: проверяем авторизацию перед стартом
            await self.client.connect()
            if not await self.client.is_user_authorized():
                await self.client.disconnect()
                raise RuntimeError(
                    "Требуется аутентификация! Используйте команду /parser_auth"
                )
            
            # Если авторизованы - просто стартуем (это не вызовет запрос кода)
            await self.client.start(phone=self.phone)
            
        self.logger.info("✅ Telethon клиент авторизован")

        # Регистрируем обработчик новых сообщений (слушаем все чаты, фильтруем внутри)
        @self.client.on(events.NewMessage())
        async def handler(event: events.NewMessage.Event) -> None:
            """Обработчик новых сообщений из группы"""
            await self._handle_new_message(event)

        self.is_running = True
        self.logger.info(f"🟢 Мониторинг группы {self.group_id} активен (слушаем все события)")

    async def stop(self) -> None:
        """Останавливает Telethon клиент"""
        self.logger.info("Остановка Telethon клиента")
        self.is_running = False

        if self.client.is_connected():
            await self.client.disconnect()
            self.logger.info("✅ Telethon клиент отключён")

    async def run_until_disconnected(self) -> None:
        """
        Запускает клиент и держит его активным до отключения.

        Используется для запуска в отдельной задаче (asyncio.Task).
        """
        await self.client.run_until_disconnected()

    def set_group_id(self, group_id: int) -> None:
        """
        Устанавливает ID группы для мониторинга.

        Args:
            group_id: ID Telegram-группы
        """
        old_group_id = self.group_id
        self.group_id = group_id

        if old_group_id != group_id:
            self.logger.info(f"Группа для мониторинга изменена: {old_group_id} → {group_id}")

    def set_message_callback(self, callback: Callable[[str, int, int | None], None]) -> None:
        """
        Устанавливает callback для обработки новых сообщений.

        Args:
            callback: Async функция с сигнатурой (text: str, message_id: int, sender_id: int | None) -> None
        """
        self.on_message_callback = callback
        self.logger.debug("Callback для обработки сообщений установлен")

    async def _handle_new_message(self, event: events.NewMessage.Event) -> None:
        """
        Внутренний обработчик новых сообщений из группы.

        Args:
            event: Событие нового сообщения от Telethon
        """
        message: Message = event.message

        # Проверяем что это текстовое сообщение
        if not message.text:
            self.logger.debug(f"Пропущено нетекстовое сообщение (ID: {message.id})")
            return

        # Проверяем что сообщение из нужной группы
        if message.chat_id != self.group_id:
            # Логируем только если это похоже на нашу группу (например, тот же ID но без минуса или 100)
            # Или просто логируем все для отладки (временно)
            self.logger.debug(
                f"DEBUG: Сообщение из чата {message.chat_id} пропущено (ожидался {self.group_id})"
            )
            return

        self.logger.info(
            f"📨 Новое сообщение из группы {self.group_id} (ID: {message.id}, длина: {len(message.text)} символов)"
        )
        self.logger.debug(f"Текст сообщения: {message.text[:100]}...")

        # Вызываем callback если он установлен
        if self.on_message_callback:
            try:
                # Если callback корутина — await, иначе просто вызываем
                if asyncio.iscoroutinefunction(self.on_message_callback):
                    await self.on_message_callback(message.text, message.id, message.sender_id)
                else:
                    self.on_message_callback(message.text, message.id, message.sender_id)
            except Exception as e:
                self.logger.exception(
                    f"Ошибка в callback обработки сообщения (ID: {message.id}): {e}",
                )
        else:
            self.logger.warning("Callback для обработки сообщений не установлен")

    @classmethod
    def from_config(
        cls,
        on_message_callback: Callable[[str, int, int | None], Awaitable[None]] | None = None,
    ) -> "TelethonClient":
        """
        Создаёт TelethonClient из конфигурации приложения.

        Args:
            on_message_callback: Callback для обработки новых сообщений

        Returns:
            Экземпляр TelethonClient

        Raises:
            ValueError: Если в конфигурации отсутствуют необходимые параметры
        """
        if not Config.TELETHON_API_ID:
            raise ValueError("TELETHON_API_ID не установлен в конфигурации")
        if not Config.TELETHON_API_HASH:
            raise ValueError("TELETHON_API_HASH не установлен в конфигурации")
        if not Config.TELETHON_PHONE:
            raise ValueError("TELETHON_PHONE не установлен в конфигурации")

        return cls(
            api_id=Config.TELETHON_API_ID,
            api_hash=Config.TELETHON_API_HASH,
            phone=Config.TELETHON_PHONE,
            session_name=Config.TELETHON_SESSION_NAME,
            on_message_callback=on_message_callback,
        )
