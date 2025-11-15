"""
Сервис поиска заказов
"""

import logging
import re

from app.database import Database
from app.database.models import Order
from app.utils import format_datetime, format_phone


logger = logging.getLogger(__name__)


class OrderSearchService:
    """Сервис для поиска заказов по различным критериям"""

    def __init__(self, db: Database):
        """
        Инициализация

        Args:
            db: Экземпляр базы данных
        """
        self.db = db

    async def search_orders_by_phone(self, phone: str) -> list[Order]:
        """
        Поиск заказов по номеру телефона

        Args:
            phone: Номер телефона для поиска

        Returns:
            Список найденных заказов
        """
        # Нормализуем номер телефона
        normalized_phone = self._normalize_phone(phone)

        if not normalized_phone:
            return []

        logger.info(f"Поиск заказов по телефону: {normalized_phone}")

        # Используем существующий метод из базы данных
        orders = await self.db.get_orders_by_client_phone(normalized_phone)

        logger.info(f"Найдено заказов по телефону: {len(orders)}")
        return orders

    async def search_orders_by_address(self, address: str) -> list[Order]:
        """
        Поиск заказов по адресу

        Args:
            address: Адрес для поиска

        Returns:
            Список найденных заказов
        """
        if not address or len(address.strip()) < 3:
            return []

        # Нормализуем адрес для поиска
        normalized_address = self._normalize_address(address)

        logger.info(f"Поиск заказов по адресу: {normalized_address}")

        # Выполняем поиск в базе данных
        orders = await self._search_orders_by_address_in_db(normalized_address)

        # Если не нашли по полному адресу, пробуем поиск по отдельным словам
        if not orders and len(normalized_address.split()) > 1:
            words = normalized_address.split()
            for word in words:
                if len(word) >= 3:  # Ищем только слова длиннее 3 символов
                    word_orders = await self._search_orders_by_address_in_db(word)
                    orders.extend(word_orders)

            # Убираем дубликаты
            orders = self._remove_duplicate_orders(orders)

        logger.info(f"Найдено заказов по адресу: {len(orders)}")
        return orders

    async def search_orders_by_phone_and_address(self, phone: str, address: str) -> list[Order]:
        """
        Поиск заказов по телефону и адресу одновременно

        Args:
            phone: Номер телефона
            address: Адрес

        Returns:
            Список найденных заказов
        """
        phone_orders = []
        address_orders = []

        # Поиск по телефону
        if phone:
            phone_orders = await self.search_orders_by_phone(phone)

        # Поиск по адресу
        if address:
            address_orders = await self.search_orders_by_address(address)

        # Объединяем результаты и убираем дубликаты
        all_orders = phone_orders + address_orders
        unique_orders = self._remove_duplicate_orders(all_orders)

        logger.info(f"Найдено заказов по телефону и адресу: {len(unique_orders)}")
        return unique_orders

    def format_search_results(self, orders: list[Order], search_type: str = "поиск") -> str:
        """
        Форматирование результатов поиска для отображения

        Args:
            orders: Список заказов
            search_type: Тип поиска для заголовка

        Returns:
            Отформатированный текст с результатами
        """
        if not orders:
            return f"🔍 <b>Результаты {search_type}</b>\n\n❌ Заказы не найдены."

        text = f"🔍 <b>Результаты {search_type}</b>\n\n"
        text += f"📊 Найдено заказов: <b>{len(orders)}</b>\n\n"

        for i, order in enumerate(orders, 1):
            # Статус с эмодзи
            from app.config import OrderStatus

            status_emoji = OrderStatus.get_status_emoji(order.status)
            status_name = OrderStatus.get_status_name(order.status)

            text += f"<b>{i}. Заявка #{order.id}</b>\n"
            text += f"📱 <b>Телефон:</b> {format_phone(order.client_phone)}\n"
            text += f"🏠 <b>Адрес:</b> {order.client_address}\n"
            text += f"👤 <b>Клиент:</b> {order.client_name}\n"
            text += f"🔧 <b>Техника:</b> {order.equipment_type}\n"
            text += f"📝 <b>Описание:</b> {order.description[:100]}{'...' if len(order.description) > 100 else ''}\n"
            text += f"{status_emoji} <b>Статус:</b> {status_name}\n"

            if order.master_name:
                text += f"👨‍🔧 <b>Мастер:</b> {order.master_name}\n"

            if order.created_at:
                text += f"📅 <b>Создана:</b> {format_datetime(order.created_at)}\n"

            text += "\n" + "─" * 30 + "\n\n"

        return text

    def _normalize_phone(self, phone: str) -> str | None:
        """
        Нормализация номера телефона для поиска

        Args:
            phone: Исходный номер телефона

        Returns:
            Нормализованный номер или None
        """
        if not phone:
            return None

        # Убираем все символы кроме цифр
        digits_only = re.sub(r"\D", "", phone)

        # Если номер начинается с 8, заменяем на 7
        if digits_only.startswith("8") and len(digits_only) == 11:
            digits_only = "7" + digits_only[1:]

        # Если номер начинается с 7 и имеет 11 цифр, возвращаем как есть
        if digits_only.startswith("7") and len(digits_only) == 11:
            return digits_only

        # Если номер имеет 10 цифр, добавляем 7
        if len(digits_only) == 10:
            return "7" + digits_only

        return None

    def _normalize_address(self, address: str) -> str:
        """
        Нормализация адреса для поиска

        Args:
            address: Исходный адрес

        Returns:
            Нормализованный адрес
        """
        if not address:
            return ""

        # Приводим к нижнему регистру и убираем лишние пробелы
        normalized = address.lower().strip()

        # Убираем множественные пробелы
        normalized = re.sub(r"\s+", " ", normalized)

        # Убираем знаки препинания в конце
        normalized = re.sub(r"[.,;:!?]+$", "", normalized)

        # Убираем сокращения и заменяем их на полные формы
        replacements = {
            "ул.": "улица",
            "ул ": "улица ",
            "д.": "дом",
            "д ": "дом ",
            "кв.": "квартира",
            "кв ": "квартира ",
            "пр.": "проспект",
            "пр ": "проспект ",
            "пер.": "переулок",
            "пер ": "переулок ",
            "наб.": "набережная",
            "наб ": "набережная ",
        }

        for short, full in replacements.items():
            normalized = normalized.replace(short, full)
        
        return normalized

    async def _search_orders_by_address_in_db(self, address: str) -> list[Order]:
        """
        Поиск заказов по адресу в базе данных

        Args:
            address: Нормализованный адрес

        Returns:
            Список найденных заказов
        """
        # Проверяем, какой тип базы данных используется
        if hasattr(self.db, "session_factory"):
            # ORMDatabase
            return await self._search_orders_by_address_orm(address)
        # Legacy Database
        return await self._search_orders_by_address_legacy(address)

    async def _search_orders_by_address_orm(self, address: str) -> list[Order]:
        """
        Поиск заказов по адресу через ORM

        Args:
            address: Нормализованный адрес

        Returns:
            Список найденных заказов
        """
        from sqlalchemy import func, select
        from sqlalchemy.orm import joinedload

        from app.database.orm_models import Master, User
        from app.database.orm_models import Order as ORMOrder

        async with self.db.session_factory() as session:
            # Получаем все заказы и фильтруем в Python (из-за проблем с func.lower() и кириллицей)
            query = (
                select(ORMOrder)
                .options(
                    joinedload(ORMOrder.assigned_master).joinedload(Master.user),
                    joinedload(ORMOrder.dispatcher)
                )
                .order_by(ORMOrder.created_at.desc())
            )

            result = await session.execute(query)
            all_orders = result.unique().scalars().all()
            
            # Фильтруем в Python
            orm_orders = []
            for order in all_orders:
                if address in order.client_address.lower():
                    orm_orders.append(order)

            # Конвертируем ORM модели в dataclass модели
            orders = []
            for orm_order in orm_orders:
                order = Order(
                    id=orm_order.id,
                    equipment_type=orm_order.equipment_type,
                    description=orm_order.description,
                    client_name=orm_order.client_name,
                    client_address=orm_order.client_address,
                    client_phone=orm_order.client_phone,
                    status=orm_order.status,
                    assigned_master_id=orm_order.assigned_master_id,
                    dispatcher_id=orm_order.dispatcher_id,
                    notes=orm_order.notes,
                    scheduled_time=orm_order.scheduled_time,
                    total_amount=orm_order.total_amount,
                    materials_cost=orm_order.materials_cost,
                    master_profit=orm_order.master_profit,
                    company_profit=orm_order.company_profit,
                    has_review=orm_order.has_review,
                    out_of_city=orm_order.out_of_city,
                    created_at=orm_order.created_at,
                    updated_at=orm_order.updated_at,
                    rescheduled_count=orm_order.rescheduled_count,
                    last_rescheduled_at=orm_order.last_rescheduled_at,
                    reschedule_reason=orm_order.reschedule_reason,
                    estimated_completion_date=orm_order.estimated_completion_date,
                    prepayment_amount=orm_order.prepayment_amount,
                )

                # Получаем информацию о мастере и диспетчере
                if orm_order.assigned_master:
                    master = orm_order.assigned_master
                    if master.user:
                        if master.user.first_name and master.user.last_name:
                            order.master_name = f"{master.user.first_name} {master.user.last_name}"
                        elif master.user.first_name:
                            order.master_name = master.user.first_name
                        elif master.user.username:
                            order.master_name = f"@{master.user.username}"

                if orm_order.dispatcher:
                    dispatcher = orm_order.dispatcher
                    if dispatcher.first_name and dispatcher.last_name:
                        order.dispatcher_name = f"{dispatcher.first_name} {dispatcher.last_name}"
                    elif dispatcher.first_name:
                        order.dispatcher_name = dispatcher.first_name
                    elif dispatcher.username:
                        order.dispatcher_name = f"@{dispatcher.username}"

                orders.append(order)

            return orders

    async def _search_orders_by_address_legacy(self, address: str) -> list[Order]:
        """
        Поиск заказов по адресу через legacy Database

        Args:
            address: Нормализованный адрес

        Returns:
            Список найденных заказов
        """
        if not self.db.connection:
            await self.db.connect()

        # Используем LIKE для поиска по частичному совпадению
        cursor = await self.db.connection.execute(
            """
            SELECT o.*,
                   m.first_name as master_first_name, m.last_name as master_last_name, m.username as master_username,
                   u.first_name as dispatcher_first_name, u.last_name as dispatcher_last_name, u.username as dispatcher_username
            FROM orders o
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u ON o.dispatcher_id = u.telegram_id
            WHERE LOWER(o.client_address) LIKE ? AND o.deleted_at IS NULL
            ORDER BY o.created_at DESC
            """,
            (f"%{address}%",),
        )
        rows = await cursor.fetchall()

        orders = []
        for row in rows:
            order = Order(
                id=row["id"],
                equipment_type=row["equipment_type"],
                description=row["description"],
                client_name=row["client_name"],
                client_address=row["client_address"],
                client_phone=row["client_phone"],
                status=row["status"],
                assigned_master_id=row["assigned_master_id"],
                dispatcher_id=row["dispatcher_id"],
                notes=row["notes"],
                scheduled_time=row["scheduled_time"],
                total_amount=row["total_amount"],
                materials_cost=row["materials_cost"],
                master_profit=row["master_profit"],
                company_profit=row["company_profit"],
                has_review=bool(row["has_review"]) if row["has_review"] is not None else None,
                out_of_city=bool(row["out_of_city"]) if row["out_of_city"] is not None else None,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                rescheduled_count=row["rescheduled_count"],
                last_rescheduled_at=row["last_rescheduled_at"],
                reschedule_reason=row["reschedule_reason"],
                estimated_completion_date=row["estimated_completion_date"],
                prepayment_amount=row["prepayment_amount"],
            )

            # Формируем имя мастера
            if row["master_first_name"] and row["master_last_name"]:
                order.master_name = f"{row['master_first_name']} {row['master_last_name']}"
            elif row["master_first_name"]:
                order.master_name = row["master_first_name"]
            elif row["master_username"]:
                order.master_name = f"@{row['master_username']}"

            # Формируем имя диспетчера
            if row["dispatcher_first_name"] and row["dispatcher_last_name"]:
                order.dispatcher_name = (
                    f"{row['dispatcher_first_name']} {row['dispatcher_last_name']}"
                )
            elif row["dispatcher_first_name"]:
                order.dispatcher_name = row["dispatcher_first_name"]
            elif row["dispatcher_username"]:
                order.dispatcher_name = f"@{row['dispatcher_username']}"

            orders.append(order)

        return orders

    def _remove_duplicate_orders(self, orders: list[Order]) -> list[Order]:
        """
        Удаление дубликатов заказов из списка

        Args:
            orders: Список заказов

        Returns:
            Список уникальных заказов
        """
        seen_ids = set()
        unique_orders = []

        for order in orders:
            if order.id not in seen_ids:
                seen_ids.add(order.id)
                unique_orders.append(order)

        return unique_orders
