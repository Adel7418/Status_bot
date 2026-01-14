"""
Telethon Client для мониторинга Telegram-группы

Обрабатывает входящие сообщения из группы через Telethon (MTProto).
Работает параллельно с aiogram ботом.
"""

import asyncio
import logging
import os
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
        session_dir: str = "",
        on_message_callback: Callable[[str, int, int | None], Awaitable[None]] | None = None,
    ) -> None:
        """
        Инициализация Telethon клиента.

        Args:
            api_id: API ID от my.telegram.org
            api_hash: API Hash от my.telegram.org
            phone: Номер телефона для авторизации
            session_name: Имя session файла (default: "parser_session")
            session_dir: Директория для session файла (для Docker persistence)
            on_message_callback: Callback для обработки новых сообщений
                                Сигнатура: async def callback(text: str, message_id: int, sender_id: int | None)
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_name = session_name
        self.session_dir = session_dir
        self.on_message_callback = on_message_callback

        # Определяем полный путь к session файлу
        if self.session_dir:
            os.makedirs(self.session_dir, exist_ok=True)
            self.session_path = os.path.join(self.session_dir, self.session_name)
        else:
            self.session_path = self.session_name

        # Создаём клиент
        self.client = TelegramClient(
            session=self.session_path,
            api_id=self.api_id,
            api_hash=self.api_hash,
        )

        self.group_id: int | None = None
        self.is_running = False

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def start(self, group_id: int | None = None) -> None:
        """
        Запускает Telethon клиент и начинает мониторинг группы.

        Требует предварительной аутентификации через auth_parser.py.
        Session файл должен быть скопирован в TELETHON_SESSION_DIR.

        Args:
            group_id: ID Telegram-группы для мониторинга (опционально)

        Raises:
            ValueError: Если group_id не указан и не был установлен ранее
            RuntimeError: Если session файл не найден или невалиден
        """
        if group_id is not None:
            self.group_id = group_id

        if self.group_id is None:
            raise ValueError("group_id должен быть установлен перед запуском")

        self.logger.info(
            f"Запуск Telethon клиента для группы {self.group_id} (сессия: {self.session_path})"
        )

        # Подключаемся к Telegram
        await self.client.connect()

        if not await self.client.is_user_authorized():
            await self.client.disconnect()
            raise RuntimeError(
                f"Session файл не найден или невалиден: {self.session_path}.session\n"
                "Выполните аутентификацию локально: python auth_parser.py"
            )

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
            session_dir=Config.TELETHON_SESSION_DIR,
            on_message_callback=on_message_callback,
        )
