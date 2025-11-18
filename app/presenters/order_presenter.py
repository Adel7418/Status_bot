"""
OrderPresenter - форматирование заказов для отображения
"""


from app.config import OrderStatus
from app.utils import escape_html as escape_html_util


class OrderPresenter:
    """Presenter для форматирования заказов"""

    @staticmethod
    def format_order_details(
        order,
        include_client_phone: bool = True,
        master=None,
        escape_html: bool = False,
        phone_visibility_mode: str = "default",
    ) -> str:
        """
        Форматирование детальной информации о заказе

        Args:
            order: Объект заказа
            include_client_phone: Включать ли телефон клиента (используется если phone_visibility_mode='default')
            master: Объект мастера (опционально, для отображения имени вместо ID)
            escape_html: Экранировать HTML-спецсимволы для безопасности
            phone_visibility_mode: Режим показа телефона:
                - 'default': используется include_client_phone (показать или скрыть с сообщением "после прибытия")
                - 'conditional': зависит от статуса заказа (для мастеров)
                - 'always': всегда показывать телефон
                - 'never': никогда не показывать телефон

        Returns:
            Отформатированный текст с деталями заказа
        """
        status_emoji = OrderStatus.get_status_emoji(order.status)
        status_name = OrderStatus.get_status_name(order.status)

        # Применяем escape_html к полям, если необходимо
        def safe(value):
            return escape_html_util(value) if escape_html and value else value

        text = f"📋 <b>Заявка #{order.id}</b>\n\n"
        text += f"📊 <b>Статус:</b> {status_emoji} {status_name}\n"

        # Мастер (если передан)
        if master:
            text += f"👨‍🔧 <b>Мастер:</b> {master.get_display_name()}\n"
        elif order.assigned_master_id:
            text += f"👨‍🔧 <b>Мастер:</b> ID {order.assigned_master_id}\n"

        text += (
            f"🔧 <b>Тип техники:</b> {safe(order.equipment_type)}\n"
            f"📝 <b>Описание:</b> {safe(order.description)}\n\n"
            f"👤 <b>Клиент:</b> {safe(order.client_name)}\n"
            f"📍 <b>Адрес:</b> {safe(order.client_address)}\n"
        )

        # Логика отображения телефона
        if phone_visibility_mode == "always":
            text += f"📞 <b>Телефон:</b> {safe(order.client_phone)}\n\n"
        elif phone_visibility_mode == "never":
            pass  # Телефон не показываем вообще
        elif phone_visibility_mode == "conditional":
            # Режим для мастеров: показываем телефон в зависимости от статуса
            if order.status in [OrderStatus.ONSITE, OrderStatus.DR, OrderStatus.CLOSED]:
                text += f"📞 <b>Телефон:</b> {safe(order.client_phone)}\n\n"
            elif order.status == OrderStatus.ACCEPTED:
                text += "📞 <b>Телефон:</b> <i>Будет доступен после прибытия на объект</i>\n\n"
            else:
                text += "<i>Контактная информация клиента будет доступна\nпосле принятия заявки.</i>\n\n"
        elif include_client_phone:
            text += f"📞 <b>Телефон:</b> {safe(order.client_phone)}\n\n"
        else:
            text += "📞 <b>Телефон:</b> <i>Будет доступен после прибытия на объект</i>\n\n"

        # Заметки
        if order.notes:
            text += f"📝 <b>Заметки:</b> {safe(order.notes)}\n\n"

        # Время прибытия/визита
        if order.scheduled_time:
            text += f"⏰ <b>Время прибытия:</b> {safe(order.scheduled_time)}\n\n"

        # Финансы (если заказ завершен)
        if order.status == OrderStatus.CLOSED and order.total_amount is not None:
            text += "\n💰 <b>Финансы:</b>\n"
            text += f"├ Общая сумма: {order.total_amount:.2f} ₽\n"
            if order.materials_cost is not None:
                text += f"├ Расходники: {order.materials_cost:.2f} ₽\n"
            if order.master_profit is not None:
                text += f"├ Мастеру: {order.master_profit:.2f} ₽\n"
            if order.company_profit is not None:
                text += f"└ Компании: {order.company_profit:.2f} ₽\n"

        # ДР информация
        if order.status == OrderStatus.DR:
            if order.estimated_completion_date:
                text += f"\n⏰ <b>Примерный срок окончания:</b> {safe(order.estimated_completion_date)}\n"
            if order.prepayment_amount:
                text += f"💰 <b>Предоплата:</b> {order.prepayment_amount:.2f} ₽\n"

        # Даты
        text += f"\n📅 <b>Создана:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"

        return text

    @staticmethod
    def format_order_short(order) -> str:
        """
        Краткое форматирование заказа для списков

        Args:
            order: Объект заказа

        Returns:
            Краткий текст заказа
        """
        status_emoji = OrderStatus.get_status_emoji(order.status)
        scheduled = f" ({order.scheduled_time})" if order.scheduled_time else ""

        return f"{status_emoji} #{order.id} - {order.equipment_type}{scheduled}"

    @staticmethod
    def format_order_list(orders: list, title: str = "Заявки") -> str:
        """
        Форматирование списка заказов

        Args:
            orders: Список заказов
            title: Заголовок списка

        Returns:
            Отформатированный список заказов
        """
        if not orders:
            return f"📭 {title}: нет заявок"

        text = f"📋 <b>{title}:</b> ({len(orders)})\n\n"

        for order in orders:
            text += f"• {OrderPresenter.format_order_short(order)}\n"

        return text

    @staticmethod
    def format_financial_summary(
        total_amount: float,
        materials_cost: float,
        master_profit: float,
        company_profit: float,
        has_review: bool = False,
        out_of_city: bool = False,
    ) -> str:
        """
        Форматирование финансовой сводки

        Args:
            total_amount: Общая сумма
            materials_cost: Стоимость материалов
            master_profit: Прибыль мастера
            company_profit: Прибыль компании
            has_review: Есть ли отзыв
            out_of_city: Выезд за город

        Returns:
            Отформатированная финансовая сводка
        """
        net_profit = total_amount - materials_cost
        review_text = "⭐ Да" if has_review else "❌ Нет"
        out_of_city_text = "🚗 Да" if out_of_city else "❌ Нет"

        return (
            f"💰 <b>Финансы:</b>\n"
            f"├ Общая сумма: {total_amount:.2f} ₽\n"
            f"├ Расходники: {materials_cost:.2f} ₽\n"
            f"├ Чистая прибыль: {net_profit:.2f} ₽\n"
            f"├ К выплате мастеру: <b>{master_profit:.2f} ₽</b>\n"
            f"└ Прибыль компании: <b>{company_profit:.2f} ₽</b>\n\n"
            f"📊 <b>Дополнительно:</b>\n"
            f"├ Отзыв: {review_text}\n"
            f"└ Выезд за город: {out_of_city_text}"
        )

    @staticmethod
    def format_order_notification(order, action: str, additional_info: str | None = None) -> str:
        """
        Форматирование уведомления о заказе

        Args:
            order: Объект заказа
            action: Действие (создана, назначена, завершена и т.д.)
            additional_info: Дополнительная информация

        Returns:
            Отформатированное уведомление
        """
        text = (
            f"📋 <b>Заявка {action}</b>\n\n"
            f"📋 Заявка #{order.id}\n"
            f"🔧 {order.equipment_type}\n"
            f"📝 {order.description}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n"
        )

        if order.scheduled_time:
            text += f"⏰ Время: {order.scheduled_time}\n"

        if additional_info:
            text += f"\n{additional_info}"

        return text
