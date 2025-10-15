"""
Обработчики для взаимодействия с заказами в группах
"""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import OrderStatus, UserRole
from app.core.constants import GROUP_ANONYMOUS_BOT_ID
from app.database import Database
from app.filters import IsGroupChat, IsGroupOrderCallback, IsMasterInGroup
from app.keyboards.inline import get_group_order_keyboard
from app.utils import format_datetime, get_now, log_action


logger = logging.getLogger(__name__)

router = Router(name="group_interaction")


async def get_master_from_callback(callback: CallbackQuery, db: Database):
    """
    Получение мастера из callback (поддержка анонимных админов)
    
    Args:
        callback: Callback query
        db: Database instance
        
    Returns:
        Tuple[Master | None, bool]: (master, is_anonymous_admin)
    """
    user_id = callback.from_user.id
    
    # Проверяем, является ли пользователь анонимным админом
    if user_id == GROUP_ANONYMOUS_BOT_ID:
        # Анонимный админ - ищем мастера по ID группы
        master = await db.get_master_by_work_chat_id(callback.message.chat.id)
        if master:
            logger.info(f"Анонимный админ работает в группе мастера {master.get_display_name()}")
            return master, True
        else:
            logger.warning(f"Не найден мастер для группы {callback.message.chat.id}")
            return None, True
    else:
        # Обычный пользователь - ищем по telegram_id
        master = await db.get_master_by_telegram_id(user_id)
        
        # Если мастер не найден, проверяем, может это админ
        if not master:
            # Проверяем, является ли пользователь админом
            user = await db.get_user_by_telegram_id(user_id)
            if user and user.role == UserRole.ADMIN:
                # Админ работает в группе - ищем мастера по группе
                master = await db.get_master_by_work_chat_id(callback.message.chat.id)
                if master:
                    logger.info(f"Админ {user.first_name} работает в группе мастера {master.get_display_name()}")
                    return master, False
        
        return master, False


async def check_master_work_group(master, callback: CallbackQuery) -> bool:
    """
    Проверка, что у мастера настроена рабочая группа и он работает в ней
    
    Args:
        master: Объект мастера
        callback: Callback query
        
    Returns:
        True если проверка пройдена, False если нет
    """
    # Проверяем наличие рабочей группы
    if not master.work_chat_id:
        await callback.answer(
            "❌ У вас не настроена рабочая группа!\n"
            "Обратитесь к администратору для настройки.",
            show_alert=True
        )
        return False
    
    # Проверяем, что действие выполняется в правильной группе
    if callback.message.chat.id != master.work_chat_id:
        await callback.answer(
            "❌ Вы можете работать только в своей рабочей группе!",
            show_alert=True
        )
        return False
    
    return True


@router.callback_query(F.data.startswith("group_accept_order:"))
async def callback_group_accept_order(callback: CallbackQuery):
    """
    Принятие заявки мастером, админом или анонимным админом в группе

    Args:
        callback: Callback query
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        
        # Получаем мастера (с поддержкой анонимных админов)
        master, is_anonymous = await get_master_from_callback(callback, db)
        
        if not master:
            await callback.answer(
                "❌ Не удалось определить мастера для этой группы.\n"
                "Убедитесь, что у мастера настроена эта группа как рабочая.",
                show_alert=True
            )
            return
        
        # Проверяем рабочую группу (если это не анонимный админ)
        if not is_anonymous:
            if not await check_master_work_group(master, callback):
                return

        # Проверяем права на заявку
        if order.assigned_master_id != master.id:
            await callback.answer("Это не заявка для вашей группы", show_alert=True)
            return

        # Обновляем статус
        await db.update_order_status(
            order_id, OrderStatus.ACCEPTED, changed_by=callback.from_user.id
        )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ACCEPT_ORDER_GROUP",
            details=f"Accepted order #{order_id} in group",
        )

        # Формируем текст с деталями заявки
        acceptance_text = (
            f"✅ <b>Заявка #{order_id} принята!</b>\n\n"
            f"👨‍🔧 Мастер: {master.get_display_name()}\n"
            f"📋 Статус: {OrderStatus.get_status_name(OrderStatus.ACCEPTED)}\n"
            f"⏰ Время принятия: {format_datetime(get_now())}\n\n"
            f"🔧 <b>Детали заявки:</b>\n"
            f"📱 Тип техники: {order.equipment_type}\n"
            f"📝 Описание: {order.description}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n"
            f"📞 Телефон: <i>Будет доступен после прибытия на объект</i>\n"
        )
        
        # Добавляем заметки если есть
        if order.notes:
            acceptance_text += f"\n📝 <b>Заметки:</b> {order.notes}\n"
        
        # Добавляем время прибытия если указано
        if order.scheduled_time:
            acceptance_text += f"\n⏰ <b>Время прибытия к клиенту:</b> {order.scheduled_time}\n"
        
        acceptance_text += f"\n<b>Когда будете на объекте, нажмите кнопку ниже.</b>"
        
        # Обновляем сообщение в группе
        await callback.message.edit_text(
            acceptance_text,
            parse_mode="HTML",
            reply_markup=get_group_order_keyboard(order, OrderStatus.ACCEPTED),
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"✅ Мастер {master.get_display_name()} принял заявку #{order_id} в группе",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        log_action(callback.from_user.id, "ACCEPT_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Заявка принята!")


@router.callback_query(F.data.startswith("group_refuse_order:"))
async def callback_group_refuse_order(callback: CallbackQuery):
    """
    Отклонение заявки мастером, админом или анонимным админом в группе

    Args:
        callback: Callback query
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        
        # Получаем мастера (с поддержкой анонимных админов)
        master, is_anonymous = await get_master_from_callback(callback, db)
        
        if not master:
            await callback.answer(
                "❌ Не удалось определить мастера для этой группы.\n"
                "Убедитесь, что у мастера настроена эта группа как рабочая.",
                show_alert=True
            )
            return
        
        # Проверяем рабочую группу (если это не анонимный админ)
        if not is_anonymous:
            if not await check_master_work_group(master, callback):
                return

        # Проверяем права
        if order.assigned_master_id != master.id:
            await callback.answer("Это не заявка для вашей группы", show_alert=True)
            return

        # Возвращаем статус в NEW и убираем мастера
        await db.connection.execute(
            "UPDATE orders SET status = ?, assigned_master_id = NULL WHERE id = ?",
            (OrderStatus.NEW, order_id),
        )
        await db.connection.commit()

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="REFUSE_ORDER_GROUP",
            details=f"Master refused order #{order_id} in group",
        )

        # Обновляем сообщение в группе (номер телефона скрыт, т.к. заявка отклонена до прибытия на объект)
        await callback.message.edit_text(
            f"❌ <b>Заявка #{order_id} отклонена</b>\n\n"
            f"👨‍🔧 Мастер: {master.get_display_name()}\n"
            f"📋 Статус: Требует нового назначения\n"
            f"⏰ Время отклонения: {format_datetime(get_now())}\n\n"
            f"🔧 <b>Детали заявки:</b>\n"
            f"📱 Тип техники: {order.equipment_type}\n"
            f"📝 Описание: {order.description}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n\n"
            f"Диспетчер получил уведомление для назначения другого мастера.",
            parse_mode="HTML",
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"❌ Мастер {master.get_display_name()} отклонил заявку #{order_id} в группе\n"
                    f"Необходимо назначить другого мастера.",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        log_action(callback.from_user.id, "REFUSE_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Заявка отклонена")


@router.callback_query(F.data.startswith("group_onsite_order:"))
async def callback_group_onsite_order(callback: CallbackQuery):
    """
    Мастер на объекте (поддержка анонимных админов)

    Args:
        callback: Callback query
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        
        # Получаем мастера (с поддержкой анонимных админов)
        master, is_anonymous = await get_master_from_callback(callback, db)
        
        if not master:
            await callback.answer(
                "❌ Не удалось определить мастера для этой группы.\n"
                "Убедитесь, что у мастера настроена эта группа как рабочая.",
                show_alert=True
            )
            return
        
        # Проверяем рабочую группу (если это не анонимный админ)
        if not is_anonymous:
            if not await check_master_work_group(master, callback):
                return

        # Проверяем права
        if order.assigned_master_id != master.id:
            await callback.answer("Это не заявка для вашей группы", show_alert=True)
            return

        # Обновляем статус
        await db.update_order_status(
            order_id, OrderStatus.ONSITE, changed_by=callback.from_user.id
        )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ONSITE_ORDER_GROUP",
            details=f"Master on site for order #{order_id} in group",
        )

        # Обновляем сообщение в группе
        await callback.message.edit_text(
            f"🏠 <b>Мастер на объекте!</b>\n\n"
            f"👨‍🔧 Мастер: {master.get_display_name()}\n"
            f"📋 Заявка #{order_id}\n"
            f"📋 Статус: {OrderStatus.get_status_name(OrderStatus.ONSITE)}\n"
            f"⏰ Время прибытия: {format_datetime(get_now())}\n\n"
            f"🔧 <b>Детали заявки:</b>\n"
            f"📱 Тип техники: {order.equipment_type}\n"
            f"📝 Описание: {order.description}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n"
            f"📞 Телефон: {order.client_phone}\n\n"
            f"После завершения работы нажмите кнопку ниже.",
            parse_mode="HTML",
            reply_markup=get_group_order_keyboard(order, OrderStatus.ONSITE),
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"🏠 Мастер {master.get_display_name()} на объекте (Заявка #{order_id})",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        log_action(callback.from_user.id, "ONSITE_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Статус обновлен!")


@router.callback_query(F.data.startswith("group_complete_order:"))
async def callback_group_complete_order(callback: CallbackQuery, state: FSMContext):
    """
    Начало процесса завершения заявки (поддержка анонимных админов)

    Args:
        callback: Callback query
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        
        # Получаем мастера (с поддержкой анонимных админов)
        master, is_anonymous = await get_master_from_callback(callback, db)
        
        if not master:
            await callback.answer(
                "❌ Не удалось определить мастера для этой группы.\n"
                "Убедитесь, что у мастера настроена эта группа как рабочая.",
                show_alert=True
            )
            return
        
        # Проверяем рабочую группу (если это не анонимный админ)
        if not is_anonymous:
            if not await check_master_work_group(master, callback):
                return

        # Проверяем права
        if order.assigned_master_id != master.id:
            await callback.answer("Это не заявка для вашей группы", show_alert=True)
            return

        # Сохраняем ID заказа и ID сообщения в группе
        await state.update_data(
            order_id=order_id,
            group_chat_id=callback.message.chat.id,
            group_message_id=callback.message.message_id,
            acting_as_master_id=master.telegram_id,
        )

        # Переходим в состояние запроса общей суммы
        from app.states import CompleteOrderStates

        await state.set_state(CompleteOrderStates.enter_total_amount)

        # Запрашиваем сумму прямо в группе
        await callback.message.reply(
            f"💰 <b>Завершение заявки #{order_id}</b>\n\n"
            f"👨‍🔧 Мастер: {master.get_display_name()}\n\n"
            f"Пожалуйста, введите <b>общую сумму заказа</b> (в рублях):\n"
            f"Например: 5000, 5000.50 или 0",
            parse_mode="HTML",
        )

        await callback.answer("Введите общую сумму заказа")

        log_action(callback.from_user.id, "START_COMPLETE_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("group_dr_order:"))
async def callback_group_dr_order(callback: CallbackQuery, state: FSMContext):
    """
    Переход в длительный ремонт (поддержка анонимных админов)

    Args:
        callback: Callback query
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        
        # Получаем мастера (с поддержкой анонимных админов)
        master, is_anonymous = await get_master_from_callback(callback, db)
        
        if not master:
            await callback.answer(
                "❌ Не удалось определить мастера для этой группы.\n"
                "Убедитесь, что у мастера настроена эта группа как рабочая.",
                show_alert=True
            )
            return
        
        # Проверяем рабочую группу (если это не анонимный админ)
        if not is_anonymous:
            if not await check_master_work_group(master, callback):
                return

        # Проверяем права
        if order.assigned_master_id != master.id:
            await callback.answer("Это не заявка для вашей группы", show_alert=True)
            return

        # Сохраняем order_id и мастера в state для длительного ремонта
        await state.update_data(
            order_id=order_id,
            acting_as_master_id=master.telegram_id,
        )
        
        # Переходим к вводу срока окончания и предоплаты
        from app.states import LongRepairStates
        await state.set_state(LongRepairStates.enter_completion_date_and_prepayment)
        
        await callback.message.reply(
            f"⏳ <b>Длительный ремонт - Заявка #{order_id}</b>\n\n"
            f"Введите <b>примерный срок окончания ремонта</b> и <b>предоплату</b> (если была).\n\n"
            f"<b>Примеры:</b>\n"
            f"• <code>20.10.2025</code>\n"
            f"• <code>20.10.2025 предоплата 2000</code>\n"
            f"• <code>через 3 дня</code>\n"
            f"• <code>завтра, предоплата 1500</code>\n"
            f"• <code>неделя</code>\n\n"
            f"<i>Если предоплаты не было - просто укажите срок.</i>",
            parse_mode="HTML"
        )
        
        await callback.answer()
        
        logger.debug(f"[DR] Group DR process started for order #{order_id}, master: {master.telegram_id}")
        
        return

    finally:
        await db.disconnect()


@router.message(Command("order"), IsGroupChat(), IsMasterInGroup())
async def cmd_order_in_group(message: Message):
    """
    Команда для просмотра заказа в группе
    """
    if message.chat.type not in ["group", "supergroup"]:
        return

    # Извлекаем ID заказа из команды
    try:
        order_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.reply(
            "❌ Неверный формат команды.\n"
            "Используйте: /order <номер_заявки>\n"
            "Пример: /order 123"
        )
        return

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        if not order:
            await message.reply(f"❌ Заявка #{order_id} не найдена.")
            return

        # Проверяем, есть ли мастер в этой группе
        master = None
        if order.assigned_master_id:
            master = await db.get_master_by_id(order.assigned_master_id)
            if master and master.work_chat_id != message.chat.id:
                await message.reply(f"❌ Заявка #{order_id} назначена другому мастеру.")
                return

        # Формируем сообщение
        text = f"📋 <b>Заявка #{order.id}</b>\n\n"
        text += f"📊 <b>Статус:</b> {OrderStatus.get_status_name(order.status)}\n"
        text += f"🔧 <b>Тип техники:</b> {order.equipment_type}\n"
        text += f"📝 <b>Описание:</b> {order.description}\n\n"
        text += f"👤 <b>Клиент:</b> {order.client_name}\n"
        text += f"📍 <b>Адрес:</b> {order.client_address}\n"

        # Показываем номер телефона только после прибытия на объект
        if order.status in [OrderStatus.ONSITE, OrderStatus.DR, OrderStatus.CLOSED]:
            text += f"📞 <b>Телефон:</b> {order.client_phone}\n\n"
        elif order.status == OrderStatus.ACCEPTED:
            text += "📞 <b>Телефон:</b> <i>Будет доступен после прибытия на объект</i>\n\n"
        else:
            text += "📞 <b>Телефон:</b> <i>Недоступно</i>\n\n"

        if order.notes:
            text += f"📄 <b>Заметки:</b> {order.notes}\n\n"

        if order.assigned_master_id and master:
            text += f"👨‍🔧 <b>Мастер:</b> {master.get_display_name()}\n"

        if order.dispatcher_name:
            text += f"📞 <b>Диспетчер:</b> {order.dispatcher_name}\n"

        text += f"📅 <b>Создана:</b> {format_datetime(order.created_at)}\n"
        text += f"🔄 <b>Обновлена:</b> {format_datetime(order.updated_at)}"

        # Отправляем сообщение с клавиатурой, если это заявка мастера
        if master and master.telegram_id == message.from_user.id:
            keyboard = get_group_order_keyboard(order, order.status)
            await message.reply(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await message.reply(text, parse_mode="HTML")

    finally:
        await db.disconnect()
