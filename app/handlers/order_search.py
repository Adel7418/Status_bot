"""
Обработчики для поиска заказов
"""

import logging
import math

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import UserRole
from app.database import get_database
from app.decorators import handle_errors, require_role
from app.keyboards.inline import (
    get_order_details_keyboard,
    get_order_search_results_list_keyboard,
    get_search_cancel_keyboard,
)
from app.services.order_search import OrderSearchService
from app.states import SearchOrderStates
from app.utils import escape_html, format_datetime, format_phone

logger = logging.getLogger(__name__)

router = Router(name="order_search")

ORDERS_PER_PAGE = 5


@router.message(F.text == "🔍 Поиск заказов")
@handle_errors
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
async def btn_search_orders(message: Message, state: FSMContext, user_role: str):
    """
    Начало процесса поиска заказов (Smart Search)

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    await state.clear()
    await state.set_state(SearchOrderStates.enter_query)

    await message.answer(
        "🔍 <b>Поиск заказов</b>\n\n"
        "Введите запрос — система автоматически определит тип:\n\n"
        "🔢 <b>Номер заявки:</b> 123, 4567\n"
        "📞 <b>Телефон:</b> +79991234567, 89991234567\n"
        "🏠 <b>Адрес:</b> Ленина 15, Москва Тверская\n\n"
        "<i>Для адресов-цифр (дом 15) добавьте название улицы</i>",
        parse_mode="HTML",
        reply_markup=get_search_cancel_keyboard(),
    )


@router.callback_query(F.data == "search_new")
@handle_errors
async def callback_search_new(callback: CallbackQuery, state: FSMContext):
    """
    Новый поиск (возврат к вводу)

    Args:
        callback: Callback query
        state: FSM контекст
    """
    await callback.answer()
    await state.clear()
    await state.set_state(SearchOrderStates.enter_query)

    message = callback.message
    if isinstance(message, Message):
        await message.edit_text(
            "🔍 <b>Поиск заказов</b>\n\n"
            "Введите запрос — система автоматически определит тип:\n\n"
            "🔢 <b>Номер заявки:</b> 123, 4567\n"
            "📞 <b>Телефон:</b> +79991234567, 89991234567\n"
            "🏠 <b>Адрес:</b> Ленина 15, Москва Тверская\n\n"
            "<i>Для адресов-цифр (дом 15) добавьте название улицы</i>",
            parse_mode="HTML",
            reply_markup=get_search_cancel_keyboard(),
        )


@router.callback_query(F.data == "search_cancel")
@handle_errors
async def callback_search_cancel(callback: CallbackQuery, state: FSMContext):
    """
    Отмена поиска

    Args:
        callback: Callback query
        state: FSM контекст
    """
    await callback.answer()
    await state.clear()

    message = callback.message
    if isinstance(message, Message):
        await message.edit_text(
            "❌ Поиск отменен.",
        )


@router.message(SearchOrderStates.enter_query, F.text)
@handle_errors
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
async def process_search_query(message: Message, state: FSMContext, user_role: str):
    """
    Обработка поискового запроса

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    query = (message.text or "").strip()

    if query == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Поиск отменен.", reply_markup=None)
        return

    if len(query) < 1:
        await message.answer(
            "⚠️ Введите запрос для поиска.",
            reply_markup=get_search_cancel_keyboard(),
        )
        return

    # Отправляем сообщение "Ищу..."
    loading_msg = await message.answer("⏳ Ищу заказы...")

    # Выполняем поиск
    db = get_database()
    await db.connect()

    try:
        search_service = OrderSearchService(db)
        orders, search_type = await search_service.unified_search(query)

        # Удаляем сообщение "Ищу..."
        await loading_msg.delete()

        if not orders:
            # Генерируем умные подсказки в зависимости от типа запроса
            suggestions = []
            if query.isdigit():
                digit_count = len(query)
                if digit_count <= 6:
                    suggestions.append("💡 <i>Возможно, это номер дома? Попробуйте добавить название улицы</i>")
                else:
                    suggestions.append("💡 <i>Возможно, это номер телефона? Попробуйте добавить +7 или 8 в начале</i>")

            suggestion_text = "\n".join(suggestions) if suggestions else ""

            await message.answer(
                f"❌ <b>Заказы не найдены</b>\n\n"
                f"Тип поиска: {search_type}\n"
                f"Запрос: <b>{escape_html(query)}</b>\n\n"
                f"{suggestion_text}\n\n" if suggestion_text else "\n"
                f"Попробуйте ввести другие данные:\n"
                f"🏠 <b>Адрес</b> (например: Москва, ул. Ленина)\n"
                f"📞 <b>Номер телефона</b> (например: +79123456789)\n"
                f"🔢 <b>ID заказа</b> (например: 12345)",
                parse_mode="HTML",
                reply_markup=get_search_cancel_keyboard(),
            )
            return

        # Сохраняем результаты в FSM для пагинации
        orders_ids = [order.id for order in orders]
        await state.update_data(found_orders=orders_ids, query=query, search_type=search_type)

        # Показываем первую страницу
        total_pages = math.ceil(len(orders) / ORDERS_PER_PAGE)
        current_page = 1
        page_orders = orders[:ORDERS_PER_PAGE]

        # Формируем заголовок в зависимости от типа поиска и количества результатов
        if search_type == "поиск по ID заказа" and len(orders) == 1:
            # Для поиска по ID - краткое сообщение
            text = f"✅ Найден заказ <b>#{orders[0].id}</b>\n\nВыберите заказ для просмотра:"
        elif len(orders) == 1:
            # Один заказ найден - без указания количества
            text = f"✅ Найдено {search_type}: <b>{escape_html(query)}</b>\n\nВыберите заказ для просмотра:"
        else:
            # Несколько заказов - показываем количество
            text = (
                f"✅ Найдено {search_type}: <b>{escape_html(query)}</b>\n"
                f"Всего заказов: <b>{len(orders)}</b>\n\n"
                f"Выберите заказ для просмотра:"
            )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_order_search_results_list_keyboard(
                page_orders, current_page, total_pages
            ),
        )

    finally:
        if hasattr(db, "engine") and db.engine:
            await db.engine.dispose()


@router.callback_query(F.data.startswith("search_page_"))
@handle_errors
async def callback_search_pagination(callback: CallbackQuery, state: FSMContext):
    """
    Пагинация результатов поиска

    Args:
        callback: Callback query
        state: FSM контекст
    """
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    found_orders_ids = data.get("found_orders", [])
    query = data.get("query", "")
    search_type = data.get("search_type", "по запросу")

    if not found_orders_ids:
        await callback.answer("⚠️ Данные поиска устарели. Повторите поиск.", show_alert=True)
        return

    # Загружаем заказы для текущей страницы
    db = get_database()
    await db.connect()

    try:
        start_idx = (page - 1) * ORDERS_PER_PAGE
        end_idx = start_idx + ORDERS_PER_PAGE
        page_ids = found_orders_ids[start_idx:end_idx]

        page_orders = []
        for order_id in page_ids:
            order = await db.get_order_by_id(order_id)
            if order:
                page_orders.append(order)

        total_pages = math.ceil(len(found_orders_ids) / ORDERS_PER_PAGE)

        text = (
            f"✅ Найдено {search_type}: <b>{escape_html(query)}</b>\n"
            f"Всего заказов: <b>{len(found_orders_ids)}</b>\n\n"
            f"Выберите заказ для просмотра:"
        )

        message = callback.message
        if isinstance(message, Message):
            await message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_order_search_results_list_keyboard(
                    page_orders, page, total_pages
                ),
            )

    finally:
        if hasattr(db, "engine") and db.engine:
            await db.engine.dispose()

    await callback.answer()


@router.callback_query(F.data.startswith("search_view_order:"))
@handle_errors
async def callback_search_view_order(callback: CallbackQuery, state: FSMContext):
    """
    Просмотр детальной информации о заказе из поиска

    Args:
        callback: Callback query
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[-1])

    db = get_database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        # Формируем текст карточки
        from app.config import OrderStatus

        status_emoji = OrderStatus.get_status_emoji(order.status)
        status_name = OrderStatus.get_status_name(order.status)

        text = f"📄 <b>Заказ #{order.id}</b>\n\n"
        text += f"👤 <b>Клиент:</b> {order.client_name}\n"
        text += f"📱 <b>Телефон:</b> {format_phone(order.client_phone)}\n"
        text += f"🏠 <b>Адрес:</b> {order.client_address}\n"
        text += f"🔧 <b>Техника:</b> {order.equipment_type}\n"
        text += f"📝 <b>Проблема:</b> {order.description}\n\n"

        # Финансовая информация
        if order.total_amount:
            materials = order.materials_cost or 0
            net_total = order.total_amount - materials  # Чистая общая сумма (без материалов)

            # Если нет расходных материалов, показываем только чистую прибыль компании
            if materials == 0:
                if order.company_profit:
                    text += f"🟢 <b>Чистая прибыль:</b> {int(order.company_profit):,} ₽\n".replace(",", " ")
            else:
                # Есть расходные материалы - показываем чистую общую сумму и чистую прибыль компании
                text += f"💰 <b>Общая сумма:</b> {int(net_total):,} ₽\n".replace(",", " ")
                if order.company_profit:
                    text += f"🟢 <b>Чистая прибыль:</b> {int(order.company_profit):,} ₽\n".replace(",", " ")

        if order.master_name:
            text += f"👨‍🔧 <b>Мастер:</b> {order.master_name}\n"

        text += f"\n{status_emoji} <b>Статус:</b> {status_name}\n"

        if order.created_at:
            text += f"📅 <b>Создан:</b> {format_datetime(order.created_at)}\n"

        # Если заявка завершена, показываем дату завершения
        if order.status == "CLOSED":
            # Ищем дату последнего изменения статуса на CLOSED в истории
            if hasattr(order, 'status_history') and order.status_history:
                closed_history = [h for h in order.status_history if h.new_status == "CLOSED"]
                if closed_history:
                    completion_date = max(closed_history, key=lambda h: h.changed_at).changed_at
                    text += f"✅ <b>Завершён:</b> {format_datetime(completion_date)}\n"
            elif order.updated_at:
                # Fallback на updated_at, если нет истории
                text += f"✅ <b>Завершён:</b> {format_datetime(order.updated_at)}\n"

        message = callback.message
        if isinstance(message, Message):
            await message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_order_details_keyboard(order.id),
            )

    finally:
        if hasattr(db, "engine") and db.engine:
            await db.engine.dispose()

    await callback.answer()


@router.callback_query(F.data == "search_back_to_list")
@handle_errors
async def callback_search_back_to_list(callback: CallbackQuery, state: FSMContext):
    """
    Возврат к списку результатов

    Args:
        callback: Callback query
        state: FSM контекст
    """
    # Возвращаемся на 1 страницу
    page = 1
    data = await state.get_data()
    found_orders_ids = data.get("found_orders", [])
    query = data.get("query", "")
    search_type = data.get("search_type", "по запросу")

    if not found_orders_ids:
        await callback.answer("⚠️ Данные поиска устарели. Повторите поиск.", show_alert=True)
        return

    # Загружаем заказы для текущей страницы
    db = get_database()
    await db.connect()

    try:
        start_idx = (page - 1) * ORDERS_PER_PAGE
        end_idx = start_idx + ORDERS_PER_PAGE
        page_ids = found_orders_ids[start_idx:end_idx]

        page_orders = []
        for order_id in page_ids:
            order = await db.get_order_by_id(order_id)
            if order:
                page_orders.append(order)

        total_pages = math.ceil(len(found_orders_ids) / ORDERS_PER_PAGE)

        # Формируем заголовок в зависимости от типа поиска и количества результатов
        if search_type == "поиск по ID заказа" and len(found_orders_ids) == 1:
            text = f"✅ Найден заказ <b>#{found_orders_ids[0]}</b>\n\nВыберите заказ для просмотра:"
        elif len(found_orders_ids) == 1:
            text = f"✅ Найдено {search_type}: <b>{escape_html(query)}</b>\n\nВыберите заказ для просмотра:"
        else:
            text = (
                f"✅ Найдено {search_type}: <b>{escape_html(query)}</b>\n"
                f"Всего заказов: <b>{len(found_orders_ids)}</b>\n\n"
                f"Выберите заказ для просмотра:"
            )

        message = callback.message
        if isinstance(message, Message):
            await message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_order_search_results_list_keyboard(
                    page_orders, page, total_pages
                ),
            )

    finally:
        if hasattr(db, "engine") and db.engine:
            await db.engine.dispose()

    await callback.answer()
