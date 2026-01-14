"""
Parser Integration Service

Интеграция Telethon парсера с основным ботом.
Управляет запуском TelethonClient и связывает его с OrderParserService и OrderConfirmationService.
"""

import asyncio
import contextlib
import logging
import time

from aiogram import Bot

from app.core.config import Config
from app.database.orm_database import ORMDatabase
from app.database.parser_config_repository import ParserConfigRepository
from app.services.parser_analytics import ParserAnalyticsService
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
        self.analytics_service: ParserAnalyticsService = ParserAnalyticsService(db.session_factory)
        self.group_id: int | None = None  # ID группы для парсера

        self.is_running = False
        self.telethon_task: asyncio.Task | None = None

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("ParserIntegration initialized")

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

        # Сохраняем group_id для использования
        self.group_id = config.group_id

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
            try:
                await self.telethon_client.start(group_id=config.group_id)
                self.logger.info(f"✅ Telethon запущен для группы {config.group_id}")

                # Запускаем в фоновой задаче
                self.telethon_task = asyncio.create_task(
                    self.telethon_client.run_until_disconnected()
                )
                self.is_running = True
                self.logger.info("🟢 Парсер заявок успешно запущен!")
            except RuntimeError as e:
                # Session файл не найден или невалиден
                self.logger.warning(f"⚠️ {e}")
                self.logger.info(
                    "Выполните аутентификацию локально: python auth_parser.py\n"
                    "Затем скопируйте session файл в TELETHON_SESSION_DIR"
                )

        except Exception as e:
            self.logger.error(f"Ошибка при запуске парсера: {e}")
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

    async def reset_client(self) -> None:
        """
        Сбрасывает текущий клиент Telethon.
        Используется при сбросе сессии, чтобы гарантировать пересоздание клиента.
        """
        await self.stop()
        self.telethon_client = None
        self.logger.info("🔄 TelethonClient сброшен (будет пересоздан при следующем запуске)")

    async def _on_new_message(self, text: str, message_id: int, sender_id: int | None) -> None:
        """
        Callback для обработки новых сообщений из Telegram-группы.

        Args:
            text: Текст сообщения
            message_id: ID сообщения в Telegram
            sender_id: ID отправителя сообщения
        """
        self.logger.info(f"Обработка сообщения {message_id} от {sender_id} (длина: {len(text)} символов)")

        # Игнорируем сообщения от самого бота (предотвращаем зацикливание)
        if sender_id:
            # Получаем bot_id из токена (первая часть токена до первого двоеточия)
            bot_id = int(Config.BOT_TOKEN.split(':')[0]) if Config.BOT_TOKEN else None
            if bot_id and sender_id == bot_id:
                self.logger.debug(f"Игнорируем сообщение от бота (sender_id={sender_id})")
                return
        
        # Игнорируем слишком короткие сообщения (< 15 символов)
        # Это обычно фрагменты редактирования или команды, не заявки
        if len(text.strip()) < 15:
            self.logger.debug(f"Пропускаем короткое сообщение ({len(text)} символов): {text[:20]}")
            return
        
        # Игнорируем сообщения, содержащие только время (паттерн ЧЧ:ММ)
        import re
        time_only_pattern = r'^\s*\d{1,2}:\d{2}\s*$'
        if re.match(time_only_pattern, text.strip()):
            self.logger.debug(f"Пропускаем сообщение с только временем: {text}")
            return


        # Парсинг сообщения (измеряем время)
        start_time = time.time()
        parse_result = self.parser_service.parse_message(text, message_id)
        processing_time_ms = int((time.time() - start_time) * 1000)

        if not parse_result.success:
            # Логируем как INFO, чтобы не спамить в логах (так как это могут быть обычные сообщения)
            self.logger.info(
                f"Сообщение {message_id} не распознано как заявка: {parse_result.error_message}"
            )

            # Отправляем уведомление в группу для:
            # 1. Некорректного телефона (invalid_format + phone)
            # 2. Отсутствия описания проблемы (missing_fields + problem_description)
            # (для остальных ошибок не спамим, т.к. это могут быть обычные сообщения)
            should_notify = (
                (parse_result.status == "invalid_format" and "phone" in parse_result.missing_fields) or
                (parse_result.status == "missing_fields" and "problem_description" in parse_result.missing_fields)
            )

            if should_notify and self.group_id:
                try:
                    await self.bot.send_message(
                        chat_id=self.group_id,
                        text=parse_result.error_message,
                        parse_mode=None,
                    )
                except Exception as e:
                    self.logger.error(f"Ошибка при отправке уведомления об ошибке: {e}")
            
            # Записываем аналитику (неуспешный парсинг)
            await self.analytics_service.track_parse_event(
                message_id=message_id,
                group_id=self.group_id,
                success=False,
                error_type=parse_result.status,
                processing_time_ms=processing_time_ms,
            )
            return

        # Успешный парсинг — отправляем подтверждение
        self.logger.info(
            f"✅ Сообщение {message_id} успешно распарсено: "
            f"{parse_result.data.equipment_type} - {parse_result.data.address}"
        )
        
        # Записываем аналитику (успешный парсинг)
        await self.analytics_service.track_parse_event(
            message_id=message_id,
            group_id=self.group_id,
            success=True,
            parsed_equipment_type=parse_result.data.equipment_type,
            parsed_address=parse_result.data.address,
            parsed_phone=parse_result.data.phone,
            processing_time_ms=processing_time_ms,
        )

        # Проверяем на дубликаты и историю клиента ПЕРЕД отправкой подтверждения
        try:
            async with self.db.session_factory() as session:
                from app.database.orm_models import Order
                from sqlalchemy import select, and_, or_, func
                
                client_phone = parse_result.data.phone or "Не указан"
                client_address = parse_result.data.address

                # 1. Проверяем на дубликаты (активные заявки с такими же данными)
                active_statuses = ["NEW", "ASSIGNED", "ACCEPTED", "ONSITE"]
                duplicate_query = select(Order).where(
                    and_(
                        Order.client_address == client_address,
                        Order.client_phone == client_phone,
                        Order.equipment_type == parse_result.data.equipment_type,
                        Order.status.in_(active_statuses)
                    )
                )
                result = await session.execute(duplicate_query)
                existing_order = result.scalar_one_or_none()

                if existing_order:
                    self.logger.warning(
                        f"⚠️ Дубликат заявки обнаружен! Заявка #{existing_order.id} уже существует "
                        f"(статус: {existing_order.status}, адрес: {client_address}, "
                        f"телефон: {client_phone})"
                    )
                    # Отправляем уведомление о дубликате в группу
                    if self.group_id:
                        await self.bot.send_message(
                            chat_id=self.group_id,
                            text=(
                                f"⚠️ <b>Дубликат заявки!</b>\n\n"
                                f"Заявка #{existing_order.id} уже существует с такими данными:\n"
                                f"🔧 Тип: {parse_result.data.equipment_type}\n"
                                f"📍 Адрес: {client_address}\n"
                                f"📞 Телефон: {client_phone}\n"
                                f"📊 Статус: {existing_order.status}"
                            ),
                            parse_mode="HTML"
                        )
                    return  # Не отправляем подтверждение

                # 2. Проверяем историю клиента (по телефону или адресу)
                history_query = select(Order).where(
                    or_(
                        Order.client_phone == client_phone,
                        Order.client_address == client_address
                    )
                ).order_by(Order.created_at.desc())

                result = await session.execute(history_query)
                client_orders = result.scalars().all()

                if client_orders:
                    # Формируем сообщение об истории клиента
                    history_message = f"ℹ️ <b>История клиента</b>\n\n"
                    history_message += f"📞 Телефон: {client_phone}\n"
                    history_message += f"📍 Адрес: {client_address}\n\n"

                    # Статистика
                    completed_orders = [o for o in client_orders if o.status == "CLOSED"]
                    refused_orders = [o for o in client_orders if o.status == "REFUSED"]

                    total_revenue = sum(o.total_amount or 0 for o in completed_orders)

                    history_message += f"📊 <b>Статистика:</b>\n"
                    history_message += f"• Всего заказов: {len(client_orders)}\n"
                    history_message += f"• Выполнено: {len(completed_orders)}\n"
                    history_message += f"• Отменено/Отказ: {len(refused_orders)}\n"
                    history_message += f"• Общая сумма: {total_revenue:.2f} руб.\n\n"

                    # Список заказов (последние 5)
                    history_message += f"📋 <b>Последние заказы:</b>\n"
                    for order in client_orders[:5]:
                        status_emoji = {
                            "CLOSED": "✅",
                            "REFUSED": "❌",
                            "NEW": "🆕",
                            "ASSIGNED": "👷",
                            "ACCEPTED": "✔️",
                            "ONSITE": "🚗"
                        }.get(order.status, "❓")

                        history_message += f"\n{status_emoji} Заказ #{order.id}\n"
                        history_message += f"  🔧 {order.equipment_type}\n"
                        history_message += f"  📅 {order.created_at.strftime('%d.%m.%Y')}\n"

                        if order.status == "CLOSED":
                            total_sum = (order.total_amount or 0)
                            history_message += f"  💰 Сумма: {total_sum:.2f} руб.\n"
                        elif order.status == "REFUSED" and order.refuse_reason:
                            history_message += f"  ❗ Причина: {order.refuse_reason}\n"

                    if len(client_orders) > 5:
                        history_message += f"\n... и ещё {len(client_orders) - 5} заказ(ов)"

                    # Отправляем историю в группу
                    if self.group_id:
                        await self.bot.send_message(
                            chat_id=self.group_id,
                            text=history_message,
                            parse_mode="HTML"
                        )

        except Exception as e:
            self.logger.exception(f"Ошибка при проверке дубликатов/истории: {e}")
            # Продолжаем работу даже при ошибке проверки

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
                from app.database.orm_models import Order
                from app.utils.helpers import get_now

                # Проверка на дубликаты уже выполнена в _on_new_message,
                # поэтому здесь просто создаём заявку
                new_order = Order(
                    equipment_type=order.equipment_type,
                    description=order.problem_description,  # Исправлено: description вместо problem_description
                    client_name=order.client_name,
                    client_address=order.address,
                    client_phone=order.phone or "Не указан",  # Телефон обязателен в БД
                    scheduled_time=order.scheduled_time,  # Время прибытия/ремонта
                    status="NEW",  # Допустимые статусы: NEW, ASSIGNED, ACCEPTED, ONSITE, CLOSED, REFUSED, DR
                    created_at=get_now(),
                    updated_at=get_now(),  # Явно указываем updated_at, чтобы избежать IntegrityError
                )

                session.add(new_order)
                await session.commit()
                await session.refresh(new_order)

                # Обновляем аналитику
                await self.analytics_service.mark_confirmed(
                    message_id=order.message_id,
                    confirmed=True,
                    created_order_id=new_order.id,
                )
                

                self.logger.info(f"Заявка #{new_order.id} создана из распарсенного сообщения {order.message_id}")

                # Уведомления
                from app.utils.helpers import escape_html, safe_send_message
                
                # 1. Уведомление в группу (если настроено)
                if Config.DISPATCHER_GROUP_ID:
                    group_message_text = f"✅ <b>Заявка #{new_order.id} создана из парсера!</b>\n\n"
                    group_message_text += f"🔧 {order.equipment_type}\n"
                    group_message_text += f"📍 {order.address}\n"
                    group_message_text += f"📞 {order.phone or 'не указан'}"

                    # Добавляем информацию о времени, если оно указано
                    if order.scheduled_time:
                        group_message_text += f"\n⏰ Время: {order.scheduled_time}"

                    await self.bot.send_message(
                        chat_id=Config.DISPATCHER_GROUP_ID,
                        text=group_message_text,
                        parse_mode="HTML",
                    )
                
                # 2. Уведомления в личку всем админам и диспетчерам (как при ручном создании)
                admins_and_dispatchers = await self.db.get_admins_and_dispatchers()
                
                notification_text = (
                    f"🆕 <b>Новая заявка #{new_order.id} из парсера</b>\n\n"
                    f"🔧 Тип: {escape_html(order.equipment_type)}\n"
                    f"📝 {escape_html(order.problem_description)}\n\n"
                    f"👤 Клиент: {escape_html(order.client_name)}\n"
                    f"📍 {escape_html(order.address)}\n"
                    f"📞 {order.phone or 'не указан'}\n"
                )
                
                if order.scheduled_time:
                    notification_text += f"\n⏰ Прибытие: {escape_html(order.scheduled_time)}"
                
                notification_text += "\n\n⚠️ <b>Требует назначения мастера!</b>"
                
                # Отправляем уведомления каждому диспетчеру в личку
                for user in admins_and_dispatchers:
                    try:
                        await safe_send_message(
                            self.bot, user.telegram_id, notification_text, parse_mode="HTML"
                        )
                        self.logger.info(f"Уведомление отправлено {user.telegram_id} о заявке #{new_order.id} из парсера")
                    except Exception as e:
                        self.logger.error(f"Не удалось уведомить пользователя {user.telegram_id}: {e}")

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
