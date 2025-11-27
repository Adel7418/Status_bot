"""
Parser Integration Service

Интеграция Telethon парсера с основным ботом.
Управляет запуском TelethonClient и связывает его с OrderParserService и OrderConfirmationService.
"""

import asyncio
import contextlib
import logging

from aiogram import Bot

from app.core.config import Config
from app.database.orm_database import ORMDatabase
from app.database.parser_config_repository import ParserConfigRepository
from app.services.telegram_parser import (
    OrderConfirmationService,
    OrderParsed,
    OrderParserService,
    TelethonClient,
)


logger = logging.getLogger(__name__)


class ParserIntegration:
    """
    Сервис интеграции Telethon парсера с основным ботом.

    Управляет жизненным циклом парсера:
    1. Инициализация TelethonClient, OrderParserService, OrderConfirmationService
    2. Запуск мониторинга группы
    3. Обработка новых сообщений (парсинг + подтверждение)
    4. Создание заявок в БД после подтверждения
    """

    def __init__(self, bot: Bot, db: ORMDatabase) -> None:
        """
        Инициализация сервиса интеграции.

        Args:
            bot: Экземпляр aiogram Bot
            db: Экземпляр ORMDatabase
        """
        self.bot = bot
        self.db = db

        self.telethon_client: TelethonClient | None = None
        self.parser_service: OrderParserService | None = None
        self.confirmation_service: OrderConfirmationService | None = None

        self.is_running = False
        self.telethon_task: asyncio.Task | None = None

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def start(self) -> None:
        """
        Запускает парсер (если включён в конфигурации).

        Проверяет:
        1. PARSER_ENABLED в Config
        2. Наличие group_id в БД
        3. Наличие Telethon credentials

        Raises:
            ValueError: Если парсер не может быть запущен
        """
        # Проверка 1: Парсер включён в .env?
        if not Config.PARSER_ENABLED:
            self.logger.info("Парсер отключён (PARSER_ENABLED=false), пропускаем запуск")
            return

        self.logger.info("Инициализация парсера заявок...")

        # Проверка 2: group_id установлен в БД?
        async with self.db.session_factory() as session:
            repo = ParserConfigRepository(session)
            config = await repo.get_config()

        if not config or not config.group_id:
            self.logger.warning(
                "⚠️ Парсер включён, но group_id не установлен. "
                "Используйте /set_group для настройки."
            )
            return

        if not config.enabled:
            self.logger.info(
                "Парсер отключён в БД (enabled=false). "
                "Используйте /parser_status для проверки."
            )
            return

        # Инициализация компонентов
        try:
            # 1. OrderParserService
            self.parser_service = OrderParserService()
            self.logger.info("✅ OrderParserService инициализирован")

            # 2. OrderConfirmationService
            self.confirmation_service = OrderConfirmationService(
                bot=self.bot,
                on_confirm_callback=self._on_order_confirmed,
            )
            self.logger.info("✅ OrderConfirmationService инициализирован")

            # 3. TelethonClient
            self.telethon_client = TelethonClient.from_config(
                on_message_callback=self._on_new_message,
            )
            self.logger.info("✅ TelethonClient создан")

            # Запуск Telethon
            await self.telethon_client.start(group_id=config.group_id)
            self.logger.info(f"✅ Telethon запущен для группы {config.group_id}")

            # Запускаем в фоновой задаче
            self.telethon_task = asyncio.create_task(
                self.telethon_client.run_until_disconnected()
            )
            self.is_running = True

            self.logger.info("🟢 Парсер заявок успешно запущен!")

        except Exception as e:
            self.logger.exception(f"Ошибка при запуске парсера: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Останавливает парсер"""
        if not self.is_running:
            return

        self.logger.info("Остановка парсера заявок...")

        # Остановка Telethon
        if self.telethon_client:
            try:
                await self.telethon_client.stop()
                self.logger.info("✅ TelethonClient остановлен")
            except Exception as e:
                self.logger.error(f"Ошибка при остановке TelethonClient: {e}")

        # Отмена фоновой задачи
        if self.telethon_task and not self.telethon_task.done():
            self.telethon_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.telethon_task

        self.is_running = False
        self.logger.info("🛑 Парсер заявок остановлен")

    async def _on_new_message(self, text: str, message_id: int) -> None:
        """
        Callback для обработки новых сообщений из Telegram-группы.

        Args:
            text: Текст сообщения
            message_id: ID сообщения в Telegram
        """
        self.logger.info(f"Обработка сообщения {message_id} (длина: {len(text)} символов)")

        # Парсинг сообщения
        parse_result = self.parser_service.parse_message(text, message_id)

        if not parse_result.success:
            self.logger.warning(
                f"Не удалось распарсить сообщение {message_id}: {parse_result.error_message}"
            )
            # НЕ отправляем уведомление в группу о неудачном парсинге
            # (чтобы не спамить при обычных сообщениях диспетчеров)
            return

        # Успешный парсинг — отправляем подтверждение
        self.logger.info(
            f"✅ Сообщение {message_id} успешно распарсено: "
            f"{parse_result.data.equipment_type} - {parse_result.data.address}"
        )

        try:
            # Отправляем в группу диспетчеров (или в ту же группу)
            chat_id = Config.DISPATCHER_GROUP_ID or self.telethon_client.group_id

            await self.confirmation_service.send_confirmation(
                chat_id=chat_id,
                order=parse_result.data,
            )
            self.logger.info(f"Отправлено подтверждение для заявки из сообщения {message_id}")

        except Exception as e:
            self.logger.exception(
                f"Ошибка при отправке подтверждения для сообщения {message_id}: {e}",
            )

    async def _on_order_confirmed(self, order: OrderParsed) -> None:
        """
        Callback для создания заявки после подтверждения.

        Args:
            order: Распарсенная заявка для создания
        """
        self.logger.info(
            f"Создание заявки из сообщения {order.message_id}: "
            f"{order.equipment_type} - {order.address}"
        )

        try:
            # Создаём заявку в БД
            async with self.db.session_factory() as session:
                # Используем существующий метод create_order из ORMDatabase
                # NOTE: Это упрощённая версия, в реальности нужно использовать OrderRepository
                from app.database.orm_models import Order
                from app.utils.helpers import get_now

                new_order = Order(
                    equipment_type=order.equipment_type,
                    problem_description=order.problem_description,
                    client_name=order.client_name,
                    client_address=order.address,
                    client_phone=order.phone,
                    status="created",
                    created_at=get_now(),
                )

                session.add(new_order)
                await session.commit()
                await session.refresh(new_order)

                self.logger.info(
                    f"✅ Заявка #{new_order.id} успешно создана из сообщения {order.message_id}"
                )

                # Отправляем уведомление диспетчерам
                if Config.DISPATCHER_GROUP_ID:
                    await self.bot.send_message(
                        chat_id=Config.DISPATCHER_GROUP_ID,
                        text=f"✅ <b>Заявка #{new_order.id} создана из парсера!</b>\n\n"
                        f"🔧 {order.equipment_type}\n"
                        f"📍 {order.address}\n"
                        f"📞 {order.phone or 'не указан'}",
                        parse_mode="HTML",
                    )

        except Exception as e:
            self.logger.exception(
                f"Ошибка при создании заявки из сообщения {order.message_id}: {e}",
            )
            # Отправляем уведомление об ошибке
            if Config.DISPATCHER_GROUP_ID:
                await self.bot.send_message(
                    chat_id=Config.DISPATCHER_GROUP_ID,
                    text=f"❌ Ошибка при создании заявки из парсера:\n{e!s}",
                )
