"""
Обработчики для мастеров
"""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import OrderStatus, UserRole
from app.database import Database
from app.keyboards.inline import get_order_actions_keyboard, get_order_list_keyboard
from app.states import CompleteOrderStates
from app.utils import calculate_profit_split, format_datetime, log_action


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

        if order.created_at:
            text += f"📅 <b>Создана:</b> {format_datetime(order.created_at)}\n"

        keyboard = get_order_actions_keyboard(order, UserRole.MASTER)

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

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
            details=f"Accepted order #{order_id}",
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"✅ Мастер {master.get_display_name()} принял заявку #{order_id}",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        await callback.message.edit_text(
            f"✅ <b>Заявка #{order_id} принята!</b>\n\n"
            f"Теперь вы можете просмотреть контактную информацию клиента.\n"
            f"Когда будете на объекте, обновите статус заявки.",
            parse_mode="HTML",
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
            (OrderStatus.NEW, order_id),
        )
        await db.connection.commit()

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="REFUSE_ORDER_MASTER",
            details=f"Master refused order #{order_id}",
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"❌ Мастер {master.get_display_name()} отклонил заявку #{order_id}\n"
                    f"Необходимо назначить другого мастера.",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        await callback.message.edit_text(
            f"❌ Заявка #{order_id} отклонена.\n\n" f"Диспетчер получил уведомление."
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
            details=f"Master on site for order #{order_id}",
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

        await callback.message.edit_text(
            f"🏠 <b>Статус обновлен!</b>\n\n"
            f"Заявка #{order_id} - вы на объекте.\n"
            f"После завершения работы не забудьте закрыть заявку.",
            parse_mode="HTML",
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
            f"Например: 5000 или 5000.50",
            parse_mode="HTML",
        )

        log_action(callback.from_user.id, "START_COMPLETE_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer()


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
            details=f"Order #{order_id} marked as long-term repair",
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await callback.bot.send_message(
                    order.dispatcher_id,
                    f"⏳ Заявка #{order_id} переведена в длительный ремонт\n"
                    f"Мастер: {master.get_display_name()}",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        await callback.message.edit_text(
            f"⏳ <b>Статус обновлен!</b>\n\n" f"Заявка #{order_id} переведена в длительный ремонт.",
            parse_mode="HTML",
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

        await message.answer(text, parse_mode="HTML")

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
        if total_amount <= 0:
            await message.reply(
                "❌ Сумма должна быть положительным числом.\n" "Попробуйте еще раз:"
            )
            return
    except ValueError:
        await message.reply(
            "❌ Неверный формат суммы.\n" "Пожалуйста, введите число (например: 5000 или 5000.50):"
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

    # Переходим к запросу об отзыве
    await state.set_state(CompleteOrderStates.confirm_review)

    await message.reply(
        f"✅ Сумма расходного материала: <b>{materials_cost:.2f} ₽</b>\n\n"
        f"❓ <b>Взяли ли вы отзыв у клиента?</b>\n"
        f"(За отзыв вы получите дополнительно +10% к прибыли)\n\n"
        f"Ответьте:\n"
        f"• <b>Да</b> - если взяли отзыв\n"
        f"• <b>Нет</b> - если не взяли",
        parse_mode="HTML",
    )


@router.message(CompleteOrderStates.confirm_review)
async def process_review_confirmation(message: Message, state: FSMContext):
    """
    Обработка подтверждения наличия отзыва и завершение заказа (работает и в личке, и в группе)

    Args:
        message: Сообщение
        state: FSM контекст
    """
    # Проверяем ответ
    answer = message.text.strip().lower()

    if answer in ["да", "yes", "lf", "+"]:
        has_review = True
    elif answer in ["нет", "no", "ytn", "-"]:
        has_review = False
    else:
        await message.reply("❌ Пожалуйста, ответьте <b>Да</b> или <b>Нет</b>", parse_mode="HTML")
        return

    # Получаем данные из состояния
    data = await state.get_data()
    order_id = data.get("order_id")
    total_amount = data.get("total_amount")
    materials_cost = data.get("materials_cost")

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(message.from_user.id)

        if not master or not order or order.assigned_master_id != master.id:
            await message.answer("❌ Ошибка: заявка не найдена или не принадлежит вам.")
            await state.clear()
            return

        # Рассчитываем распределение прибыли с учетом отзыва
        master_profit, company_profit = calculate_profit_split(
            total_amount, materials_cost, has_review
        )
        net_profit = total_amount - materials_cost

        # Определяем процентную ставку для отображения
        profit_rate = "50/50" if net_profit >= 7000 else "40/60"
        review_bonus_text = " + бонус за отзыв" if has_review else ""

        # Обновляем суммы в базе данных
        await db.update_order_amounts(
            order_id=order_id,
            total_amount=total_amount,
            materials_cost=materials_cost,
            master_profit=master_profit,
            company_profit=company_profit,
            has_review=has_review,
        )

        # Обновляем статус на CLOSED
        await db.update_order_status(order_id, OrderStatus.CLOSED)

        # Добавляем в лог
        await db.add_audit_log(
            user_id=message.from_user.id,
            action="COMPLETE_ORDER",
            details=f"Completed order #{order_id}, total: {total_amount}, materials: {materials_cost}",
        )

        # Обновляем сообщение в группе, если заказ был завершен оттуда
        group_chat_id = data.get("group_chat_id")
        group_message_id = data.get("group_message_id")

        if group_chat_id and group_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=group_chat_id,
                    message_id=group_message_id,
                    text=(
                        f"✅ <b>Заявка #{order_id} завершена!</b>\n\n"
                        f"👨‍🔧 Мастер: {master.get_display_name()}\n"
                        f"📋 Статус: {OrderStatus.get_status_name(OrderStatus.CLOSED)}\n"
                        f"⏰ Время завершения: {format_datetime(datetime.now())}\n\n"
                        f"🔧 <b>Детали заявки:</b>\n"
                        f"📱 Тип техники: {order.equipment_type}\n"
                        f"📝 Описание: {order.description}\n"
                        f"👤 Клиент: {order.client_name}\n"
                        f"📍 Адрес: {order.client_address}\n"
                        f"📞 Телефон: {order.client_phone}\n\n"
                        f"💰 <b>Финансовая информация:</b>\n"
                        f"• Общая сумма: <b>{total_amount:.2f} ₽</b>\n"
                        f"• Расходный материал: <b>{materials_cost:.2f} ₽</b>\n"
                        f"• Чистая прибыль: <b>{net_profit:.2f} ₽</b>\n"
                        f"• Отзыв: {'✅ Взят (+10%)' if has_review else '❌ Не взят'}\n\n"
                        f"📊 <b>Распределение прибыли ({profit_rate}{review_bonus_text}):</b>\n"
                        f"• Мастер: <b>{master_profit:.2f} ₽</b>\n"
                        f"• Компания: <b>{company_profit:.2f} ₽</b>\n\n"
                        f"🎉 Работа успешно выполнена!"
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to update group message: {e}")

        # Уведомляем диспетчера
        if order.dispatcher_id:
            try:
                await message.bot.send_message(
                    order.dispatcher_id,
                    f"💰 <b>Заявка #{order_id} завершена!</b>\n\n"
                    f"👨‍🔧 Мастер: {master.get_display_name()}\n"
                    f"💵 Общая сумма: <b>{total_amount:.2f} ₽</b>\n"
                    f"🔧 Расходный материал: <b>{materials_cost:.2f} ₽</b>\n"
                    f"💎 Чистая прибыль: <b>{net_profit:.2f} ₽</b>\n"
                    f"⭐ Отзыв: {'✅ Взят (+10%)' if has_review else '❌ Не взят'}\n\n"
                    f"📊 <b>Распределение ({profit_rate}{review_bonus_text}):</b>\n"
                    f"👨‍🔧 Мастер: <b>{master_profit:.2f} ₽</b>\n"
                    f"🏢 Компания: <b>{company_profit:.2f} ₽</b>",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id}: {e}")

        # Отправляем итоговое сообщение (reply для групп, answer для личных чатов)
        review_text = (
            "⭐ <b>Отзыв взят!</b> Вы получили дополнительные +10%\n" if has_review else ""
        )
        completion_message = (
            f"✅ <b>Заявка #{order_id} успешно завершена!</b>\n\n"
            f"{review_text}"
            f"💰 <b>Финансовая информация:</b>\n"
            f"• Общая сумма: <b>{total_amount:.2f} ₽</b>\n"
            f"• Расходный материал: <b>{materials_cost:.2f} ₽</b>\n"
            f"• Чистая прибыль: <b>{net_profit:.2f} ₽</b>\n\n"
            f"📊 <b>Распределение прибыли ({profit_rate}{review_bonus_text}):</b>\n"
            f"👨‍🔧 Ваша доля: <b>{master_profit:.2f} ₽</b>\n"
            f"🏢 Доля компании: <b>{company_profit:.2f} ₽</b>\n\n"
            f"Отличная работа! 🎉"
        )

        if message.chat.type in ["group", "supergroup"]:
            await message.reply(completion_message, parse_mode="HTML")
        else:
            await message.answer(completion_message, parse_mode="HTML")

        log_action(message.from_user.id, "COMPLETE_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()
        await state.clear()


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
