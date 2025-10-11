"""
Обработчики для мастеров
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.config import OrderStatus, UserRole
from app.filters import IsMaster
from app.database import Database
from app.keyboards.inline import get_order_actions_keyboard, get_order_list_keyboard
from app.utils import log_action, format_datetime
from app.decorators import require_role

logger = logging.getLogger(__name__)

router = Router(name='master')
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
    await state.clear()
    
    db = Database()
    await db.connect()
    
    try:
        # Получаем мастера
        master = await db.get_master_by_telegram_id(message.from_user.id)
        
        if not master:
            await message.answer(
                "❌ Вы не зарегистрированы как мастер в системе."
            )
            return
        
        # Получаем заявки мастера
        orders = await db.get_orders_by_master(master.id, exclude_closed=True)
        
        if not orders:
            await message.answer(
                "📭 У вас пока нет активных заявок.\n\n"
                "Заявки будут назначаться диспетчером."
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
            OrderStatus.DR
        ]
        
        for status in status_order:
            if status in by_status:
                status_emoji = OrderStatus.get_status_emoji(status)
                status_name = OrderStatus.get_status_name(status)
                
                text += f"\n<b>{status_emoji} {status_name}:</b>\n"
                
                for order in by_status[status]:
                    text += f"  • Заявка #{order.id} - {order.equipment_type}\n"
                
                text += "\n"
        
        keyboard = get_order_list_keyboard(orders)
        
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("view_order:"), IsMaster())
async def callback_view_order_master(callback: CallbackQuery):
    """
    Просмотр детальной информации о заявке для мастера
    
    Args:
        callback: Callback query
    """
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
        
        # Показываем контактную информацию клиента только при определенных статусах
        if order.status in [OrderStatus.ACCEPTED, OrderStatus.ONSITE, OrderStatus.DR, OrderStatus.CLOSED]:
            text += (
                f"👤 <b>Клиент:</b> {order.client_name}\n"
                f"📍 <b>Адрес:</b> {order.client_address}\n"
                f"📞 <b>Телефон:</b> {order.client_phone}\n\n"
            )
        else:
            text += (
                f"<i>Контактная информация клиента будет доступна\n"
                f"после принятия заявки.</i>\n\n"
            )
        
        if order.notes:
            text += f"📝 <b>Заметки:</b> {order.notes}\n\n"
        
        if order.created_at:
            text += f"📅 <b>Создана:</b> {format_datetime(order.created_at)}\n"
        
        from app.config import UserRole
        keyboard = get_order_actions_keyboard(order, UserRole.MASTER)
        
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    finally:
        await db.disconnect()
    
    await callback.answer()


@router.callback_query(F.data.startswith("accept_order:"))
async def callback_accept_order(callback: CallbackQuery):
    """
    Принятие заявки мастером
    
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
            action="ACCEPT_ORDER",
            details=f"Accepted order #{order_id}"
        )
        
        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"✅ Мастер {master.get_display_name()} принял заявку #{order_id}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")
        
        await callback.message.edit_text(
            f"✅ <b>Заявка #{order_id} принята!</b>\n\n"
            f"Теперь вы можете просмотреть контактную информацию клиента.\n"
            f"Когда будете на объекте, обновите статус заявки.",
            parse_mode="HTML"
        )
        
        log_action(callback.from_user.id, "ACCEPT_ORDER", f"Order #{order_id}")
        
    finally:
        await db.disconnect()
    
    await callback.answer("Заявка принята!")


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
        
        # Возвращаем статус в NEW и убираем мастера
        await db.connection.execute(
            "UPDATE orders SET status = ?, assigned_master_id = NULL WHERE id = ?",
            (OrderStatus.NEW, order_id)
        )
        await db.connection.commit()
        
        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="REFUSE_ORDER_MASTER",
            details=f"Master refused order #{order_id}"
        )
        
        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"❌ Мастер {master.get_display_name()} отклонил заявку #{order_id}\n"
                    f"Необходимо назначить другого мастера.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")
        
        await callback.message.edit_text(
            f"❌ Заявка #{order_id} отклонена.\n\n"
            f"Диспетчер получил уведомление."
        )
        
        log_action(callback.from_user.id, "REFUSE_ORDER_MASTER", f"Order #{order_id}")
        
    finally:
        await db.disconnect()
    
    await callback.answer("Заявка отклонена")


@router.callback_query(F.data.startswith("onsite_order:"))
async def callback_onsite_order(callback: CallbackQuery):
    """
    Мастер на объекте
    
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
            action="ONSITE_ORDER",
            details=f"Master on site for order #{order_id}"
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
        
        await callback.message.edit_text(
            f"🏠 <b>Статус обновлен!</b>\n\n"
            f"Заявка #{order_id} - вы на объекте.\n"
            f"После завершения работы не забудьте закрыть заявку.",
            parse_mode="HTML"
        )
        
        log_action(callback.from_user.id, "ONSITE_ORDER", f"Order #{order_id}")
        
    finally:
        await db.disconnect()
    
    await callback.answer("Статус обновлен!")


@router.callback_query(F.data.startswith("complete_order:"))
async def callback_complete_order(callback: CallbackQuery):
    """
    Завершение заявки мастером
    
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
        await db.update_order_status(order_id, OrderStatus.CLOSED)
        
        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="COMPLETE_ORDER",
            details=f"Completed order #{order_id}"
        )
        
        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"💰 Мастер {master.get_display_name()} завершил заявку #{order_id}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")
        
        await callback.message.edit_text(
            f"✅ <b>Заявка #{order_id} завершена!</b>\n\n"
            f"Отличная работа! 🎉",
            parse_mode="HTML"
        )
        
        log_action(callback.from_user.id, "COMPLETE_ORDER", f"Order #{order_id}")
        
    finally:
        await db.disconnect()
    
    await callback.answer("Заявка завершена!")


@router.callback_query(F.data.startswith("dr_order:"))
async def callback_dr_order(callback: CallbackQuery):
    """
    Длительный ремонт
    
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
            action="DR_ORDER",
            details=f"Order #{order_id} marked as long-term repair"
        )
        
        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"⏳ Заявка #{order_id} переведена в длительный ремонт\n"
                    f"Мастер: {master.get_display_name()}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")
        
        await callback.message.edit_text(
            f"⏳ <b>Статус обновлен!</b>\n\n"
            f"Заявка #{order_id} переведена в длительный ремонт.",
            parse_mode="HTML"
        )
        
        log_action(callback.from_user.id, "DR_ORDER", f"Order #{order_id}")
        
    finally:
        await db.disconnect()
    
    await callback.answer("Статус обновлен!")


@router.message(F.text == "📊 Моя статистика")
async def btn_my_stats(message: Message):
    """
    Статистика мастера
    
    Args:
        message: Сообщение
    """
    db = Database()
    await db.connect()
    
    try:
        master = await db.get_master_by_telegram_id(message.from_user.id)
        
        if not master:
            await message.answer(
                "❌ Вы не зарегистрированы как мастер в системе."
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
        active = sum(by_status.get(s, 0) for s in [OrderStatus.ASSIGNED, OrderStatus.ACCEPTED, OrderStatus.ONSITE])
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
        
        await message.answer(text, parse_mode="HTML")
        
    finally:
        await db.disconnect()


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
            await message.answer(
                "❌ Вы не зарегистрированы как мастер в системе."
            )
            return
        
        user = await db.get_user_by_telegram_id(message.from_user.id)
        
        settings_text = (
            f"⚙️ <b>Настройки профиля</b>\n\n"
            f"👤 <b>Имя:</b> {master.get_display_name()}\n"
            f"🆔 <b>Telegram ID:</b> <code>{master.telegram_id}</code>\n"
            f"📞 <b>Телефон:</b> {master.phone}\n"
            f"🔧 <b>Специализация:</b> {master.specialization}\n"
            f"👔 <b>Роль:</b> {user.role if user else 'MASTER'}\n"
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
