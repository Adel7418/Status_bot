"""
Обработчики для мастеров
"""

import logging
import re
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest

from app.config import OrderStatus, UserRole
from app.database import Database, get_database
from app.decorators import handle_errors
from app.handlers.common import get_menu_with_counter
from app.keyboards.inline import (
    get_order_actions_keyboard,
    get_order_list_keyboard,
    get_yes_no_keyboard,
)
from app.keyboards.reply import get_main_menu_keyboard
from app.presenters import OrderPresenter
from app.states import (
    CompleteOrderStates,
    LongRepairStates,
    RefuseOrderStates,
    RescheduleOrderStates,
)
from app.utils import get_now, log_action


logger = logging.getLogger(__name__)

router = Router(name="master")
# Фильтры на уровне роутера НЕ работают, т.к. выполняются ДО middleware
# Проверка роли теперь в каждом обработчике через декоратор


@router.message(F.text == "📋 Мои заявки")
@handle_errors
async def btn_my_orders(
    message: Message, state: FSMContext, user_role: str, user_roles: list, db: Database
):
    """
    Просмотр заявок мастера

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
        user_roles: Список ролей пользователя
        db: Database instance (injected by DependencyInjectionMiddleware)
    """
    # Проверка роли
    if user_role not in [UserRole.MASTER, UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    # Проверяем, что это не личное сообщение (только для чистых мастеров, админ может работать в приватном чате)
    if (
        message.chat.type == "private"
        and user_role == UserRole.MASTER
        and UserRole.ADMIN not in user_roles
    ):
        await message.answer(
            "⚠️ <b>Работа только в рабочей группе!</b>\n\n"
            "Для мастеров взаимодействие с ботом доступно только в рабочей группе.",
            parse_mode="HTML",
        )
        return

    await state.clear()

    # ✅ DI: Database injected, no need for connect/disconnect
    # Получаем мастера
    master = None
    if message.from_user and message.from_user.id:
        master = await db.get_master_by_telegram_id(message.from_user.id)

    if not master:
        await message.answer("❌ Вы не зарегистрированы как мастер в системе.")
        return

    assert master.id is not None  # Added assertion for mypy # nosec

    # Получаем заявки мастера
    orders = await db.get_orders_by_master(master.id, exclude_closed=True)

    if not orders:
        await message.answer(
            "📭 У вас пока нет активных заявок.\n\n" "Заявки будут назначаться диспетчером."
        )
        return

    text = "📋 <b>Ваши заявки:</b>\n\n"

    # Группируем по статусам
    by_status: dict[str, list] = {}
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
                text += f"  • {OrderPresenter.format_order_short(order)}\n"

            text += "\n"

    # Конвертируем ORM заказы в Legacy заказы для совместимости с клавиатурой
    from app.handlers.admin import _convert_orm_order_to_legacy

    legacy_orders = [
        _convert_orm_order_to_legacy(order) if hasattr(order, "__table__") else order
        for order in orders
    ]
    keyboard = get_order_list_keyboard(legacy_orders, for_master=True)

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("view_order_master:"))
async def callback_view_order_master(callback: CallbackQuery, user_roles: list, db: Database):
    """
    Просмотр детальной информации о заявке для мастера

    Args:
        callback: Callback query
        user_roles: Список ролей пользователя
        db: Database instance (injected by DependencyInjectionMiddleware)
    """
    # Проверяем роль мастера или админа
    if UserRole.MASTER not in user_roles and UserRole.ADMIN not in user_roles:
        await callback.answer("У вас нет доступа к этой функции", show_alert=True)
        return

    if not callback.data:
        return
    order_id = int(callback.data.split(":")[1])

    # ✅ DI: Database injected, no need for connect/disconnect
    order = await db.get_order_by_id(order_id)

    if not order:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    # Проверяем, что заявка назначена этому мастеру
    master = await db.get_master_by_telegram_id(callback.from_user.id)

    if not master:
        await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
        return

    # Проверяем роль пользователя
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    is_admin = False
    if user:
        is_admin = "ADMIN" in user.get_roles()

    if not is_admin and order.assigned_master_id != master.id:
        await callback.answer("Это не ваша заявка", show_alert=True)
        return

    # Используем OrderPresenter с режимом conditional (показывает телефон в зависимости от статуса)
    text = OrderPresenter.format_order_details(
        order, phone_visibility_mode="conditional", escape_html=False
    )

    # Показываем детальную финансовую информацию для закрытых заявок (специфично для мастеров)
    if order.status == OrderStatus.CLOSED and order.total_amount:
        net_profit = order.total_amount - (order.materials_cost or 0)

        # Определяем базовую ставку с учетом типа техники
        base_rate = "50/50" if net_profit >= 7000 else "40/60"
        if order.equipment_type:
            from app.database.orm_database import ORMDatabase

            if isinstance(db, ORMDatabase):
                specialization_rate = await db.get_specialization_rate(
                    equipment_type=order.equipment_type,
                )
            else:
                specialization_rate = None
            if specialization_rate:
                base_master_pct, base_company_pct = specialization_rate
                master_pct_display = int(round(base_master_pct))
                company_pct_display = int(round(base_company_pct))
                base_rate = f"{master_pct_display}/{company_pct_display}"

        text += "\n💰 <b>Финансовая информация:</b>\n"
        text += f"• Сумма заказа: <b>{order.total_amount:.2f} ₽</b>\n"
        text += f"• Чистая прибыль: <b>{net_profit:.2f} ₽</b>\n"
        text += f"\n📊 <b>Распределение ({base_rate}):</b>\n"

        if order.master_profit:
            master_percent = (order.master_profit / net_profit * 100) if net_profit > 0 else 0
            text += f"• Ваша прибыль: <b>{order.master_profit:.2f} ₽</b> ({master_percent:.0f}%)\n"
        if order.company_profit:
            company_percent = (order.company_profit / net_profit * 100) if net_profit > 0 else 0
            text += f"• Прибыль компании: <b>{order.company_profit:.2f} ₽</b> ({company_percent:.0f}%)\n"

        # Надбавки и бонусы (показываем только если явно True)
        bonuses = []
        if order.has_review is True:
            bonuses.append("✅ Отзыв")
        if order.out_of_city is True:
            bonuses.append("✅ Выезд за город")

        if bonuses:
            text += f"\n🎁 <b>Надбавки:</b> {', '.join(bonuses)}\n"

        text += "\n"

    # Дата создания уже показана OrderPresenter

    keyboard = get_order_actions_keyboard(order, UserRole.MASTER)

    message_obj = callback.message
    if not isinstance(message_obj, Message):
        await callback.answer("❌ Сообщение недоступно", show_alert=True)
        return

    await message_obj.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("accept_order:"))
async def callback_accept_order(callback: CallbackQuery, user_roles: list, db: Database):
    """
    Принятие заявки мастером

    Args:
        callback: Callback query
        user_roles: Роли пользователя (передаётся из RoleCheckMiddleware)
        db: Database instance (injected)
    """
    if not callback.data:
        return
    order_id = int(callback.data.split(":")[1])

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        # Проверяем права
        if not master:
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        assert order is not None  # Added assertion for mypy # nosec
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

        # Перезагружаем заказ и мастера для получения актуальных данных
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ACCEPT_ORDER",
            details=f"Accepted order #{order_id}",
        )

        # Уведомляем диспетчера с retry механизмом
        assert order is not None  # Added assertion for mypy # nosec
        if order.dispatcher_id:
            from app.utils import safe_send_message

            assert order.dispatcher_id is not None  # Added assertion for mypy # nosec
            result = await safe_send_message(
                callback.bot,
                order.dispatcher_id,
                f"✅ Мастер {master.get_display_name() if master else 'Неизвестный мастер'} принял заявку #{order_id}",
                parse_mode="HTML",
            )
            if not result:
                logger.error(
                    f"Не удалось уведомить диспетчера {order.dispatcher_id} после повторных попыток"
                )

        # Формируем текст с деталями заявки
        assert order is not None  # nosec B101
        acceptance_text = (
            f"✅ <b>Заявка #{order_id} принята!</b>\n\n"
            f"🔧 <b>Детали заявки:</b>\n"
            f"📱 Тип техники: {order.equipment_type}\n"
            f"📝 Описание: {order.description}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n"
        )

        # Добавляем заметки если есть
        if order and order.notes:
            acceptance_text += f"\n📝 <b>Заметки:</b> {order.notes}\n"

        # Добавляем время прибытия если указано
        if order and order.scheduled_time:
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

        message_obj = callback.message
        if not isinstance(message_obj, Message):
            await callback.answer("❌ Сообщение недоступно", show_alert=True)
            return

        await message_obj.edit_text(
            acceptance_text, parse_mode="HTML", reply_markup=keyboard_builder.as_markup()
        )

        log_action(callback.from_user.id, "ACCEPT_ORDER", f"Order #{order_id}")

    except Exception as e:
        logger.exception(f"Error accepting order #{order_id}: {e}")
        raise

    # Защита от двойного клика: 10 секунд для критичной операции
    from app.utils import safe_answer_callback

    await safe_answer_callback(callback, "Заявка принята!", cache_time=10)


@router.callback_query(F.data.startswith("refuse_order_master:"))
async def callback_refuse_order_master(
    callback: CallbackQuery, user_roles: list, state: FSMContext, db: Database
):
    """
    Начало процесса отклонения/отмены заявки мастером (запрос причины)

    Args:
        callback: Callback query
        user_roles: Роли пользователя (передаётся из RoleCheckMiddleware)
        state: FSM контекст
        db: Database instance (injected)
    """
    if not callback.data:
        return
    order_id = int(callback.data.split(":")[1])

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

        # Проверяем роль пользователя
        user = await db.get_user_by_telegram_id(callback.from_user.id)
        is_admin = False
        if user:
            is_admin = "ADMIN" in user.get_roles()

        assert order is not None  # Added assertion for mypy # nosec
        if not is_admin and order.assigned_master_id != master.id:
            logger.warning(
                f"[REFUSE] Access denied - Master ID: {master.id}, Assigned: {order.assigned_master_id}"
            )
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Сохраняем order_id в state и запрашиваем причину отказа/отмены
        await state.set_state(RefuseOrderStates.enter_refuse_reason)
        await state.update_data(order_id=order_id)

        action_type = (
            "отмены" if order.status in [OrderStatus.NEW, OrderStatus.ACCEPTED] else "отказа"
        )

        message_obj = callback.message
        if not isinstance(message_obj, Message):
            await callback.answer("❌ Сообщение недоступно", show_alert=True)
            return

        await message_obj.edit_text(
            f"📝 Укажите причину {action_type} заявки #{order_id}:\n\n"
            f"Например: 'Слишком далеко', 'Нет запчастей', 'Некорректный адрес' и т.д.",
            reply_markup=None,
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"[REFUSE] Error in refuse_order_master: {e}")
        await callback.answer("Произошла ошибка при обработке запроса", show_alert=True)


@router.message(RefuseOrderStates.enter_refuse_reason)
async def process_refuse_reason(message: Message, state: FSMContext):
    """
    Обработка ввода причины отказа/отмены и выполнение отказа

    Args:
        message: Сообщение с причиной
        state: FSM контекст
    """
    if not message.text:
        await message.reply("❌ Пожалуйста, укажите причину отказа.")
        return
    refuse_reason = message.text.strip()

    if not refuse_reason or len(refuse_reason) < 3:
        await message.reply(
            "❌ Причина слишком короткая. Пожалуйста, укажите более подробную причину (минимум 3 символа):"
        )
        return

    # Получаем данные из state
    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await message.reply("❌ Ошибка: не найден ID заявки. Попробуйте еще раз.")
        await state.clear()
        return

    db = get_database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            await message.reply("❌ Ошибка: заявка не найдена.")
            return
        assert order is not None  # Added assertion for mypy # nosec

        # Получаем роли пользователя из state (если есть) или из БД
        user_roles = data.get("user_roles", [])
        if not user_roles:
            user_telegram_id = message.from_user.id if message.from_user else None
            if user_telegram_id is not None:
                user = await db.get_user_by_telegram_id(user_telegram_id)
                if user:
                    user_roles = user.get_roles()

        # Для мастеров проверяем наличие мастера, для диспетчеров/админов - не требуется
        master = None
        if UserRole.MASTER in user_roles:
            user_telegram_id = message.from_user.id if message.from_user else None
            if user_telegram_id is not None:
                master = await db.get_master_by_telegram_id(user_telegram_id)
            if not master:
                await message.reply("❌ Ошибка: мастер не найден.")
                return
        elif UserRole.ADMIN in user_roles or UserRole.DISPATCHER in user_roles:
            # Для админа/диспетчера получаем мастера из заявки (если назначен)
            if order.assigned_master_id is not None:
                master = await db.get_master_by_id(order.assigned_master_id)

        # Удаляем карточки заявки в рабочей группе (если были сохранены)
        try:
            if hasattr(db, "get_active_group_messages_by_order"):
                messages = await db.get_active_group_messages_by_order(order_id)
                if messages:
                    from app.utils.retry import safe_delete_message

                    for m in messages:
                        await safe_delete_message(message.bot, m.chat_id, m.message_id)
                    from app.database.orm_database import ORMDatabase

                    if isinstance(db, ORMDatabase):
                        await db.deactivate_group_messages(order_id)
        except (
            Exception
        ):  # nosec B110 - игнорирование ошибок деактивации групповых сообщений не критично
            pass

        # Возвращаем статус в NEW и убираем мастера, сохраняем причину отказа
        if hasattr(db, "unassign_master_from_order"):
            await db.unassign_master_from_order(order_id, refuse_reason=refuse_reason)
        else:
            # Legacy: прямой SQL
            from app.database.orm_database import ORMDatabase

            if isinstance(db, ORMDatabase):
                async with db.get_session() as session:
                    from sqlalchemy import text

                    await session.execute(
                        text(
                            "UPDATE orders SET status = :status, assigned_master_id = NULL, refuse_reason = :refuse_reason WHERE id = :order_id"
                        ),
                        {
                            "status": OrderStatus.NEW,
                            "order_id": order_id,
                            "refuse_reason": refuse_reason,
                        },
                    )
                    await session.commit()

        # Перезагружаем заказ для получения актуальных данных
        order = await db.get_order_by_id(order_id)

        # Добавляем в лог
        user_telegram_id = message.from_user.id if message.from_user else None
        if user_telegram_id is not None:
            await db.add_audit_log(
                user_id=user_telegram_id,
                action="REFUSE_ORDER_MASTER",
                details=f"Master refused order #{order_id}, reason: {refuse_reason}",
            )
        else:
            logger.warning("Audit log skipped: message.from_user.id is None")

        action_type = (
            "отменена"
            if order and order.status in [OrderStatus.NEW, OrderStatus.ACCEPTED]
            else "отклонена"
        )

        # Проверяем, откуда был отказ (группа или админ)
        group_chat_id = data.get("group_chat_id")
        group_message_id = data.get("group_message_id")
        admin_message_id = data.get("admin_message_id")
        admin_chat_id = data.get("admin_chat_id")
        user_roles = data.get("user_roles", [])

        if admin_message_id and admin_chat_id:
            # Отказ от админа/диспетчера
            user_telegram_id = message.from_user.id if message.from_user else None
            await db.update_order_status(
                order_id=order_id,
                status=OrderStatus.REFUSED,
                changed_by=user_telegram_id,  # Use the null-checked variable
                user_roles=user_roles,
            )

            # Уведомляем мастера если был назначен
            if (
                order
                and order.assigned_master_id
                and (not master or order.assigned_master_id != master.id)
            ):
                assigned_master = await db.get_master_by_id(order.assigned_master_id)
                if assigned_master:
                    from app.utils import safe_send_message

                    await safe_send_message(
                        message.bot,
                        assigned_master.telegram_id,
                        f"ℹ️ Заявка #{order_id} была отклонена.\n" f"📝 Причина: {refuse_reason}",
                        parse_mode="HTML",
                        max_attempts=3,
                    )

            await message.reply(
                f"✅ Заявка #{order_id} {action_type}.\n" f"Причина: {refuse_reason}",
                reply_markup=None,
            )

            # Обновляем исходное сообщение админа
            try:
                if message.bot is not None:
                    await message.bot.edit_message_text(
                        chat_id=admin_chat_id,
                        message_id=admin_message_id,
                        text=f"❌ Заявка #{order_id} {action_type}.\n📝 Причина: {refuse_reason}",
                    )
            except Exception as e:
                logger.error(f"Failed to update admin message: {e}")

        elif group_chat_id and group_message_id:
            # Отказ из группы - обновляем сообщение в группе
            try:
                from app.utils import get_now
                from app.utils.helpers import format_datetime

                master_name = master.get_display_name() if master else "Не назначен"
                if message.bot is not None:  # Added check for message.bot
                    assert order is not None  # Added assertion for mypy # nosec
                    await message.bot.edit_message_text(
                        chat_id=group_chat_id,
                        message_id=group_message_id,
                        text=(
                            f"❌ <b>Заявка #{order_id} {action_type}</b>\n\n"
                            f"👨‍🔧 Мастер: {master_name}\n"
                            f"📝 Причина: {refuse_reason}\n"
                            f"📋 Статус: Требует нового назначения\n"
                            f"⏰ Время: {format_datetime(get_now())}\n\n"
                            f"🔧 <b>Детали заявки:</b>\n"
                            f"📱 Тип техники: {order.equipment_type}\n"
                            f"📝 Описание: {order.description}\n"
                            f"👤 Клиент: {order.client_name}\n"
                            f"📍 Адрес: {order.client_address}\n\n"
                            f"Диспетчер получил уведомление."
                        ),
                        parse_mode="HTML",
                    )
            except Exception as e:
                logger.error(f"Failed to update group message: {e}")

            await message.reply(
                f"✅ Заявка #{order_id} {action_type}.\n"
                f"Причина: {refuse_reason}\n\n"
                f"Сообщение в группе обновлено.",
                reply_markup=get_main_menu_keyboard([UserRole.MASTER]),
            )
        else:
            # Отказ из личного чата мастера
            await message.reply(
                f"✅ Заявка #{order_id} {action_type}.\n"
                f"Причина: {refuse_reason}\n\n"
                f"Диспетчер получил уведомление.",
                reply_markup=get_main_menu_keyboard([UserRole.MASTER]),
            )

        # Уведомляем диспетчера с retry механизмом
        assert order is not None  # Added assertion for mypy # nosec
        if order.dispatcher_id is not None:
            assert order.dispatcher_id is not None  # Added assertion for mypy # nosec
            from app.utils import safe_send_message

            # Формируем текст уведомления в зависимости от того, кто отказал
            if UserRole.MASTER in user_roles and master:
                # Отказ от мастера
                notification_text = (
                    f"❌ Мастер {master.get_display_name()} {action_type} заявку #{order_id}\n"
                    f"📝 Причина: {refuse_reason}"
                )
            else:
                # Отказ от админа/диспетчера
                user_telegram_id = message.from_user.id if message.from_user else None
                if user_telegram_id is not None:
                    user = await db.get_user_by_telegram_id(user_telegram_id)
                user_name = user.get_display_name() if user else "Администратор"
                notification_text = (
                    f"❌ {user_name} {action_type} заявку #{order_id}\n"
                    f"📝 Причина: {refuse_reason}"
                )

            result = await safe_send_message(
                message.bot,
                order.dispatcher_id,
                notification_text,
                parse_mode="HTML",
                max_attempts=3,
            )
            if not result:
                logger.error(
                    f"Не удалось уведомить диспетчера {order.dispatcher_id} после повторных попыток"
                )

        user_telegram_id = message.from_user.id if message.from_user else None
        if user_telegram_id is not None:
            log_action(
                user_telegram_id,
                "REFUSE_ORDER_MASTER",
                f"Order #{order_id}, reason: {refuse_reason}",
            )
        else:
            logger.warning("Log action skipped: message.from_user.id is None")

    finally:
        await db.disconnect()
        await state.clear()


@router.callback_query(F.data.startswith("onsite_order:"))
async def callback_onsite_order(callback: CallbackQuery, user_roles: list, db: Database):
    """
    Мастер на объекте

    Args:
        callback: Callback query
        user_roles: Роли пользователя (передаётся из RoleCheckMiddleware)
        db: Database instance (injected)
    """
    if not callback.data:
        return
    order_id = int(callback.data.split(":")[1])

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        # Проверяем права
        if not master:
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        # Проверяем роль пользователя
        user = await db.get_user_by_telegram_id(callback.from_user.id)
        is_admin = False
        if user:
            is_admin = "ADMIN" in user.get_roles()

        assert order is not None  # Added assertion for mypy # nosec
        if not is_admin and order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Обновляем статус (с валидацией через State Machine)
        await db.update_order_status(
            order_id=order_id,
            status=OrderStatus.ONSITE,
            changed_by=callback.from_user.id,
            user_roles=user_roles,
        )

        # Перезагружаем заказ и мастера для получения актуальных данных
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ONSITE_ORDER",
            details=f"Master on site for order #{order_id}",
        )

        # Уведомляем диспетчера с retry механизмом
        assert order is not None  # Added assertion for mypy # nosec
        if order.dispatcher_id is not None:
            assert order.dispatcher_id is not None  # Added assertion for mypy # nosec
            from app.utils import safe_send_message

            result = await safe_send_message(
                callback.bot,
                order.dispatcher_id,
                f"🏠 Мастер {master.get_display_name() if master else 'Неизвестный мастер'} на объекте (Заявка #{order_id})",
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

        message_obj = callback.message
        if not isinstance(message_obj, Message):
            await callback.answer("❌ Сообщение недоступно", show_alert=True)
            return

        await message_obj.edit_text(
            f"🏠 <b>Статус обновлен!</b>\n\n" f"Заявка #{order_id} - вы на объекте.",
            parse_mode="HTML",
            reply_markup=keyboard_builder.as_markup(),
        )

        log_action(callback.from_user.id, "ONSITE_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Статус обновлен!")


@router.callback_query(F.data.startswith("low_amount_is_refusal:"))
async def callback_low_amount_refusal_confirmation(callback: CallbackQuery, state: FSMContext):
    """
    Обработка ответа на вопрос "Это отказ?" при сумме <1000р

    Args:
        callback: Callback query
        state: FSM контекст
    """
    if not callback.data:
        return
    answer = callback.data.split(":")[1]  # yes или no

    data = await state.get_data()
    total_amount = data.get("total_amount", 0)
    order_id = data.get("order_id")

    if answer == "yes":
        # Это отказ - запрашиваем причину
        await state.set_state(CompleteOrderStates.enter_refuse_reason_on_complete)

        message_obj = callback.message
        if not isinstance(message_obj, Message):
            await callback.answer("❌ Сообщение недоступно", show_alert=True)
            return

        await message_obj.edit_text(
            f"📝 Укажите причину отказа от заявки #{order_id}:\n\n"
            f"Например: 'Слишком мелкий заказ', 'Клиент отказался', 'Нет смысла' и т.д.",
            reply_markup=None,
        )
        await callback.answer()
    else:
        # Не отказ - продолжаем обычный процесс завершения
        await callback.answer("Продолжаем обычное завершение заявки")
        message_obj = callback.message
        if not isinstance(message_obj, Message):
            return
        await message_obj.delete()

        # Переходим к запросу суммы расходного материала
        await state.set_state(CompleteOrderStates.enter_materials_cost)

        # Удаляем промпт-сообщение
        prompt_message_id = data.get("prompt_message_id")
        if not isinstance(callback.message, Message):  # Added check
            await callback.answer("❌ Сообщение недоступно", show_alert=True)  # Added error message
            return  # Added return
        allowed_chat_id = data.get("allowed_chat_id") or callback.message.chat.id

        if prompt_message_id:
            try:
                from app.utils.retry import safe_delete_message

                await safe_delete_message(callback.bot, allowed_chat_id, prompt_message_id)
                logger.info(f"Deleted prompt message {prompt_message_id} after total amount input")
            except Exception as e:
                logger.warning(f"Failed to delete prompt message {prompt_message_id}: {e}")

        materials_prompt = await callback.message.answer(
            f"✅ Общая сумма заказа: <b>{total_amount:.2f} ₽</b>\n\n"
            f"Теперь введите <b>сумму расходного материала</b> (в рублях):\n"
            f"Например: 1500 или 1500.50\n\n"
            f"Если расходного материала не было, введите: 0",
            parse_mode="HTML",
        )

        # Сохраняем ID текущего сообщения для последующего удаления
        await state.update_data(
            current_prompt_message_id=materials_prompt.message_id,
            current_prompt_chat_id=materials_prompt.chat.id,
        )


@router.message(CompleteOrderStates.enter_refuse_reason_on_complete)
async def process_refuse_reason_on_complete(message: Message, state: FSMContext):
    """
    Обработка ввода причины отказа при завершении с суммой <1000р

    Args:
        message: Сообщение с причиной
        state: FSM контекст
    """
    if not message.text:
        await message.reply(
            "❌ Причина слишком короткая. Пожалуйста, укажите более подробную причину (минимум 3 символа):"
        )
        return
    refuse_reason = message.text.strip()

    if not refuse_reason or len(refuse_reason) < 3:
        await message.reply(
            "❌ Причина слишком короткая. Пожалуйста, укажите более подробную причину (минимум 3 символа):"
        )
        return

    # Получаем данные из state
    data = await state.get_data()
    order_id = data.get("order_id")
    acting_as_master_id = data.get("acting_as_master_id")
    total_amount = data.get("total_amount", 0)

    # Устанавливаем значения для отказа
    await state.update_data(
        materials_cost=0.0, has_review=False, out_of_city=False, refuse_reason=refuse_reason
    )

    if order_id is None:
        logger.error("Error in process_refuse_reason_on_complete: order_id is None")
        await message.reply("❌ Ошибка: не найден ID заявки. Попробуйте еще раз.")
        await state.clear()
        return

    # Завершаем заказ как отказ с указанной причиной и суммой
    await complete_order_as_refusal(
        message,
        state,
        order_id,
        acting_as_master_id,
        refuse_reason=refuse_reason,
        total_amount=float(total_amount),
    )


@router.callback_query(F.data.startswith("refuse_order_complete:"))
async def callback_refuse_order_complete(callback: CallbackQuery, state: FSMContext, db: Database):
    """
    Быстрое завершение заявки как отказ (0 рублей)

    Args:
        callback: Callback query
        state: FSM контекст
        db: Database instance (injected)
    """
    if not callback.data:
        return
    order_id = int(callback.data.split(":")[1])

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        # Проверяем права
        if not master:
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        # Проверяем роль пользователя
        user = await db.get_user_by_telegram_id(callback.from_user.id)
        is_admin = False
        if user:
            is_admin = "ADMIN" in user.get_roles()

        assert order is not None  # Added assertion for mypy # nosec
        if not is_admin and order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Сохраняем order_id в состоянии
        await state.update_data(order_id=order_id)

        # Переходим к подтверждению отказа
        from app.states import RefuseOrderStates

        await state.set_state(RefuseOrderStates.confirm_refusal)

        # Показываем подтверждение
        message_obj = callback.message
        if not isinstance(message_obj, Message):
            await callback.answer("❌ Сообщение недоступно", show_alert=True)
            return

        assert order is not None  # Added assertion for mypy # nosec
        await message_obj.edit_text(
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
async def callback_complete_order(callback: CallbackQuery, state: FSMContext, db: Database):
    """
    Начало процесса завершения заявки мастером

    Args:
        callback: Callback query
        state: FSM контекст
        db: Database instance (injected)
    """
    if not callback.data:
        return
    order_id = int(callback.data.split(":")[1])

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        # Проверяем права
        if not master:
            await callback.answer("Вы не зарегистрированы как мастер", show_alert=True)
            return

        # Проверяем роль пользователя
        user = await db.get_user_by_telegram_id(callback.from_user.id)
        is_admin = False
        if user:
            is_admin = "ADMIN" in user.get_roles()

        assert order is not None  # Added assertion for mypy # nosec
        if not is_admin and order.assigned_master_id != master.id:
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # Сохраняем контекст завершения в FSM
        if not isinstance(callback.message, Message):  # Added check
            await callback.answer("❌ Сообщение недоступно", show_alert=True)  # Added error message
            return  # Added return
        await state.update_data(
            order_id=order_id,
            initiator_user_id=callback.from_user.id,
            allowed_chat_id=callback.message.chat.id,
        )

        # Переходим в состояние запроса общей суммы
        from app.keyboards.reply import get_cancel_keyboard
        from app.states import CompleteOrderStates

        await state.set_state(CompleteOrderStates.enter_total_amount)

        prompt = await callback.message.answer(
            f"💰 <b>Завершение заявки #{order_id}</b>\n\n"
            f"Пожалуйста, введите <b>общую сумму заказа</b> (в рублях):\n"
            f"Например: 5000, 5000.50 или 0",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard(),
        )

        await state.update_data(prompt_message_id=prompt.message_id)

        log_action(callback.from_user.id, "START_COMPLETE_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("dr_order:"))
async def callback_dr_order(callback: CallbackQuery, state: FSMContext, db: Database):
    """
    ДР - запрос срока окончания

    Args:
        callback: Callback query
        state: FSM контекст
        db: Database instance (injected)
    """
    if not callback.data:
        return
    order_id = int(callback.data.split(":")[1])

    logger.debug(f"[DR] Starting DR process for order #{order_id} by user {callback.from_user.id}")

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        logger.debug(f"[DR] Order found: {order is not None}, Master found: {master is not None}")

        # Проверяем роль пользователя
        user = await db.get_user_by_telegram_id(callback.from_user.id)
        is_admin = False
        if user:
            is_admin = "ADMIN" in user.get_roles()

        # Проверяем права
        # Если админ, то пропускаем проверку на совпадение мастера
        if not is_admin and (
            not master or (order is not None and order.assigned_master_id != master.id)
        ):
            logger.warning(
                f"[DR] Access denied - Master ID: {master.id if master else None}, Assigned: {order.assigned_master_id if order else None}"
            )
            await callback.answer("Это не ваша заявка", show_alert=True)
            return

        # ВАЛИДАЦИЯ: Проверяем, что заявка ещё НЕ в статусе DR
        if order is not None and order.status == OrderStatus.DR:
            logger.warning(f"[DR] Order #{order_id} is already in DR status")
            await callback.answer(
                "❌ Эта заявка уже в статусе 'ДР'!\n"
                "Для изменения срока используйте кнопку '✏️ Редактировать'",
                show_alert=True,
            )
            return

        # ВАЛИДАЦИЯ: Можно переводить в DR только из статуса ONSITE
        if order is not None and order.status != OrderStatus.ONSITE:
            logger.warning(f"[DR] Cannot move order #{order_id} to DR from status {order.status}")
            await callback.answer(
                "❌ Перевести в длительный ремонт можно только из статуса 'На объекте'",
                show_alert=True,
            )
            return

        # Сохраняем order_id в state
        await state.update_data(order_id=order_id)

        logger.debug("[DR] Transitioning to LongRepairStates.enter_completion_date")

        # Переходим к вводу срока окончания
        await state.set_state(LongRepairStates.enter_completion_date)

        message_obj = callback.message
        if not isinstance(message_obj, Message):
            await callback.answer("❌ Сообщение недоступно", show_alert=True)
            return

        await message_obj.edit_text(
            f"⏳ <b>ДР - Заявка #{order_id}</b>\n\n"
            f"Введите <b>примерный срок окончания ремонта</b>.\n\n"
            f"<b>Примеры:</b>\n"
            f"• завтра\n"
            f"• через 3 дня\n"
            f"• через неделю\n"
            f"• 25.12.2025",
            parse_mode="HTML",
        )

        await callback.answer()

    finally:
        await db.disconnect()


@router.message(LongRepairStates.enter_completion_date, F.text)
async def process_dr_info(message: Message, state: FSMContext, user_roles: list):
    """
    Обработка ввода срока окончания для DR

    Args:
        message: Сообщение
        state: FSM контекст
        user_roles: Список ролей пользователя
    """
    import re

    user_id = message.from_user.id if message.from_user else "Unknown"
    logger.debug(f"[DR] Processing DR completion date from user {user_id}")

    # Получаем данные из state
    data = await state.get_data()
    order_id = data.get("order_id")

    logger.debug(f"[DR] Order ID from state: {order_id}, FSM data: {data}")

    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "⚠️ Пожалуйста, отправьте текстовое сообщение со сроком окончания ремонта."
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
        db = get_database()
        await db.connect()
        try:
            user = None
            if message.from_user and message.from_user.id:
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

    completion_date = text

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

    db = get_database()
    await db.connect()

    try:
        if order_id is None:
            logger.error("Error in process_dr_info: order_id is None")
            await message.reply("❌ Ошибка: не найден ID заявки. Попробуйте еще раз.")
            await state.clear()
            return

        order = await db.get_order_by_id(order_id)

        if not order:
            logger.error(f"[DR] Ошибка - Заявка не найдена: {order_id}")
            await message.reply("❌ Ошибка: заявка не найдена")
            await state.clear()
            return

        # Для мастера проверяем, что он назначен на эту заявку
        # Для администратора проверка не нужна
        master = None
        if message.from_user and message.from_user.id:
            master = await db.get_master_by_telegram_id(message.from_user.id)

            user = None
            if message.from_user:
                user = await db.get_user_by_telegram_id(message.from_user.id)
        is_admin = False
        if user:
            is_admin = "ADMIN" in user.get_roles()

        logger.debug(
            f"[DR] Order found: {order is not None}, Master found: {master is not None}, Is Admin: {is_admin}"
        )

        # Если это не администратор, проверяем что мастер назначен
        # Если пользователь админ, он может переводить в ДР любые заявки
        if not is_admin and master is not None and order.assigned_master_id != master.id:
            logger.error(
                f"[DR] Master {master.id if master else 'None'} not assigned to order {order_id}"
            )
            await message.reply("❌ Ошибка: эта заявка назначена другому мастеру")
            await state.clear()
            return

        # Сохраняем дату в состоянии
        await state.update_data(completion_date=completion_date)

        # Переходим к вводу информации о запчастях
        await state.set_state(LongRepairStates.enter_parts_info)
        
        await message.answer(
            f"🔧 <b>Информация о запчастях</b>\n\n"
            f"Укажите, какие запчасти требуют замены.\n\n"
            f"<i>Если запчасти не требуются, напишите 'нет' или 'не требуются'</i>",
            parse_mode="HTML",
        )

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


@router.message(LongRepairStates.enter_parts_info, F.text)
async def process_parts_info(message: Message, state: FSMContext):
    """
    Обработка информации о запчастях
    
    Args:
        message: Сообщение
        state: FSM контекст
    """
    if not message.text:
        await message.reply("⚠️ Пожалуйста, отправьте текстовое сообщение.")
        return
    
    parts_info = message.text.strip()
    
    # Проверяем на отмену
    if parts_info.lower() in ["отмена", "отменить", "❌ отмена", "cancel"]:
        await message.answer(
            "❌ Перевод в длительный ремонт отменен.", reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        
        # Показываем главное меню
        db = get_database()
        await db.connect()
        try:
            user = None
            if message.from_user and message.from_user.id:
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
    
    # Сохраняем информацию о запчастях
    await state.update_data(parts_info=parts_info)
    
    # Переходим к вводу суммы согласования
    await state.set_state(LongRepairStates.enter_estimated_cost)
    
    await message.answer(
        f"💰 <b>Предварительная сумма</b>\n\n"
        f"Укажите предварительную сумму согласования с клиентом.\n\n"
        f"<b>Примеры:</b>\n"
        f"• 5000\n"
        f"• 12500.50\n\n"
        f"<i>Если сумма еще не согласована, напишите 'нет' или '0'</i>",
        parse_mode="HTML",
    )


@router.message(LongRepairStates.enter_estimated_cost, F.text)
async def process_estimated_cost(message: Message, state: FSMContext):
    """
    Обработка предварительной суммы согласования с клиентом
    
    Args:
        message: Сообщение
        state: FSM контекст
    """
    if not message.text:
        await message.reply("⚠️ Пожалуйста, отправьте текстовое сообщение.")
        return
    
    cost_text = message.text.strip()
    
    # Проверяем на отмену
    if cost_text.lower() in ["отмена", "отменить", "❌ отмена", "cancel"]:
        await message.answer(
            "❌ Перевод в длительный ремонт отменен.", reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        
        # Показываем главное меню
        db = get_database()
        await db.connect()
        try:
            user = None
            if message.from_user and message.from_user.id:
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
    
    # Парсим сумму
    estimated_cost = None
    if cost_text.lower() not in ["нет", "не", "no", "0"]:
        try:
            # Заменяем запятую на точку и пробуем распарсить
            cost_text_cleaned = cost_text.replace(",", ".").replace(" ", "")
            estimated_cost = float(cost_text_cleaned)
            
            if estimated_cost < 0:
                await message.reply(
                    "❌ Сумма не может быть отрицательной. Попробуйте еще раз."
                )
                return
        except ValueError:
            await message.reply(
                f"❌ Не удалось распознать сумму: '{cost_text}'\n\n"
                f"Пожалуйста, введите число (например: 5000 или 12500.50)"
            )
            return
    
    # Сохраняем сумму
    await state.update_data(estimated_cost=estimated_cost)
    
    # Показываем подтверждение
    await show_dr_confirmation(message, state)


@router.message(F.text == "📊 Моя статистика")
@handle_errors
async def btn_my_stats(message: Message, user_role: str, user_roles: list, db: Database):
    """
    Статистика мастера

    Args:
        message: Сообщение
        user_role: Роль пользователя
        user_roles: Список ролей пользователя
        db: Database instance (injected)
    """
    # Проверка роли
    if user_role not in [UserRole.MASTER, UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    # Проверяем, что это не личное сообщение (только для чистых мастеров, админ может работать в приватном чате)
    if (
        message.chat.type == "private"
        and user_role == UserRole.MASTER
        and UserRole.ADMIN not in user_roles
    ):
        await message.answer(
            "⚠️ <b>Работа только в рабочей группе!</b>\n\n"
            "Для мастеров взаимодействие с ботом доступно только в рабочей группе.",
            parse_mode="HTML",
        )
        return

    try:
        master = None
        if message.from_user and message.from_user.id:
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

        assert master.id is not None  # Added assertion for mypy # nosec
        # Получаем все заявки мастера
        orders = await db.get_orders_by_master(master.id, exclude_closed=False)

        # Подсчитываем статистику
        total = len(orders)
        by_status: dict[str, int] = {}

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

        assert master.id is not None  # Added assertion for mypy # nosec
        keyboard = get_master_stats_keyboard(master.id)

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    finally:
        await db.disconnect()


@router.message(CompleteOrderStates.enter_total_amount, ~F.text.startswith("/"))
async def process_total_amount(message: Message, state: FSMContext):
    """
    Обработка ввода общей суммы заказа (работает и в личке, и в группе)

    Args:
        message: Сообщение
        state: FSM контекст
    """
    # Проверяем, не нажата ли кнопка отмены
    if message.text == "❌ Отмена":
        # Получаем роли пользователя для правильной клавиатуры
        try:
            _db = get_database()
            await _db.connect()
            try:
                if message.from_user is None:
                    user_roles = ["MASTER"]
                else:
                    _user = await _db.get_user_by_telegram_id(message.from_user.id)
                    user_roles = _user.role.split(",") if _user and _user.role else ["MASTER"]
            finally:
                await _db.disconnect()
        except Exception:
            user_roles = ["MASTER"]

        await state.clear()
        await message.reply(
            "❌ Завершение заявки отменено.", reply_markup=get_main_menu_keyboard(user_roles)
        )
        return

    # Добавляем логирование для отладки
    user_telegram_id = message.from_user.id if message.from_user else "Unknown"
    logger.info(
        f"[PROCESS_TOTAL_AMOUNT] Received message: '{message.text}' from user {user_telegram_id} in chat {message.chat.id}"
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
    user_telegram_id_check = message.from_user.id if message.from_user else None
    if initiator_user_id and user_telegram_id_check == initiator_user_id:
        is_sender_allowed = True

    # Проверка 2: в нужном чате
    if allowed_chat_id and message.chat and message.chat.id == allowed_chat_id:
        is_sender_allowed = True

    # Проверка 3: реплай на промпт-сообщение (для ForceReply)
    if (
        prompt_message_id
        and message.reply_to_message
        and message.reply_to_message.message_id == prompt_message_id
    ):
        is_sender_allowed = True

    # Проверка 4: админ действует за мастера
    user_telegram_id_acting = message.from_user.id if message.from_user else None
    if acting_as_master_id and user_telegram_id_acting == acting_as_master_id:
        is_sender_allowed = True

    if not is_sender_allowed:
        # Дополнительный допуск: администратор может вводить сумму из любого чата
        try:
            from app.config import UserRole as _UserRole

            _db = get_database()
            await _db.connect()
            try:
                user_telegram_id_admin_override = (
                    message.from_user.id if message.from_user else None
                )
                if user_telegram_id_admin_override is not None:
                    _user = await _db.get_user_by_telegram_id(user_telegram_id_admin_override)
                    if _user and _user.has_role(_UserRole.ADMIN):
                        is_sender_allowed = True
                        logger.info(
                            f"[PROCESS_TOTAL_AMOUNT] Admin override allowed for user {user_telegram_id_admin_override}"
                        )
            finally:
                await _db.disconnect()
        except (
            Exception
        ) as exc:  # nosec B110 - игнорирование ошибок проверки админского override не критично
            logger.debug("Admin override check failed in PROCESS_TOTAL_AMOUNT: %s", exc)

    if not is_sender_allowed:
        user_telegram_id_warning = message.from_user.id if message.from_user else "Unknown"
        logger.warning(
            f"[PROCESS_TOTAL_AMOUNT] Rejected message from user {user_telegram_id_warning} in chat {message.chat.id}. "
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
        raw_text.replace("\u00a0", "")
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

    # Если сумма 0 или до 1000 рублей, спрашиваем - это отказ?
    if total_amount <= 1000:
        await state.set_state(CompleteOrderStates.confirm_low_amount_refusal)

        # Создаем инлайн-клавиатуру
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Да, это отказ", callback_data="low_amount_is_refusal:yes"
                    ),
                    InlineKeyboardButton(
                        text="❌ Нет, продолжить", callback_data="low_amount_is_refusal:no"
                    ),
                ]
            ]
        )

        warning_text = (
            f"⚠️ Указана сумма {total_amount:.2f} ₽"
            + (" (нулевая сумма)" if total_amount == 0 else " (меньше 1000 рублей)")
            + ".\n\n<b>Это отказ от заявки?</b>"
        )
        await message.reply(
            warning_text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    # Удаляем промпт-сообщение сразу после ввода суммы
    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")
    allowed_chat_id = data.get("allowed_chat_id") or message.chat.id

    if prompt_message_id:
        try:
            from app.utils.retry import safe_delete_message

            await safe_delete_message(message.bot, allowed_chat_id, prompt_message_id)
            logger.info(f"Deleted prompt message {prompt_message_id} after total amount input")
        except Exception as e:
            logger.warning(f"Failed to delete prompt message {prompt_message_id}: {e}")

    # Переходим к запросу суммы расходного материала
    await state.set_state(CompleteOrderStates.enter_materials_cost)

    prompt_text = (
        f"✅ Общая сумма заказа: <b>{total_amount:.2f} ₽</b>\n\n"
        f"Теперь введите <b>сумму расходного материала</b> (в рублях):\n"
        f"Например: 1500 или 1500.50\n\n"
        f"Если расходного материала не было, введите: 0"
    )

    try:
        materials_prompt = await message.reply(prompt_text, parse_mode="HTML")
    except TelegramBadRequest:
        # Если сообщение пользователя удалено, отправляем новое сообщение
        materials_prompt = await message.answer(prompt_text, parse_mode="HTML")

    # Сохраняем ID текущего сообщения для последующего удаления
    await state.update_data(
        current_prompt_message_id=materials_prompt.message_id,
        current_prompt_chat_id=materials_prompt.chat.id,
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
        try:
            await message.reply(
                "❌ Пожалуйста, отправьте текстовое сообщение с суммой.\n"
                "Введите число (например: 500, 0):"
            )
        except TelegramBadRequest:
            await message.answer(
                "❌ Пожалуйста, отправьте текстовое сообщение с суммой.\n"
                "Введите число (например: 500, 0):"
            )
        return

    # Проверяем, что введена корректная сумма
    try:
        materials_cost = float(message.text.replace(",", ".").strip())
        if materials_cost < 0:
            try:
                await message.reply(
                    "❌ Сумма не может быть отрицательной.\n"
                    "Попробуйте еще раз (или введите 0, если расходов не было):"
                )
            except TelegramBadRequest:
                await message.answer(
                    "❌ Сумма не может быть отрицательной.\n"
                    "Попробуйте еще раз (или введите 0, если расходов не было):"
                )
            return
    except ValueError:
        try:
            await message.reply(
                "❌ Неверный формат суммы.\n" "Пожалуйста, введите число (например: 1500 или 0):"
            )
        except TelegramBadRequest:
            await message.answer(
                "❌ Неверный формат суммы.\n" "Пожалуйста, введите число (например: 1500 или 0):"
            )
        return

    # Сохраняем сумму расходного материала
    await state.update_data(materials_cost=materials_cost)

    # Удаляем предыдущее сообщение о запросе суммы материалов
    data = await state.get_data()
    current_prompt_message_id = data.get("current_prompt_message_id")
    current_prompt_chat_id = data.get("current_prompt_chat_id") or message.chat.id

    if current_prompt_message_id:
        try:
            from app.utils.retry import safe_delete_message

            await safe_delete_message(
                message.bot, current_prompt_chat_id, current_prompt_message_id
            )
            logger.info(f"Deleted materials prompt message {current_prompt_message_id}")
        except Exception as e:
            logger.warning(
                f"Failed to delete materials prompt message {current_prompt_message_id}: {e}"
            )

    # Получаем ID заказа для inline кнопок
    order_id = data.get("order_id")

    # Переходим к подтверждению материалов
    await state.set_state(CompleteOrderStates.confirm_materials)

    from app.keyboards.inline import get_yes_no_keyboard

    confirm_text = (
        f"💰 <b>Подтвердите сумму расходных материалов:</b>\n\n"
        f"Сумма: <b>{materials_cost:.2f} ₽</b>\n\n"
        f"Верно ли указана сумма?"
    )

    try:
        materials_confirm = await message.reply(
            confirm_text,
            parse_mode="HTML",
            reply_markup=get_yes_no_keyboard("confirm_materials", int(order_id) if order_id else 0),
        )
    except TelegramBadRequest:
        materials_confirm = await message.answer(
            confirm_text,
            parse_mode="HTML",
            reply_markup=get_yes_no_keyboard("confirm_materials", int(order_id) if order_id else 0),
        )

    # Сохраняем ID текущего сообщения для последующего удаления
    await state.update_data(
        current_prompt_message_id=materials_confirm.message_id,
        current_prompt_chat_id=materials_confirm.chat.id,
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
    if callback_query.message is not None:
        logger.info(f"[DEBUG_MATERIALS] Message ID: {callback_query.message.message_id}")
        logger.info(f"[DEBUG_MATERIALS] Chat ID: {callback_query.message.chat.id}")
    else:
        logger.warning("[DEBUG_MATERIALS] Message is None")

    # Получаем текущее состояние FSM
    current_state = await state.get_state()
    logger.info(f"[DEBUG_MATERIALS] Current FSM state: {current_state}")

    # Получаем данные из FSM
    fsm_data = await state.get_data()
    logger.info(f"[DEBUG_MATERIALS] FSM data: {fsm_data}")

    # Парсим callback data
    from app.utils import parse_callback_data

    try:
        if callback_query.data is None:
            logger.error("[DEBUG_MATERIALS] Callback data is None")
            await callback_query.answer("❌ Ошибка: нет данных callback", show_alert=True)
            return
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

    if callback_query.data is None:
        logger.error("[MATERIALS_CONFIRM] Callback data is None")
        await callback_query.answer("❌ Ошибка: нет данных callback", show_alert=True)
        return
    parsed_data = parse_callback_data(callback_query.data)
    action = parsed_data.get("action")
    params = parsed_data.get("params", [])
    answer = params[0] if len(params) > 0 else None  # yes/no
    order_id = params[1] if len(params) > 1 else None  # order_id
    logger.info(
        f"[MATERIALS_CONFIRM] Processing action: {action}, answer: {answer}, order_id: {order_id}"
    )

    # Проверка статуса заявки
    if order_id:
        db = get_database()
        await db.connect()
        try:
            order = await db.get_order_by_id(int(order_id))
            if order and order.status == OrderStatus.CLOSED:
                await callback_query.answer("❌ Заявка уже закрыта!", show_alert=True)
                # Очищаем состояние, так как заявка закрыта
                await state.clear()
                return
        finally:
            await db.disconnect()

    if answer == "yes":
        # Удаляем предыдущее сообщение о подтверждении материалов
        try:
            from app.utils.retry import safe_delete_message

            if callback_query.message is not None:
                await safe_delete_message(
                    callback_query.bot,
                    callback_query.message.chat.id,
                    callback_query.message.message_id,
                )
            logger.info(f"Deleted materials confirmation message for order {order_id}")
        except Exception as e:
            logger.warning(f"Failed to delete materials confirmation message: {e}")

        # Подтверждаем сумму материалов и переходим к отзыву
        await state.set_state(CompleteOrderStates.confirm_review)
        logger.info(f"[MATERIALS_CONFIRM] State changed to confirm_review for order {order_id}")

        from app.keyboards.inline import get_yes_no_keyboard

        try:
            keyboard = get_yes_no_keyboard("confirm_review", int(order_id) if order_id else 0)
            logger.info(f"[MATERIALS_CONFIRM] Created keyboard: {keyboard}")

            # Отправляем новое сообщение вместо редактирования
            if callback_query.message is None:
                await callback_query.answer("❌ Сообщение недоступно", show_alert=True)
                return
            review_message = await callback_query.message.answer(
                "✅ Сумма расходного материала подтверждена\n\n"
                "❓ <b>Взяли ли вы отзыв у клиента?</b>",
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            # Сохраняем ID текущего сообщения
            await state.update_data(
                current_prompt_message_id=review_message.message_id,
                current_prompt_chat_id=review_message.chat.id,
            )
            logger.info(f"[MATERIALS_CONFIRM] Message sent successfully for order {order_id}")
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
            message_obj = callback_query.message
            if not isinstance(message_obj, Message):
                await callback_query.answer("❌ Сообщение недоступно", show_alert=True)
                return

            await message_obj.edit_text(
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

    if callback_query.data is None:
        await callback_query.answer("❌ Ошибка: нет данных callback", show_alert=True)
        return
    callback_data = parse_callback_data(callback_query.data)
    answer = callback_data["params"][0] if len(callback_data["params"]) > 0 else None  # yes/no

    # Определяем ответ
    has_review = answer == "yes"

    # Сохраняем ответ об отзыве
    await state.update_data(has_review=has_review)

    # Удаляем предыдущее сообщение об отзыве
    try:
        from app.utils.retry import safe_delete_message

        if callback_query.message is not None:
            await safe_delete_message(
                callback_query.bot,
                callback_query.message.chat.id,
                callback_query.message.message_id,
            )
        logger.info("Deleted review confirmation message")
    except Exception as e:
        logger.warning(f"Failed to delete review confirmation message: {e}")

    # Переходим к запросу выезда за город
    await state.set_state(CompleteOrderStates.confirm_out_of_city)

    review_text = "✅ Отзыв взят!" if has_review else "❌ Отзыв не взят"

    from app.keyboards.inline import get_yes_no_keyboard

    # Получаем order_id из состояния, так как в callback data он может быть перепутан
    data = await state.get_data()
    order_id_from_state = data.get("order_id")

    # Проверка статуса заявки
    if order_id_from_state:
        db = get_database()
        await db.connect()
        try:
            order = await db.get_order_by_id(int(order_id_from_state))
            if order and order.status == OrderStatus.CLOSED:
                await callback_query.answer("❌ Заявка уже закрыта!", show_alert=True)
                await state.clear()
                return
        finally:
            await db.disconnect()

    # Отправляем новое сообщение вместо редактирования
    if callback_query.message is None:
        await callback_query.answer("❌ Сообщение недоступно", show_alert=True)
        return
    out_of_city_message = await callback_query.message.answer(
        f"{review_text}\n\n"
        f"🚗 <b>Был ли выезд за город?</b>\n"
        f"(За выезд за город вы получите дополнительно +10% к прибыли)",
        parse_mode="HTML",
        reply_markup=get_yes_no_keyboard(
            "confirm_out_of_city", int(order_id_from_state) if order_id_from_state else 0
        ),
    )
    # Сохраняем ID текущего сообщения
    await state.update_data(
        current_prompt_message_id=out_of_city_message.message_id,
        current_prompt_chat_id=out_of_city_message.chat.id,
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
    # Если пользователь хочет отменить или выйти
    if message.text and (
        message.text.startswith("/")
        or message.text in ["❌ Отмена", "📋 Мои заявки", "⚙️ Настройки"]
    ):
        await state.clear()
        await message.answer("🔄 Действие отменено. Выберите пункт меню:")
        return

    await message.reply(
        "❌ Пожалуйста, используйте кнопки для ответа.\n"
        "Если кнопки не отображаются, введите /cancel для сброса."
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

    if callback_query.data is None:
        await callback_query.answer("❌ Ошибка: нет данных callback", show_alert=True)
        return
    callback_data = parse_callback_data(callback_query.data)
    answer = callback_data["params"][0] if len(callback_data["params"]) > 0 else None  # yes/no

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

    db = get_database()
    await db.connect()

    # Получаем order_id из состояния, так как в callback data он может быть перепутан
    data = await state.get_data()
    order_id_from_state = data.get("order_id")

    try:
        order = await db.get_order_by_id(int(order_id_from_state) if order_id_from_state else 0)

        # Если админ действует от имени мастера
        if acting_as_master_id:
            master = await db.get_master_by_telegram_id(acting_as_master_id)
        else:
            master = await db.get_master_by_telegram_id(callback_query.from_user.id)

        # Проверяем роль пользователя
        user = await db.get_user_by_telegram_id(callback_query.from_user.id)
        is_admin = False
        if user:
            is_admin = "ADMIN" in user.get_roles()

        if not order:
            message_obj = callback_query.message
            if isinstance(message_obj, Message):
                await message_obj.edit_text("❌ Ошибка: заявка не найдена.")
            return

        # Проверка на статус CLOSED
        if order.status == OrderStatus.CLOSED:
            await callback_query.answer("❌ Заявка уже закрыта!", show_alert=True)
            message_obj = callback_query.message
            if isinstance(message_obj, Message):
                await message_obj.edit_text("❌ Заявка уже закрыта.")
            await state.clear()
            return

        # Если не админ, проверяем мастера
        if not is_admin and (not master or order.assigned_master_id != master.id):
            message_obj = callback_query.message
            if isinstance(message_obj, Message):
                await message_obj.edit_text("❌ Ошибка: заявка не принадлежит вам.")
            return

        master_roles = []
        if master:
            user = await db.get_user_by_telegram_id(master.telegram_id)
            if user:
                master_roles = user.get_roles()

        # Рассчитываем распределение прибыли с учетом отзыва и выезда за город
        from app.utils.helpers import calculate_profit_split, get_city_key

        # Получаем ставку для расчета по типу техники
        specialization_rate = None
        if order.equipment_type:
            from app.database.orm_database import ORMDatabase

            if isinstance(db, ORMDatabase):
                specialization_rate = await db.get_specialization_rate(
                    equipment_type=order.equipment_type,
                )

        # Получаем порог процентной ставки из настроек города
        profit_rate_threshold = 7000.0  # Значение по умолчанию
        from app.database.orm_database import ORMDatabase

        if isinstance(db, ORMDatabase):
            city_key = get_city_key()
            profit_rate_threshold = await db.get_profit_rate_threshold(city_key)

        master_profit, company_profit = calculate_profit_split(
            float(total_amount) if total_amount is not None else 0.0,
            float(materials_cost) if materials_cost is not None else 0.0,
            bool(has_review),
            out_of_city,
            equipment_type=order.equipment_type,
            specialization_rate=specialization_rate,
            master_roles=master_roles,
            profit_rate_threshold=profit_rate_threshold,
        )
        net_profit = (float(total_amount) if total_amount is not None else 0.0) - (
            float(materials_cost) if materials_cost is not None else 0.0
        )

        # Определяем процентную ставку для отображения
        # Если есть специальная ставка (например, для электрика/сантехника) - показываем 50/50
        if specialization_rate:
            base_master_pct, base_company_pct = specialization_rate
            # Округляем до целых для отображения
            master_pct_display = int(round(base_master_pct))
            company_pct_display = int(round(base_company_pct))
            profit_rate = f"{master_pct_display}/{company_pct_display}"
        else:
            # Стандартная логика с использованием порога из настроек
            profit_rate = "50/50" if net_profit >= profit_rate_threshold else "40/60"

        bonus_text = ""
        if out_of_city:
            bonus_text += " + бонус за выезд"
        if has_review:
            from app.core.config import Config
            if Config.REVIEW_BONUS_ENABLED:
                bonus_text += " + бонус за отзыв"

        # Обновляем суммы в базе данных
        await db.update_order_amounts(
            order_id=int(order_id_from_state) if order_id_from_state else 0,
            total_amount=float(total_amount) if total_amount is not None else 0.0,
            materials_cost=float(materials_cost) if materials_cost is not None else 0.0,
            master_profit=master_profit,
            company_profit=company_profit,
            has_review=has_review,
            out_of_city=out_of_city,
        )

        # Обновляем статус на CLOSED (с валидацией через State Machine)

        await db.update_order_status(
            order_id=int(order_id_from_state) if order_id_from_state else 0,
            status=OrderStatus.CLOSED,
            changed_by=callback_query.from_user.id,
            user_roles=user_roles,  # Передаём роли для валидации
        )

        # Перезагружаем заказ и мастера для получения актуальных данных
        updated_order = await db.get_order_by_id(
            int(order_id_from_state) if order_id_from_state else 0
        )
        if acting_as_master_id:
            master = await db.get_master_by_telegram_id(acting_as_master_id)
        else:
            master = await db.get_master_by_telegram_id(callback_query.from_user.id)

        # Создаем отчет по заказу
        try:
            from app.services.order_reports import OrderReportsService

            order_reports_service = OrderReportsService()

            # Получаем данные диспетчера
            dispatcher = None
            if updated_order is not None and updated_order.dispatcher_id:
                dispatcher = await db.get_user_by_telegram_id(updated_order.dispatcher_id)

            # Создаем запись в отчете
            if updated_order is not None:
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

        # ✨ УВЕДОМЛЕНИЕ АДМИНИСТРАТОРОВ И ДИСПЕТЧЕРОВ О ЗАКРЫТИИ ЗАЯВКИ
        # Получаем список получателей (админы + диспетчеры)
        recipients = await db.get_admins_and_dispatchers()
        recipient_ids = {user.telegram_id for user in recipients}
        
        # Добавляем назначенного диспетчера, если его нет в списке (на всякий случай)
        if updated_order is not None and updated_order.dispatcher_id:
            recipient_ids.add(updated_order.dispatcher_id)

        if recipient_ids:
            from app.utils import safe_send_message

            notification_text = (
                f"✅ <b>Заявка завершена!</b>\n\n"
                f"📋 <b>Заявка #{order_id_from_state}</b>\n"
                f"👨‍🔧 <b>Мастер:</b> {master.get_display_name() if master else 'Неизвестен'}\n\n"
                f"💰 <b>Финансы:</b>\n"
                f"└ Общая сумма: {(total_amount if total_amount else 0):.2f} ₽\n"
                f"└ Материалы: {(materials_cost if materials_cost else 0):.2f} ₽\n"
                f"└ Прибыль: {net_profit:.2f} ₽\n\n"
                f"📊 <b>Распределение:</b>\n"
                f"└ Мастер: {master_profit:.2f} ₽\n"
                f"└ Компания: {company_profit:.2f} ₽\n"
            )

            if has_review:
                notification_text += "\n⭐ <b>Отзыв:</b> Да"
            if out_of_city:
                notification_text += "\n🚗 <b>Выезд:</b> Да"

            for recipient_id in recipient_ids:
                result = await safe_send_message(
                    callback_query.bot,
                    recipient_id,
                    notification_text,
                    parse_mode="HTML",
                )

                if not result:
                    logger.error(
                        f"Failed to notify user {recipient_id} about order #{order_id_from_state} completion"
                    )
                else:
                    logger.info(
                        f"User {recipient_id} notified about order #{order_id_from_state} completion"
                    )

        # Удаляем предыдущее сообщение о выезде за город
        try:
            from app.utils.retry import safe_delete_message

            if callback_query.message is not None:
                await safe_delete_message(
                    callback_query.bot,
                    callback_query.message.chat.id,
                    callback_query.message.message_id,
                )
            logger.info(
                f"Deleted out of city confirmation message for order #{order_id_from_state}"
            )
        except Exception as e:
            logger.warning(f"Failed to delete out of city confirmation message: {e}")

        # Формируем текст подтверждения
        out_of_city_text = "🚗 Да" if out_of_city else "❌ Нет"
        review_text = "⭐ Да" if has_review else "❌ Нет"

        # Отправляем новое сообщение с результатами вместо редактирования
        if callback_query.message is None:
            await callback_query.answer("❌ Сообщение недоступно", show_alert=True)
            return
        await callback_query.message.answer(
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
        message_obj = callback_query.message
        if isinstance(message_obj, Message):
            await message_obj.edit_text("❌ Произошла ошибка при завершении заявки.")
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
    # Если пользователь хочет отменить или выйти
    if message.text and (
        message.text.startswith("/")
        or message.text in ["❌ Отмена", "📋 Мои заявки", "⚙️ Настройки"]
    ):
        await state.clear()
        await message.answer("🔄 Действие отменено. Выберите пункт меню:")
        return

    await message.reply(
        "❌ Пожалуйста, используйте кнопки для ответа.\n"
        "Если кнопки не отображаются, введите /cancel для сброса."
    )


@router.message(F.text == "⚙️ Настройки")
@handle_errors
async def btn_settings_master(message: Message, user_role: str, db: Database):
    """
    Обработчик кнопки настроек для мастеров

    Args:
        message: Сообщение
        user_role: Роль пользователя
        db: Database instance (injected)
    """
    # Проверка роли
    if user_role not in [UserRole.MASTER, UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    try:
        master = None
        if message.from_user and message.from_user.id:
            master = await db.get_master_by_telegram_id(message.from_user.id)

        if not master:
            await message.answer("❌ Вы не зарегистрированы как мастер в системе.")
            return

        if message.from_user is None:
            await message.answer("❌ Ошибка: не удалось определить пользователя")
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
    if not callback.data:
        return
    order_id = int(callback.data.split(":")[1])

    db = get_database()
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

        message_obj = callback.message
        if not isinstance(message_obj, Message):
            await callback.answer("❌ Сообщение недоступно", show_alert=True)
            return

        await message_obj.edit_text(
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

    reason: str | None = message.text.strip()

    # Если пользователь указал "-", причины нет
    if reason == "-":
        reason = None

    # Сохраняем причину
    await state.update_data(reschedule_reason=reason)

    # Получаем данные из state
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
    db = get_database()
    await db.connect()

    try:
        order = await db.get_order_by_id(int(order_id) if order_id else 0)
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
        db_role = get_database()
        await db_role.connect()
        try:
            if message.from_user is None:
                await message.reply("❌ Ошибка: не удалось определить пользователя")
                return
            _user_with_db_role = await db_role.get_user_by_telegram_id(message.from_user.id)
            user_role = _user_with_db_role.role if _user_with_db_role else "MASTER"
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

    db = get_database()
    await db.connect()

    try:
        if order_id is None:
            await message.reply("❌ Ошибка: ID заявки не найден")
            return
        order = await db.get_order_by_id(int(order_id))
        if not order:
            await message.reply("❌ Ошибка: заявка не найдена")
            return

        old_time = order.scheduled_time or "не указано"

        # Обновляем заявку
        from app.database.orm_database import ORMDatabase

        if isinstance(db, ORMDatabase):
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
                        "order_id": int(order_id),
                    },
                )

        # Добавляем в лог
        if message.from_user is None:
            logger.warning("message.from_user is None, cannot add audit log for reschedule.")
        else:
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
        if message.from_user is None:
            logger.warning("message.from_user is None, cannot determine user role for main menu.")
            user_role = "MASTER"  # Default to MASTER if user is unknown
        else:
            user = await db.get_user_by_telegram_id(message.from_user.id)
            user_role = user.role if user else "MASTER"
        await message.answer(
            result_text, parse_mode="HTML", reply_markup=get_main_menu_keyboard(user_role)
        )

        # Уведомляем диспетчера
        if order.dispatcher_id:
            master = await db.get_master_by_telegram_id(int(initiated_by) if initiated_by else 0)
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
                if message.bot is None:
                    logger.error("Bot instance is None")
                else:
                    await message.bot.send_message(
                        order.dispatcher_id, notification, parse_mode="HTML"
                    )
                    logger.info(f"Reschedule notification sent to dispatcher {order.dispatcher_id}")
            except Exception as e:
                logger.error(f"Не удалось уведомить диспетчера {order.dispatcher_id}: {e}")

        # Уведомляем мастера, если перенос выполнен из админ-панели
        initiator_user = await db.get_user_by_telegram_id(int(initiated_by) if initiated_by else 0)
        is_admin_reschedule = initiator_user and initiator_user.has_role(UserRole.ADMIN)

        if is_admin_reschedule and order.assigned_master_id:
            # Получаем мастера по ID
            assigned_master = await db.get_master_by_id(order.assigned_master_id)
            if assigned_master:
                from app.utils import safe_send_message

                master_notification = (
                    f"📅 <b>Визит перенесен</b>\n\n"
                    f"Заявка #{order_id}\n"
                    f"👤 Клиент: {order.client_name}\n"
                    f"📍 Адрес: {order.client_address}\n"
                    f"🔧 Техника: {order.equipment_type}\n\n"
                    f"Было: {old_time}\n"
                    f"<b>Стало: {new_time}</b>\n"
                )

                if reason:
                    master_notification += f"\n📝 Причина: {reason}"

                # Отправляем в группу, если есть work_chat_id, иначе в личные сообщения
                target_chat_id = (
                    assigned_master.work_chat_id
                    if assigned_master.work_chat_id
                    else assigned_master.telegram_id
                )

                result = await safe_send_message(
                    message.bot,
                    target_chat_id,
                    master_notification,
                    parse_mode="HTML",
                )
                if result:
                    chat_type = "group" if assigned_master.work_chat_id else "private"
                    logger.info(
                        f"Reschedule notification sent to master {assigned_master.telegram_id} "
                        f"({chat_type} chat {target_chat_id}, order #{order_id})"
                    )
                else:
                    logger.error(
                        f"Не удалось уведомить мастера {assigned_master.telegram_id} "
                        f"(chat {target_chat_id}) о переносе заявки #{order_id} после повторных попыток"
                    )

        if message.from_user is None:
            logger.warning("message.from_user is None, skipping log_action")
        else:
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
    parts_info = data.get("parts_info")
    estimated_cost = data.get("estimated_cost")

    # Получаем информацию о заявке
    db = get_database()
    await db.connect()

    try:
        order = await db.get_order_by_id(int(order_id) if order_id else 0)
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

        # Добавляем информацию о запчастях
        if parts_info and parts_info.lower() not in ["нет", "не", "no", "не требуются"]:
            text += f"🔩 <b>Требуемые запчасти:</b>\n{parts_info}\n\n"
        else:
            text += "🔩 <b>Запчасти:</b> не требуются\n\n"

        # Добавляем предварительную сумму
        if estimated_cost:
            text += f"💰 <b>Предварительная сумма:</b> {estimated_cost:.2f} ₽\n"
        else:
            text += "💰 <b>Предварительная сумма:</b> не согласована\n"

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
        db = get_database()
        await db.connect()
        try:
            if message.from_user is None:
                await message.reply("❌ Ошибка: не удалось определить пользователя")
                return
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
        await state.set_state(LongRepairStates.enter_completion_date)
        await process_dr_info(message, state, [])


async def confirm_dr_translation(message: Message, state: FSMContext):
    """
    Подтверждение и выполнение перевода в длительный ремонт
    """
    data = await state.get_data()
    order_id = data.get("order_id")
    completion_date = data.get("completion_date")
    parts_info = data.get("parts_info", "")
    estimated_cost = data.get("estimated_cost")

    db = get_database()
    await db.connect()

    try:
        order = await db.get_order_by_id(int(order_id) if order_id else 0)
        if not order:
            await message.reply("❌ Ошибка: заявка не найдена")
            return

        # Формируем информацию для заметок
        dr_notes = []
        
        # Добавляем информацию о запчастях
        if parts_info and parts_info.lower() not in ["нет", "не", "no", "не требуются"]:
            dr_notes.append(f"Требуемые запчасти: {parts_info}")
        
        # Добавляем предварительную сумму
        if estimated_cost:
            dr_notes.append(f"Предварительная сумма согласования: {estimated_cost:.2f} ₽")
        
        # Объединяем с существующими заметками
        existing_notes = order.notes or ""
        dr_info = "\n".join(dr_notes)
        
        if existing_notes:
            updated_notes = f"{existing_notes}\n\n[ДР] {dr_info}" if dr_info else existing_notes
        else:
            updated_notes = f"[ДР] {dr_info}" if dr_info else None

        # Обновляем заявку
        from app.database.orm_database import ORMDatabase

        if isinstance(db, ORMDatabase):
            async with db.get_session() as session:
                from sqlalchemy import text

                await session.execute(
                    text(
                        """
                UPDATE orders
                SET status = :status,
                    estimated_completion_date = :estimated_completion_date,
                    notes = :notes,
                    updated_at = :updated_at
                WHERE id = :order_id
                """
                    ),
                    {
                        "status": OrderStatus.DR,
                        "estimated_completion_date": completion_date,
                        "notes": updated_notes,
                        "updated_at": get_now(),
                        "order_id": order_id,
                    },
                )

        # Добавляем в лог
        if message.from_user is None:
            logger.warning("message.from_user is None, skipping audit log")
        else:
            await db.add_audit_log(
                user_id=message.from_user.id,
                action="LONG_REPAIR_ORDER",
                details=f"Order #{order_id} translated to long repair. Completion: {completion_date}, Parts: {parts_info or 'none'}, Cost: {estimated_cost or 'none'}",
            )

        # Форматируем дату с расчетом дней для отображения
        from app.utils.date_parser import format_estimated_completion_with_days

        completion_date_formatted = format_estimated_completion_with_days(
            str(completion_date) if completion_date else ""
        )

        # Формируем сообщение с результатом
        result_text = (
            f"✅ <b>Заявка #{order_id} переведена в длительный ремонт</b>\n\n"
            f"⏰ <b>Срок завершения:</b> {completion_date_formatted}\n"
        )

        if parts_info and parts_info.lower() not in ["нет", "не", "no", "не требуются"]:
            result_text += f"🔩 <b>Требуемые запчасти:</b>\n{parts_info}\n\n"

        if estimated_cost:
            result_text += f"💰 <b>Предварительная сумма:</b> {estimated_cost:.2f} ₽\n"

        result_text += "\n<i>Диспетчер уведомлен</i>"

        # Отправляем результат и удаляем клавиатуру
        await message.reply(result_text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())

        # Очищаем состояние FSM
        await state.clear()

        # Получаем роли пользователя и показываем главное меню
        if message.from_user is None:
            await message.reply("❌ Ошибка: не удалось определить пользователя")
            return
        user = await db.get_user_by_telegram_id(message.from_user.id)
        if user:
            user_roles = user.get_roles()
            menu_keyboard = await get_menu_with_counter(user_roles)
            await message.answer(
                "🏠 <b>Главное меню</b>", parse_mode="HTML", reply_markup=menu_keyboard
            )

        # Получаем данные о том, кто инициировал перевод в DR
        acting_as_master_id = data.get("acting_as_master_id")

        # Уведомляем диспетчера
        if order.dispatcher_id:
            master = await db.get_master_by_telegram_id(message.from_user.id)
            master_name = master.get_display_name() if master else f"ID: {message.from_user.id}"

            # Форматируем дату с расчетом дней для отображения
            from app.utils.date_parser import format_estimated_completion_with_days

            completion_date_formatted = format_estimated_completion_with_days(
                str(completion_date) if completion_date else ""
            )

            notification = (
                f"🔧 <b>Заявка #{order_id} переведена в длительный ремонт</b>\n\n"
                f"👨‍🔧 {master_name}\n"
                f"👤 {order.client_name} - {order.client_phone}\n"
                f"🔧 {order.equipment_type}\n\n"
                f"⏰ <b>Срок завершения:</b> {completion_date_formatted}\n"
            )

            if parts_info and parts_info.lower() not in ["нет", "не", "no", "не требуются"]:
                notification += f"🔩 <b>Требуемые запчасти:</b>\n{parts_info}\n\n"

            if estimated_cost:
                notification += f"💰 <b>Предварительная сумма:</b> {estimated_cost:.2f} ₽\n"

            notification += "\n💡 Свяжитесь с клиентом для подтверждения"

            try:
                if message.bot is None:
                    logger.error("Bot instance is None")
                else:
                    await message.bot.send_message(
                        order.dispatcher_id, notification, parse_mode="HTML"
                    )
                logger.info(f"DR notification sent to dispatcher {order.dispatcher_id}")
            except Exception as e:
                logger.error(f"Не удалось уведомить диспетчера {order.dispatcher_id}: {e}")

        # Уведомляем мастера в рабочую группу, если перевод сделан админом от его имени
        if acting_as_master_id and order.assigned_master_id:
            master = await db.get_master_by_id(order.assigned_master_id)
            current_user_id = message.from_user.id if message.from_user else None
            if (
                master
                and current_user_id
                and master.telegram_id != current_user_id
                and master.work_chat_id
            ):
                # Форматируем дату с расчетом дней для отображения
                from app.utils import safe_send_message
                from app.utils.date_parser import format_estimated_completion_with_days

                master_notification = (
                    f"🔧 <b>Заявка #{order_id} переведена в длительный ремонт</b>\n\n"
                    f"<i>Администратор изменил статус от имени мастера {master.get_display_name()}</i>\n\n"
                    f"👤 Клиент: {order.client_name}\n"
                    f"🔧 Техника: {order.equipment_type}\n"
                    f"📝 {order.description}\n\n"
                    f"⏰ <b>Срок завершения:</b> {completion_date_formatted}\n"
                )

                if parts_info and parts_info.lower() not in ["нет", "не", "no", "не требуются"]:
                    master_notification += f"🔩 <b>Требуемые запчасти:</b>\n{parts_info}\n\n"

                if estimated_cost:
                    master_notification += f"💰 <b>Предварительная сумма:</b> {estimated_cost:.2f} ₽\n"

                result = await safe_send_message(
                    message.bot,
                    master.work_chat_id,
                    master_notification,
                    parse_mode="HTML",
                )
                if result:
                    logger.info(
                        f"DR notification sent to master's work group {master.work_chat_id}"
                    )
                else:
                    logger.error(
                        f"Failed to notify master's work group {master.work_chat_id} about DR status"
                    )
            elif master and master.telegram_id != message.from_user.id:
                logger.warning(
                    f"Master {master.telegram_id} has no work_chat_id, DR notification not sent"
                )

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
async def callback_master_report_excel(callback: CallbackQuery, db: Database):
    """
    Генерация и отправка Excel отчета мастеру

    Args:
        callback: Callback query
        db: Database instance (injected)
    """
    if not callback.data:
        return
    master_id = int(callback.data.split(":")[1])

    try:
        # Проверяем, что мастер запрашивает свой отчет
        master = await db.get_master_by_telegram_id(callback.from_user.id)

        if not master or master.id != master_id:
            await callback.answer("❌ Вы можете просматривать только свои отчеты", show_alert=True)
            return

        await callback.answer("📊 Генерирую отчет...")

        message_obj = callback.message
        if not isinstance(message_obj, Message):
            await callback.answer("❌ Сообщение недоступно", show_alert=True)
            return

        await message_obj.edit_text(
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
        await message_obj.answer_document(
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
        await message_obj.delete()

        logger.info(f"Excel отчет отправлен мастеру {master_id}")

    except Exception as e:
        logger.exception(f"Ошибка при генерации отчета для мастера {master_id}: {e}")
        message_obj = callback.message
        if isinstance(message_obj, Message):
            await message_obj.edit_text(
                "❌ <b>Ошибка при генерации отчета</b>\n\n"
                "Попробуйте еще раз позже или обратитесь к администратору.",
                parse_mode="HTML",
            )
    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("master_reports_archive:"))
async def callback_master_reports_archive(callback: CallbackQuery, db: Database):
    """
    Просмотр архивных отчетов мастера

    Args:
        callback: Callback query
        db: Database instance (injected)
    """
    if not callback.data:
        return
    master_id = int(callback.data.split(":")[1])

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

        message_obj = callback.message
        if not isinstance(message_obj, Message):
            await callback.answer("❌ Сообщение недоступно", show_alert=True)
            return

        await message_obj.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("download_archive_report:"))
async def callback_download_archive_report(callback: CallbackQuery, db: Database):
    """
    Загрузка архивного отчета

    Args:
        callback: Callback query
        db: Database instance (injected)
    """
    if not callback.data:
        await callback.answer("❌ Нет данных callback", show_alert=True)
        return

    # Парсим callback data: download_archive_report:report_id:master_id
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("❌ Некорректные данные callback", show_alert=True)
        return

    report_id = int(parts[1])
    master_id = int(parts[2])

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

        if report is None:
            await callback.answer("❌ Отчет не найден", show_alert=True)
            return

        caption = (
            f"📚 <b>Архивный отчет</b>\n\n"
            f"📅 Период: {report.period_start.strftime('%d.%m.%Y')} - {report.period_end.strftime('%d.%m.%Y')}\n"
            f"📋 Заявок: {report.total_orders}\n"
            f"✅ Завершено: {report.completed_orders}\n"
            f"💰 Выручка: {report.total_revenue:.2f} ₽"
        )

        # Отправляем файл
        if callback.message is None:
            await callback.answer("❌ Сообщение недоступно", show_alert=True)
            return

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
    message: Message,
    state: FSMContext,
    order_id: int,
    user_telegram_id: int | None = None,
    refuse_reason: str | None = None,
    total_amount: float = 0.0,
):
    """
    Завершение заказа как отказ (для заявок в 0 рублей или с суммой <1000р)

    Args:
        message: Сообщение
        state: FSM контекст
        order_id: ID заказа
        user_telegram_id: ID мастера, если админ действует от его имени
        refuse_reason: Причина отказа
        total_amount: Сумма которую ввел мастер (по умолчанию 0)
    """
    from app.config import OrderStatus
    from app.utils.helpers import calculate_profit_split

    db = get_database()
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
        telegram_id = user_telegram_id or (message.from_user.id if message.from_user else 0)
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

        # Проверяем роль пользователя
        user = await db.get_user_by_telegram_id(telegram_id)
        is_admin = False
        if user:
            is_admin = "ADMIN" in user.get_roles()

        # Проверяем, что заявка назначена на этого мастера
        logger.info(
            f"[REFUSE] Order assigned_master_id: {order.assigned_master_id}, master.id: {master.id}"
        )
        if not is_admin and order.assigned_master_id != master.id:
            await message.reply("❌ Ошибка: заявка не назначена на этого мастера.")
            return

        # Устанавливаем все суммы (total_amount берем из параметра)
        materials_cost = 0.0
        has_review = False
        out_of_city = False

        # Рассчитываем распределение прибыли (все будет 0)
        # Получаем ставку для расчета по типу техники
        specialization_rate = None
        if order.equipment_type:
            from app.database.orm_database import ORMDatabase

            if isinstance(db, ORMDatabase):
                specialization_rate = await db.get_specialization_rate(
                    equipment_type=order.equipment_type,
                )

        master_roles = []
        if master:
            user = await db.get_user_by_telegram_id(master.telegram_id)
            if user:
                master_roles = user.get_roles()

        master_profit, company_profit = calculate_profit_split(
            total_amount,
            materials_cost,
            has_review,
            out_of_city,
            equipment_type=order.equipment_type,
            specialization_rate=specialization_rate,
            master_roles=master_roles,
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
            changed_by=message.from_user.id if message.from_user else 0,
            user_roles=["MASTER"],  # Мастер завершает заказ
        )

        # Сохраняем причину отказа если указана
        if refuse_reason:
            if hasattr(db, "update_order_field"):
                await db.update_order_field(order_id, "refuse_reason", refuse_reason)
            else:
                # Legacy SQL
                from app.database.orm_database import ORMDatabase

                if isinstance(db, ORMDatabase):
                    async with db.get_session() as session:
                        from sqlalchemy import text

                        await session.execute(
                            text(
                                "UPDATE orders SET refuse_reason = :refuse_reason WHERE id = :order_id"
                            ),
                            {"refuse_reason": refuse_reason, "order_id": order_id},
                        )
                        await session.commit()

        # Добавляем в лог
        log_details = f"Order #{order_id} completed as refusal (0 rubles)"
        if refuse_reason:
            log_details += f", reason: {refuse_reason}"

        if message.from_user is None:
            logger.warning("message.from_user is None, skipping audit log")
        else:
            await db.add_audit_log(
                user_id=message.from_user.id,
                action="COMPLETE_ORDER_AS_REFUSAL",
                details=log_details,
            )

        # Удаляем промпт-сообщение если оно есть
        try:
            data = await state.get_data()
            prompt_message_id = data.get("prompt_message_id")
            current_prompt_message_id = data.get("current_prompt_message_id")
            allowed_chat_id = data.get("allowed_chat_id") or message.chat.id
            current_prompt_chat_id = data.get("current_prompt_chat_id") or message.chat.id

            from app.utils.retry import safe_delete_message

            # Удаляем промпт-сообщение если оно есть
            if prompt_message_id:
                try:
                    await safe_delete_message(message.bot, allowed_chat_id, prompt_message_id)
                    logger.info(f"Deleted prompt message {prompt_message_id} for order #{order_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete prompt message {prompt_message_id}: {e}")

            # Удаляем текущее промежуточное сообщение если оно есть
            if current_prompt_message_id:
                try:
                    await safe_delete_message(
                        message.bot, current_prompt_chat_id, current_prompt_message_id
                    )
                    logger.info(
                        f"Deleted current prompt message {current_prompt_message_id} for order #{order_id}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to delete current prompt message {current_prompt_message_id}: {e}"
                    )
        except Exception as e:
            logger.warning(f"Error deleting messages for order #{order_id}: {e}")

        # Очищаем состояние FSM
        await state.clear()

        # Отправляем подтверждение
        confirmation_text = (
            f"❌ <b>Заявка #{order_id} завершена как отказ</b>\n\n"
            f"💰 Сумма заказа: {total_amount:.2f} ₽\n"
            f"📋 Статус: Отказ\n"
        )
        if refuse_reason:
            confirmation_text += f"\n📝 Причина отказа: {refuse_reason}"
        elif total_amount == 0:
            confirmation_text += (
                "\nЗаявка автоматически помечена как отказ, так как сумма составляет 0 рублей."
            )

        await message.reply(confirmation_text, parse_mode="HTML")

        # Уведомляем диспетчера
        if order.dispatcher_id:
            from app.utils import safe_send_message

            dispatcher_reason = refuse_reason if refuse_reason else "Сумма заказа 0 рублей"
            dispatcher_text = (
                f"❌ Заявка #{order_id} завершена как отказ\n"
                f"Мастер: {master.get_display_name()}\n"
            )
            if total_amount > 0:
                dispatcher_text += f"💰 Сумма: {total_amount:.2f} ₽\n"
            dispatcher_text += f"Причина: {dispatcher_reason}"

            result = await safe_send_message(
                message.bot,
                order.dispatcher_id,
                dispatcher_text,
                parse_mode="HTML",
            )
            if not result:
                logger.error(f"Не удалось уведомить диспетчера {order.dispatcher_id} об отказе")

        # Уведомляем мастера в рабочую группу, если админ действует от его имени
        if user_telegram_id and user_telegram_id != (
            message.from_user.id if message.from_user else 0
        ):
            if master.work_chat_id:
                from app.utils import safe_send_message

                group_reason = refuse_reason if refuse_reason else "Отказ от заявки"
                master_notification = (
                    f"❌ <b>Заявка #{order_id} завершена как отказ</b>\n\n"
                    f"<i>Администратор {message.from_user.full_name if message.from_user else 'Unknown'} изменил статус от имени мастера {master.get_display_name()}</i>\n\n"
                    f"👤 Клиент: {order.client_name}\n"
                    f"🔧 Техника: {order.equipment_type}\n"
                    f"📝 {order.description}\n\n"
                    f"💰 Сумма заказа: {total_amount:.2f} ₽\n"
                    f"📋 Причина: {group_reason}"
                )

                result = await safe_send_message(
                    message.bot,
                    master.work_chat_id,
                    master_notification,
                    parse_mode="HTML",
                )
                if result:
                    logger.info(
                        f"REFUSED notification sent to master's work group {master.work_chat_id}"
                    )
                else:
                    logger.error(
                        f"Failed to notify master's work group {master.work_chat_id} about REFUSED status"
                    )
            else:
                logger.warning(
                    f"Master {master.telegram_id} has no work_chat_id, REFUSED notification not sent"
                )

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
    if not callback_query.data:
        return
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
        message_obj = callback_query.message
        if not isinstance(message_obj, Message):
            await callback_query.answer("❌ Сообщение недоступно", show_alert=True)
            return

        await complete_order_as_refusal(message_obj, state, order_id, callback_query.from_user.id)

        # Очищаем состояние
        await state.clear()

        await callback_query.answer("Заявка отклонена")
    else:
        # Отменяем отказ - получаем заказ для клавиатуры
        db = get_database()
        await db.connect()
        try:
            order = await db.get_order_by_id(order_id)
            message_obj = callback_query.message
            if not isinstance(message_obj, Message):
                await callback_query.answer("❌ Сообщение недоступно", show_alert=True)
                return

            if order:
                await message_obj.edit_text(
                    "❌ Отказ отменен.\n\nЗаявка остается активной.",
                    reply_markup=get_order_actions_keyboard(order, UserRole.MASTER),
                )
            else:
                await message_obj.edit_text("❌ Отказ отменен.\n\nЗаявка не найдена.")
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
async def callback_complete_dr_order(callback: CallbackQuery, state: FSMContext, db: Database):
    """
    Завершение заявки из статуса ДР (Длительный Ремонт)

    Args:
        callback: Callback query
        state: FSM контекст
        db: Database instance (injected)
    """
    if not callback.data:
        return
    if not callback.data:
        return
    order_id = int(callback.data.split(":")[1])

    logger.info(
        f"[COMPLETE_DR] Starting completion process for DR order #{order_id} by user {callback.from_user.id}"
    )

    db = get_database()
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
        if callback.message is None:
            await callback.answer("❌ Сообщение недоступно", show_alert=True)
            return

        await state.update_data(
            order_id=order_id,
            allowed_chat_id=callback.message.chat.id,
        )

        # Переходим в состояние запроса общей суммы
        from app.states import CompleteOrderStates

        await state.set_state(CompleteOrderStates.enter_total_amount)

        # В ЛС открываем ForceReply, чтобы у пользователя автоматически включился режим ответа
        from aiogram.types import ForceReply

        if callback.message:
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
