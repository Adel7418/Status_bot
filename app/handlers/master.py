"""
Обработчики для мастеров
"""

import logging
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import OrderStatus, UserRole
from app.database import Database
from app.keyboards.inline import get_order_actions_keyboard, get_order_list_keyboard
from app.states import CompleteOrderStates, LongRepairStates, RescheduleOrderStates
from app.utils import format_datetime, get_now, log_action


logger = logging.getLogger(__name__)

router = Router(name="master")
# Фильтры на уровне роутера НЕ работают, т.к. выполняются ДО middleware
# Проверка роли теперь в каждом обработчике через декоратор


@router.message(F.text == "📋 Мои заявки")
async def btn_my_orders(message: Message, state: FSMContext):
    """
    Просмотр заявок мастера

    Args:
        message: Сообщение
        state: FSM контекст
    """
    # Проверяем, что это не личное сообщение
    if message.chat.type == "private":
        await message.answer(
            "⚠️ <b>Работа только в рабочей группе!</b>\n\n"
            "Для мастеров взаимодействие с ботом доступно только в рабочей группе.",
            parse_mode="HTML",
        )
        return

    await state.clear()

    db = Database()
    await db.connect()

    try:
        # Получаем мастера
        master = await db.get_master_by_telegram_id(message.from_user.id)

        if not master:
            await message.answer("❌ Вы не зарегистрированы как мастер в системе.")
            return

        # Получаем заявки мастера
        orders = await db.get_orders_by_master(master.id, exclude_closed=True)

        if not orders:
            await message.answer(
                "📭 У вас пока нет активных заявок.\n\n" "Заявки будут назначаться диспетчером."
            )
            return

        text = "📋 <b>Ваши заявки:</b>\n\n"

        # Группируем по статусам
        by_status = {}
        for order in orders:
            if order.status not in by_status:
                by_status[order.status] = []
            by_status[order.status].append(order)

        # Порядок отображения статусов
        status_order = [
            OrderStatus.ASSIGNED,
            OrderStatus.ACCEPTED,
            OrderStatus.ONSITE,
            OrderStatus.DR,
        ]

        for status in status_order:
            if status in by_status:
                status_emoji = OrderStatus.get_status_emoji(status)
                status_name = OrderStatus.get_status_name(status)

                text += f"\n<b>{status_emoji} {status_name}:</b>\n"

                for order in by_status[status]:
                    text += f"  • Заявка #{order.id} - {order.equipment_type}\n"

                text += "\n"

        keyboard = get_order_list_keyboard(orders, for_master=True)

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("view_order_master:"))
async def callback_view_order_master(callback: CallbackQuery, user_roles: list):
    """
    Просмотр детальной информации о заявке для мастера

    Args:
        callback: Callback query
        user_roles: Список ролей пользователя
    """
    # Проверяем роль мастера
    if UserRole.MASTER not in user_roles:
        await callback.answer("У вас нет доступа к этой функции", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        # Проверяем, что заявка назначена этому мастеру
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        if not master or order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        status_emoji = OrderStatus.get_status_emoji(order.status)
        status_name = OrderStatus.get_status_name(order.status)

        text = (
            f"📋 <b>Заявка #{order.id}</b>\n\n"
            f"📊 <b>Статус:</b> {status_emoji} {status_name}\n"
            f"🔧 <b>Тип техники:</b> {order.equipment_type}\n"
            f"📝 <b>Описание:</b> {order.description}\n\n"
        )

        # Показываем контактную информацию клиента только после прибытия на объект
        if order.status in [OrderStatus.ONSITE, OrderStatus.DR, OrderStatus.CLOSED]:
            text += (
                f"👤 <b>Клиент:</b> {order.client_name}\n"
                f"📍 <b>Адрес:</b> {order.client_address}\n"
                f"📞 <b>Телефон:</b> {order.client_phone}\n\n"
            )
        elif order.status == OrderStatus.ACCEPTED:
            text += (
                f"👤 <b>Клиент:</b> {order.client_name}\n"
                f"📍 <b>Адрес:</b> {order.client_address}\n"
                f"📞 <b>Телефон:</b> <i>Будет доступен после прибытия на объект</i>\n\n"
            )
        else:
            text += (
                "<i>Контактная информация клиента будет доступна\n" "после принятия заявки.</i>\n\n"
            )

        if order.notes:
            text += f"📝 <b>Заметки:</b> {order.notes}\n\n"

        if order.scheduled_time:
            text += f"⏰ <b>Время прибытия:</b> {order.scheduled_time}\n\n"

        # Показываем информацию о длительном ремонте
        if order.status == OrderStatus.DR:
            if order.estimated_completion_date:
                text += f"⏰ <b>Примерный срок окончания:</b> {order.estimated_completion_date}\n"
            if order.prepayment_amount:
                text += f"💰 <b>Предоплата:</b> {order.prepayment_amount:.2f} ₽\n"
            text += "\n"

        # Показываем финансовую информацию для закрытых заявок
        if order.status == OrderStatus.CLOSED and order.total_amount:
            net_profit = order.total_amount - (order.materials_cost or 0)

            # Определяем базовую ставку
            base_rate = "50/50" if net_profit >= 7000 else "40/60"

            text += "\n💰 <b>Финансовая информация:</b>\n"
            text += f"• Сумма заказа: <b>{order.total_amount:.2f} ₽</b>\n"
            text += f"• Чистая прибыль: <b>{net_profit:.2f} ₽</b>\n"
            text += f"\n📊 <b>Распределение ({base_rate}):</b>\n"

            if order.master_profit:
                master_percent = (order.master_profit / net_profit * 100) if net_profit > 0 else 0
                text += (
                    f"• Ваша прибыль: <b>{order.master_profit:.2f} ₽</b> ({master_percent:.0f}%)\n"
                )
            if order.company_profit:
                company_percent = (order.company_profit / net_profit * 100) if net_profit > 0 else 0
                text += f"• Прибыль компании: <b>{order.company_profit:.2f} ₽</b> ({company_percent:.0f}%)\n"

            # Надбавки и бонусы (показываем только если явно True)
            bonuses = []
            if order.has_review is True:
                bonuses.append("✅ Отзыв (+10% вам)")
            if order.out_of_city is True:
                bonuses.append("✅ Выезд за город")

            if bonuses:
                text += f"\n🎁 <b>Надбавки:</b> {', '.join(bonuses)}\n"

            text += "\n"

        if order.created_at:
            text += f"📅 <b>Создана:</b> {format_datetime(order.created_at)}\n"

        keyboard = get_order_actions_keyboard(order, UserRole.MASTER)

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("accept_order:"))
async def callback_accept_order(callback: CallbackQuery, user_roles: list):
    """
    Принятие заявки мастером

    Args:
        callback: Callback query
        user_roles: Роли пользователя (передаётся из RoleCheckMiddleware)
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        # Проверяем права
        if not master or order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Обновляем статус (с валидацией через State Machine)
        await db.update_order_status(
            order_id=order_id,
            status=OrderStatus.ACCEPTED,
            changed_by=callback.from_user.id,
            user_roles=user_roles,  # Передаём роли для валидации
        )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ACCEPT_ORDER",
            details=f"Accepted order #{order_id}",
        )

        # Уведомляем диспетчера с retry механизмом
        if order.dispatcher_id:
            from app.utils import safe_send_message

            result = await safe_send_message(
                callback.bot,
                order.dispatcher_id,
                f"✅ Мастер {master.get_display_name()} принял заявку #{order_id}",
                parse_mode="HTML",
            )
            if not result:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id} after retries")

        # Формируем текст с деталями заявки
        acceptance_text = (
            f"✅ <b>Заявка #{order_id} принята!</b>\n\n"
            f"🔧 <b>Детали заявки:</b>\n"
            f"📱 Тип техники: {order.equipment_type}\n"
            f"📝 Описание: {order.description}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n"
        )

        # Добавляем заметки если есть
        if order.notes:
            acceptance_text += f"\n📝 <b>Заметки:</b> {order.notes}\n"

        # Добавляем время прибытия если указано
        if order.scheduled_time:
            acceptance_text += f"\n⏰ <b>Время прибытия к клиенту:</b> {order.scheduled_time}\n"

        acceptance_text += (
            "\n<b>Телефон клиента будет доступен после прибытия на объект.</b>\n"
            "Когда будете на месте, нажмите кнопку ниже."
        )

        # Обновляем сообщение с кнопкой "Я на объекте"
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        keyboard_builder = InlineKeyboardBuilder()
        keyboard_builder.row(
            InlineKeyboardButton(text="🏠 Я на объекте", callback_data=f"onsite_order:{order_id}")
        )

        await callback.message.edit_text(
            acceptance_text, parse_mode="HTML", reply_markup=keyboard_builder.as_markup()
        )

        log_action(callback.from_user.id, "ACCEPT_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    # Защита от двойного клика: 10 секунд для критичной операции
    from app.utils import safe_answer_callback

    await safe_answer_callback(callback, "Заявка принята!", cache_time=10)


@router.callback_query(F.data.startswith("refuse_order_master:"))
async def callback_refuse_order_master(callback: CallbackQuery):
    """
    Отклонение заявки мастером

    Args:
        callback: Callback query
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        # Проверяем права
        if not master or order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Возвращаем статус в NEW и убираем мастера (ORM compatible)
        if hasattr(db, "unassign_master_from_order"):
            await db.unassign_master_from_order(order_id)
        else:
            # Legacy: прямой SQL
            await db.connection.execute(
                "UPDATE orders SET status = ?, assigned_master_id = NULL WHERE id = ?",
                (OrderStatus.NEW, order_id),
            )
            await db.connection.commit()

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="REFUSE_ORDER_MASTER",
            details=f"Master refused order #{order_id}",
        )

        # Меню обновится автоматически в update_order_status

        # Уведомляем диспетчера с retry механизмом
        if order.dispatcher_id:
            from app.utils import safe_send_message

            result = await safe_send_message(
                callback.bot,
                order.dispatcher_id,
                f"❌ Мастер {master.get_display_name()} отклонил заявку #{order_id}\n"
                f"Необходимо назначить другого мастера.",
                parse_mode="HTML",
            )
            if not result:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id} after retries")

        await callback.message.edit_text(
            f"❌ Заявка #{order_id} отклонена.\n\n" f"Диспетчер получил уведомление."
        )

        log_action(callback.from_user.id, "REFUSE_ORDER_MASTER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    # Защита от двойного клика: 8 секунд для критичной операции
    from app.utils import safe_answer_callback

    await safe_answer_callback(callback, "Заявка отклонена", cache_time=8)


@router.callback_query(F.data.startswith("onsite_order:"))
async def callback_onsite_order(callback: CallbackQuery, user_roles: list):
    """
    Мастер на объекте

    Args:
        callback: Callback query
        user_roles: Роли пользователя (передаётся из RoleCheckMiddleware)
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        # Проверяем права
        if not master or order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Обновляем статус (с валидацией через State Machine)
        await db.update_order_status(
            order_id=order_id,
            status=OrderStatus.ONSITE,
            changed_by=callback.from_user.id,
            user_roles=user_roles,
        )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ONSITE_ORDER",
            details=f"Master on site for order #{order_id}",
        )

        # Уведомляем диспетчера с retry механизмом
        if order.dispatcher_id:
            from app.utils import safe_send_message

            result = await safe_send_message(
                callback.bot,
                order.dispatcher_id,
                f"🏠 Мастер {master.get_display_name()} на объекте (Заявка #{order_id})",
                parse_mode="HTML",
            )
            if not result:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id} after retries")

        # Обновляем сообщение с кнопками завершения
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        keyboard_builder = InlineKeyboardBuilder()
        keyboard_builder.row(
            InlineKeyboardButton(text="💰 Завершить", callback_data=f"complete_order:{order_id}")
        )
        keyboard_builder.row(
            InlineKeyboardButton(text="⏳ Длительный ремонт", callback_data=f"dr_order:{order_id}")
        )

        await callback.message.edit_text(
            f"🏠 <b>Статус обновлен!</b>\n\n"
            f"Заявка #{order_id} - вы на объекте.\n\n"
            f"📞 <b>Телефон клиента:</b> {order.client_phone}\n\n"
            f"После завершения работы нажмите кнопку ниже.",
            parse_mode="HTML",
            reply_markup=keyboard_builder.as_markup(),
        )

        log_action(callback.from_user.id, "ONSITE_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Статус обновлен!")


@router.callback_query(F.data.startswith("complete_order:"))
async def callback_complete_order(callback: CallbackQuery, state: FSMContext):
    """
    Начало процесса завершения заявки мастером

    Args:
        callback: Callback query
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        # Проверяем права
        if not master or order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Сохраняем ID заказа в состоянии FSM
        await state.update_data(order_id=order_id)

        # Переходим в состояние запроса общей суммы
        from app.states import CompleteOrderStates

        await state.set_state(CompleteOrderStates.enter_total_amount)

        await callback.message.edit_text(
            f"💰 <b>Завершение заявки #{order_id}</b>\n\n"
            f"Пожалуйста, введите <b>общую сумму заказа</b> (в рублях):\n"
            f"Например: 5000, 5000.50 или 0",
            parse_mode="HTML",
        )

        log_action(callback.from_user.id, "START_COMPLETE_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("dr_order:"))
async def callback_dr_order(callback: CallbackQuery, state: FSMContext):
    """
    Длительный ремонт - запрос срока окончания и предоплаты

    Args:
        callback: Callback query
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[1])

    logger.debug(f"[DR] Starting DR process for order #{order_id} by user {callback.from_user.id}")

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        logger.debug(f"[DR] Order found: {order is not None}, Master found: {master is not None}")

        # Проверяем права
        if not master or order.assigned_master_id != master.id:
            logger.warning(
                f"[DR] Access denied - Master ID: {master.id if master else None}, Assigned: {order.assigned_master_id if order else None}"
            )
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Сохраняем order_id в state
        await state.update_data(order_id=order_id)

        logger.debug("[DR] Transitioning to LongRepairStates.enter_completion_date_and_prepayment")

        # Переходим к вводу срока окончания и предоплаты
        await state.set_state(LongRepairStates.enter_completion_date_and_prepayment)

        await callback.message.edit_text(
            f"⏳ <b>Длительный ремонт - Заявка #{order_id}</b>\n\n"
            f"Введите <b>примерный срок окончания ремонта</b> и <b>предоплату</b> (если была).\n\n"
            f"<b>Примеры:</b>\n"
            f"• <code>20.10.2025</code>\n"
            f"• <code>20.10.2025 предоплата 2000</code>\n"
            f"• <code>через 3 дня</code>\n"
            f"• <code>завтра, предоплата 1500</code>\n"
            f"• <code>неделя</code>\n\n"
            f"<i>Если предоплаты не было - просто укажите срок.</i>",
            parse_mode="HTML",
        )

        await callback.answer()

    finally:
        await db.disconnect()


@router.message(LongRepairStates.enter_completion_date_and_prepayment, F.text)
async def process_dr_info(message: Message, state: FSMContext, user_roles: list):
    """
    Обработка ввода срока окончания и предоплаты для DR

    Args:
        message: Сообщение
        state: FSM контекст
        user_roles: Список ролей пользователя
    """
    import re

    logger.debug(f"[DR] Processing DR info from user {message.from_user.id}")

    # Получаем данные из state
    data = await state.get_data()
    order_id = data.get("order_id")

    logger.debug(f"[DR] Order ID from state: {order_id}, FSM data: {data}")

    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "⚠️ Пожалуйста, отправьте текстовое сообщение с информацией о сроках и предоплате."
        )
        return

    # Парсим введенный текст
    text = message.text.strip()
    logger.debug(f"[DR] Input text: '{text}'")

    # Ищем упоминание предоплаты и сумму
    prepayment_amount = None
    completion_date = text

    # Паттерн для поиска предоплаты: "предоплата 2000" или "аванс 1500" и т.д.
    prepayment_patterns = [
        r"предоплат[аы]?\s+(\d+(?:[.,]\d+)?)",
        r"аванс\s+(\d+(?:[.,]\d+)?)",
        r"предв\.?\s+(\d+(?:[.,]\d+)?)",
    ]

    for pattern in prepayment_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            prepayment_str = match.group(1).replace(",", ".")
            logger.debug(f"[DR] Found prepayment pattern: {pattern}, value: {prepayment_str}")
            try:
                prepayment_amount = float(prepayment_str)
                # Убираем упоминание предоплаты из срока
                completion_date = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
                # Убираем лишние запятые и пробелы
                completion_date = re.sub(r"\s*,\s*$", "", completion_date).strip()
                logger.debug(
                    f"[DR] Parsed - completion_date: '{completion_date}', prepayment: {prepayment_amount}"
                )
                break
            except ValueError as e:
                logger.warning(f"[DR] Failed to parse prepayment amount '{prepayment_str}': {e}")

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            logger.error(f"[DR] Error - Order not found: {order_id}")
            await message.reply("❌ Ошибка: заявка не найдена")
            await state.clear()
            return

        # Для мастера проверяем, что он назначен на эту заявку
        # Для администратора проверка не нужна
        master = await db.get_master_by_telegram_id(message.from_user.id)

        logger.debug(f"[DR] Order found: {order is not None}, Master found: {master is not None}")

        # Если это не администратор, проверяем что мастер назначен
        if master and order.assigned_master_id != master.id:
            logger.error(f"[DR] Master {master.id} not assigned to order {order_id}")
            await message.reply("❌ Ошибка: эта заявка назначена другому мастеру")
            await state.clear()
            return

        # Обновляем заявку
        logger.debug(
            f"[DR] Updating order #{order_id}: "
            f"completion_date='{completion_date}', prepayment={prepayment_amount}"
        )

        # Сначала обновляем поля DR
        await db.connection.execute(
            """
            UPDATE orders
            SET estimated_completion_date = ?,
                prepayment_amount = ?
            WHERE id = ?
            """,
            (completion_date, prepayment_amount, order_id),
        )
        await db.connection.commit()

        # Затем обновляем статус с валидацией через State Machine
        await db.update_order_status(
            order_id=order_id,
            status=OrderStatus.DR,
            changed_by=message.from_user.id,
            user_roles=user_roles,  # Передаём роли для валидации
        )

        logger.info(f"[DR] Order #{order_id} updated to DR status successfully")

        # Добавляем в лог
        await db.add_audit_log(
            user_id=message.from_user.id,
            action="DR_ORDER",
            details=f"Order #{order_id} marked as long-term repair. Completion: {completion_date}, Prepayment: {prepayment_amount or 0}",
        )

        # Формируем сообщение с результатом
        result_text = (
            f"✅ <b>Заявка #{order_id} переведена в длительный ремонт</b>\n\n"
            f"⏰ <b>Примерный срок:</b> {completion_date}\n"
        )

        if prepayment_amount:
            result_text += f"💰 <b>Предоплата:</b> {prepayment_amount:.2f} ₽\n"
        else:
            result_text += "💰 <b>Предоплата:</b> не было\n"

        result_text += "\n<i>Диспетчер получит уведомление.</i>"

        await message.reply(result_text, parse_mode="HTML")

        # Уведомляем диспетчера
        if order.dispatcher_id:
            # Определяем кто перевел заявку в DR
            initiator_name = master.get_display_name() if master else message.from_user.full_name

            notification = (
                f"⏳ <b>Заявка #{order_id} переведена в длительный ремонт</b>\n\n"
                f"👨‍🔧 Инициатор: {initiator_name}\n"
                f"⏰ Примерный срок: {completion_date}\n"
            )

            if prepayment_amount:
                notification += f"💰 Предоплата: {prepayment_amount:.2f} ₽"

            logger.debug(f"[DR] Sending notification to dispatcher {order.dispatcher_id}")

            try:
                await message.bot.send_message(order.dispatcher_id, notification, parse_mode="HTML")
                logger.debug("[DR] Dispatcher notification sent successfully")
            except Exception as e:
                logger.error(f"[DR] Failed to notify dispatcher {order.dispatcher_id}: {e}")

        log_action(message.from_user.id, "DR_ORDER", f"Order #{order_id}")

        logger.info(f"[DR] ✅ Order #{order_id} successfully marked as DR")

    except Exception as e:
        logger.exception(f"[DR] ❌ Error processing DR for order #{order_id}: {e}")
        await message.reply(
            "❌ Произошла ошибка при переводе заявки в длительный ремонт.\n"
            "Попробуйте еще раз или обратитесь к диспетчеру."
        )
    finally:
        await db.disconnect()
        await state.clear()
        logger.debug(f"[DR] State cleared and DB disconnected for order #{order_id}")


@router.message(F.text == "📊 Моя статистика")
async def btn_my_stats(message: Message):
    """
    Статистика мастера

    Args:
        message: Сообщение
    """
    # Проверяем, что это не личное сообщение
    if message.chat.type == "private":
        await message.answer(
            "⚠️ <b>Работа только в рабочей группе!</b>\n\n"
            "Для мастеров взаимодействие с ботом доступно только в рабочей группе.",
            parse_mode="HTML",
        )
        return

    db = Database()
    await db.connect()

    try:
        master = await db.get_master_by_telegram_id(message.from_user.id)

        if not master:
            await message.answer("❌ Вы не зарегистрированы как мастер в системе.")
            return

        # Получаем все заявки мастера
        orders = await db.get_orders_by_master(master.id, exclude_closed=False)

        # Подсчитываем статистику
        total = len(orders)
        by_status = {}

        for order in orders:
            by_status[order.status] = by_status.get(order.status, 0) + 1

        completed = by_status.get(OrderStatus.CLOSED, 0)
        active = sum(
            by_status.get(s, 0)
            for s in [OrderStatus.ASSIGNED, OrderStatus.ACCEPTED, OrderStatus.ONSITE]
        )
        dr = by_status.get(OrderStatus.DR, 0)

        text = (
            f"📊 <b>Ваша статистика</b>\n\n"
            f"👤 <b>Мастер:</b> {master.get_display_name()}\n"
            f"🔧 <b>Специализация:</b> {master.specialization}\n"
            f"📞 <b>Телефон:</b> {master.phone}\n\n"
            f"📈 <b>Заявки:</b>\n"
            f"• Всего: {total}\n"
            f"• ✅ Завершено: {completed}\n"
            f"• 🔄 Активных: {active}\n"
            f"• ⏳ Длительный ремонт: {dr}\n\n"
        )

        if total > 0:
            completion_rate = (completed / total) * 100
            text += f"📊 <b>Процент завершения:</b> {completion_rate:.1f}%\n"

        # Добавляем кнопки для просмотра заявок
        from app.keyboards.inline import get_master_stats_keyboard

        keyboard = get_master_stats_keyboard(master.id)

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    finally:
        await db.disconnect()


@router.message(CompleteOrderStates.enter_total_amount)
async def process_total_amount(message: Message, state: FSMContext):
    """
    Обработка ввода общей суммы заказа (работает и в личке, и в группе)

    Args:
        message: Сообщение
        state: FSM контекст
    """
    # Проверяем, что введена корректная сумма
    try:
        total_amount = float(message.text.replace(",", ".").strip())
        if total_amount < 0:
            await message.reply("❌ Сумма не может быть отрицательной.\n" "Попробуйте еще раз:")
            return
    except ValueError:
        await message.reply(
            "❌ Неверный формат суммы.\n"
            "Пожалуйста, введите число (например: 5000, 5000.50 или 0):"
        )
        return

    # Сохраняем общую сумму
    await state.update_data(total_amount=total_amount)

    # Переходим к запросу суммы расходного материала
    await state.set_state(CompleteOrderStates.enter_materials_cost)

    await message.reply(
        f"✅ Общая сумма заказа: <b>{total_amount:.2f} ₽</b>\n\n"
        f"Теперь введите <b>сумму расходного материала</b> (в рублях):\n"
        f"Например: 1500 или 1500.50\n\n"
        f"Если расходного материала не было, введите: 0",
        parse_mode="HTML",
    )


@router.message(CompleteOrderStates.enter_materials_cost)
async def process_materials_cost(message: Message, state: FSMContext):
    """
    Обработка ввода суммы расходного материала и запрос об отзыве (работает и в личке, и в группе)

    Args:
        message: Сообщение
        state: FSM контекст
    """
    # Проверяем, что введена корректная сумма
    try:
        materials_cost = float(message.text.replace(",", ".").strip())
        if materials_cost < 0:
            await message.reply(
                "❌ Сумма не может быть отрицательной.\n"
                "Попробуйте еще раз (или введите 0, если расходов не было):"
            )
            return
    except ValueError:
        await message.reply(
            "❌ Неверный формат суммы.\n" "Пожалуйста, введите число (например: 1500 или 0):"
        )
        return

    # Сохраняем сумму расходного материала
    await state.update_data(materials_cost=materials_cost)

    # Получаем ID заказа для inline кнопок
    data = await state.get_data()
    order_id = data.get("order_id")

    # Переходим к запросу об отзыве
    await state.set_state(CompleteOrderStates.confirm_review)

    from app.keyboards.inline import get_yes_no_keyboard

    await message.reply(
        f"✅ Сумма расходного материала: <b>{materials_cost:.2f} ₽</b>\n\n"
        f"❓ <b>Взяли ли вы отзыв у клиента?</b>\n"
        f"(За отзыв вы получите дополнительно +10% к прибыли)",
        parse_mode="HTML",
        reply_markup=get_yes_no_keyboard("confirm_review", order_id),
    )


@router.callback_query(lambda c: c.data.startswith("confirm_review"))
async def process_review_confirmation_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка подтверждения наличия отзыва через inline кнопки

    Args:
        callback_query: Callback запрос
        state: FSM контекст
    """
    # Извлекаем данные из callback
    from app.utils import parse_callback_data

    callback_data = parse_callback_data(callback_query.data)
    order_id = callback_data["params"][0] if len(callback_data["params"]) > 0 else None
    answer = callback_data["params"][1] if len(callback_data["params"]) > 1 else None

    # Определяем ответ
    has_review = answer == "yes"

    # Сохраняем ответ об отзыве
    await state.update_data(has_review=has_review)

    # Переходим к запросу выезда за город
    await state.set_state(CompleteOrderStates.confirm_out_of_city)

    review_text = "✅ Отзыв взят!" if has_review else "❌ Отзыв не взят"

    from app.keyboards.inline import get_yes_no_keyboard

    await callback_query.message.edit_text(
        f"{review_text}\n\n"
        f"🚗 <b>Был ли выезд за город?</b>\n"
        f"(За выезд за город вы получите дополнительно +10% к прибыли)",
        parse_mode="HTML",
        reply_markup=get_yes_no_keyboard("confirm_out_of_city", int(order_id)),
    )

    await callback_query.answer()


@router.message(CompleteOrderStates.confirm_review)
async def process_review_confirmation_fallback(message: Message, state: FSMContext):
    """
    Fallback обработка для текстовых сообщений (на случай если кнопки не работают)

    Args:
        message: Сообщение
        state: FSM контекст
    """
    await message.reply(
        "❌ Пожалуйста, используйте кнопки для ответа.\n"
        "Если кнопки не отображаются, попробуйте перезапустить процесс завершения заказа."
    )


@router.callback_query(lambda c: c.data.startswith("confirm_out_of_city"))
async def process_out_of_city_confirmation_callback(
    callback_query: CallbackQuery, state: FSMContext, user_roles: list
):
    """
    Обработка подтверждения выезда за город через inline кнопки и завершение заказа

    Args:
        callback_query: Callback запрос
        state: FSM контекст
        user_roles: Список ролей пользователя
    """
    # Извлекаем данные из callback
    from app.utils import parse_callback_data

    callback_data = parse_callback_data(callback_query.data)
    order_id = callback_data["params"][0] if len(callback_data["params"]) > 0 else None
    answer = callback_data["params"][1] if len(callback_data["params"]) > 1 else None

    # Определяем ответ
    out_of_city = answer == "yes"

    # Получаем данные из состояния
    data = await state.get_data()
    total_amount = data.get("total_amount")
    materials_cost = data.get("materials_cost")
    has_review = data.get("has_review")
    acting_as_master_id = data.get(
        "acting_as_master_id"
    )  # ID мастера, если админ действует от его имени

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(int(order_id))

        # Если админ действует от имени мастера
        if acting_as_master_id:
            master = await db.get_master_by_telegram_id(acting_as_master_id)
        else:
            master = await db.get_master_by_telegram_id(callback_query.from_user.id)

        if not master or not order or order.assigned_master_id != master.id:
            await callback_query.message.edit_text(
                "❌ Ошибка: заявка не найдена или не принадлежит вам."
            )
            return

        # Рассчитываем распределение прибыли с учетом отзыва и выезда за город
        from app.utils.helpers import calculate_profit_split

        master_profit, company_profit = calculate_profit_split(
            total_amount, materials_cost, has_review, out_of_city
        )
        net_profit = total_amount - materials_cost

        # Определяем процентную ставку для отображения
        profit_rate = "50/50" if net_profit >= 7000 else "40/60"
        bonus_text = ""
        if has_review:
            bonus_text += " + бонус за отзыв"
        if out_of_city:
            bonus_text += " + бонус за выезд"

        # Обновляем суммы в базе данных
        await db.update_order_amounts(
            order_id=int(order_id),
            total_amount=total_amount,
            materials_cost=materials_cost,
            master_profit=master_profit,
            company_profit=company_profit,
            has_review=has_review,
            out_of_city=out_of_city,
        )

        # Обновляем статус на CLOSED (с валидацией через State Machine)
        from app.config import OrderStatus

        await db.update_order_status(
            order_id=int(order_id),
            status=OrderStatus.CLOSED,
            changed_by=callback_query.from_user.id,
            user_roles=user_roles,  # Передаём роли для валидации
        )

        # Создаем отчет по заказу
        try:
            from app.services.order_reports import OrderReportsService

            order_reports_service = OrderReportsService()

            # Получаем актуальные данные заказа
            updated_order = await db.get_order_by_id(int(order_id))

            # Получаем данные диспетчера
            dispatcher = None
            if updated_order.dispatcher_id:
                dispatcher = await db.get_user_by_telegram_id(updated_order.dispatcher_id)

            # Создаем запись в отчете
            await order_reports_service.create_order_report(updated_order, master, dispatcher)
            logger.info(f"Order report created for order #{order_id}")

        except Exception as e:
            logger.error(f"Failed to create order report for #{order_id}: {e}")

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback_query.from_user.id,
            action="COMPLETE_ORDER",
            details=f"Completed order #{order_id}, total: {total_amount}, materials: {materials_cost}",
        )

        # ✨ УВЕДОМЛЕНИЕ ДИСПЕТЧЕРА О ЗАКРЫТИИ ЗАЯВКИ
        if order.dispatcher_id:
            from app.utils import safe_send_message

            notification_text = (
                f"✅ <b>Заявка завершена!</b>\n\n"
                f"📋 <b>Заявка #{order_id}</b>\n"
                f"👨‍🔧 <b>Мастер:</b> {master.get_display_name()}\n\n"
                f"💰 <b>Финансы:</b>\n"
                f"└ Общая сумма: {total_amount:.2f} ₽\n"
                f"└ Материалы: {materials_cost:.2f} ₽\n"
                f"└ Прибыль: {net_profit:.2f} ₽\n\n"
                f"📊 <b>Распределение:</b>\n"
                f"└ Мастер: {master_profit:.2f} ₽\n"
                f"└ Компания: {company_profit:.2f} ₽\n"
            )

            if has_review:
                notification_text += "\n⭐ <b>Отзыв:</b> Да"
            if out_of_city:
                notification_text += "\n🚗 <b>Выезд:</b> Да"

            result = await safe_send_message(
                callback_query.bot,
                order.dispatcher_id,
                notification_text,
                parse_mode="HTML",
            )

            if not result:
                logger.error(
                    f"Failed to notify dispatcher {order.dispatcher_id} about order #{order_id} completion"
                )
            else:
                logger.info(
                    f"Dispatcher {order.dispatcher_id} notified about order #{order_id} completion"
                )

        # Формируем текст подтверждения
        out_of_city_text = "🚗 Да" if out_of_city else "❌ Нет"
        review_text = "⭐ Да" if has_review else "❌ Нет"

        # Обновляем сообщение с результатами
        await callback_query.message.edit_text(
            f"✅ <b>Заявка #{order_id} завершена!</b>\n\n"
            f"📊 <b>Итоговая информация:</b>\n"
            f"└ Общая сумма: <b>{total_amount:.2f} ₽</b>\n"
            f"└ Расходный материал: <b>{materials_cost:.2f} ₽</b>\n"
            f"└ Чистая прибыль: <b>{net_profit:.2f} ₽</b>\n\n"
            f"💰 <b>Распределение прибыли ({profit_rate}{bonus_text}):</b>\n"
            f"└ Мастер: <b>{master_profit:.2f} ₽</b>\n"
            f"└ Компания: <b>{company_profit:.2f} ₽</b>\n\n"
            f"📋 <b>Дополнительно:</b>\n"
            f"└ Отзыв: {review_text}\n"
            f"└ Выезд за город: {out_of_city_text}",
            parse_mode="HTML",
        )

        await callback_query.answer("✅ Заявка успешно завершена!")

        # Очищаем состояние
        await state.clear()

    except Exception as e:
        logger.error(f"Error completing order #{order_id}: {e}")
        await callback_query.message.edit_text("❌ Произошла ошибка при завершении заявки.")
    finally:
        await db.disconnect()


@router.message(CompleteOrderStates.confirm_out_of_city)
async def process_out_of_city_confirmation_fallback(message: Message, state: FSMContext):
    """
    Fallback обработка для текстовых сообщений (на случай если кнопки не работают)

    Args:
        message: Сообщение
        state: FSM контекст
    """
    await message.reply(
        "❌ Пожалуйста, используйте кнопки для ответа.\n"
        "Если кнопки не отображаются, попробуйте перезапустить процесс завершения заказа."
    )


@router.message(F.text == "⚙️ Настройки")
async def btn_settings_master(message: Message):
    """
    Обработчик кнопки настроек для мастеров

    Args:
        message: Сообщение
    """
    db = Database()
    await db.connect()

    try:
        master = await db.get_master_by_telegram_id(message.from_user.id)

        if not master:
            await message.answer("❌ Вы не зарегистрированы как мастер в системе.")
            return

        user = await db.get_user_by_telegram_id(message.from_user.id)

        # Получаем список ролей
        role_names = {
            UserRole.ADMIN: "Администратор",
            UserRole.DISPATCHER: "Диспетчер",
            UserRole.MASTER: "Мастер",
            UserRole.UNKNOWN: "Неизвестно",
        }

        if user:
            user_roles = user.get_roles()
            roles_display = ", ".join([role_names.get(r, r) for r in user_roles])
        else:
            roles_display = role_names[UserRole.MASTER]

        settings_text = (
            f"⚙️ <b>Настройки профиля</b>\n\n"
            f"👤 <b>Имя:</b> {master.get_display_name()}\n"
            f"🆔 <b>Telegram ID:</b> <code>{master.telegram_id}</code>\n"
            f"📞 <b>Телефон:</b> {master.phone}\n"
            f"🔧 <b>Специализация:</b> {master.specialization}\n"
            f"👔 <b>Роли:</b> {roles_display}\n"
        )

        if user and user.username:
            settings_text += f"📱 <b>Username:</b> @{user.username}\n"

        status_emoji = "✅" if master.is_approved else "⏳"
        active_emoji = "🟢" if master.is_active else "🔴"

        settings_text += f"\n📊 <b>Статус:</b> {status_emoji} {'Одобрен' if master.is_approved else 'Ожидает одобрения'}\n"
        settings_text += f"🔄 <b>Активность:</b> {active_emoji} {'Активен' if master.is_active else 'Неактивен'}\n"

        await message.answer(settings_text, parse_mode="HTML")

    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("export_order:"))
async def callback_export_order_master(callback: CallbackQuery):
    """
    Экспорт заявки в Excel (для мастера)

    Args:
        callback: Callback query
    """
    order_id = int(callback.data.split(":")[1])

    await callback.answer("⏳ Генерирую Excel файл...")

    from app.services.order_export import OrderExportService

    excel_file = await OrderExportService.export_order_to_excel(order_id)

    if excel_file:
        await callback.message.answer_document(
            document=excel_file, caption=f"📊 Детали заявки #{order_id}"
        )
        logger.info(f"Order #{order_id} exported to Excel by master {callback.from_user.id}")
    else:
        await callback.answer("❌ Заявка не найдена", show_alert=True)


# ==================== ПЕРЕНОС ЗАЯВКИ ====================


@router.callback_query(F.data.startswith("reschedule_order:"))
async def callback_reschedule_order(callback: CallbackQuery, state: FSMContext):
    """
    Начало процесса переноса заявки

    Args:
        callback: Callback query
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        # Проверяем, что заявка в статусе ASSIGNED или ACCEPTED
        if order.status not in [OrderStatus.ASSIGNED, OrderStatus.ACCEPTED]:
            await callback.answer(
                "Перенести можно только заявки в статусе 'Назначена' или 'Принята'", show_alert=True
            )
            return

        # Сохраняем данные в state
        await state.update_data(order_id=order_id, reschedule_initiated_by=callback.from_user.id)

        # Переходим к вводу нового времени
        await state.set_state(RescheduleOrderStates.enter_new_time)

        current_time = order.scheduled_time or "не указано"

        await callback.message.edit_text(
            f"📅 <b>Перенос заявки #{order_id}</b>\n\n"
            f"⏰ Сейчас: {current_time}\n\n"
            f"Напишите новое время:\n"
            f"<i>Например: завтра 14:00, сегодня 18:00, через 2 часа</i>",
            parse_mode="HTML",
        )

        await callback.answer()

    finally:
        await db.disconnect()


@router.message(RescheduleOrderStates.enter_new_time)
async def process_reschedule_new_time(message: Message, state: FSMContext):
    """
    Обработка ввода нового времени для переноса заявки

    Args:
        message: Сообщение
        state: FSM контекст
    """
    new_time = message.text.strip()

    # Сохраняем новое время
    await state.update_data(new_scheduled_time=new_time)

    # Переходим к запросу причины
    await state.set_state(RescheduleOrderStates.enter_reason)

    await message.reply(
        f"✅ Новое время: <b>{new_time}</b>\n\n"
        f"Укажите причину переноса:\n"
        f"<i>(или отправьте '-' чтобы пропустить)</i>",
        parse_mode="HTML",
    )


@router.message(RescheduleOrderStates.enter_reason)
async def process_reschedule_reason(message: Message, state: FSMContext):
    """
    Обработка ввода причины переноса и завершение процесса

    Args:
        message: Сообщение
        state: FSM контекст
    """
    reason = message.text.strip()

    # Если пользователь указал "-", причины нет
    if reason == "-":
        reason = None

    # Получаем данные из state
    data = await state.get_data()
    order_id = data.get("order_id")
    new_time = data.get("new_scheduled_time")
    initiated_by = data.get("reschedule_initiated_by")

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            await message.reply("❌ Ошибка: заявка не найдена")
            return

        # Обновляем заявку
        old_time = order.scheduled_time or "не указано"

        await db.connection.execute(
            """
            UPDATE orders
            SET scheduled_time = ?,
                rescheduled_count = rescheduled_count + 1,
                last_rescheduled_at = ?,
                reschedule_reason = ?
            WHERE id = ?
            """,
            (new_time, get_now(), reason, order_id),
        )
        await db.connection.commit()

        # Добавляем в лог
        await db.add_audit_log(
            user_id=message.from_user.id,
            action="RESCHEDULE_ORDER",
            details=f"Order #{order_id} rescheduled from '{old_time}' to '{new_time}'. Reason: {reason or 'не указана'}",
        )

        # Формируем сообщение с результатом
        result_text = (
            f"✅ <b>Заявка #{order_id} перенесена</b>\n\n"
            f"Было: {old_time}\n"
            f"Стало: <b>{new_time}</b>\n"
        )

        if reason:
            result_text += f"\n📝 {reason}"

        result_text += "\n\n<i>Диспетчер уведомлен</i>"

        await message.reply(result_text, parse_mode="HTML")

        # Уведомляем диспетчера
        if order.dispatcher_id:
            master = await db.get_master_by_telegram_id(initiated_by)
            master_name = master.get_display_name() if master else f"ID: {initiated_by}"

            notification = (
                f"📅 <b>Заявка #{order_id} перенесена</b>\n\n"
                f"👨‍🔧 {master_name}\n"
                f"👤 {order.client_name} - {order.client_phone}\n"
                f"🔧 {order.equipment_type}\n\n"
                f"Было: {old_time}\n"
                f"<b>Стало: {new_time}</b>\n"
            )

            if reason:
                notification += f"\n📝 {reason}"

            notification += "\n\n💡 Свяжитесь с клиентом для подтверждения"

            try:
                await message.bot.send_message(order.dispatcher_id, notification, parse_mode="HTML")
                logger.info(f"Reschedule notification sent to dispatcher {order.dispatcher_id}")
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        log_action(message.from_user.id, "RESCHEDULE_ORDER", f"Order #{order_id}")

        logger.info(f"✅ Order #{order_id} successfully rescheduled to '{new_time}'")

    except Exception as e:
        logger.exception(f"❌ Error rescheduling order #{order_id}: {e}")
        await message.reply(
            "❌ Произошла ошибка при переносе заявки.\n"
            "Попробуйте еще раз или обратитесь к диспетчеру."
        )
    finally:
        await db.disconnect()
        await state.clear()


# ==================== EXCEL ОТЧЕТЫ ДЛЯ МАСТЕРОВ ====================


@router.callback_query(F.data.startswith("master_report_excel:"))
async def callback_master_report_excel(callback: CallbackQuery):
    """
    Генерация и отправка Excel отчета мастеру

    Args:
        callback: Callback query
    """
    master_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        # Проверяем, что мастер запрашивает свой отчет
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        if not master or master.id != master_id:
            await callback.answer("❌ Вы можете просматривать только свои отчеты", show_alert=True)
            return

        await callback.answer("📊 Генерирую отчет...")

        await callback.message.edit_text(
            "⏳ <b>Генерация Excel отчета...</b>\n\nПожалуйста, подождите.", parse_mode="HTML"
        )

        # Генерируем отчет
        from app.services.master_reports import MasterReportsService

        reports_service = MasterReportsService(db)

        excel_file = await reports_service.generate_master_report_excel(
            master_id=master_id,
            save_to_archive=False,  # Не сохраняем в архив, это текущий отчет
        )

        # Отправляем файл
        await callback.message.answer_document(
            document=excel_file,
            caption=(
                f"📊 <b>Ваш личный отчет</b>\n\n"
                f"👤 Мастер: {master.get_display_name()}\n"
                f"📅 Дата: {datetime.now(UTC).strftime('%d.%m.%Y %H:%M')}\n\n"
                f"В отчете 2 листа:\n"
                f"• 📋 Активные заявки\n"
                f"• ✅ Завершенные заявки"
            ),
            parse_mode="HTML",
        )

        # Удаляем сообщение о генерации
        await callback.message.delete()

        logger.info(f"Excel отчет отправлен мастеру {master_id}")

    except Exception as e:
        logger.exception(f"Ошибка при генерации отчета для мастера {master_id}: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка при генерации отчета</b>\n\n"
            "Попробуйте еще раз позже или обратитесь к администратору.",
            parse_mode="HTML",
        )
    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("master_reports_archive:"))
async def callback_master_reports_archive(callback: CallbackQuery):
    """
    Просмотр архивных отчетов мастера

    Args:
        callback: Callback query
    """
    master_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        # Проверяем, что мастер запрашивает свои отчеты
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        if not master or master.id != master_id:
            await callback.answer("❌ Вы можете просматривать только свои отчеты", show_alert=True)
            return

        # Получаем архивные отчеты
        from app.services.master_reports import MasterReportsService

        reports_service = MasterReportsService(db)

        archived_reports = await reports_service.get_master_archived_reports(master_id, limit=10)

        if not archived_reports:
            await callback.answer(
                "📭 У вас пока нет архивных отчетов.\n\n"
                "Архивные отчеты создаются автоматически каждые 30 дней.",
                show_alert=True,
            )
            return

        # Формируем сообщение
        text = "📚 <b>Архив отчетов</b>\n\n"
        text += f"Всего отчетов: {len(archived_reports)}\n\n"
        text += "Нажмите на отчет, чтобы скачать его:"

        # Клавиатура с отчетами
        from app.keyboards.inline import get_master_archived_reports_keyboard

        keyboard = get_master_archived_reports_keyboard(archived_reports, master_id)

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("download_archive_report:"))
async def callback_download_archive_report(callback: CallbackQuery):
    """
    Скачивание архивного отчета

    Args:
        callback: Callback query
    """
    # Парсим данные: report_id_master_id
    data = callback.data.split(":")[1]
    report_id, master_id = map(int, data.split("_"))

    db = Database()
    await db.connect()

    try:
        # Проверяем права
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        if not master or master.id != master_id:
            await callback.answer("❌ Нет доступа к этому отчету", show_alert=True)
            return

        await callback.answer("📥 Загружаю отчет...")

        # Получаем файл отчета
        from app.services.master_reports import MasterReportsService

        reports_service = MasterReportsService(db)

        excel_file = await reports_service.get_archived_report_file(report_id, master_id)

        if not excel_file:
            await callback.answer("❌ Файл отчета не найден", show_alert=True)
            return

        # Получаем информацию об отчете
        report = await db.get_master_report_archive_by_id(report_id)

        caption = (
            f"📚 <b>Архивный отчет</b>\n\n"
            f"📅 Период: {report.period_start.strftime('%d.%m.%Y')} - {report.period_end.strftime('%d.%m.%Y')}\n"
            f"📋 Заявок: {report.total_orders}\n"
            f"✅ Завершено: {report.completed_orders}\n"
            f"💰 Выручка: {report.total_revenue:.2f} ₽"
        )

        # Отправляем файл
        await callback.message.answer_document(
            document=excel_file, caption=caption, parse_mode="HTML"
        )

        logger.info(f"Архивный отчет {report_id} отправлен мастеру {master_id}")

    except Exception as e:
        logger.exception(f"Ошибка при загрузке архивного отчета {report_id}: {e}")
        await callback.answer("❌ Ошибка при загрузке отчета", show_alert=True)
    finally:
        await db.disconnect()

    await callback.answer()
