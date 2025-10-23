"""
Обработчики для взаимодействия с заказами в группах
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import OrderStatus
from app.database import Database
from app.filters import IsGroupChat, IsMasterInGroup
from app.keyboards.inline import get_group_order_keyboard
from app.states import RescheduleOrderStates
from app.utils import format_datetime, get_now, log_action


logger = logging.getLogger(__name__)

router = Router(name="group_interaction")


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
            "❌ У вас не настроена рабочая группа!\n" "Обратитесь к администратору для настройки.",
            show_alert=True,
        )
        return False

    # Проверяем, что действие выполняется в правильной группе
    if callback.message.chat.id != master.work_chat_id:
        await callback.answer(
            "❌ Вы можете работать только в своей рабочей группе!", show_alert=True
        )
        return False

    return True


@router.callback_query(F.data.startswith("group_accept_order:"))
async def callback_group_accept_order(callback: CallbackQuery, user_roles: list):
    """
    Принятие заявки мастером или админом в группе

    Args:
        callback: Callback query
        user_roles: Список ролей пользователя
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        from app.config import UserRole

        order = await db.get_order_by_id(order_id)

        # Если пользователь - админ в группе, ищем мастера по work_chat_id группы
        if UserRole.ADMIN in user_roles:
            # Находим мастера по ID группы
            master = await db.get_master_by_work_chat_id(callback.message.chat.id)

            if not master:
                await callback.answer(
                    "❌ В этой группе не настроена работа для мастера", show_alert=True
                )
                return

            logger.info(
                f"Admin {callback.from_user.id} acting as master {master.telegram_id} in group {callback.message.chat.id}"
            )
        else:
            # Обычная проверка для мастера
            master = await db.get_master_by_telegram_id(callback.from_user.id)

            # Проверяем рабочую группу
            if not await check_master_work_group(master, callback):
                return

        # Проверяем права на заявку
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

        acceptance_text += "\n<b>Когда будете на объекте, нажмите кнопку ниже.</b>"

        # Обновляем сообщение в группе
        await callback.message.edit_text(
            acceptance_text,
            parse_mode="HTML",
            reply_markup=get_group_order_keyboard(order, OrderStatus.ACCEPTED),
        )

        # Уведомляем диспетчера с retry механизмом
        if order.dispatcher_id:
            from app.utils import safe_send_message

            result = await safe_send_message(
                callback.bot,
                order.dispatcher_id,
                f"✅ Мастер {master.get_display_name()} принял заявку #{order_id} в группе",
                parse_mode="HTML",
            )
            if not result:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id} after retries")

        log_action(callback.from_user.id, "ACCEPT_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Заявка принята!")


@router.callback_query(F.data.startswith("group_refuse_order:"))
async def callback_group_refuse_order(callback: CallbackQuery, user_roles: list):
    """
    Отклонение заявки мастером или админом в группе

    Args:
        callback: Callback query
        user_roles: Список ролей пользователя
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        from app.config import UserRole

        order = await db.get_order_by_id(order_id)

        # Если пользователь - админ в группе, ищем мастера по work_chat_id группы
        if UserRole.ADMIN in user_roles:
            master = await db.get_master_by_work_chat_id(callback.message.chat.id)

            if not master:
                await callback.answer(
                    "❌ В этой группе не настроена работа для мастера", show_alert=True
                )
                return

            logger.info(
                f"Admin {callback.from_user.id} refusing order as master {master.telegram_id}"
            )
        else:
            master = await db.get_master_by_telegram_id(callback.from_user.id)

            # Проверяем рабочую группу
            if not await check_master_work_group(master, callback):
                return

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
            action="REFUSE_ORDER_GROUP",
            details=f"Master refused order #{order_id} in group",
        )

        # Меню обновится автоматически в update_order_status

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

        # Уведомляем диспетчера с retry механизмом
        if order.dispatcher_id:
            from app.utils import safe_send_message

            result = await safe_send_message(
                callback.bot,
                order.dispatcher_id,
                f"❌ Мастер {master.get_display_name()} отклонил заявку #{order_id} в группе\n"
                f"Необходимо назначить другого мастера.",
                parse_mode="HTML",
            )
            if not result:
                logger.error(f"Failed to notify dispatcher {order.dispatcher_id} after retries")

        log_action(callback.from_user.id, "REFUSE_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Заявка отклонена")


@router.callback_query(F.data.startswith("group_onsite_order:"))
async def callback_group_onsite_order(callback: CallbackQuery, user_roles: list):
    """
    Мастер на объекте или админ за мастера в группе

    Args:
        callback: Callback query
        user_roles: Список ролей пользователя
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        from app.config import UserRole

        order = await db.get_order_by_id(order_id)

        # Если пользователь - админ в группе, ищем мастера по work_chat_id группы
        if UserRole.ADMIN in user_roles:
            master = await db.get_master_by_work_chat_id(callback.message.chat.id)

            if not master:
                await callback.answer(
                    "❌ В этой группе не настроена работа для мастера", show_alert=True
                )
                return

            logger.info(
                f"Admin {callback.from_user.id} marking onsite as master {master.telegram_id}"
            )
        else:
            master = await db.get_master_by_telegram_id(callback.from_user.id)

            # Проверяем рабочую группу
            if not await check_master_work_group(master, callback):
                return

        # Проверяем права
        if not master or order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Обновляем статус (с валидацией через State Machine)
        await db.update_order_status(
            order_id=order_id,
            status=OrderStatus.ONSITE,
            changed_by=callback.from_user.id,
            user_roles=user_roles,  # Передаём роли для валидации
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
            f"📍 Адрес: {order.client_address}\n\n"
            f'Контактный телефон не сохраняется в чате. Нажмите кнопку "📞 Показать телефон" для просмотра.',
            parse_mode="HTML",
            reply_markup=get_group_order_keyboard(order, OrderStatus.ONSITE),
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

        log_action(callback.from_user.id, "ONSITE_ORDER_GROUP", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Статус обновлен!")


@router.callback_query(F.data.startswith("group_complete_order:"))
async def callback_group_complete_order(
    callback: CallbackQuery, state: FSMContext, user_roles: list
):
    """
    Начало процесса завершения заявки мастером или админом в группе

    Args:
        callback: Callback query
        state: FSM контекст
        user_roles: Список ролей пользователя
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        from app.config import UserRole

        order = await db.get_order_by_id(order_id)

        # Если пользователь - админ в группе, ищем мастера по work_chat_id группы
        if UserRole.ADMIN in user_roles:
            master = await db.get_master_by_work_chat_id(callback.message.chat.id)

            if not master:
                await callback.answer(
                    "❌ В этой группе не настроена работа для мастера", show_alert=True
                )
                return

            is_admin_acting = True
            logger.info(
                f"Admin {callback.from_user.id} completing order as master {master.telegram_id}"
            )
        else:
            master = await db.get_master_by_telegram_id(callback.from_user.id)
            is_admin_acting = False

            # Проверяем рабочую группу
            if not await check_master_work_group(master, callback):
                return

        # Проверяем права
        if not master or order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Если админ действует от имени мастера, нужно установить состояние для МАСТЕРА, а не админа
        # Для этого создаем FSM контекст для мастера
        if is_admin_acting:
            from aiogram.fsm.context import FSMContext
            from aiogram.fsm.storage.base import StorageKey

            # Создаем ключ для состояния мастера в этом чате
            master_storage_key = StorageKey(
                bot_id=callback.bot.id, chat_id=callback.message.chat.id, user_id=master.telegram_id
            )

            # Получаем FSM контекст для мастера
            master_state = FSMContext(storage=state.storage, key=master_storage_key)

            # Устанавливаем состояние и данные для мастера
            await master_state.update_data(
                order_id=order_id,
                group_chat_id=callback.message.chat.id,
                group_message_id=callback.message.message_id,
                acting_as_master_id=None,  # Мастер действует от своего имени
            )

            from app.states import CompleteOrderStates

            await master_state.set_state(CompleteOrderStates.enter_total_amount)

            # Также очищаем состояние админа, если оно было
            await state.clear()
        else:
            # Обычный мастер - сохраняем для него
            await state.update_data(
                order_id=order_id,
                group_chat_id=callback.message.chat.id,
                group_message_id=callback.message.message_id,
                acting_as_master_id=None,
            )

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
async def callback_group_dr_order(callback: CallbackQuery, state: FSMContext, user_roles: list):
    """
    Переход в длительный ремонт мастером или админом в группе

    Args:
        callback: Callback query
        state: FSM контекст
        user_roles: Список ролей пользователя
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        from app.config import UserRole

        order = await db.get_order_by_id(order_id)

        # Если пользователь - админ в группе, ищем мастера по work_chat_id группы
        if UserRole.ADMIN in user_roles:
            master = await db.get_master_by_work_chat_id(callback.message.chat.id)

            if not master:
                await callback.answer(
                    "❌ В этой группе не настроена работа для мастера", show_alert=True
                )
                return

            logger.info(f"Admin {callback.from_user.id} starting DR as master {master.telegram_id}")
        else:
            master = await db.get_master_by_telegram_id(callback.from_user.id)

            # Проверяем рабочую группу
            if not await check_master_work_group(master, callback):
                return

        # Проверяем права
        if not master or order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Сохраняем order_id и мастера в state для длительного ремонта
        # Определяем, является ли инициатор админом
        is_admin = UserRole.ADMIN in user_roles
        await state.update_data(
            order_id=order_id,
            acting_as_master_id=master.telegram_id if is_admin else None,
        )

        # Переходим к вводу срока окончания и предоплаты
        from app.states import LongRepairStates

        await state.set_state(LongRepairStates.enter_completion_date_and_prepayment)

        await callback.message.reply(
            f"⏳ <b>Длительный ремонт - Заявка #{order_id}</b>\n\n"
            f"Введите <b>примерный срок окончания ремонта</b> и <b>предоплату</b> (если была).\n\n"
            f"<i>Если предоплаты не было - просто укажите срок.</i>",
            parse_mode="HTML",
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка в callback_group_start_long_repair: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)
    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("group_show_phone:"))
async def callback_group_show_phone(callback: CallbackQuery, user_roles: list):
    """
    Показ телефона клиента в рабочей группе во всплывающем окне.
    Доступ только мастеру заявки или администратору этой рабочей группы.
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        from app.config import UserRole

        order = await db.get_order_by_id(order_id)
        if not order:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        # Если админ кликает в группе, проверяем, что это его рабочая группа мастера
        if UserRole.ADMIN in user_roles:
            master = await db.get_master_by_work_chat_id(callback.message.chat.id)
            if not master or order.assigned_master_id != master.id:
                await callback.answer("❌ Нет доступа", show_alert=True)
                return
        else:
            master = await db.get_master_by_telegram_id(callback.from_user.id)
            if not master or order.assigned_master_id != master.id:
                await callback.answer("❌ Это не ваша заявка", show_alert=True)
                return

        # Телефон доступен после прибытия (ONSITE), а также в DR/закрыта
        if order.status not in [OrderStatus.ONSITE, OrderStatus.DR, OrderStatus.CLOSED]:
            await callback.answer("📵 Телефон доступен после прибытия на объект", show_alert=True)
            return

        await callback.answer(f"📞 Телефон клиента: {order.client_phone}", show_alert=True)

    finally:
        await db.disconnect()

        logger.debug(
            f"[DR] Group DR process started for order #{order_id}, master: {master.telegram_id}"
        )


@router.callback_query(F.data.startswith("group_reschedule_order:"))
async def callback_group_reschedule_order(
    callback: CallbackQuery, state: FSMContext, user_roles: list
):
    """
    Перенос заявки мастером или админом в группе

    Args:
        callback: Callback query
        state: FSM контекст
        user_roles: Список ролей пользователя
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        from app.config import UserRole

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

        # Если пользователь - админ в группе, ищем мастера по work_chat_id группы
        if UserRole.ADMIN in user_roles:
            master = await db.get_master_by_work_chat_id(callback.message.chat.id)

            if not master:
                await callback.answer(
                    "❌ В этой группе не настроена работа для мастера", show_alert=True
                )
                return

            logger.info(
                f"Admin {callback.from_user.id} rescheduling as master {master.telegram_id}"
            )
        else:
            master = await db.get_master_by_telegram_id(callback.from_user.id)

            # Проверяем рабочую группу
            if not await check_master_work_group(master, callback):
                return

        # Проверяем права
        if not master or order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Сохраняем данные в state
        await state.update_data(
            order_id=order_id,
            reschedule_initiated_by=callback.from_user.id,
            is_group_reschedule=True,
        )

        # Переходим к вводу нового времени
        await state.set_state(RescheduleOrderStates.enter_new_time)

        current_time = order.scheduled_time or "не указано"

        await callback.message.reply(
            f"📅 <b>Перенос заявки #{order_id}</b>\n\n"
            f"⏰ Сейчас: {current_time}\n\n"
            f"Напишите новое время:\n"
            f"<i>Например: завтра 14:00, сегодня 18:00, через 3 часа</i>",
            parse_mode="HTML",
        )

        await callback.answer()

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
