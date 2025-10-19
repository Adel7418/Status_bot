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
        # Мастера видят кнопки в своей группе
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
        builder.row(
            InlineKeyboardButton(
                text="📅 Перенести визит",
                callback_data=create_callback_data("group_reschedule_order", order.id),
            )
        )
    elif status == OrderStatus.ACCEPTED:
        builder.row(
            InlineKeyboardButton(
                text="📅 Перенести визит",
                callback_data=create_callback_data("group_reschedule_order", order.id),
            )
        )
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

            # Кнопка "Клиент ждет" для активных заявок с назначенным мастером
            if order.status in [OrderStatus.ASSIGNED, OrderStatus.ACCEPTED, OrderStatus.ONSITE]:
                builder.row(
                    InlineKeyboardButton(
                        text="📞 Клиент ждет",
                        callback_data=create_callback_data("client_waiting", order.id),
                    )
                )

        # Добавляем кнопки действий мастера для админа (только если мастер назначен)
        if user_role == UserRole.ADMIN and order.assigned_master_id:
            if order.status == OrderStatus.ASSIGNED:
                builder.row(
                    InlineKeyboardButton(
                        text="✅ Принять (за мастера)",
                        callback_data=create_callback_data("admin_accept_order", order.id),
                    )
                )
                builder.row(
                    InlineKeyboardButton(
                        text="📅 Перенести визит",
                        callback_data=create_callback_data("reschedule_order", order.id),
                    )
                )
            elif order.status == OrderStatus.ACCEPTED:
                builder.row(
                    InlineKeyboardButton(
                        text="📅 Перенести визит",
                        callback_data=create_callback_data("reschedule_order", order.id),
                    )
                )
                builder.row(
                    InlineKeyboardButton(
                        text="🏠 На объекте (за мастера)",
                        callback_data=create_callback_data("admin_onsite_order", order.id),
                    )
                )
            elif order.status == OrderStatus.ONSITE:
                builder.row(
                    InlineKeyboardButton(
                        text="💰 Завершить (за мастера)",
                        callback_data=create_callback_data("admin_complete_order", order.id),
                    ),
                    InlineKeyboardButton(
                        text="⏳ DR (за мастера)",
                        callback_data=create_callback_data("admin_dr_order", order.id),
                    ),
                )
            elif order.status == OrderStatus.DR:
                builder.row(
                    InlineKeyboardButton(
                        text="💰 Завершить ремонт (за мастера)",
                        callback_data=create_callback_data("admin_complete_order", order.id),
                    )
                )

        if order.status not in [OrderStatus.CLOSED, OrderStatus.REFUSED]:
            # TODO: Реализовать функционал редактирования заявок
            # builder.row(
            #     InlineKeyboardButton(
            #         text="✏️ Редактировать",
            #         callback_data=create_callback_data("edit_order", order.id),
            #     )
            # )

            # Кнопку "Закрыть заявку" убрали - теперь админ завершает через "Завершить (за мастера)"
            # которая запускает правильный процесс с запросом суммы и материалов

            builder.row(
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
            builder.row(
                InlineKeyboardButton(
                    text="📅 Перенести визит",
                    callback_data=create_callback_data("reschedule_order", order.id),
                )
            )
        elif order.status == OrderStatus.ACCEPTED:
            builder.row(
                InlineKeyboardButton(
                    text="📅 Перенести визит",
                    callback_data=create_callback_data("reschedule_order", order.id),
                )
            )
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
        elif order.status == OrderStatus.DR:
            # Для заявок в длительном ремонте - можно завершить
            builder.row(
                InlineKeyboardButton(
                    text="💰 Завершить ремонт",
                    callback_data=create_callback_data("complete_order", order.id),
                )
            )

    # Кнопка экспорта в Excel (для всех ролей)
    builder.row(
        InlineKeyboardButton(
            text="📊 Экспорт в Excel",
            callback_data=create_callback_data("export_order", order.id),
        )
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

        # Добавляем предупреждение если нет рабочей группы
        warning = " ⚠️ НЕТ ГРУППЫ" if not master.work_chat_id else ""

        if order_id:
            callback_data = create_callback_data(action, order_id, master.id)
        else:
            callback_data = create_callback_data(action, master.telegram_id)

        builder.row(
            InlineKeyboardButton(
                text=f"{display_name}{specialization}{warning}", callback_data=callback_data
            )
        )

    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))

    return builder.as_markup()


def get_orders_filter_keyboard(counts: dict | None = None) -> InlineKeyboardMarkup:
    """
    Клавиатура фильтрации заявок с счетчиками

    Args:
        counts: Словарь с количеством заявок по статусам {status: count}

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    # Если счетчики не переданы, используем пустой словарь
    if counts is None:
        counts = {}

    # Формируем текст кнопок с счетчиками
    new_text = (
        f"🆕 Новые ({counts.get(OrderStatus.NEW, 0)})"
        if counts.get(OrderStatus.NEW, 0) > 0
        else "🆕 Новые"
    )
    assigned_text = (
        f"👨‍🔧 Назначенные ({counts.get(OrderStatus.ASSIGNED, 0)})"
        if counts.get(OrderStatus.ASSIGNED, 0) > 0
        else "👨‍🔧 Назначенные"
    )
    accepted_text = (
        f"✅ Принятые ({counts.get(OrderStatus.ACCEPTED, 0)})"
        if counts.get(OrderStatus.ACCEPTED, 0) > 0
        else "✅ Принятые"
    )
    onsite_text = (
        f"🏠 На объекте ({counts.get(OrderStatus.ONSITE, 0)})"
        if counts.get(OrderStatus.ONSITE, 0) > 0
        else "🏠 На объекте"
    )
    # Длительные ремонты - всегда показываем счётчик для видимости
    dr_text = f"⏳ Длительные ремонты ({counts.get(OrderStatus.DR, 0)})"

    builder.row(
        InlineKeyboardButton(
            text=new_text, callback_data=create_callback_data("filter_orders", OrderStatus.NEW)
        ),
        InlineKeyboardButton(
            text=assigned_text,
            callback_data=create_callback_data("filter_orders", OrderStatus.ASSIGNED),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=accepted_text,
            callback_data=create_callback_data("filter_orders", OrderStatus.ACCEPTED),
        ),
        InlineKeyboardButton(
            text=onsite_text,
            callback_data=create_callback_data("filter_orders", OrderStatus.ONSITE),
        ),
    )
    # Длительные ремонты - отдельная широкая строка для лучшей видимости
    builder.row(
        InlineKeyboardButton(
            text=dr_text,
            callback_data=create_callback_data("filter_orders", OrderStatus.DR),
        ),
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


def get_yes_no_keyboard(callback_prefix: str, order_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопками Да/Нет для подтверждения действий

    Args:
        callback_prefix: Префикс для callback_data (например "confirm_review", "confirm_out_of_city")
        order_id: ID заказа

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да", callback_data=create_callback_data(callback_prefix, order_id, "yes")
        ),
        InlineKeyboardButton(
            text="❌ Нет", callback_data=create_callback_data(callback_prefix, order_id, "no")
        ),
    )

    return builder.as_markup()


def get_dev_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для меню разработчика

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🧪 Создать тестовую заявку", callback_data="dev_create_test_order"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🗄️ Архивировать старые заявки", callback_data="dev_archive_orders"
        )
    )

    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="dev_close"))

    return builder.as_markup()
