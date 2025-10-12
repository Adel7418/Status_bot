"""
Обработчики для взаимодействия с заказами в группах
"""
import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import OrderStatus
from app.database import Database
from app.filters import IsGroupChat, IsGroupOrderCallback, IsMasterInGroup
from app.keyboards.inline import get_group_order_keyboard
from app.utils import format_datetime, log_action


logger = logging.getLogger(__name__)

router = Router(name="group_interaction")


@router.callback_query(F.data.startswith("group_accept_order:"), IsGroupOrderCallback())
async def callback_group_accept_order(callback: CallbackQuery):
    """
    Принятие заявки мастером в группе

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

        # Обновляем статус
        await db.update_order_status(order_id, OrderStatus.ACCEPTED)

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ACCEPT_ORDER_GROUP",
            details=f"Accepted order #{order_id} in group"
        )

        # Обновляем сообщение в группе
        await callback.message.edit_text(
            f"✅ <b>Заявка #{order_id} принята!</b>\n\n"
            f"👨‍🔧 Мастер: {master.get_display_name()}\n"
            f"📋 Статус: {OrderStatus.get_status_name(OrderStatus.ACCEPTED)}\n"
            f"⏰ Время принятия: {format_datetime(datetime.now())}\n\n"
            f"🔧 <b>Детали заявки:</b>\n"
            f"📱 Тип техники: {order.equipment_type}\n"
            f"📝 Описание: {order.description}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n"
            f"📞 Телефон: <i>Будет доступен после прибытия на объект</i>\n\n"
            f"Когда будете на объекте, нажмите кнопку ниже.",
            parse_mode="HTML",
            reply_markup=get_group_order_keyboard(order, OrderStatus.ACCEPTED)
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"✅ Мастер {master.get_display_name()} принял заявку #{order_id} в группе",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        log_action(callback.from_user.id, "ACCEPT_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Заявка принята!")


@router.callback_query(F.data.startswith("group_refuse_order:"), IsGroupOrderCallback())
async def callback_group_refuse_order(callback: CallbackQuery):
    """
    Отклонение заявки мастером в группе

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

        # Возвращаем статус в NEW и убираем мастера
        await db.connection.execute(
            "UPDATE orders SET status = ?, assigned_master_id = NULL WHERE id = ?",
            (OrderStatus.NEW, order_id)
        )
        await db.connection.commit()

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="REFUSE_ORDER_GROUP",
            details=f"Master refused order #{order_id} in group"
        )

        # Обновляем сообщение в группе (номер телефона скрыт, т.к. заявка отклонена до прибытия на объект)
        await callback.message.edit_text(
            f"❌ <b>Заявка #{order_id} отклонена</b>\n\n"
            f"👨‍🔧 Мастер: {master.get_display_name()}\n"
            f"📋 Статус: Требует нового назначения\n"
            f"⏰ Время отклонения: {format_datetime(datetime.now())}\n\n"
            f"🔧 <b>Детали заявки:</b>\n"
            f"📱 Тип техники: {order.equipment_type}\n"
            f"📝 Описание: {order.description}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n\n"
            f"Диспетчер получил уведомление для назначения другого мастера.",
            parse_mode="HTML"
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"❌ Мастер {master.get_display_name()} отклонил заявку #{order_id} в группе\n"
                    f"Необходимо назначить другого мастера.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        log_action(callback.from_user.id, "REFUSE_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Заявка отклонена")


@router.callback_query(F.data.startswith("group_onsite_order:"), IsGroupOrderCallback())
async def callback_group_onsite_order(callback: CallbackQuery):
    """
    Мастер на объекте (в группе)

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

        # Обновляем статус
        await db.update_order_status(order_id, OrderStatus.ONSITE)

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ONSITE_ORDER_GROUP",
            details=f"Master on site for order #{order_id} in group"
        )

        # Обновляем сообщение в группе
        await callback.message.edit_text(
            f"🏠 <b>Мастер на объекте!</b>\n\n"
            f"👨‍🔧 Мастер: {master.get_display_name()}\n"
            f"📋 Заявка #{order_id}\n"
            f"📋 Статус: {OrderStatus.get_status_name(OrderStatus.ONSITE)}\n"
            f"⏰ Время прибытия: {format_datetime(datetime.now())}\n\n"
            f"🔧 <b>Детали заявки:</b>\n"
            f"📱 Тип техники: {order.equipment_type}\n"
            f"📝 Описание: {order.description}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n"
            f"📞 Телефон: {order.client_phone}\n\n"
            f"После завершения работы нажмите кнопку ниже.",
            parse_mode="HTML",
            reply_markup=get_group_order_keyboard(order, OrderStatus.ONSITE)
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"🏠 Мастер {master.get_display_name()} на объекте (Заявка #{order_id})",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        log_action(callback.from_user.id, "ONSITE_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Статус обновлен!")


@router.callback_query(F.data.startswith("group_complete_order:"), IsGroupOrderCallback())
async def callback_group_complete_order(callback: CallbackQuery, state: FSMContext):
    """
    Начало процесса завершения заявки мастером в группе

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

        # Сохраняем ID заказа и ID сообщения в группе для обновления позже
        await state.update_data(
            order_id=order_id,
            group_chat_id=callback.message.chat.id,
            group_message_id=callback.message.message_id
        )

        # Переходим в состояние запроса общей суммы
        from app.states import CompleteOrderStates
        await state.set_state(CompleteOrderStates.enter_total_amount)

        # Запрашиваем сумму прямо в группе
        await callback.message.reply(
            f"💰 <b>Завершение заявки #{order_id}</b>\n\n"
            f"👨‍🔧 Мастер: {master.get_display_name()}\n\n"
            f"Пожалуйста, введите <b>общую сумму заказа</b> (в рублях):\n"
            f"Например: 5000 или 5000.50",
            parse_mode="HTML"
        )

        await callback.answer("Введите общую сумму заказа")

        log_action(callback.from_user.id, "START_COMPLETE_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("group_dr_order:"), IsGroupOrderCallback())
async def callback_group_dr_order(callback: CallbackQuery):
    """
    Переход в длительный ремонт (в группе)

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

        # Обновляем статус
        await db.update_order_status(order_id, OrderStatus.DR)

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="DR_ORDER_GROUP",
            details=f"Order #{order_id} moved to long repair in group"
        )

        # Обновляем сообщение в группе
        await callback.message.edit_text(
            f"⏳ <b>Заявка переведена в длительный ремонт</b>\n\n"
            f"👨‍🔧 Мастер: {master.get_display_name()}\n"
            f"📋 Заявка #{order_id}\n"
            f"📋 Статус: {OrderStatus.get_status_name(OrderStatus.DR)}\n"
            f"⏰ Время перевода: {format_datetime(datetime.now())}\n\n"
            f"🔧 <b>Детали заявки:</b>\n"
            f"📱 Тип техники: {order.equipment_type}\n"
            f"📝 Описание: {order.description}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n"
            f"📞 Телефон: {order.client_phone}\n\n"
            f"Заявка требует длительного ремонта.",
            parse_mode="HTML"
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"⏳ Мастер {master.get_display_name()} перевел заявку #{order_id} в длительный ремонт",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        log_action(callback.from_user.id, "DR_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Заявка переведена в длительный ремонт")


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
