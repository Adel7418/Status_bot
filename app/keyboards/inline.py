"""
Inline клавиатуры
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import EquipmentType, OrderStatus
from app.database.models import Master, Order
from app.utils import create_callback_data


def get_group_order_keyboard(order: Order, status: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для взаимодействия с заказом в группе

    Args:
        order: Заявка
        status: Текущий статус заявки

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    if status == OrderStatus.ASSIGNED:
        builder.row(
            InlineKeyboardButton(
                text="✅ Принять заявку",
                callback_data=create_callback_data("group_accept_order", order.id),
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=create_callback_data("group_refuse_order", order.id),
            ),
        )
    elif status == OrderStatus.ACCEPTED:
        builder.row(
            InlineKeyboardButton(
                text="🏠 Я на объекте",
                callback_data=create_callback_data("group_onsite_order", order.id),
            )
        )
    elif status == OrderStatus.ONSITE:
        builder.row(
            InlineKeyboardButton(
                text="💰 Завершить",
                callback_data=create_callback_data("group_complete_order", order.id),
            ),
            InlineKeyboardButton(
                text="⏳ Длительный ремонт",
                callback_data=create_callback_data("group_dr_order", order.id),
            ),
        )

    return builder.as_markup()


def get_equipment_types_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора типа техники

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    for equipment_type in EquipmentType.all_types():
        builder.row(
            InlineKeyboardButton(
                text=equipment_type, callback_data=create_callback_data("equipment", equipment_type)
            )
        )

    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))

    return builder.as_markup()


def get_order_actions_keyboard(order: Order, user_role: str) -> InlineKeyboardMarkup:
    """
    Клавиатура действий с заявкой

    Args:
        order: Заявка
        user_role: Роль пользователя

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    from app.config import UserRole

    # Действия для администраторов и диспетчеров
    if user_role in [UserRole.ADMIN, UserRole.DISPATCHER]:
        if order.status == OrderStatus.NEW:
            builder.row(
                InlineKeyboardButton(
                    text="👨‍🔧 Назначить мастера",
                    callback_data=create_callback_data("assign_master", order.id),
                )
            )

        # Кнопка переназначения мастера для заявок с уже назначенным мастером
        if order.assigned_master_id and order.status not in [
            OrderStatus.CLOSED,
            OrderStatus.REFUSED,
        ]:
            builder.row(
                InlineKeyboardButton(
                    text="🔄 Переназначить мастера",
                    callback_data=create_callback_data("reassign_master", order.id),
                ),
                InlineKeyboardButton(
                    text="🚫 Снять мастера",
                    callback_data=create_callback_data("unassign_master", order.id),
                ),
            )

        if order.status not in [OrderStatus.CLOSED, OrderStatus.REFUSED]:
            # TODO: Реализовать функционал редактирования заявок
            # builder.row(
            #     InlineKeyboardButton(
            #         text="✏️ Редактировать",
            #         callback_data=create_callback_data("edit_order", order.id),
            #     )
            # )
            builder.row(
                InlineKeyboardButton(
                    text="💰 Закрыть заявку",
                    callback_data=create_callback_data("close_order", order.id),
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=create_callback_data("refuse_order", order.id),
                ),
            )

    # Действия для мастеров
    elif user_role == UserRole.MASTER:
        if order.status == OrderStatus.ASSIGNED:
            builder.row(
                InlineKeyboardButton(
                    text="✅ Принять заявку",
                    callback_data=create_callback_data("accept_order", order.id),
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=create_callback_data("refuse_order_master", order.id),
                ),
            )
        elif order.status == OrderStatus.ACCEPTED:
            builder.row(
                InlineKeyboardButton(
                    text="🏠 Я на объекте",
                    callback_data=create_callback_data("onsite_order", order.id),
                )
            )
        elif order.status == OrderStatus.ONSITE:
            builder.row(
                InlineKeyboardButton(
                    text="💰 Завершить",
                    callback_data=create_callback_data("complete_order", order.id),
                ),
                InlineKeyboardButton(
                    text="⏳ Длительный ремонт",
                    callback_data=create_callback_data("dr_order", order.id),
                ),
            )

    # Кнопка "Назад" для всех
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_orders"))

    return builder.as_markup()


def get_masters_list_keyboard(
    masters: list[Master], order_id: int | None = None, action: str = "select_master"
) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком мастеров

    Args:
        masters: Список мастеров
        order_id: ID заявки (если назначение на заявку)
        action: Действие при выборе

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    for master in masters:
        display_name = master.get_display_name()
        specialization = f" ({master.specialization})"

        if order_id:
            callback_data = create_callback_data(action, order_id, master.id)
        else:
            callback_data = create_callback_data(action, master.telegram_id)

        builder.row(
            InlineKeyboardButton(
                text=f"{display_name}{specialization}", callback_data=callback_data
            )
        )

    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))

    return builder.as_markup()


def get_master_approval_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура одобрения мастера

    Args:
        telegram_id: Telegram ID мастера

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить", callback_data=create_callback_data("approve_master", telegram_id)
        ),
        InlineKeyboardButton(
            text="❌ Отклонить", callback_data=create_callback_data("reject_master", telegram_id)
        ),
    )

    return builder.as_markup()


def get_orders_filter_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура фильтрации заявок

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🆕 Новые", callback_data=create_callback_data("filter_orders", OrderStatus.NEW)
        ),
        InlineKeyboardButton(
            text="👨‍🔧 Назначенные",
            callback_data=create_callback_data("filter_orders", OrderStatus.ASSIGNED),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ Принятые",
            callback_data=create_callback_data("filter_orders", OrderStatus.ACCEPTED),
        ),
        InlineKeyboardButton(
            text="🏠 На объекте",
            callback_data=create_callback_data("filter_orders", OrderStatus.ONSITE),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 Завершенные",
            callback_data=create_callback_data("filter_orders", OrderStatus.CLOSED),
        ),
        InlineKeyboardButton(
            text="⏳ Длительный ремонт",
            callback_data=create_callback_data("filter_orders", OrderStatus.DR),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 Все заявки", callback_data=create_callback_data("filter_orders", "all")
        )
    )

    return builder.as_markup()


def get_order_list_keyboard(orders: list[Order], for_master: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком заявок

    Args:
        orders: Список заявок
        for_master: True если клавиатура для мастера (для раздела "Мои заявки")

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    # Используем разные callback_data для мастеров и диспетчеров
    callback_prefix = "view_order_master" if for_master else "view_order"

    for order in orders:
        status_emoji = OrderStatus.get_status_emoji(order.status)
        text = f"{status_emoji} Заявка #{order.id} - {order.equipment_type}"

        builder.row(
            InlineKeyboardButton(
                text=text, callback_data=create_callback_data(callback_prefix, order.id)
            )
        )

    if not orders:
        builder.row(InlineKeyboardButton(text="❌ Заявок нет", callback_data="no_orders"))

    return builder.as_markup()


def get_reports_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора типа отчета

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="👥 По мастерам", callback_data="report_masters"))
    builder.row(InlineKeyboardButton(text="📊 По статусам", callback_data="report_statuses"))
    builder.row(InlineKeyboardButton(text="🔧 По типам техники", callback_data="report_equipment"))
    builder.row(InlineKeyboardButton(text="📅 За период", callback_data="report_period"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))

    return builder.as_markup()


def get_period_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора периода

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📅 Сегодня", callback_data="period_today"),
        InlineKeyboardButton(text="📅 Вчера", callback_data="period_yesterday"),
    )
    builder.row(
        InlineKeyboardButton(text="📅 Неделя", callback_data="period_week"),
        InlineKeyboardButton(text="📅 Месяц", callback_data="period_month"),
    )
    builder.row(InlineKeyboardButton(text="📅 Год", callback_data="period_year"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))

    return builder.as_markup()


def get_master_management_keyboard(telegram_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура управления мастером

    Args:
        telegram_id: Telegram ID мастера
        is_active: Активен ли мастер

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    # Кнопка установки рабочей группы
    builder.row(
        InlineKeyboardButton(
            text="💬 Установить рабочую группу",
            callback_data=create_callback_data("set_work_chat", telegram_id),
        )
    )

    if is_active:
        builder.row(
            InlineKeyboardButton(
                text="🚫 Деактивировать",
                callback_data=create_callback_data("deactivate_master", telegram_id),
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Активировать",
                callback_data=create_callback_data("activate_master", telegram_id),
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика", callback_data=create_callback_data("master_stats", telegram_id)
        )
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_masters"))

    return builder.as_markup()


def get_pagination_keyboard(
    current_page: int, total_pages: int, callback_prefix: str
) -> InlineKeyboardMarkup:
    """
    Клавиатура пагинации

    Args:
        current_page: Текущая страница
        total_pages: Всего страниц
        callback_prefix: Префикс для callback_data

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    buttons = []

    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="◀️", callback_data=create_callback_data(callback_prefix, current_page - 1)
            )
        )

    buttons.append(
        InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="current_page")
    )

    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="▶️", callback_data=create_callback_data(callback_prefix, current_page + 1)
            )
        )

    builder.row(*buttons)

    return builder.as_markup()
