"""
Обработчики для администраторов
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import OrderStatus, UserRole
from app.database.orm_database import ORMDatabase
from app.decorators import handle_errors, require_role
from app.keyboards.inline import (
    get_master_management_keyboard,
    get_masters_list_keyboard,
    get_order_actions_keyboard,
    get_yes_no_keyboard,
)
from app.keyboards.reply import get_cancel_keyboard
from app.states import AddMasterStates, AdminCloseOrderStates, SetWorkChatStates
from app.utils import format_phone, log_action, validate_phone


logger = logging.getLogger(__name__)

router = Router(name="admin")
# Фильтры на уровне роутера НЕ работают, т.к. выполняются ДО middleware
# Проверка роли теперь в каждом обработчике через декоратор


# УДАЛЕНО: обработчик "📊 Отчеты" перенесен в dispatcher.py
# для универсальной обработки админов и диспетчеров


@router.callback_query(F.data == "generate_daily_report")
@handle_errors
async def callback_generate_daily_report(callback: CallbackQuery, user_role: str):
    """Генерация ежедневного отчета"""
    if user_role not in [UserRole.ADMIN]:
        return

    await callback.message.edit_text("⏳ Генерирую ежедневный отчет...")

    try:
        from app.services.reports_notifier import ReportsNotifier

        notifier = ReportsNotifier(callback.bot)
        await notifier.send_daily_report()

        await callback.message.edit_text("✅ Ежедневный отчет успешно отправлен!")

    except Exception as e:
        logger.error(f"Ошибка генерации ежедневного отчета: {e}")
        await callback.message.edit_text(f"❌ Ошибка генерации отчета: {e}")

    await callback.answer()


@router.callback_query(F.data == "generate_weekly_report")
@handle_errors
async def callback_generate_weekly_report(callback: CallbackQuery, user_role: str):
    """Генерация еженедельного отчета"""
    if user_role not in [UserRole.ADMIN]:
        return

    await callback.message.edit_text("⏳ Генерирую еженедельный отчет...")

    try:
        from app.services.reports_notifier import ReportsNotifier

        notifier = ReportsNotifier(callback.bot)
        await notifier.send_weekly_report()

        await callback.message.edit_text("✅ Еженедельный отчет успешно отправлен!")

    except Exception as e:
        logger.error(f"Ошибка генерации еженедельного отчета: {e}")
        await callback.message.edit_text(f"❌ Ошибка генерации отчета: {e}")

    await callback.answer()


@router.callback_query(F.data == "generate_monthly_report")
@handle_errors
async def callback_generate_monthly_report(callback: CallbackQuery, user_role: str):
    """Генерация ежемесячного отчета"""
    if user_role not in [UserRole.ADMIN]:
        return

    await callback.message.edit_text("⏳ Генерирую ежемесячный отчет...")

    try:
        from app.services.reports_notifier import ReportsNotifier

        notifier = ReportsNotifier(callback.bot)
        await notifier.send_monthly_report()

        await callback.message.edit_text("✅ Ежемесячный отчет успешно отправлен!")

    except Exception as e:
        logger.error(f"Ошибка генерации ежемесячного отчета: {e}")
        await callback.message.edit_text(f"❌ Ошибка генерации отчета: {e}")

    await callback.answer()


# Хэндлер кнопки "Обновить все отчеты" удален - таблицы обновляются при каждом запросе


@router.callback_query(F.data == "export_active_orders_admin")
@handle_errors
async def callback_export_active_orders_admin(callback: CallbackQuery, user_role: str):
    """
    Экспорт активных заявок в Excel

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    await callback.answer("📊 Генерирую отчет...", show_alert=False)

    try:
        from app.services.realtime_active_orders import realtime_active_orders_service

        # Обновляем таблицу активных заказов
        await realtime_active_orders_service.update_table()

        # Получаем путь к текущей таблице
        filepath = await realtime_active_orders_service.get_current_table_path()

        if filepath:
            # Отправляем файл
            from aiogram.types import FSInputFile

            file = FSInputFile(filepath)
            await callback.message.answer_document(
                file,
                caption="📋 <b>Отчет по активным заявкам</b>\n\n"
                "В файле указаны все незакрытые заявки:\n"
                "• Сводный лист со всеми заявками\n"
                "• Отдельные листы для каждого мастера\n"
                "• Статус и время создания\n"
                "• Назначенный мастер\n"
                "• Контакты клиента\n"
                "• Запланированное время\n\n"
                "Таблица обновляется при каждом запросе.",
                parse_mode="HTML",
            )

            logger.info(f"Active orders report sent to {callback.from_user.id}")
            await callback.message.edit_text(
                "✅ Отчет по активным заявкам сформирован!", reply_markup=None
            )
        else:
            await callback.answer("❌ Нет активных заявок", show_alert=True)

    except Exception as e:
        logger.error(f"Error generating active orders report: {e}")
        await callback.answer("❌ Ошибка при создании отчета", show_alert=True)


@router.callback_query(F.data == "back_to_admin_menu")
@handle_errors
async def callback_back_to_admin_menu(callback: CallbackQuery):
    """Возврат в главное меню администратора"""
    await callback.message.delete()
    await callback.answer()


@router.message(F.text == "👥 Мастера")
async def btn_masters(message: Message, state: FSMContext, user_role: str):
    """
    Обработчик кнопки управления мастерами

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    # Проверка роли
    if user_role != UserRole.ADMIN:
        return

    await state.clear()

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👥 Все мастера", callback_data="list_all_masters"))
    builder.row(InlineKeyboardButton(text="➕ Добавить мастера", callback_data="add_master"))

    await message.answer(
        "👥 <b>Управление мастерами</b>\n\n" "Выберите действие:",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "list_all_masters")
async def callback_list_all_masters(callback: CallbackQuery, user_role: str):
    """
    Вывод списка всех мастеров

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    db = ORMDatabase()
    await db.connect()

    try:
        masters = await db.get_all_masters()

        if not masters:
            await callback.message.edit_text(
                "📝 В системе пока нет мастеров.\n\n"
                "Используйте кнопку 'Добавить мастера' для добавления."
            )
            await callback.answer()
            return

        text = "👥 <b>Все мастера:</b>\n\n"

        for master in masters:
            status = "✅" if master.is_approved else "⏳"
            active = "🟢" if master.is_active else "🔴"
            display_name = master.get_display_name()

            text += (
                f"{status} {active} <b>{display_name}</b>\n"
                f"   📞 {master.phone}\n"
                f"   🔧 {master.specialization}\n\n"
            )

        # Клавиатура со списком для управления
        keyboard = get_masters_list_keyboard(masters, action="manage_master")

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data == "add_master")
async def callback_add_master(callback: CallbackQuery, state: FSMContext):
    """
    Начало процесса добавления мастера

    Args:
        callback: Callback query
        state: FSM контекст
    """
    await state.set_state(AddMasterStates.enter_telegram_id)

    await callback.message.answer(
        "➕ <b>Добавление нового мастера</b>\n\n"
        "Введите Telegram ID мастера:\n"
        "<i>(попросите мастера отправить команду /start боту и сообщить вам его ID)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )

    await callback.message.delete()
    await callback.answer()


@router.message(AddMasterStates.enter_telegram_id, F.text != "❌ Отмена")
async def process_master_telegram_id(message: Message, state: FSMContext):
    """
    Обработка ввода Telegram ID мастера

    Args:
        message: Сообщение
        state: FSM контекст
    """
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Введите числовой ID:", reply_markup=get_cancel_keyboard()
        )
        return

    # Проверяем, существует ли пользователь
    db = ORMDatabase()
    await db.connect()

    try:
        user = await db.get_user_by_telegram_id(telegram_id)
        if not user:
            await message.answer(
                "❌ Пользователь с таким ID не найден в системе.\n"
                "Попросите пользователя сначала отправить /start боту.",
                reply_markup=get_cancel_keyboard(),
            )
            return

        # Проверяем, не является ли уже мастером
        master = await db.get_master_by_telegram_id(telegram_id)
        if master:
            await message.answer(
                "❌ Этот пользователь уже зарегистрирован как мастер.",
                reply_markup=get_cancel_keyboard(),
            )
            return

        # Сохраняем ID и переходим к вводу телефона
        await state.update_data(telegram_id=telegram_id, user_name=user.get_full_name())
        await state.set_state(AddMasterStates.enter_phone)

        await message.answer(
            f"✅ Пользователь найден: {user.get_full_name()}\n\n"
            "Введите номер телефона мастера:\n"
            "<i>(в формате +7XXXXXXXXXX)</i>",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard(),
        )

    finally:
        await db.disconnect()


@router.message(AddMasterStates.enter_phone, F.text != "❌ Отмена")
async def process_master_phone(message: Message, state: FSMContext):
    """
    Обработка ввода телефона мастера

    Args:
        message: Сообщение
        state: FSM контекст
    """
    phone = message.text.strip()

    if not validate_phone(phone):
        await message.answer(
            "❌ Неверный формат номера телефона.\n" "Введите номер в формате: +7XXXXXXXXXX",
            reply_markup=get_cancel_keyboard(),
        )
        return

    phone = format_phone(phone)

    await state.update_data(phone=phone)
    await state.set_state(AddMasterStates.enter_specialization)

    await message.answer(
        "📝 Введите специализацию мастера:\n"
        "<i>(например: Стиральные машины, Сантехника и т.д.)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AddMasterStates.enter_specialization, F.text != "❌ Отмена")
async def process_master_specialization(message: Message, state: FSMContext):
    """
    Обработка ввода специализации мастера

    Args:
        message: Сообщение
        state: FSM контекст
    """
    specialization = message.text.strip()

    if len(specialization) < 3:
        await message.answer(
            "❌ Специализация слишком короткая. Попробуйте еще раз:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(specialization=specialization)
    await state.set_state(AddMasterStates.confirm)

    # Получаем все данные
    data = await state.get_data()

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_add_master"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
    )

    await message.answer(
        "📋 <b>Проверьте данные мастера:</b>\n\n"
        f"👤 Имя: {data['user_name']}\n"
        f"🆔 Telegram ID: <code>{data['telegram_id']}</code>\n"
        f"📞 Телефон: {data['phone']}\n"
        f"🔧 Специализация: {data['specialization']}\n\n"
        "Подтвердите добавление:",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "confirm_add_master")
async def callback_confirm_add_master(callback: CallbackQuery, state: FSMContext, user_role: str):
    """
    Подтверждение добавления мастера

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    data = await state.get_data()

    db = ORMDatabase()
    await db.connect()

    try:
        # Создаем мастера
        await db.create_master(
            telegram_id=data["telegram_id"],
            phone=data["phone"],
            specialization=data["specialization"],
            is_approved=True,  # Администратор добавляет сразу с одобрением
        )

        # Добавляем роль мастера (не удаляя существующие роли)
        await db.add_user_role(data["telegram_id"], UserRole.MASTER)

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ADD_MASTER",
            details=f"Added master {data['telegram_id']}",
        )

        # Уведомляем мастера с retry механизмом
        from app.utils import safe_send_message

        result = await safe_send_message(
            callback.bot,
            data["telegram_id"],
            "✅ <b>Поздравляем!</b>\n\n"
            "Вы добавлены в систему как мастер.\n"
            "Теперь вы можете получать заявки на ремонт.\n\n"
            "Используйте /start для начала работы.",
            parse_mode="HTML",
        )
        if not result:
            logger.error(
                f"Failed to send notification to master {data['telegram_id']} after retries"
            )

        await callback.message.edit_text(
            f"✅ <b>Мастер успешно добавлен!</b>\n\n"
            f"👤 {data['user_name']}\n"
            f"🆔 ID: {data['telegram_id']}\n"
            f"📞 {data['phone']}\n"
            f"🔧 {data['specialization']}",
            parse_mode="HTML",
        )

        log_action(callback.from_user.id, "ADD_MASTER", f"Master ID: {data['telegram_id']}")

    finally:
        await db.disconnect()

    await state.clear()
    await callback.answer("Мастер добавлен!")

    # Возвращаем главное меню
    from app.handlers.common import get_menu_with_counter

    menu_keyboard = await get_menu_with_counter([UserRole.ADMIN])
    await callback.message.answer("Главное меню:", reply_markup=menu_keyboard)


@router.callback_query(F.data.startswith("manage_master:"))
async def callback_manage_master(callback: CallbackQuery, user_role: str):
    """
    Управление конкретным мастером

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    telegram_id = int(callback.data.split(":")[1])

    db = ORMDatabase()
    await db.connect()

    try:
        master = await db.get_master_by_telegram_id(telegram_id)

        if not master:
            await callback.answer("Мастер не найден", show_alert=True)
            return

        display_name = master.get_display_name()
        status = "✅ Одобрен" if master.is_approved else "⏳ Ожидает одобрения"
        active = "🟢 Активен" if master.is_active else "🔴 Неактивен"

        # Получаем статистику мастера
        orders = await db.get_orders_by_master(master.id, exclude_closed=False)
        total_orders = len(orders)
        completed_orders = len([o for o in orders if o.status == OrderStatus.CLOSED])

        text = (
            f"👤 <b>{display_name}</b>\n\n"
            f"🆔 Telegram ID: <code>{telegram_id}</code>\n"
            f"📞 Телефон: {master.phone}\n"
            f"🔧 Специализация: {master.specialization}\n"
            f"📊 Статус: {status}\n"
            f"🔄 Активность: {active}\n\n"
            f"📈 <b>Статистика:</b>\n"
            f"• Всего заявок: {total_orders}\n"
            f"• Завершено: {completed_orders}\n"
        )

        keyboard = get_master_management_keyboard(telegram_id, master.is_active)

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("deactivate_master:"))
async def callback_deactivate_master(callback: CallbackQuery, user_role: str):
    """
    Деактивация мастера

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    telegram_id = int(callback.data.split(":")[1])

    db = ORMDatabase()
    await db.connect()

    try:
        # Получаем информацию о мастере для архивирования
        master = await db.get_master_by_telegram_id(telegram_id)
        if not master:
            await callback.answer("Мастер не найден", show_alert=True)
            return

        # Архивируем заявки мастера
        from app.services.master_archive_service import MasterArchiveService

        archive_service = MasterArchiveService()
        archive_path = await archive_service.archive_master_orders(master.id, "deactivation")

        if archive_path:
            await callback.message.answer(
                f"📁 <b>Архив создан</b>\n\n"
                f"Заявки мастера {master.get_display_name()} сохранены в архиве:\n"
                f"<code>{archive_path}</code>",
                parse_mode="HTML",
            )

        await db.update_master_status(telegram_id, is_active=False)

        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="DEACTIVATE_MASTER",
            details=f"Deactivated master {telegram_id} and archived orders",
        )

        # Обновляем сообщение
        await callback_manage_master(callback, user_role)

        log_action(callback.from_user.id, "DEACTIVATE_MASTER", f"Master ID: {telegram_id}")

    finally:
        await db.disconnect()

    await callback.answer("Мастер деактивирован и заявки заархивированы")


@router.callback_query(F.data.startswith("activate_master:"))
async def callback_activate_master(callback: CallbackQuery, user_role: str):
    """
    Активация мастера

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    telegram_id = int(callback.data.split(":")[1])

    db = ORMDatabase()
    await db.connect()

    try:
        await db.update_master_status(telegram_id, is_active=True)

        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ACTIVATE_MASTER",
            details=f"Activated master {telegram_id}",
        )

        # Обновляем сообщение
        await callback_manage_master(callback, user_role)

        log_action(callback.from_user.id, "ACTIVATE_MASTER", f"Master ID: {telegram_id}")

    finally:
        await db.disconnect()

    await callback.answer("Мастер активирован")


@router.callback_query(F.data.startswith("fire_master:"))
async def callback_fire_master(callback: CallbackQuery, user_role: str):
    """
    Увольнение мастера (удаление из системы)

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    telegram_id = int(callback.data.split(":")[1])

    db = ORMDatabase()
    await db.connect()

    try:
        master = await db.get_master_by_telegram_id(telegram_id)
        if not master:
            await callback.answer("Мастер не найден", show_alert=True)
            return

        # Проверяем, есть ли активные заказы у мастера
        orders = await db.get_orders_by_master(master.id, exclude_closed=True)
        if orders:
            await callback.answer(
                f"❌ Нельзя уволить мастера с активными заказами ({len(orders)} шт.)",
                show_alert=True,
            )
            return

        # Архивируем заявки мастера перед увольнением
        from app.services.master_archive_service import MasterArchiveService

        archive_service = MasterArchiveService()
        archive_path = await archive_service.archive_master_orders(master.id, "firing")

        if archive_path:
            await callback.message.answer(
                f"📁 <b>Архив создан</b>\n\n"
                f"Заявки мастера {master.get_display_name()} сохранены в архиве:\n"
                f"<code>{archive_path}</code>",
                parse_mode="HTML",
            )

        # Удаляем мастера из системы
        await db.delete_master(telegram_id)

        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="FIRE_MASTER",
            details=f"Fired master {telegram_id} ({master.get_display_name()}) and archived orders",
        )

        # Возвращаемся к списку мастеров
        await callback_list_all_masters(callback, user_role)

        log_action(callback.from_user.id, "FIRE_MASTER", f"Master ID: {telegram_id}")

    finally:
        await db.disconnect()

    await callback.answer("Мастер уволен и заявки заархивированы")


@router.callback_query(F.data.startswith("master_stats:"))
async def callback_master_stats(callback: CallbackQuery, user_role: str):
    """
    Статистика мастера

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    telegram_id = int(callback.data.split(":")[1])

    db = ORMDatabase()
    await db.connect()

    try:
        master = await db.get_master_by_telegram_id(telegram_id)

        if not master:
            await callback.answer("Мастер не найден", show_alert=True)
            return

        orders = await db.get_orders_by_master(master.id, exclude_closed=False)

        # Подсчет статистики
        total = len(orders)
        by_status = {}

        for order in orders:
            by_status[order.status] = by_status.get(order.status, 0) + 1

        display_name = master.get_display_name()

        text = (
            f"📊 <b>Статистика мастера</b>\n"
            f"👤 {display_name}\n\n"
            f"<b>Всего заявок:</b> {total}\n\n"
            f"<b>По статусам:</b>\n"
        )

        for status, count in by_status.items():
            emoji = OrderStatus.get_status_emoji(status)
            name = OrderStatus.get_status_name(status)
            text += f"{emoji} {name}: {count}\n"

        await callback.answer(text, show_alert=True)

    finally:
        await db.disconnect()


@router.message(F.text.regexp(r"^/closed_order(\d+)$"))
@handle_errors
async def cmd_closed_order_edit(message: Message, user_role: str):
    """
    Команда для редактирования закрытой заявки
    Формат: /closed_order123
    """
    if user_role not in [UserRole.ADMIN]:
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return

    # Извлекаем номер заявки из команды
    import re

    match = re.match(r"^/closed_order(\d+)$", message.text)
    if not match:
        await message.reply("❌ Неверный формат команды. Используйте: /closed_order123")
        return

    order_id = int(match.group(1))

    db = ORMDatabase()
    await db.connect()

    try:
        # Получаем заявку
        order = await db.get_order_by_id(order_id)
        if not order:
            await message.reply(f"❌ Заявка #{order_id} не найдена.")
            return

        # Проверяем, что заявка закрыта
        if order.status != OrderStatus.CLOSED:
            await message.reply(f"❌ Заявка #{order_id} не закрыта (статус: {order.status}).")
            return

        # Показываем финансовую информацию заявки
        await show_closed_order_financial_info(message, order, user_role)

    except Exception as e:
        logger.exception(f"Ошибка при редактировании закрытой заявки #{order_id}: {e}")
        await message.reply("❌ Произошла ошибка при получении заявки.")
    finally:
        await db.disconnect()


@router.message(F.text == "👤 Пользователи")
async def btn_users(message: Message, user_role: str):
    """
    Обработчик кнопки управления пользователями

    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    db = ORMDatabase()
    await db.connect()

    try:
        users = await db.get_all_users()

        text = "👤 <b>Пользователи системы:</b>\n\n"

        # Группируем по ролям
        by_role = {}
        for user in users:
            if user.role not in by_role:
                by_role[user.role] = []
            by_role[user.role].append(user)

        role_names = {
            UserRole.ADMIN: "Администратор",
            UserRole.DISPATCHER: "Диспетчер",
            UserRole.MASTER: "Мастер",
            UserRole.UNKNOWN: "Неизвестно",
        }

        # Отображаем пользователей с группировкой
        role_headers = {
            UserRole.ADMIN: "Администраторы",
            UserRole.DISPATCHER: "Диспетчеры",
            UserRole.MASTER: "Мастера",
            UserRole.UNKNOWN: "Неизвестные",
        }

        for role, role_users in by_role.items():
            text += f"<b>{role_headers.get(role, role)}:</b>\n"
            for user in role_users:
                # Формируем имя пользователя из доступных полей
                display_name = user.first_name or ""
                if user.last_name:
                    display_name += f" {user.last_name}"
                if not display_name.strip():
                    display_name = user.username or f"User{user.telegram_id}"

                # Показываем все роли пользователя
                user_roles = user.get_roles()
                roles_str = ", ".join([role_names.get(r, r) for r in user_roles])
                text += f"  • {display_name} (ID: {user.telegram_id}) - {roles_str}\n"
            text += "\n"

        await message.answer(text, parse_mode="HTML")

    finally:
        await db.disconnect()


@router.callback_query(F.data == "back_to_masters")
async def callback_back_to_masters(callback: CallbackQuery, user_role: str):
    """
    Возврат к списку мастеров

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    # Создаем новое сообщение с меню мастеров
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👥 Все мастера", callback_data="list_all_masters"))
    builder.row(InlineKeyboardButton(text="➕ Добавить мастера", callback_data="add_master"))

    await callback.message.edit_text(
        "👥 <b>Управление мастерами</b>\n\n" "Выберите действие:",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )

    await callback.answer()


# ==================== УСТАНОВКА РАБОЧЕЙ ГРУППЫ ====================


@router.callback_query(F.data.startswith("set_work_chat:"))
async def callback_set_work_chat(callback: CallbackQuery, state: FSMContext, user_role: str):
    """
    Начало процесса установки рабочей группы для мастера

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    telegram_id = int(callback.data.split(":")[1])

    # Сохраняем telegram_id мастера в состоянии
    await state.update_data(master_telegram_id=telegram_id)
    await state.set_state(SetWorkChatStates.enter_chat_id)

    # Создаем reply клавиатуру с KeyboardButtonRequestChat
    from aiogram.types import KeyboardButton, KeyboardButtonRequestChat
    from aiogram.utils.keyboard import ReplyKeyboardBuilder

    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(
            text="💬 Выбрать группу",
            request_chat=KeyboardButtonRequestChat(
                request_id=1,
                chat_is_channel=False,  # Включает только обычные группы (не каналы)
            ),
        )
    )
    builder.row(KeyboardButton(text="❌ Отмена"))

    keyboard = builder.as_markup(resize_keyboard=True)

    await callback.message.answer(
        "💬 <b>Установка рабочей группы</b>\n\n"
        "Для установки рабочей группы для мастера:\n\n"
        "1️⃣ Добавьте бота в рабочую группу с мастером\n"
        "2️⃣ Нажмите кнопку ниже и выберите группу\n\n"
        "<i>Кнопка отмены доступна внизу</i>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    await callback.answer()


@router.message(F.chat_shared, SetWorkChatStates.enter_chat_id)
async def handle_work_chat_selection(message: Message, state: FSMContext, user_role: str):
    """
    Обработка выбранной группы для мастера

    Args:
        message: Сообщение с информацией о выбранной группе
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    # Получаем информацию о выбранной группе
    chat_shared = message.chat_shared

    if not chat_shared or chat_shared.request_id != 1:
        from app.handlers.common import get_menu_with_counter

        menu_keyboard = await get_menu_with_counter([user_role])
        await message.answer("❌ Неверный запрос.", reply_markup=menu_keyboard)
        await state.clear()
        return

    chat_id = chat_shared.chat_id
    data = await state.get_data()
    master_telegram_id = data.get("master_telegram_id")

    # Получаем информацию о группе через API
    try:
        chat_info = await message.bot.get_chat(chat_id)
        chat_title = chat_info.title or f"ID: {chat_id}"
        chat_type = chat_info.type

        # Проверяем, что это действительно группа
        if chat_type not in ["group", "supergroup"]:
            from app.handlers.common import get_menu_with_counter

            menu_keyboard = await get_menu_with_counter([user_role])
            await message.answer(
                "❌ Выбранный чат не является группой.",
                reply_markup=menu_keyboard,
            )
            await state.clear()
            return

        # Сохраняем work_chat_id для мастера
        db = ORMDatabase()
        await db.connect()

        try:
            # Получаем информацию о мастере
            master = await db.get_master_by_telegram_id(master_telegram_id)

            if not master:
                from app.handlers.common import get_menu_with_counter

                menu_keyboard = await get_menu_with_counter([user_role])
                await message.answer("❌ Мастер не найден", reply_markup=menu_keyboard)
                await state.clear()
                return

            # Обновляем work_chat_id
            await db.update_master_work_chat(master_telegram_id, chat_id)

            # Проверяем, что обновление прошло успешно
            updated_master = await db.get_master_by_telegram_id(master_telegram_id)
            logger.info(
                f"Work chat update verification: master {master_telegram_id} -> work_chat_id: {updated_master.work_chat_id if updated_master else 'NOT FOUND'}"
            )

            from app.handlers.common import get_menu_with_counter

            menu_keyboard = await get_menu_with_counter([user_role])
            await message.answer(
                f"✅ <b>Рабочая группа установлена!</b>\n\n"
                f"👤 Мастер: {master.get_display_name()}\n"
                f"💬 Группа: {chat_title}\n"
                f"🆔 Chat ID: <code>{chat_id}</code>\n\n"
                f"Теперь все уведомления о новых заявках будут отправляться в эту группу.",
                parse_mode="HTML",
                reply_markup=menu_keyboard,
            )

            logger.info(f"Work chat {chat_id} set for master {master_telegram_id}")

        finally:
            await db.disconnect()

    except Exception as e:
        logger.error(f"Error getting chat info: {e}")
        from app.handlers.common import get_menu_with_counter

        menu_keyboard = await get_menu_with_counter([user_role])
        await message.answer(
            f"✅ <b>Рабочая группа установлена!</b>\n\n"
            f"🆔 Chat ID: <code>{chat_id}</code>\n\n"
            f"Теперь все уведомления о новых заявках будут отправляться в эту группу.",
            parse_mode="HTML",
            reply_markup=menu_keyboard,
        )

    await state.clear()


@router.message(F.text == "❌ Отмена", SetWorkChatStates.enter_chat_id)
async def handle_cancel_work_chat(message: Message, state: FSMContext, user_role: str):
    """
    Отмена установки рабочей группы

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    from app.handlers.common import get_menu_with_counter

    menu_keyboard = await get_menu_with_counter([user_role])
    await message.answer(
        "❌ <b>Установка рабочей группы отменена</b>\n\n"
        "Вы можете попробовать снова в любое время.",
        parse_mode="HTML",
        reply_markup=menu_keyboard,
    )

    await state.clear()


# ==================== АДМИН ДЕЙСТВУЕТ ОТ ИМЕНИ МАСТЕРА ====================


@router.callback_query(F.data.startswith("admin_accept_order:"))
async def callback_admin_accept_order(callback: CallbackQuery, user_role: str, user_roles: list):
    """
    Принятие заявки админом от имени мастера

    Args:
        callback: Callback query
        user_role: Роль пользователя (основная)
        user_roles: Список ролей пользователя
    """
    if user_role != UserRole.ADMIN:
        await callback.answer("У вас нет доступа к этой функции", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])

    db = ORMDatabase()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        if not order.assigned_master_id:
            await callback.answer("Мастер не назначен на эту заявку", show_alert=True)
            return

        master = await db.get_master_by_id(order.assigned_master_id)

        if not master:
            await callback.answer("Мастер не найден", show_alert=True)
            return

        # Обновляем статус (админ может менять от имени мастера)
        # Используем skip_validation=True так как админ имеет особые права
        await db.update_order_status(
            order_id=order_id,
            status=OrderStatus.ACCEPTED,
            changed_by=callback.from_user.id,
            skip_validation=True,  # Админ может менять статусы принудительно
        )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ADMIN_ACCEPT_ORDER_FOR_MASTER",
            details=f"Admin accepted order #{order_id} on behalf of master {master.telegram_id}",
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

        # Личных уведомлений мастеру нет — бот работает только в рабочих группах

        await callback.answer("Заявка принята от имени мастера!")

        # Обновляем сообщение
        from app.keyboards.inline import get_order_actions_keyboard

        status_emoji = OrderStatus.get_status_emoji(OrderStatus.ACCEPTED)
        status_name = OrderStatus.get_status_name(OrderStatus.ACCEPTED)

        text = (
            f"📋 <b>Заявка #{order.id}</b>\n\n"
            f"📊 <b>Статус:</b> {status_emoji} {status_name}\n"
            f"👨‍🔧 <b>Мастер:</b> {master.get_display_name()}\n"
            f"🔧 <b>Тип техники:</b> {order.equipment_type}\n"
            f"📝 <b>Описание:</b> {order.description}\n\n"
            f"👤 <b>Клиент:</b> {order.client_name}\n"
            f"📍 <b>Адрес:</b> {order.client_address}\n"
            f"📞 <b>Телефон:</b> <i>Будет доступен после прибытия на объект</i>\n\n"
        )

        if order.notes:
            text += f"📝 <b>Заметки:</b> {order.notes}\n\n"

        if order.scheduled_time:
            text += f"⏰ <b>Время прибытия:</b> {order.scheduled_time}\n\n"

        text += "<i>✅ Заявка принята администратором от имени мастера</i>"

        keyboard = get_order_actions_keyboard(order, UserRole.ADMIN)

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

        log_action(
            callback.from_user.id,
            "ADMIN_ACCEPT_ORDER_FOR_MASTER",
            f"Order #{order_id} for master {master.telegram_id}",
        )

    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("admin_onsite_order:"))
async def callback_admin_onsite_order(callback: CallbackQuery, user_role: str, user_roles: list):
    """
    Отметка 'На объекте' админом от имени мастера

    Args:
        callback: Callback query
        user_role: Роль пользователя (основная)
        user_roles: Список ролей пользователя
    """
    if user_role != UserRole.ADMIN:
        await callback.answer("У вас нет доступа к этой функции", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])

    db = ORMDatabase()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        if not order.assigned_master_id:
            await callback.answer("Мастер не назначен на эту заявку", show_alert=True)
            return

        master = await db.get_master_by_id(order.assigned_master_id)

        if not master:
            await callback.answer("Мастер не найден", show_alert=True)
            return

        # Обновляем статус (админ может менять от имени мастера)
        # Используем skip_validation=True так как админ имеет особые права
        await db.update_order_status(
            order_id=order_id,
            status=OrderStatus.ONSITE,
            changed_by=callback.from_user.id,
            skip_validation=True,  # Админ может менять статусы принудительно
        )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ADMIN_ONSITE_ORDER_FOR_MASTER",
            details=f"Admin marked order #{order_id} as onsite on behalf of master {master.telegram_id}",
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

        # Личных уведомлений мастеру нет — бот работает только в рабочих группах

        await callback.answer("Статус обновлен от имени мастера!")

        # Обновляем сообщение
        from app.keyboards.inline import get_order_actions_keyboard

        status_emoji = OrderStatus.get_status_emoji(OrderStatus.ONSITE)
        status_name = OrderStatus.get_status_name(OrderStatus.ONSITE)

        text = (
            f"📋 <b>Заявка #{order.id}</b>\n\n"
            f"📊 <b>Статус:</b> {status_emoji} {status_name}\n"
            f"👨‍🔧 <b>Мастер:</b> {master.get_display_name()}\n"
            f"🔧 <b>Тип техники:</b> {order.equipment_type}\n"
            f"📝 <b>Описание:</b> {order.description}\n\n"
            f"👤 <b>Клиент:</b> {order.client_name}\n"
            f"📍 <b>Адрес:</b> {order.client_address}\n"
            f"📞 <b>Телефон:</b> {order.client_phone}\n\n"
        )

        if order.notes:
            text += f"📝 <b>Заметки:</b> {order.notes}\n\n"

        if order.scheduled_time:
            text += f"⏰ <b>Время прибытия:</b> {order.scheduled_time}\n\n"

        text += "<i>🏠 Статус обновлен администратором от имени мастера</i>"

        keyboard = get_order_actions_keyboard(order, UserRole.ADMIN)

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

        log_action(
            callback.from_user.id,
            "ADMIN_ONSITE_ORDER_FOR_MASTER",
            f"Order #{order_id} for master {master.telegram_id}",
        )

    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("admin_refuse_order_complete:"))
async def callback_admin_refuse_order_complete(
    callback: CallbackQuery, state: FSMContext, user_role: str
):
    """
    Быстрое завершение заявки как отказ админом от имени мастера (0 рублей)

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    order_id = int(callback.data.split(":")[1])

    db = ORMDatabase()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        master = await db.get_master_by_id(order.assigned_master_id)

        if not master:
            await callback.answer("Мастер не найден", show_alert=True)
            return

        # Сохраняем данные в состоянии
        await state.update_data(order_id=order_id, acting_as_master_id=master.telegram_id)

        # Переходим к подтверждению отказа
        from app.states import RefuseOrderStates

        await state.set_state(RefuseOrderStates.confirm_refusal)

        # Показываем подтверждение
        await callback.message.edit_text(
            f"⚠️ <b>Подтверждение отказа (от имени мастера)</b>\n\n"
            f"📋 Заявка #{order_id}\n"
            f"🔧 Тип техники: {order.equipment_type}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"👨‍🔧 Мастер: {master.get_display_name()}\n\n"
            f"<b>Вы уверены, что хотите закрыть заявку как отказ?</b>\n\n"
            f"<i>Заявка будет помечена как отказ с суммой 0 рублей.</i>",
            parse_mode="HTML",
            reply_markup=get_yes_no_keyboard("admin_confirm_refuse", order_id),
        )

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("admin_complete_order:"))
async def callback_admin_complete_order(callback: CallbackQuery, state: FSMContext, user_role: str):
    """
    Начало процесса завершения заявки админом от имени мастера

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        await callback.answer("У вас нет доступа к этой функции", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])

    db = ORMDatabase()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        if not order.assigned_master_id:
            await callback.answer("Мастер не назначен на эту заявку", show_alert=True)
            return

        master = await db.get_master_by_id(order.assigned_master_id)

        if not master:
            await callback.answer("Мастер не найден", show_alert=True)
            return

        # Сохраняем ID заказа и мастера в состоянии FSM
        await state.update_data(order_id=order_id, acting_as_master_id=master.telegram_id)

        # Переходим в состояние запроса общей суммы
        from app.states import CompleteOrderStates

        await state.set_state(CompleteOrderStates.enter_total_amount)

        await callback.message.answer(
            f"💰 <b>Завершение заявки #{order_id} от имени мастера {master.get_display_name()}</b>\n\n"
            f"Пожалуйста, введите <b>общую сумму заказа</b> (в рублях):\n"
            f"Например: 5000, 5000.50 или 0",
            parse_mode="HTML",
        )

        log_action(
            callback.from_user.id,
            "ADMIN_START_COMPLETE_ORDER_FOR_MASTER",
            f"Order #{order_id} for master {master.telegram_id}",
        )

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("admin_dr_order:"))
async def callback_admin_dr_order(callback: CallbackQuery, state: FSMContext, user_role: str):
    """
    ДР - админ от имени мастера

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        await callback.answer("У вас нет доступа к этой функции", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])

    logger.debug(f"[DR] Admin starting DR process for order #{order_id}")

    db = ORMDatabase()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        if not order.assigned_master_id:
            await callback.answer("Мастер не назначен на эту заявку", show_alert=True)
            return

        master = await db.get_master_by_id(order.assigned_master_id)

        if not master:
            await callback.answer("Мастер не найден", show_alert=True)
            return

        logger.debug(f"[DR] Order found, Master ID: {master.telegram_id}")

        # Сохраняем order_id и мастера в state
        await state.update_data(order_id=order_id, acting_as_master_id=master.telegram_id)

        logger.debug("[DR] Transitioning to LongRepairStates.enter_completion_date_and_prepayment")

        # Переходим к вводу срока окончания и предоплаты
        from app.states import LongRepairStates

        await state.set_state(LongRepairStates.enter_completion_date_and_prepayment)

        await callback.message.answer(
            f"⏳ <b>ДР - Заявка #{order_id}</b>\n"
            f"<b>От имени мастера:</b> {master.get_display_name()}\n\n"
            f"Введите <b>примерный срок окончания ремонта</b> и <b>предоплату</b> (если была).\n\n"
            f"<i>Если предоплаты не было - просто укажите срок.</i>",
            parse_mode="HTML",
        )

        await callback.answer()

    finally:
        await db.disconnect()


@router.callback_query(lambda c: c.data.startswith("admin_confirm_refuse"))
async def process_admin_refuse_confirmation_callback(
    callback_query: CallbackQuery, state: FSMContext, user_role: str
):
    """
    Обработка подтверждения отказа от заявки админом

    Args:
        callback_query: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role != UserRole.ADMIN:
        return

    # Извлекаем данные из callback_data
    parts = callback_query.data.split(":")
    action = parts[1]  # "yes" или "no"
    order_id = int(parts[2])

    if action == "yes":
        # Подтверждаем отказ
        data = await state.get_data()
        order_id = data.get("order_id", order_id)
        acting_as_master_id = data.get("acting_as_master_id")

        # Завершаем заказ как отказ от имени мастера
        from app.handlers.master import complete_order_as_refusal

        await complete_order_as_refusal(
            callback_query.message, state, order_id, acting_as_master_id
        )

        # Очищаем состояние
        await state.clear()

        await callback_query.answer("Заявка отклонена")
    else:
        # Отменяем отказ - получаем заказ для клавиатуры
        db = ORMDatabase()
        await db.connect()
        try:
            order = await db.get_order_by_id(order_id)
            if order:
                await callback_query.message.edit_text(
                    "❌ Отказ отменен.\n\nЗаявка остается активной.",
                    reply_markup=get_order_actions_keyboard(order, UserRole.ADMIN),
                )
            else:
                await callback_query.message.edit_text("❌ Отказ отменен.\n\nЗаявка не найдена.")
        finally:
            await db.disconnect()
        await state.clear()
        await callback_query.answer("Отказ отменен")


async def show_closed_order_financial_info(message: Message, order, user_role: str):
    """
    Показать финансовую информацию закрытой заявки с кнопками редактирования

    Args:
        message: Сообщение
        order: Объект заявки
        user_role: Роль пользователя
    """
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    # Формируем текст с финансовой информацией
    text = (
        f"💰 <b>Финансовая информация - Заявка #{order.id}</b>\n\n"
        f"📱 <b>Тип техники:</b> {order.equipment_type}\n"
        f"👤 <b>Клиент:</b> {order.client_name}\n"
        f"📍 <b>Адрес:</b> {order.client_address}\n"
        f"📞 <b>Телефон:</b> {order.client_phone}\n\n"
        f"💵 <b>Общая сумма:</b> {order.total_amount or 0:.2f} ₽\n"
        f"🔧 <b>Расходы на материалы:</b> {order.materials_cost or 0:.2f} ₽\n"
        f"👨‍🔧 <b>Доход мастера:</b> {order.master_profit or 0:.2f} ₽\n"
        f"🏢 <b>Доход компании:</b> {order.company_profit or 0:.2f} ₽\n"
    )

    # Добавляем информацию о предоплате, если есть
    if order.prepayment_amount and order.prepayment_amount > 0:
        text += f"💳 <b>Предоплата:</b> {order.prepayment_amount:.2f} ₽\n"

    # Создаем клавиатуру с кнопками редактирования
    keyboard = [
        [
            InlineKeyboardButton(
                text="💵 Редактировать общую сумму", callback_data=f"edit_total_amount:{order.id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔧 Редактировать расходы", callback_data=f"edit_materials_cost:{order.id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="👨‍🔧 Редактировать доход мастера",
                callback_data=f"edit_master_profit:{order.id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="🏢 Редактировать доход компании",
                callback_data=f"edit_company_profit:{order.id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="💳 Редактировать предоплату", callback_data=f"edit_prepayment:{order.id}"
            )
        ],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_financial_info")],
    ]

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await message.reply(text, parse_mode="HTML", reply_markup=reply_markup)


# ==================== ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ФИНАНСОВОЙ ИНФОРМАЦИИ ====================


@router.callback_query(F.data.startswith("edit_total_amount:"))
@require_role([UserRole.ADMIN])
@handle_errors
async def callback_edit_total_amount(callback: CallbackQuery, state: FSMContext, user_role: str):
    """Редактирование общей суммы заявки"""
    order_id = int(callback.data.split(":")[1])

    await state.update_data(order_id=order_id, field="total_amount")
    from app.states import AdminCloseOrderStates

    await state.set_state(AdminCloseOrderStates.enter_value)
    await callback.message.edit_text(
        f"💵 <b>Редактирование общей суммы</b>\n\n"
        f"Введите новую общую сумму для заявки #{order_id}:\n\n"
        f"<i>Например: 1500.50</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_materials_cost:"))
@require_role([UserRole.ADMIN])
@handle_errors
async def callback_edit_materials_cost(callback: CallbackQuery, state: FSMContext, user_role: str):
    """Редактирование расходов на материалы"""
    order_id = int(callback.data.split(":")[1])

    await state.update_data(order_id=order_id, field="materials_cost")
    from app.states import AdminCloseOrderStates

    await state.set_state(AdminCloseOrderStates.enter_value)
    await callback.message.edit_text(
        f"🔧 <b>Редактирование расходов на материалы</b>\n\n"
        f"Введите новые расходы на материалы для заявки #{order_id}:\n\n"
        f"<i>Например: 300.00</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_master_profit:"))
@require_role([UserRole.ADMIN])
@handle_errors
async def callback_edit_master_profit(callback: CallbackQuery, state: FSMContext, user_role: str):
    """Редактирование дохода мастера"""
    order_id = int(callback.data.split(":")[1])

    await state.update_data(order_id=order_id, field="master_profit")
    from app.states import AdminCloseOrderStates

    await state.set_state(AdminCloseOrderStates.enter_value)
    await callback.message.edit_text(
        f"👨‍🔧 <b>Редактирование дохода мастера</b>\n\n"
        f"Введите новый доход мастера для заявки #{order_id}:\n\n"
        f"<i>Например: 800.00</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_company_profit:"))
@require_role([UserRole.ADMIN])
@handle_errors
async def callback_edit_company_profit(callback: CallbackQuery, state: FSMContext, user_role: str):
    """Редактирование дохода компании"""
    order_id = int(callback.data.split(":")[1])

    await state.update_data(order_id=order_id, field="company_profit")
    from app.states import AdminCloseOrderStates

    await state.set_state(AdminCloseOrderStates.enter_value)
    await callback.message.edit_text(
        f"🏢 <b>Редактирование дохода компании</b>\n\n"
        f"Введите новый доход компании для заявки #{order_id}:\n\n"
        f"<i>Например: 400.00</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_prepayment:"))
@require_role([UserRole.ADMIN])
@handle_errors
async def callback_edit_prepayment(callback: CallbackQuery, state: FSMContext, user_role: str):
    """Редактирование предоплаты"""
    order_id = int(callback.data.split(":")[1])

    await state.update_data(order_id=order_id, field="prepayment_amount")
    from app.states import AdminCloseOrderStates

    await state.set_state(AdminCloseOrderStates.enter_value)
    await callback.message.edit_text(
        f"💳 <b>Редактирование предоплаты</b>\n\n"
        f"Введите новую предоплату для заявки #{order_id}:\n\n"
        f"<i>Например: 500.00 или 0 если предоплаты не было</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "close_financial_info")
@handle_errors
async def callback_close_financial_info(callback: CallbackQuery):
    """Закрытие финансовой информации"""
    await callback.message.delete()
    await callback.answer("Финансовая информация закрыта")


# Обработчик ввода новых значений (ТОЛЬКО в нужном состоянии)
@router.message(AdminCloseOrderStates.enter_value)
@require_role([UserRole.ADMIN])
@handle_errors
async def process_financial_value(message: Message, state: FSMContext, user_role: str):
    """Обработка ввода финансового значения (редактирование закрытой заявки)"""
    current_state = await state.get_state()
    data = await state.get_data()
    order_id = data.get("order_id")
    field = data.get("field")

    logger.info(f"[ADMIN_EDIT] state={current_state}, field={field}, raw='{message.text}'")

    if not order_id or not field:
        await message.reply("❌ Ошибка: данные не найдены. Попробуйте снова.")
        return

    # Парсим число, поддерживая запятую/точку
    text = (message.text or "").strip().replace(",", ".")
    try:
        value = float(text)
    except ValueError:
        await message.reply("❌ Неверный формат числа. Введите число (например: 1500.50)")
        return

    db = ORMDatabase()
    await db.connect()
    try:
        update_data = {field: value}
        success = await db.update_order(order_id, update_data)
        if success:
            order = await db.get_order_by_id(order_id)
            if order:
                await show_closed_order_financial_info(message, order, user_role)
                await message.reply(f"✅ {field} обновлено: {value:.2f} ₽")
            else:
                await message.reply("✅ Значение обновлено, но не удалось загрузить заявку")
        else:
            await message.reply("❌ Ошибка при обновлении значения")
    finally:
        await db.disconnect()

    await state.clear()


@router.message(Command("delete_order"))
@handle_errors
async def cmd_delete_order(message: Message, user_role: str):
    """
    Команда для удаления заявки
    
    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    # Проверяем права доступа
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        await message.reply("❌ У вас нет прав для удаления заявок")
        return
    
    # Получаем ID заявки из сообщения
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.reply(
            "❌ Неверный формат команды\n\n"
            "Используйте: /delete_order <ID_заявки>\n"
            "Пример: /delete_order 97"
        )
        return
    
    try:
        order_id = int(command_parts[1])
    except ValueError:
        await message.reply("❌ ID заявки должен быть числом")
        return
    
    db = ORMDatabase()
    await db.connect()
    
    try:
        # Получаем заявку
        order = await db.get_order_by_id(order_id)
        
        if not order:
            await message.reply(f"❌ Заявка #{order_id} не найдена")
            return
        
        # Проверяем, что заявка не удалена
        if order.deleted_at:
            await message.reply(f"❌ Заявка #{order_id} уже удалена")
            return
        
        # Показываем информацию о заявке
        await message.reply(
            f"📋 <b>Заявка #{order_id}</b>\n\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📱 Техника: {order.equipment_type}\n"
            f"📝 Описание: {order.description}\n"
            f"📊 Статус: {order.status}\n"
            f"📅 Создана: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"❓ Вы уверены, что хотите удалить эту заявку?",
            parse_mode="HTML",
            reply_markup=get_yes_no_keyboard(f"confirm_delete_order:{order_id}")
        )
        
    except Exception as e:
        logger.error(f"Error in delete_order command: {e}")
        await message.reply("❌ Ошибка при получении информации о заявке")
        
    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("confirm_delete_order:"))
@handle_errors
async def callback_confirm_delete_order(callback: CallbackQuery, user_role: str):
    """
    Подтверждение удаления заявки
    
    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    # Проверяем права доступа
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        await callback.answer("❌ У вас нет прав для удаления заявок", show_alert=True)
        return
    
    # Получаем ID заявки и действие
    parts = callback.data.split(":")
    order_id = int(parts[1])
    action = parts[2] if len(parts) > 2 else "no"
    
    if action == "no":
        await callback.message.edit_text("❌ Удаление заявки отменено")
        await callback.answer()
        return
    
    db = ORMDatabase()
    await db.connect()
    
    try:
        # Получаем заявку
        order = await db.get_order_by_id(order_id)
        
        if not order:
            await callback.message.edit_text(f"❌ Заявка #{order_id} не найдена")
            return
        
        # Мягкое удаление заявки
        success = await db.soft_delete_order(order_id)
        
        if success:
            # Добавляем в аудит
            await db.add_audit_log(
                user_id=callback.from_user.id,
                action="DELETE_ORDER_COMMAND",
                details=f"Order #{order_id} deleted via /delete_order command"
            )
            
            await callback.message.edit_text(
                f"✅ Заявка #{order_id} успешно удалена\n\n"
                f"👤 Клиент: {order.client_name}\n"
                f"📱 Техника: {order.equipment_type}\n"
                f"📊 Статус: {order.status}"
            )
            
            logger.info(f"Order #{order_id} deleted by user {callback.from_user.id} via /delete_order command")
        else:
            await callback.message.edit_text(f"❌ Ошибка при удалении заявки #{order_id}")
            
    except Exception as e:
        logger.error(f"Error deleting order {order_id}: {e}")
        await callback.message.edit_text(f"❌ Ошибка при удалении заявки #{order_id}")
        
    finally:
        await db.disconnect()
    
    await callback.answer()
