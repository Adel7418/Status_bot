"""
Обработчики для мастеров
"""

import logging
import re
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.config import OrderStatus, UserRole
from app.database import Database
from app.decorators import handle_errors
from app.handlers.common import get_menu_with_counter
from app.keyboards.inline import (
    get_order_actions_keyboard,
    get_order_list_keyboard,
    get_yes_no_keyboard,
)
from app.states import (
    CompleteOrderStates,
    LongRepairStates,
    RescheduleOrderStates,
)
from app.utils import format_datetime, get_now, log_action


logger = logging.getLogger(__name__)

router = Router(name="master")
# Фильтры на уровне роутера НЕ работают, т.к. выполняются ДО middleware
# Проверка роли теперь в каждом обработчике через декоратор


@router.message(F.text == "📋 Мои заявки")
@handle_errors
async def btn_my_orders(message: Message, state: FSMContext, user_role: str):
    """
    Просмотр заявок мастера

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    # Проверка роли
    if user_role not in [UserRole.MASTER, UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    # Проверяем, что это не личное сообщение (только для чистых мастеров)
    if message.chat.type == "private" and user_role == UserRole.MASTER:
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
                    scheduled_time = f" ({order.scheduled_time})" if order.scheduled_time else ""
                    text += f"  • Заявка #{order.id} - {order.equipment_type}{scheduled_time}\n"

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

        if not master:
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        if order.assigned_master_id != master.id:
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
        if not master:
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        if order.assigned_master_id != master.id:
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
                logger.error(
                    f"Не удалось уведомить диспетчера {order.dispatcher_id} после повторных попыток"
                )

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
async def callback_refuse_order_master(callback: CallbackQuery, user_roles: list):
    """
    Отклонение заявки мастером

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

        logger.info(
            f"[REFUSE] Order found: {order is not None}, Master found: {master is not None}"
        )
        if order:
            logger.info(f"[REFUSE] Order assigned_master_id: {order.assigned_master_id}")
        if master:
            logger.info(f"[REFUSE] Master id: {master.id}")

        # Проверяем права
        if not master:
            logger.warning(f"[REFUSE] User {callback.from_user.id} is not registered as master")
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        if order.assigned_master_id != master.id:
            logger.warning(
                f"[REFUSE] Access denied - Master ID: {master.id}, Assigned: {order.assigned_master_id}"
            )
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Удаляем карточки заявки в рабочей группе (если были сохранены)
        try:
            if hasattr(db, "get_active_group_messages_by_order"):
                messages = await db.get_active_group_messages_by_order(order_id)
                if messages:
                    from app.utils.retry import safe_delete_message

                    for m in messages:
                        await safe_delete_message(callback.bot, m.chat_id, m.message_id)
                    await db.deactivate_group_messages(order_id)
        except Exception:
            pass

        # Возвращаем статус в NEW и убираем мастера (ORM compatible)
        if hasattr(db, "unassign_master_from_order"):
            await db.unassign_master_from_order(order_id)
        else:
            # Legacy: прямой SQL
            async with db.get_session() as session:
                from sqlalchemy import text

                await session.execute(
                    text(
                        "UPDATE orders SET status = :status, assigned_master_id = NULL WHERE id = :order_id"
                    ),
                    {"status": OrderStatus.NEW, "order_id": order_id},
                )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="REFUSE_ORDER_MASTER",
            details=f"Master refused order #{order_id}",
        )

        # Удаляем текущее сообщение, если возможно; иначе редактируем
        try:
            await callback.message.delete()
        except Exception:
            await callback.message.edit_text(
                f"❌ Заявка #{order_id} отклонена.\n\n" f"Диспетчер получил уведомление."
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
                logger.error(
                    f"Не удалось уведомить диспетчера {order.dispatcher_id} после повторных попыток"
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
        if not master:
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        if order.assigned_master_id != master.id:
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
                logger.error(
                    f"Не удалось уведомить диспетчера {order.dispatcher_id} после повторных попыток"
                )

        # Обновляем сообщение с кнопками завершения
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        keyboard_builder = InlineKeyboardBuilder()
        keyboard_builder.row(
            InlineKeyboardButton(text="💰 Завершить", callback_data=f"complete_order:{order_id}")
        )
        keyboard_builder.row(
            InlineKeyboardButton(text="⏳ ДР", callback_data=f"dr_order:{order_id}")
        )

        await callback.message.edit_text(
            f"🏠 <b>Статус обновлен!</b>\n\n" f"Заявка #{order_id} - вы на объекте.",
            parse_mode="HTML",
            reply_markup=keyboard_builder.as_markup(),
        )

        log_action(callback.from_user.id, "ONSITE_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Статус обновлен!")


@router.callback_query(F.data.startswith("refuse_order_complete:"))
async def callback_refuse_order_complete(callback: CallbackQuery, state: FSMContext):
    """
    Быстрое завершение заявки как отказ (0 рублей)

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
        if not master:
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        if order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Сохраняем order_id в состоянии
        await state.update_data(order_id=order_id)

        # Переходим к подтверждению отказа
        from app.states import RefuseOrderStates

        await state.set_state(RefuseOrderStates.confirm_refusal)

        # Показываем подтверждение
        await callback.message.edit_text(
            f"⚠️ <b>Подтверждение отказа</b>\n\n"
            f"📋 Заявка #{order_id}\n"
            f"🔧 Тип техники: {order.equipment_type}\n"
            f"👤 Клиент: {order.client_name}\n\n"
            f"<b>Вы уверены, что хотите закрыть заявку как отказ?</b>\n\n"
            f"<i>Заявка будет помечена как отказ с суммой 0 рублей.</i>",
            parse_mode="HTML",
            reply_markup=get_yes_no_keyboard("confirm_refuse", order_id),
        )

    finally:
        await db.disconnect()

    await callback.answer()


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
        if not master:
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        if order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Сохраняем контекст завершения в FSM
        await state.update_data(
            order_id=order_id,
            initiator_user_id=callback.from_user.id,
            allowed_chat_id=callback.message.chat.id,
        )

        # Переходим в состояние запроса общей суммы
        from app.states import CompleteOrderStates

        await state.set_state(CompleteOrderStates.enter_total_amount)

        # В ЛС открываем ForceReply, чтобы у пользователя автоматически включился режим ответа
        from aiogram.types import ForceReply

        prompt = await callback.message.answer(
            f"💰 <b>Завершение заявки #{order_id}</b>\n\n"
            f"Пожалуйста, введите <b>общую сумму заказа</b> (в рублях):\n"
            f"Например: 5000, 5000.50 или 0",
            parse_mode="HTML",
            reply_markup=ForceReply(selective=True, input_field_placeholder="Введите сумму…"),
        )

        await state.update_data(prompt_message_id=prompt.message_id)

        log_action(callback.from_user.id, "START_COMPLETE_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("dr_order:"))
async def callback_dr_order(callback: CallbackQuery, state: FSMContext):
    """
    ДР - запрос срока окончания и предоплаты

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

        # ВАЛИДАЦИЯ: Проверяем, что заявка ещё НЕ в статусе DR
        if order.status == OrderStatus.DR:
            logger.warning(f"[DR] Order #{order_id} is already in DR status")
            await callback.answer(
                "❌ Эта заявка уже в статусе 'ДР'!\n"
                "Для изменения срока используйте кнопку '✏️ Редактировать'",
                show_alert=True,
            )
            return

        # ВАЛИДАЦИЯ: Можно переводить в DR только из статуса ONSITE
        if order.status != OrderStatus.ONSITE:
            logger.warning(f"[DR] Cannot move order #{order_id} to DR from status {order.status}")
            await callback.answer(
                "❌ Перевести в длительный ремонт можно только из статуса 'На объекте'",
                show_alert=True,
            )
            return

        # Сохраняем order_id в state
        await state.update_data(order_id=order_id)

        logger.debug("[DR] Transitioning to LongRepairStates.enter_completion_date_and_prepayment")

        # Переходим к вводу срока окончания и предоплаты
        await state.set_state(LongRepairStates.enter_completion_date_and_prepayment)

        await callback.message.edit_text(
            f"⏳ <b>ДР - Заявка #{order_id}</b>\n\n"
            f"Введите <b>примерный срок окончания ремонта</b> и <b>предоплату</b> (если была).\n\n"
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

    # Проверяем на отмену
    if text.lower() in ["отмена", "отменить", "❌ отмена", "cancel"]:
        await message.answer(
            "❌ Перевод в длительный ремонт отменен.", reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()

        # Показываем главное меню
        db = Database()
        await db.connect()
        try:
            user = await db.get_user_by_telegram_id(message.from_user.id)
            if user:
                user_roles = user.get_roles()
                menu_keyboard = await get_menu_with_counter(user_roles)
                await message.answer(
                    "🏠 <b>Главное меню</b>", parse_mode="HTML", reply_markup=menu_keyboard
                )
        finally:
            await db.disconnect()
        return

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
                logger.warning(
                    f"[DR] Не удалось распарсить сумму предоплаты '{prepayment_str}': {e}"
                )

    # ВАЛИДАЦИЯ ПРЕДОПЛАТЫ
    if prepayment_amount is not None:
        prepayment_validation = validate_dr_prepayment(prepayment_amount)
        if not prepayment_validation["valid"]:
            await message.reply(
                f"❌ <b>Ошибка валидации предоплаты:</b>\n\n"
                f"{prepayment_validation['error']}\n\n"
                f"Пожалуйста, введите корректную сумму предоплаты.",
                parse_mode="HTML",
            )
            # Оставляем пользователя в текущем состоянии для повторного ввода
            return

    # 🆕 АВТООПРЕДЕЛЕНИЕ ДАТЫ из естественного языка
    from app.utils import (
        format_datetime_for_storage,
        format_datetime_user_friendly,
        parse_natural_datetime,
        should_parse_as_date,
        validate_parsed_datetime,
    )

    if should_parse_as_date(completion_date):
        parsed_dt, _ = parse_natural_datetime(completion_date, validate=True)

        if parsed_dt:
            # Проверяем валидацию
            validation = validate_parsed_datetime(parsed_dt, completion_date)

            # СТРОГАЯ ВАЛИДАЦИЯ ДЛЯ ДЛИТЕЛЬНОГО РЕМОНТА
            dr_validation = validate_dr_completion_date(parsed_dt, completion_date)

            if not dr_validation["valid"]:
                await message.reply(
                    f"❌ <b>Ошибка валидации даты:</b>\n\n"
                    f"{dr_validation['error']}\n\n"
                    f"Пожалуйста, введите корректную дату завершения ремонта.",
                    parse_mode="HTML",
                )
                # Оставляем состояние, чтобы пользователь мог ввести дату повторно
                return

            # Успешно распознали дату - форматируем для хранения
            formatted_date = format_datetime_for_storage(parsed_dt, completion_date)
            user_friendly = format_datetime_user_friendly(parsed_dt, completion_date)

            logger.info(
                f"Автоопределение даты завершения DR: '{completion_date}' -> '{formatted_date}'"
            )

            # Обновляем completion_date с распознанной датой
            completion_date = formatted_date

            # Формируем сообщение с предупреждением если есть
            confirmation_text = f"✅ <b>Дата завершения распознана:</b>\n\n{user_friendly}"

            if validation.get("warning"):
                confirmation_text += f"\n\n⚠️ <i>{validation['warning']}</i>"

            if dr_validation.get("warning"):
                confirmation_text += f"\n\n⚠️ <i>{dr_validation['warning']}</i>"

            # Показываем пользователю что распознали
            await message.answer(
                confirmation_text,
                parse_mode="HTML",
            )
        else:
            # Не удалось распарсить дату - показываем примеры
            await message.reply(
                f"❌ <b>Не удалось распознать дату:</b> '{completion_date}'\n\n"
                f"<b>Примеры правильного ввода:</b>\n"
                f"• завтра\n"
                f"• через 3 дня\n"
                f"• через неделю\n"
                f"• 25.12.2025\n"
                f"• послезавтра в 15:00\n\n"
                f"Пожалуйста, введите дату в одном из указанных форматов.",
                parse_mode="HTML",
            )
            # Не очищаем состояние — ожидаем повторного ввода даты
            return
    else:
        # Текст не похож на дату - показываем примеры
        await message.reply(
            f"❌ <b>Введенный текст не похож на дату:</b> '{completion_date}'\n\n"
            f"<b>Примеры правильного ввода:</b>\n"
            f"• завтра\n"
            f"• через 3 дня\n"
            f"• через неделю\n"
            f"• 25.12.2025\n"
            f"• послезавтра в 15:00\n\n"
            f"Пожалуйста, введите дату в одном из указанных форматов.",
            parse_mode="HTML",
        )
        # Сохраняем текущее состояние, чтобы сообщение с корректной датой было обработано
        return

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            logger.error(f"[DR] Ошибка - Заявка не найдена: {order_id}")
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

        # Сохраняем данные в состоянии для подтверждения
        await state.update_data(
            completion_date=completion_date, prepayment_amount=prepayment_amount
        )

        # Показываем подтверждение длительного ремонта
        await show_dr_confirmation(message, state)

    except Exception as e:
        logger.exception(f"[DR] ❌ Error processing DR for order #{order_id}: {e}")
        await message.reply(
            "❌ Произошла ошибка при переводе заявки в длительный ремонт.\n"
            "Попробуйте еще раз или обратитесь к диспетчеру."
        )
        await state.clear()
    finally:
        await db.disconnect()
        logger.debug(f"[DR] DB disconnected for order #{order_id}")


@router.message(F.text == "📊 Моя статистика")
@handle_errors
async def btn_my_stats(message: Message, user_role: str):
    """
    Статистика мастера

    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    # Проверка роли
    if user_role not in [UserRole.MASTER, UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    # Проверяем, что это не личное сообщение (только для чистых мастеров)
    if message.chat.type == "private" and user_role == UserRole.MASTER:
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

        # Проверяем, что у мастера настроена рабочая группа
        if not master.work_chat_id:
            await message.answer(
                "❌ У вас не настроена рабочая группа!\n"
                "Обратитесь к администратору для настройки.",
                parse_mode="HTML",
            )
            return

        # Проверяем, что мастер работает в своей рабочей группе
        if message.chat.id != master.work_chat_id:
            await message.answer(
                "❌ Вы можете просматривать статистику только в своей рабочей группе!",
                parse_mode="HTML",
            )
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
            f"• ⏳ ДР: {dr}\n\n"
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
    # Добавляем логирование для отладки
    logger.info(
        f"[PROCESS_TOTAL_AMOUNT] Received message: '{message.text}' from user {message.from_user.id} in chat {message.chat.id}"
    )

    # Проверяем авторизацию ввода суммы относительно сохранённого контекста
    data_ctx = await state.get_data()
    initiator_user_id = data_ctx.get("initiator_user_id")
    allowed_chat_id = data_ctx.get("allowed_chat_id") or data_ctx.get("group_chat_id")
    acting_as_master_id = data_ctx.get("acting_as_master_id")
    prompt_message_id = data_ctx.get("prompt_message_id")

    # Проверка: разрешаем если сообщение:
    # 1. От инициатора процесса ИЛИ
    # 2. В нужном чате (где был запущен процесс) ИЛИ
    # 3. Это реплай на промпт-сообщение бота (для работы с ForceReply)
    is_sender_allowed = False

    # Проверка 1: от инициатора
    if initiator_user_id and message.from_user.id == initiator_user_id:
        is_sender_allowed = True

    # Проверка 2: в нужном чате
    if allowed_chat_id and message.chat and message.chat.id == allowed_chat_id:
        is_sender_allowed = True

    # Проверка 3: реплай на промпт-сообщение (для ForceReply)
    if prompt_message_id and message.reply_to_message:
        if message.reply_to_message.message_id == prompt_message_id:
            is_sender_allowed = True

    # Проверка 4: админ действует за мастера
    if acting_as_master_id and message.from_user.id == acting_as_master_id:
        is_sender_allowed = True

    if not is_sender_allowed:
        # Дополнительный допуск: администратор может вводить сумму из любого чата
        try:
            from app.database import Database as _LegacyDB
            from app.config import UserRole as _UserRole

            _db = _LegacyDB()
            await _db.connect()
            try:
                _user = await _db.get_user_by_telegram_id(message.from_user.id)
                if _user and _user.has_role(_UserRole.ADMIN):
                    is_sender_allowed = True
                    logger.info(
                        f"[PROCESS_TOTAL_AMOUNT] Admin override allowed for user {message.from_user.id}"
                    )
            finally:
                await _db.disconnect()
        except Exception:
            pass

    if not is_sender_allowed:
        logger.warning(
            f"[PROCESS_TOTAL_AMOUNT] Rejected message from user {message.from_user.id} in chat {message.chat.id}. "
            f"Context: initiator={initiator_user_id}, allowed_chat={allowed_chat_id}, acting_as={acting_as_master_id}"
        )
        await message.reply(
            "❌ Это сообщение не соответствует текущему шагу завершения заявки.\n"
            "Пожалуйста, нажмите 'Завершить заявку' ещё раз и отправьте сумму в том же чате, либо завершите через админ‑панель."
        )
        return

    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с суммой.\n"
            "Введите число (например: 5000, 5000.50 или 0):"
        )
        return

    # Нормализация пользовательского ввода: удаляем пробелы/валюту/прочие символы, заменяем запятую на точку
    raw_text = message.text.strip()
    # Удаляем неразрывные пробелы и обычные пробелы
    normalized = (
        raw_text.replace("\u00A0", "")
        .replace(" ", "")
        .replace("₽", "")
        .replace("р.", "")
        .replace("р", "")
        .replace("RUB", "")
        .replace("rub", "")
        .replace("\\", "")
    )
    # Разрешаем только цифры и разделители, остальные символы отбрасываем
    allowed_chars = set("0123456789.,")
    normalized = "".join(ch for ch in normalized if ch in allowed_chars)
    # Заменяем запятые на точки (русский формат)
    normalized = normalized.replace(",", ".")
    # Если осталось больше одной точки, пробуем убрать все, кроме последней (случай тысячных разделителей)
    if normalized.count(".") > 1:
        parts = normalized.split(".")
        normalized = "".join(parts[:-1]).replace(".", "") + "." + parts[-1]

    # Проверяем, что введена корректная сумма
    try:
        total_amount = float(normalized)
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

    # Если сумма 0 рублей, автоматически завершаем как отказ
    if total_amount == 0:
        # Устанавливаем значения по умолчанию для отказа
        await state.update_data(materials_cost=0.0, has_review=False, out_of_city=False)

        # Получаем данные из состояния
        data = await state.get_data()
        order_id = data.get("order_id")
        acting_as_master_id = data.get("acting_as_master_id")

        # Завершаем заказ как отказ
        await complete_order_as_refusal(message, state, order_id, acting_as_master_id)
        return

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
    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с суммой.\n"
            "Введите число (например: 500, 0):"
        )
        return

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

    # Переходим к подтверждению материалов
    await state.set_state(CompleteOrderStates.confirm_materials)

    from app.keyboards.inline import get_yes_no_keyboard

    await message.reply(
        f"💰 <b>Подтвердите сумму расходных материалов:</b>\n\n"
        f"Сумма: <b>{materials_cost:.2f} ₽</b>\n\n"
        f"Верно ли указана сумма?",
        parse_mode="HTML",
        reply_markup=get_yes_no_keyboard("confirm_materials", order_id),
    )


# ОТЛАДОЧНЫЙ ОБРАБОТЧИК - перехватывает ВСЕ callback'и с confirm_materials
@router.callback_query(lambda c: c.data.startswith("confirm_materials"))
async def debug_confirm_materials_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    ОТЛАДОЧНЫЙ обработчик для всех callback'ов с confirm_materials
    """
    logger.info("[DEBUG_MATERIALS] ===== CALLBACK INTERCEPTED =====")
    logger.info(f"[DEBUG_MATERIALS] Data: {callback_query.data}")
    logger.info(f"[DEBUG_MATERIALS] From user: {callback_query.from_user.id}")
    logger.info(f"[DEBUG_MATERIALS] Message ID: {callback_query.message.message_id}")
    logger.info(f"[DEBUG_MATERIALS] Chat ID: {callback_query.message.chat.id}")

    # Получаем текущее состояние FSM
    current_state = await state.get_state()
    logger.info(f"[DEBUG_MATERIALS] Current FSM state: {current_state}")

    # Получаем данные из FSM
    fsm_data = await state.get_data()
    logger.info(f"[DEBUG_MATERIALS] FSM data: {fsm_data}")

    # Парсим callback data
    from app.utils import parse_callback_data

    try:
        parsed_data = parse_callback_data(callback_query.data)
        action = parsed_data.get("action")
        params = parsed_data.get("params", [])
        order_id = params[0] if len(params) > 0 else None
        logger.info(
            f"[DEBUG_MATERIALS] Parsed - action: {action}, order_id: {order_id}, params: {params}"
        )
    except Exception as e:
        logger.error(f"[DEBUG_MATERIALS] Error parsing callback data: {e}")
        await callback_query.answer("❌ Ошибка обработки callback", show_alert=True)
        return

    # Отвечаем на callback
    await callback_query.answer()

    # Передаем управление основному обработчику
    await process_materials_confirmation_callback(callback_query, state)


@router.callback_query(lambda c: c.data.startswith("confirm_materials"))
async def process_materials_confirmation_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка подтверждения суммы материалов
    """
    logger.info(f"[MATERIALS_CONFIRM] Handler called with data: {callback_query.data}")

    from app.utils import parse_callback_data

    parsed_data = parse_callback_data(callback_query.data)
    action = parsed_data.get("action")
    params = parsed_data.get("params", [])
    answer = params[0] if len(params) > 0 else None  # yes/no
    order_id = params[1] if len(params) > 1 else None  # order_id
    logger.info(
        f"[MATERIALS_CONFIRM] Processing action: {action}, answer: {answer}, order_id: {order_id}"
    )

    if answer == "yes":
        # Подтверждаем сумму материалов и переходим к отзыву
        await state.set_state(CompleteOrderStates.confirm_review)
        logger.info(f"[MATERIALS_CONFIRM] State changed to confirm_review for order {order_id}")

        from app.keyboards.inline import get_yes_no_keyboard

        try:
            keyboard = get_yes_no_keyboard("confirm_review", order_id)
            logger.info(f"[MATERIALS_CONFIRM] Created keyboard: {keyboard}")

            await callback_query.message.edit_text(
                "✅ Сумма расходного материала подтверждена\n\n"
                "❓ <b>Взяли ли вы отзыв у клиента?</b>\n"
                "(За отзыв вы получите дополнительно +10% к прибыли)",
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            logger.info(f"[MATERIALS_CONFIRM] Message updated successfully for order {order_id}")
        except Exception as e:
            logger.exception(
                f"[MATERIALS_CONFIRM] Error updating message for order {order_id}: {e}"
            )
            await callback_query.answer("❌ Ошибка при обновлении сообщения", show_alert=True)
            return

    elif answer == "no":
        # Возвращаемся к вводу суммы материалов
        await state.set_state(CompleteOrderStates.enter_materials_cost)
        logger.info(
            f"[MATERIALS_CONFIRM] State changed to enter_materials_cost for order {order_id}"
        )

        try:
            await callback_query.message.edit_text(
                "💰 <b>Введите сумму расходного материала:</b>\n\n"
                "Введите число (например: 500, 0):",
                parse_mode="HTML",
                reply_markup=None,
            )
            logger.info(
                f"[MATERIALS_CONFIRM] Message updated for re-enter materials for order {order_id}"
            )
        except Exception as e:
            logger.exception(
                f"[MATERIALS_CONFIRM] Error updating message for re-enter materials for order {order_id}: {e}"
            )
            await callback_query.answer("❌ Ошибка при обновлении сообщения", show_alert=True)
            return

    await callback_query.answer()


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
    answer = callback_data["params"][0] if len(callback_data["params"]) > 0 else None  # yes/no
    order_id = callback_data["params"][1] if len(callback_data["params"]) > 1 else None  # order_id

    # Определяем ответ
    has_review = answer == "yes"

    # Сохраняем ответ об отзыве
    await state.update_data(has_review=has_review)

    # Переходим к запросу выезда за город
    await state.set_state(CompleteOrderStates.confirm_out_of_city)

    review_text = "✅ Отзыв взят!" if has_review else "❌ Отзыв не взят"

    from app.keyboards.inline import get_yes_no_keyboard

    # Получаем order_id из состояния, так как в callback data он может быть перепутан
    data = await state.get_data()
    order_id_from_state = data.get("order_id")

    await callback_query.message.edit_text(
        f"{review_text}\n\n"
        f"🚗 <b>Был ли выезд за город?</b>\n"
        f"(За выезд за город вы получите дополнительно +10% к прибыли)",
        parse_mode="HTML",
        reply_markup=get_yes_no_keyboard("confirm_out_of_city", order_id_from_state),
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
    answer = callback_data["params"][0] if len(callback_data["params"]) > 0 else None  # yes/no
    order_id = callback_data["params"][1] if len(callback_data["params"]) > 1 else None  # order_id

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

    # Получаем order_id из состояния, так как в callback data он может быть перепутан
    data = await state.get_data()
    order_id_from_state = data.get("order_id")

    try:
        order = await db.get_order_by_id(order_id_from_state)

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
            order_id=order_id_from_state,
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
            order_id=order_id_from_state,
            status=OrderStatus.CLOSED,
            changed_by=callback_query.from_user.id,
            user_roles=user_roles,  # Передаём роли для валидации
        )

        # Создаем отчет по заказу
        try:
            from app.services.order_reports import OrderReportsService

            order_reports_service = OrderReportsService()

            # Получаем актуальные данные заказа
            updated_order = await db.get_order_by_id(order_id_from_state)

            # Получаем данные диспетчера
            dispatcher = None
            if updated_order.dispatcher_id:
                dispatcher = await db.get_user_by_telegram_id(updated_order.dispatcher_id)

            # Создаем запись в отчете
            await order_reports_service.create_order_report(updated_order, master, dispatcher)
            logger.info(f"Order report created for order #{order_id_from_state}")

        except Exception as e:
            logger.error(f"Не удалось создать отчет для заявки #{order_id_from_state}: {e}")

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback_query.from_user.id,
            action="COMPLETE_ORDER",
            details=f"Completed order #{order_id_from_state}, total: {total_amount}, materials: {materials_cost}",
        )

        # ✨ УВЕДОМЛЕНИЕ ДИСПЕТЧЕРА О ЗАКРЫТИИ ЗАЯВКИ
        if order.dispatcher_id:
            from app.utils import safe_send_message

            notification_text = (
                f"✅ <b>Заявка завершена!</b>\n\n"
                f"📋 <b>Заявка #{order_id_from_state}</b>\n"
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
                    f"Failed to notify dispatcher {order.dispatcher_id} about order #{order_id_from_state} completion"
                )
            else:
                logger.info(
                    f"Dispatcher {order.dispatcher_id} notified about order #{order_id_from_state} completion"
                )

        # Формируем текст подтверждения
        out_of_city_text = "🚗 Да" if out_of_city else "❌ Нет"
        review_text = "⭐ Да" if has_review else "❌ Нет"

        # Обновляем сообщение с результатами
        await callback_query.message.edit_text(
            f"✅ <b>Заявка #{order_id_from_state} завершена!</b>\n\n"
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
        logger.error(f"Ошибка при завершении заявки #{order_id_from_state}: {e}")
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
@handle_errors
async def btn_settings_master(message: Message, user_role: str):
    """
    Обработчик кнопки настроек для мастеров

    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    # Проверка роли
    if user_role not in [UserRole.MASTER, UserRole.ADMIN, UserRole.DISPATCHER]:
        return

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
            f"<i>Например: завтра 14:00, сегодня 18:00, через 3 часа</i>",
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
    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с новой датой.\n"
            "Примеры: завтра в 15:00, через 3 дня, 25.10.2025 14:00"
        )
        return

    new_time = message.text.strip()

    # Попытка автоопределения даты
    from app.utils import (
        format_datetime_user_friendly,
        parse_natural_datetime,
        should_parse_as_date,
    )

    if should_parse_as_date(new_time):
        parsed_dt, _ = parse_natural_datetime(new_time, validate=True)

        if parsed_dt:
            # Успешно распознали дату
            user_friendly = format_datetime_user_friendly(parsed_dt, new_time)

            # Сохраняем распознанную дату и причину (None - причина не нужна)
            await state.update_data(new_scheduled_time=user_friendly, reschedule_reason=None)

            # Сразу переходим к подтверждению
            await show_reschedule_confirmation(message, state)
            return
        else:
            # Не смогли распознать дату - переспрашиваем с примерами
            await message.reply(
                f"❓ <b>Не удалось распознать дату:</b> {new_time}\n\n"
                f"<b>Пожалуйста, укажите дату в одном из форматов:</b>\n\n"
                f"<b>🤖 Автоопределение даты:</b>\n"
                f"• <code>завтра в 15:00</code>\n"
                f"• <code>послезавтра 14:30</code>\n"
                f"• <code>через 3 дня 15:00</code>\n"
                f"• <code>через неделю 12:00</code>\n\n"
                f"<b>⏱ Через часы/дни:</b>\n"
                f"• <code>через полтора часа</code>\n"
                f"• <code>через 1-1.5 часа</code>\n"
                f"• <code>через 3 дня</code>\n\n"
                f"<b>📅 Точная дата:</b>\n"
                f"• <code>20.10.2025 14:00</code>\n"
                f"• <code>25/10/2025 09:30</code>\n\n"
                f"<b>📝 Или просто текст:</b>\n"
                f"• <code>Набрать клиенту</code>\n"
                f"• <code>Уточнить время</code>",
                parse_mode="HTML",
            )
            return

    # Если не похоже на дату - проверяем, не является ли это простой цифрой
    if re.match(r"^\d{1,2}$", new_time.strip()):
        # Простая цифра - показываем примеры
        await message.reply(
            f"❌ <b>Введенный текст не похож на дату:</b> '{new_time}'\n\n"
            f"<b>Примеры правильного ввода:</b>\n"
            f"• завтра в 15:00\n"
            f"• через 3 дня\n"
            f"• через неделю\n"
            f"• 25.12.2025\n"
            f"• послезавтра в 15:00\n\n"
            f"Пожалуйста, введите дату в одном из указанных форматов.",
            parse_mode="HTML",
        )
        return

    # Если не цифра - сохраняем как есть (текстовая инструкция)
    await state.update_data(new_scheduled_time=new_time, reschedule_reason=None)

    # Сразу переходим к подтверждению
    await show_reschedule_confirmation(message, state)


@router.message(RescheduleOrderStates.enter_reason)
async def process_reschedule_reason(message: Message, state: FSMContext):
    """
    Обработка ввода причины переноса и переход к подтверждению

    Args:
        message: Сообщение
        state: FSM контекст
    """
    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с причиной переноса.\n"
            'Или отправьте "-" если причины нет.'
        )
        return

    reason = message.text.strip()

    # Если пользователь указал "-", причины нет
    if reason == "-":
        reason = None

    # Сохраняем причину
    await state.update_data(reschedule_reason=reason)

    # Получаем данные из state
    data = await state.get_data()
    order_id = data.get("order_id")
    new_time = data.get("new_scheduled_time")
    initiated_by = data.get("reschedule_initiated_by")

    # Показываем подтверждение переноса
    await show_reschedule_confirmation(message, state)


async def show_reschedule_confirmation(message: Message, state: FSMContext):
    """
    Показать подтверждение переноса заявки
    """
    data = await state.get_data()
    order_id = data.get("order_id")
    new_time = data.get("new_scheduled_time")
    reason = data.get("reschedule_reason")

    # Получаем информацию о заявке
    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        if not order:
            await message.reply("❌ Ошибка: заявка не найдена")
            return

        old_time = order.scheduled_time or "не указано"

        # Формируем текст подтверждения
        text = (
            f"📅 <b>Подтверждение переноса заявки #{order_id}</b>\n\n"
            f"🔧 <b>Тип техники:</b> {order.equipment_type}\n"
            f"👤 <b>Клиент:</b> {order.client_name}\n"
            f"📍 <b>Адрес:</b> {order.client_address}\n\n"
            f"⏰ <b>Было:</b> {old_time}\n"
            f"⏰ <b>Стало:</b> {new_time}\n"
        )

        if reason:
            text += f"\n📝 <b>Причина:</b> {reason}"

        text += "\n\nПодтвердите перенос заявки:"

        # Переходим к состоянию подтверждения
        await state.set_state(RescheduleOrderStates.confirm)

        # Показываем подтверждение с клавиатурой
        from app.keyboards.reply import get_reschedule_confirm_keyboard

        await message.answer(
            text, parse_mode="HTML", reply_markup=get_reschedule_confirm_keyboard()
        )

    finally:
        await db.disconnect()


@router.message(RescheduleOrderStates.confirm)
async def handle_reschedule_confirm(message: Message, state: FSMContext):
    """
    Обработка подтверждения переноса заявки
    """
    if message.text == "✅ Подтвердить перенос":
        await confirm_reschedule_order(message, state)
    elif message.text == "❌ Отмена":
        # Определяем роль пользователя (может быть ADMIN или MASTER)
        from app.database import Database
        from app.keyboards.reply import get_main_menu_keyboard

        db_role = Database()
        await db_role.connect()
        try:
            user = await db_role.get_user_by_telegram_id(message.from_user.id)
            user_role = user.role if user else "MASTER"
        finally:
            await db_role.disconnect()
        await message.answer(
            "❌ Перенос заявки отменен.", reply_markup=get_main_menu_keyboard(user_role)
        )
        await state.clear()
    else:
        # Если введен текст, обрабатываем как изменение времени
        await state.set_state(RescheduleOrderStates.enter_new_time)
        await process_reschedule_new_time(message, state)


async def confirm_reschedule_order(message: Message, state: FSMContext):
    """
    Подтверждение и выполнение переноса заявки
    """
    data = await state.get_data()
    order_id = data.get("order_id")
    new_time = data.get("new_scheduled_time")
    reason = data.get("reschedule_reason")
    initiated_by = data.get("reschedule_initiated_by")

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        if not order:
            await message.reply("❌ Ошибка: заявка не найдена")
            return

        old_time = order.scheduled_time or "не указано"

        # Обновляем заявку
        async with db.get_session() as session:
            from sqlalchemy import text

            await session.execute(
                text(
                    """
                UPDATE orders
                SET scheduled_time = :new_time,
                    rescheduled_count = rescheduled_count + 1,
                    last_rescheduled_at = :last_rescheduled_at,
                    reschedule_reason = :reason,
                    updated_at = :updated_at
                WHERE id = :order_id
                """
                ),
                {
                    "new_time": new_time,
                    "last_rescheduled_at": get_now(),
                    "reason": reason,
                    "updated_at": get_now(),
                    "order_id": order_id,
                },
            )

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

        # Убираем клавиатуру после подтверждения и возвращаем главное меню
        from app.keyboards.reply import get_main_menu_keyboard

        # Определяем роль пользователя (может быть ADMIN или MASTER)
        user = await db.get_user_by_telegram_id(message.from_user.id)
        user_role = user.role if user else "MASTER"
        await message.answer(
            result_text, parse_mode="HTML", reply_markup=get_main_menu_keyboard(user_role)
        )

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
                logger.error(f"Не удалось уведомить диспетчера {order.dispatcher_id}: {e}")

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


async def show_dr_confirmation(message: Message, state: FSMContext):
    """
    Показать подтверждение перевода в длительный ремонт
    """
    data = await state.get_data()
    order_id = data.get("order_id")
    completion_date = data.get("completion_date")
    prepayment_amount = data.get("prepayment_amount")

    # Получаем информацию о заявке
    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        if not order:
            await message.reply("❌ Ошибка: заявка не найдена")
            return

        # Формируем текст подтверждения
        text = (
            f"📋 <b>Подтверждение перевода в длительный ремонт</b>\n\n"
            f"🔧 <b>Тип техники:</b> {order.equipment_type}\n"
            f"👤 <b>Клиент:</b> {order.client_name}\n"
            f"📍 <b>Адрес:</b> {order.client_address}\n\n"
            f"⏰ <b>Примерный срок завершения:</b> {completion_date}\n"
        )

        if prepayment_amount:
            text += f"💰 <b>Предоплата:</b> {prepayment_amount:.2f} ₽\n"
        else:
            text += "💰 <b>Предоплата:</b> не указана\n"

        text += (
            "\n⚠️ <b>Внимание:</b> После подтверждения заявка будет переведена в статус "
            "'ДР' и диспетчер получит уведомление.\n\n"
            "Подтвердите перевод в длительный ремонт:"
        )

        # Переходим к состоянию подтверждения
        await state.set_state(LongRepairStates.confirm_dr)

        # Показываем подтверждение с клавиатурой
        from app.keyboards.reply import get_dr_confirm_keyboard

        await message.answer(text, parse_mode="HTML", reply_markup=get_dr_confirm_keyboard())

    finally:
        await db.disconnect()


@router.message(LongRepairStates.confirm_dr)
async def handle_dr_confirm(message: Message, state: FSMContext):
    """
    Обработка подтверждения перевода в длительный ремонт
    """
    if message.text == "✅ Подтвердить перевод":
        await confirm_dr_translation(message, state)
    elif message.text == "❌ Отмена":
        await message.answer(
            "❌ Перевод в длительный ремонт отменен.", reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()

        # Показываем главное меню
        db = Database()
        await db.connect()
        try:
            user = await db.get_user_by_telegram_id(message.from_user.id)
            if user:
                user_roles = user.get_roles()
                menu_keyboard = await get_menu_with_counter(user_roles)
                await message.answer(
                    "🏠 <b>Главное меню</b>", parse_mode="HTML", reply_markup=menu_keyboard
                )
        finally:
            await db.disconnect()
    else:
        # Если введен текст, обрабатываем как изменение даты
        await state.set_state(LongRepairStates.enter_completion_date_and_prepayment)
        await process_dr_info(message, state, [])


async def confirm_dr_translation(message: Message, state: FSMContext):
    """
    Подтверждение и выполнение перевода в длительный ремонт
    """
    data = await state.get_data()
    order_id = data.get("order_id")
    completion_date = data.get("completion_date")
    prepayment_amount = data.get("prepayment_amount")

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        if not order:
            await message.reply("❌ Ошибка: заявка не найдена")
            return

        # Обновляем заявку
        async with db.get_session() as session:
            from sqlalchemy import text

            await session.execute(
                text(
                    """
                UPDATE orders
                SET status = :status,
                    estimated_completion_date = :completion_date,
                    prepayment_amount = :prepayment_amount,
                    updated_at = :updated_at
                WHERE id = :order_id
                """
                ),
                {
                    "status": OrderStatus.DR,
                    "completion_date": completion_date,
                    "prepayment_amount": prepayment_amount,
                    "updated_at": get_now(),
                    "order_id": order_id,
                },
            )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=message.from_user.id,
            action="LONG_REPAIR_ORDER",
            details=f"Order #{order_id} translated to long repair. Completion: {completion_date}, Prepayment: {prepayment_amount or 'none'}",
        )

        # Форматируем дату с расчетом дней для отображения
        from app.utils.date_parser import format_estimated_completion_with_days
        
        completion_date_formatted = format_estimated_completion_with_days(completion_date)
        
        # Формируем сообщение с результатом
        result_text = (
            f"✅ <b>Заявка #{order_id} переведена в длительный ремонт</b>\n\n"
            f"⏰ <b>Срок завершения:</b> {completion_date_formatted}\n"
        )

        if prepayment_amount:
            result_text += f"💰 <b>Предоплата:</b> {prepayment_amount:.2f} ₽\n"

        result_text += "\n<i>Диспетчер уведомлен</i>"

        # Отправляем результат и удаляем клавиатуру
        await message.reply(result_text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())

        # Очищаем состояние FSM
        await state.clear()

        # Получаем роли пользователя и показываем главное меню
        user = await db.get_user_by_telegram_id(message.from_user.id)
        if user:
            user_roles = user.get_roles()
            menu_keyboard = await get_menu_with_counter(user_roles)
            await message.answer(
                "🏠 <b>Главное меню</b>", parse_mode="HTML", reply_markup=menu_keyboard
            )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            master = await db.get_master_by_telegram_id(message.from_user.id)
            master_name = master.get_display_name() if master else f"ID: {message.from_user.id}"

            # Форматируем дату с расчетом дней для отображения
            from app.utils.date_parser import format_estimated_completion_with_days
            
            completion_date_formatted = format_estimated_completion_with_days(completion_date)
            
            notification = (
                f"🔧 <b>Заявка #{order_id} переведена в длительный ремонт</b>\n\n"
                f"👨‍🔧 {master_name}\n"
                f"👤 {order.client_name} - {order.client_phone}\n"
                f"🔧 {order.equipment_type}\n\n"
                f"⏰ <b>Срок завершения:</b> {completion_date_formatted}\n"
            )

            if prepayment_amount:
                notification += f"💰 <b>Предоплата:</b> {prepayment_amount:.2f} ₽\n"

            notification += "\n💡 Свяжитесь с клиентом для подтверждения"

            try:
                await message.bot.send_message(order.dispatcher_id, notification, parse_mode="HTML")
                logger.info(f"DR notification sent to dispatcher {order.dispatcher_id}")
            except Exception as e:
                logger.error(f"Не удалось уведомить диспетчера {order.dispatcher_id}: {e}")

        log_action(message.from_user.id, "LONG_REPAIR_ORDER", f"Order #{order_id}")
        logger.info(f"✅ Order #{order_id} successfully translated to long repair")

    except Exception as e:
        logger.exception(f"❌ Error translating order #{order_id} to long repair: {e}")
        await message.reply(
            "❌ Произошла ошибка при переводе заявки в длительный ремонт.\n"
            "Попробуйте еще раз или обратитесь к диспетчеру."
        )
    finally:
        await db.disconnect()


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


async def complete_order_as_refusal(
    message: Message, state: FSMContext, order_id: int, user_telegram_id: int = None
):
    """
    Завершение заказа как отказ (для заявок в 0 рублей)

    Args:
        message: Сообщение
        state: FSM контекст
        order_id: ID заказа
        acting_as_master_id: ID мастера, если админ действует от его имени
    """
    from app.config import OrderStatus
    from app.utils.helpers import calculate_profit_split

    db = Database()
    await db.connect()

    try:
        logger.info(f"[REFUSE] Database type: {type(db).__name__}")
        logger.info(
            f"[REFUSE] Looking for order_id: {order_id}, user_telegram_id: {user_telegram_id}"
        )
        order = await db.get_order_by_id(order_id)
        logger.info(f"[REFUSE] Found order: {order}")

        if not order:
            await message.reply("❌ Ошибка: заявка не найдена.")
            return

        # Используем переданный ID пользователя
        telegram_id = user_telegram_id or message.from_user.id
        logger.info(f"[REFUSE] Looking for master with telegram_id: {telegram_id}")

        master = await db.get_master_by_telegram_id(telegram_id)
        logger.info(f"[REFUSE] Found master: {master}")

        if not master:
            # Дополнительная диагностика - проверим, есть ли пользователь в системе
            try:
                user = await db.get_user_by_telegram_id(telegram_id)
                logger.info(f"[REFUSE] User in system: {user}")

                all_masters = await db.get_all_masters()
                logger.info(f"[REFUSE] Total masters in DB: {len(all_masters)}")
                for m in all_masters:
                    logger.info(f"[REFUSE] Master: id={m.id}, telegram_id={m.telegram_id}")
            except Exception as e:
                logger.error(f"[REFUSE] Ошибка получения пользователя/мастеров: {e}")

            if not user:
                await message.reply(
                    "❌ Ошибка: вы не зарегистрированы в системе. Обратитесь к администратору."
                )
            else:
                await message.reply(
                    "❌ Ошибка: вы не зарегистрированы как мастер. Обратитесь к администратору для регистрации."
                )
            return

        # Проверяем, что заявка назначена на этого мастера
        logger.info(
            f"[REFUSE] Order assigned_master_id: {order.assigned_master_id}, master.id: {master.id}"
        )
        if order.assigned_master_id != master.id:
            await message.reply("❌ Ошибка: заявка не назначена на этого мастера.")
            return

        # Устанавливаем все суммы в 0
        total_amount = 0.0
        materials_cost = 0.0
        has_review = False
        out_of_city = False

        # Рассчитываем распределение прибыли (все будет 0)
        master_profit, company_profit = calculate_profit_split(
            total_amount, materials_cost, has_review, out_of_city
        )

        # Обновляем суммы в базе данных
        await db.update_order_amounts(
            order_id=order_id,
            total_amount=total_amount,
            materials_cost=materials_cost,
            master_profit=master_profit,
            company_profit=company_profit,
            has_review=has_review,
            out_of_city=out_of_city,
        )

        # Обновляем статус на REFUSED (отказ)
        await db.update_order_status(
            order_id=order_id,
            status=OrderStatus.REFUSED,
            changed_by=message.from_user.id,
            user_roles=["MASTER"],  # Мастер завершает заказ
        )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=message.from_user.id,
            action="COMPLETE_ORDER_AS_REFUSAL",
            details=f"Order #{order_id} completed as refusal (0 rubles)",
        )

        # Очищаем состояние FSM
        await state.clear()

        # Отправляем подтверждение
        await message.reply(
            f"❌ <b>Заявка #{order_id} завершена как отказ</b>\n\n"
            f"💰 Сумма заказа: 0.00 ₽\n"
            f"📋 Статус: Отказ\n\n"
            f"Заявка автоматически помечена как отказ, так как сумма составляет 0 рублей.",
            parse_mode="HTML",
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            from app.utils import safe_send_message

            result = await safe_send_message(
                message.bot,
                order.dispatcher_id,
                f"❌ Заявка #{order_id} завершена как отказ\n"
                f"Мастер: {master.get_display_name()}\n"
                f"Причина: Сумма заказа 0 рублей",
                parse_mode="HTML",
            )
            if not result:
                logger.error(f"Не удалось уведомить диспетчера {order.dispatcher_id} об отказе")

        logger.info(f"Order #{order_id} completed as refusal by master {master.id}")

    except Exception as e:
        logger.exception(f"Error completing order #{order_id} as refusal: {e}")
        await message.reply("❌ Ошибка при завершении заявки как отказ")
    finally:
        await db.disconnect()


@router.callback_query(lambda c: c.data.startswith("confirm_refuse"))
async def process_refuse_confirmation_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка подтверждения отказа от заявки

    Args:
        callback_query: Callback query
        state: FSM контекст
    """
    # Извлекаем данные из callback_data
    parts = callback_query.data.split(":")
    action = parts[1]  # "yes" или "no"
    order_id = int(parts[2])

    logger.info(
        f"[REFUSE] Callback data: {callback_query.data}, action: {action}, order_id: {order_id}"
    )

    if action == "yes":
        # Подтверждаем отказ
        data = await state.get_data()
        logger.info(f"[REFUSE] FSM data: {data}")
        order_id = data.get("order_id", order_id)
        logger.info(f"[REFUSE] Final order_id: {order_id}")

        # Завершаем заказ как отказ
        await complete_order_as_refusal(
            callback_query.message, state, order_id, callback_query.from_user.id
        )

        # Очищаем состояние
        await state.clear()

        await callback_query.answer("Заявка отклонена")
    else:
        # Отменяем отказ - получаем заказ для клавиатуры
        db = Database()
        await db.connect()
        try:
            order = await db.get_order_by_id(order_id)
            if order:
                await callback_query.message.edit_text(
                    "❌ Отказ отменен.\n\nЗаявка остается активной.",
                    reply_markup=get_order_actions_keyboard(order, UserRole.MASTER),
                )
            else:
                await callback_query.message.edit_text("❌ Отказ отменен.\n\nЗаявка не найдена.")
        finally:
            await db.disconnect()
        await state.clear()
        await callback_query.answer("Отказ отменен")


def validate_dr_completion_date(parsed_dt, original_text: str) -> dict:
    """
    Строгая валидация даты завершения длительного ремонта

    Args:
        parsed_dt: Распознанная дата
        original_text: Исходный текст

    Returns:
        dict: {"valid": bool, "error": str, "warning": str}
    """
    from datetime import timedelta

    from app.utils import get_now

    now = get_now()
    tomorrow = now + timedelta(days=1)
    max_date = now + timedelta(days=180)  # 6 месяцев

    # Проверяем, что дата не в прошлом
    if parsed_dt.date() < tomorrow.date():
        return {
            "valid": False,
            "error": f"Дата завершения ремонта не может быть раньше завтра ({tomorrow.strftime('%d.%m.%Y')})",
        }

    # Проверяем, что дата не слишком далеко в будущем
    if parsed_dt.date() > max_date.date():
        return {
            "valid": False,
            "error": f"Дата завершения ремонта не может быть позже чем через 6 месяцев ({max_date.strftime('%d.%m.%Y')})",
        }

    # Проверяем разумность срока (не менее 1 дня, не более 6 месяцев)
    days_difference = (parsed_dt.date() - now.date()).days

    warnings = []

    # Предупреждения для необычных сроков
    if days_difference < 3:
        warnings.append("Очень короткий срок для длительного ремонта")
    elif days_difference > 90:
        warnings.append("Очень длительный срок ремонта - убедитесь в корректности")

    # Проверяем на выходные дни
    if parsed_dt.weekday() >= 5:  # Суббота или воскресенье
        warnings.append("Дата завершения выпадает на выходной день")

    return {"valid": True, "warning": "; ".join(warnings) if warnings else None}


def validate_dr_prepayment(amount: float) -> dict:
    """
    Валидация предоплаты для длительного ремонта

    Args:
        amount: Сумма предоплаты

    Returns:
        dict: {"valid": bool, "error": str, "warning": str}
    """
    # Проверяем, что сумма положительная
    if amount <= 0:
        return {"valid": False, "error": "Сумма предоплаты должна быть больше 0"}

    # Проверяем разумность суммы
    if amount < 100:
        return {"valid": False, "error": "Сумма предоплаты слишком мала (минимум 100 ₽)"}

    if amount > 100000:
        return {"valid": False, "error": "Сумма предоплаты слишком велика (максимум 100,000 ₽)"}

    warnings = []

    # Предупреждения для необычных сумм
    if amount > 50000:
        warnings.append("Очень большая сумма предоплаты - убедитесь в корректности")

    return {"valid": True, "warning": "; ".join(warnings) if warnings else None}


@router.callback_query(F.data.startswith("complete_dr_order:"))
async def callback_complete_dr_order(callback: CallbackQuery, state: FSMContext):
    """
    Завершение заявки в статусе DR (длительный ремонт)

    Args:
        callback: Callback query
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[1])

    logger.info(
        f"[COMPLETE_DR] Starting completion process for DR order #{order_id} by user {callback.from_user.id}"
    )

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        # Проверяем, что заявка действительно в статусе DR
        if order.status != OrderStatus.DR:
            await callback.answer("Эта заявка не в статусе длительного ремонта", show_alert=True)
            return

        # Сохраняем контекст завершения в FSM
        await state.update_data(
            order_id=order_id,
            initiator_user_id=callback.from_user.id,
            allowed_chat_id=callback.message.chat.id,
        )

        # Переходим в состояние запроса общей суммы
        from app.states import CompleteOrderStates

        await state.set_state(CompleteOrderStates.enter_total_amount)

        # В ЛС открываем ForceReply, чтобы у пользователя автоматически включился режим ответа
        from aiogram.types import ForceReply

        prompt = await callback.message.answer(
            f"💰 <b>Завершение длительного ремонта #{order_id}</b>\n\n"
            f"Пожалуйста, введите <b>общую сумму заказа</b> (в рублях):\n"
            f"Например: 5000, 5000.50 или 0",
            parse_mode="HTML",
            reply_markup=ForceReply(selective=True, input_field_placeholder="Введите сумму…"),
        )

        await state.update_data(prompt_message_id=prompt.message_id)

        log_action(callback.from_user.id, "START_COMPLETE_DR_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer()
