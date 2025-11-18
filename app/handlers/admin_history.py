"""
Handler для работы с историей заявок (админ-панель)
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database.db import Database
from app.decorators import handle_errors
from app.filters.role_filter import RoleFilter
from app.presenters import OrderPresenter
from app.repositories.order_repository_extended import OrderRepositoryExtended
from app.services.search_service import SearchService
from app.utils.helpers import format_datetime


logger = logging.getLogger(__name__)
router = Router()


def get_history_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для работы с историей заявки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 История статусов", callback_data=f"history_status:{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 История изменений", callback_data=f"history_changes:{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Аудит действий", callback_data=f"history_audit:{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Полная история", callback_data=f"history_full:{order_id}"
                )
            ],
            [InlineKeyboardButton(text="« Назад", callback_data=f"view_order:{order_id}")],
        ]
    )


def get_deleted_orders_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура для списка удаленных заявок"""
    buttons = []

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"deleted_orders:{page-1}")
        )
    nav_buttons.append(
        InlineKeyboardButton(text="➡️ Вперед", callback_data=f"deleted_orders:{page+1}")
    )

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="« Главное меню", callback_data="admin_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_restore_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для восстановления заявки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Восстановить заявку", callback_data=f"restore_order:{order_id}"
                )
            ],
            [InlineKeyboardButton(text="📋 Просмотр", callback_data=f"view_deleted:{order_id}")],
            [InlineKeyboardButton(text="« Назад к списку", callback_data="deleted_orders:0")],
        ]
    )


# ===== КОМАНДЫ =====


@router.message(Command("history"), RoleFilter(["ADMIN", "DISPATCHER"]))
@handle_errors
async def cmd_history(message: Message, db: Database):
    """Команда для просмотра истории заявки"""
    text = message.text or ""
    args = text.split()

    if len(args) < 2:
        await message.answer(
            "📋 <b>Просмотр истории заявки</b>\n\n"
            "Использование: /history <номер_заявки>\n\n"
            "Пример: /history 123",
            parse_mode="HTML",
        )
        return

    try:
        order_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный номер заявки")
        return

    order_repo = OrderRepositoryExtended(db.get_connection())

    # Проверяем существование заявки
    order = await order_repo.get_by_id(order_id, include_deleted=True)

    if not order:
        await message.answer(f"❌ Заявка #{order_id} не найдена")
        return

    # Показываем меню истории
    text = f"📋 <b>История заявки #{order_id}</b>\n\n"
    text += f"🔧 Тип: {order.equipment_type}\n"
    text += f"📊 Текущий статус: {order.status}\n"
    text += f"👤 Клиент: {order.client_name}\n"

    if hasattr(order, "deleted_at") and order.deleted_at:
        text += f"\n🗑 <i>Заявка удалена: {format_datetime(order.deleted_at)}</i>\n"

    await message.answer(text, reply_markup=get_history_keyboard(order_id), parse_mode="HTML")


@router.message(Command("deleted"), RoleFilter(["ADMIN"]))
@handle_errors
async def cmd_deleted_orders(message: Message, db: Database):
    """Команда для просмотра удаленных заявок"""
    order_repo = OrderRepositoryExtended(db.get_connection())

    # Получаем удаленные заявки
    deleted_orders = await order_repo.get_deleted_orders(limit=10, offset=0)

    if not deleted_orders:
        await message.answer("✅ Нет удаленных заявок")
        return

    # Форматируем список
    text = "🗑 <b>Удаленные заявки</b>\n\n"
    text += f"Всего найдено: {len(deleted_orders)}\n\n"

    for order in deleted_orders:
        text += f"📋 <b>#{order.id}</b> - {order.equipment_type}\n"
        text += f"   👤 {order.client_name}\n"
        text += f"   📊 {order.status}\n"
        if hasattr(order, "deleted_at") and order.deleted_at:
            text += f"   🗑 {format_datetime(order.deleted_at)}\n"
        text += "\n"

    await message.answer(text, reply_markup=get_deleted_orders_keyboard(page=0), parse_mode="HTML")


@router.message(Command("search"), RoleFilter(["ADMIN", "DISPATCHER"]))
@handle_errors
async def cmd_search(message: Message, db: Database):
    """Команда для поиска заявок"""
    text = message.text or ""
    args = text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "🔍 <b>Поиск заявок</b>\n\n"
            "Использование: /search <запрос>\n\n"
            "Примеры:\n"
            "• /search холодильник\n"
            "• /search Иванов\n"
            "• /search 79991234567",
            parse_mode="HTML",
        )
        return

    query = args[1]

    order_repo = OrderRepositoryExtended(db.get_connection())
    search_service = SearchService(order_repo)

    # Поиск
    orders = await search_service.search(query=query, limit=20)

    # Форматируем результаты
    result = search_service.format_search_results(orders)

    await message.answer(result, parse_mode="HTML")


# ===== CALLBACK HANDLERS =====


@router.callback_query(F.data.startswith("history_status:"))
@handle_errors
async def callback_history_status(callback: CallbackQuery, db: Database):
    """Показать историю статусов"""
    data = callback.data or ""
    order_id = int(data.split(":")[1])

    order_repo = OrderRepositoryExtended(db.get_connection())

    # Получаем историю статусов
    history = await order_repo.get_status_history(order_id)

    if not history:
        await callback.answer("История статусов пуста", show_alert=True)
        return

    # Форматируем
    text = f"📊 <b>История статусов заявки #{order_id}</b>\n\n"

    for h in history[:10]:  # Последние 10
        text += f"🕐 {h['changed_at']}\n"
        text += f"   {h['old_status']} → <b>{h['new_status']}</b>\n"

        if h.get("username"):
            text += f"   Пользователь: @{h['username']}\n"

        if h.get("notes"):
            text += f"   📝 {h['notes']}\n"

        text += "\n"

    message_obj = callback.message
    if isinstance(message_obj, Message):
        await message_obj.edit_text(
            text, reply_markup=get_history_keyboard(order_id), parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("history_changes:"))
@handle_errors
async def callback_history_changes(callback: CallbackQuery, db: Database):
    """Показать историю изменений полей"""
    data = callback.data or ""
    order_id = int(data.split(":")[1])

    order_repo = OrderRepositoryExtended(db.get_connection())

    # Получаем полную историю
    full_history = await order_repo.get_full_history(order_id)
    field_history = full_history["field_history"]

    if not field_history:
        await callback.answer("История изменений пуста", show_alert=True)
        return

    # Форматируем
    text = f"🔄 <b>История изменений заявки #{order_id}</b>\n\n"

    for h in field_history[:10]:  # Последние 10
        text += f"🕐 {h['changed_at']}\n"
        text += f"   Поле: <b>{h['field_name']}</b>\n"
        text += f"   Было: {h['old_value'] or '(пусто)'}...\n"
        text += f"   Стало: {h['new_value'] or '(пусто)'}...\n"

        if h.get("username"):
            text += f"   Пользователь: @{h['username']}\n"

        text += "\n"

    message_obj = callback.message
    if isinstance(message_obj, Message):
        await message_obj.edit_text(
            text, reply_markup=get_history_keyboard(order_id), parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("history_audit:"))
@handle_errors
async def callback_history_audit(callback: CallbackQuery, db: Database):
    """Показать аудит действий"""
    data = callback.data or ""
    order_id = int(data.split(":")[1])

    order_repo = OrderRepositoryExtended(db.get_connection())

    # Получаем полную историю
    full_history = await order_repo.get_full_history(order_id)
    audit_logs = full_history["audit_logs"]

    if not audit_logs:
        await callback.answer("Аудит пуст", show_alert=True)
        return

    # Форматируем
    text = f"📝 <b>Аудит заявки #{order_id}</b>\n\n"

    for log in audit_logs[:10]:  # Последние 10
        text += f"🕐 {log['timestamp']}\n"
        text += f"   Действие: <b>{log['action']}</b>\n"
        text += f"   {log['details']}\n"

        if log.get("username"):
            text += f"   Пользователь: @{log['username']}\n"

        text += "\n"

    message_obj = callback.message
    if isinstance(message_obj, Message):
        await message_obj.edit_text(
            text, reply_markup=get_history_keyboard(order_id), parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("history_full:"))
@handle_errors
async def callback_history_full(callback: CallbackQuery, db: Database):
    """Показать полную историю"""
    data = callback.data or ""
    order_id = int(data.split(":")[1])

    order_repo = OrderRepositoryExtended(db.get_connection())
    search_service = SearchService(order_repo)

    # Получаем полную историю
    history = await search_service.get_full_order_history(order_id)

    # Форматируем краткую сводку
    text = f"📋 <b>Полная история заявки #{order_id}</b>\n\n"
    text += f"📊 Изменений статусов: {len(history['status_history'])}\n"
    text += f"🔄 Изменений полей: {len(history['field_history'])}\n"
    text += f"📝 Записей аудита: {len(history['audit_logs'])}\n\n"

    # Последние 3 изменения статусов
    if history["status_history"]:
        text += "<b>Последние изменения статусов:</b>\n"
        for h in history["status_history"][:3]:
            text += f"• {h['changed_at']}: {h['old_status']} → {h['new_status']}\n"

    message_obj = callback.message
    if isinstance(message_obj, Message):
        await message_obj.edit_text(
            text, reply_markup=get_history_keyboard(order_id), parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("deleted_orders:"))
@handle_errors
async def callback_deleted_orders(callback: CallbackQuery, db: Database):
    """Показать список удаленных заявок"""
    data = callback.data or ""
    page = int(data.split(":")[1])

    order_repo = OrderRepositoryExtended(db.get_connection())

    # Получаем удаленные заявки
    page_size = 10
    deleted_orders = await order_repo.get_deleted_orders(limit=page_size, offset=page * page_size)

    if not deleted_orders:
        await callback.answer("Больше нет удаленных заявок", show_alert=True)
        return

    # Форматируем список
    text = f"🗑 <b>Удаленные заявки</b> (страница {page + 1})\n\n"

    for order in deleted_orders:
        text += f"📋 <b>#{order.id}</b> - {order.equipment_type}\n"
        text += f"   👤 {order.client_name}\n"
        text += f"   📊 {order.status}\n"
        if hasattr(order, "deleted_at") and order.deleted_at:
            text += f"   🗑 {format_datetime(order.deleted_at)}\n"
        text += f"   /restore_{order.id}\n"
        text += "\n"

    message_obj = callback.message
    if isinstance(message_obj, Message):
        await message_obj.edit_text(
            text, reply_markup=get_deleted_orders_keyboard(page=page), parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("restore_order:"))
@handle_errors
async def callback_restore_order(callback: CallbackQuery, db: Database):
    """Восстановить удаленную заявку"""
    data = callback.data or ""
    order_id = int(data.split(":")[1])
    user = callback.from_user
    if user is None:
        await callback.answer("❌ Не удалось определить пользователя", show_alert=True)
        return
    user_id = user.id

    order_repo = OrderRepositoryExtended(db.get_connection())

    # Проверяем, что заявка удалена
    order = await order_repo.get_by_id(order_id, include_deleted=True)

    if not order:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    if not (hasattr(order, "deleted_at") and order.deleted_at):
        await callback.answer("❌ Заявка не удалена", show_alert=True)
        return

    # Восстанавливаем
    success = await order_repo.restore(order_id, restored_by=user_id)

    if success:
        await callback.answer("✅ Заявка восстановлена!", show_alert=True)

        # Обновляем сообщение
        text = f"✅ <b>Заявка #{order_id} восстановлена</b>\n\n"
        text += f"🔧 {order.equipment_type}\n"
        text += f"👤 {order.client_name}\n"
        text += f"📊 Статус: {order.status}\n\n"
        text += f"Восстановил: {user.first_name}"

        message_obj = callback.message
        if isinstance(message_obj, Message):
            await message_obj.edit_text(text, parse_mode="HTML")

    else:
        await callback.answer("❌ Ошибка восстановления", show_alert=True)


@router.callback_query(F.data.startswith("view_deleted:"))
@handle_errors
async def callback_view_deleted(callback: CallbackQuery, db: Database):
    """Просмотр удаленной заявки"""
    data = callback.data or ""
    order_id = int(data.split(":")[1])

    order_repo = OrderRepositoryExtended(db.get_connection())

    # Получаем заявку
    order = await order_repo.get_by_id(order_id, include_deleted=True)

    if not order:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Форматируем
    text = OrderPresenter.format_order_details(order, include_client_phone=True)
    # Добавляем маркер удаления в заголовок
    text = text.replace("📋 <b>Заявка #", "📋 <b>Заявка (удалена) #")

    if hasattr(order, "deleted_at") and order.deleted_at:
        text += f"\n🗑 <b>Удалена:</b> {format_datetime(order.deleted_at)}"

    message_obj = callback.message
    if isinstance(message_obj, Message):
        await message_obj.edit_text(
            text, reply_markup=get_restore_keyboard(order_id), parse_mode="HTML"
        )


# Команды для быстрого восстановления
@router.message(Command(commands=["restore"]), RoleFilter(["ADMIN"]))
@handle_errors
async def cmd_restore_order(message: Message, db: Database):
    """Команда для быстрого восстановления заявки"""
    # Проверяем формат команды
    text = message.text or ""
    parts = text.split("_")

    if len(parts) < 2:
        await message.answer(
            "📋 <b>Восстановление заявки</b>\n\n"
            "Использование: /restore_<номер>\n"
            "Пример: /restore_123",
            parse_mode="HTML",
        )
        return

    try:
        order_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный номер заявки")
        return

    order_repo = OrderRepositoryExtended(db.get_connection())

    # Восстанавливаем
    user = message.from_user
    if user is None:
        await message.answer("❌ Не удалось определить пользователя")
        return
    success = await order_repo.restore(order_id, restored_by=user.id)

    if success:
        await message.answer(f"✅ Заявка #{order_id} успешно восстановлена!", parse_mode="HTML")
    else:
        await message.answer(f"❌ Ошибка восстановления заявки #{order_id}")
