"""
Обработчики для режима разработчика
"""

import logging
import os
import random

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.config import Config, EquipmentType, UserRole
from app.database import Database
from app.decorators import handle_errors, require_role
from app.keyboards.inline import get_dev_menu_keyboard


logger = logging.getLogger(__name__)

router = Router(name="developer")


@router.message(Command("dev"))
@require_role([UserRole.ADMIN])
@handle_errors
async def cmd_dev(message: Message, user_role: str):
    """
    Команда для доступа к меню разработчика

    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    if not Config.DEV_MODE:
        await message.answer(
            "⚠️ <b>Developer режим отключен</b>\n\n"
            "Для включения установите <code>DEV_MODE=true</code> в .env файле и перезапустите бота.",
            parse_mode="HTML",
        )
        return

    db_name = os.path.basename(Config.DATABASE_PATH)

    await message.answer(
        "🔧 <b>Developer Mode</b>\n\n"
        f"📊 База данных: <code>{db_name}</code>\n\n"
        "⚠️ Все тестовые данные создаются в отдельной dev БД.\n"
        "Production БД не затрагивается!\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_dev_menu_keyboard(),
    )


@router.callback_query(lambda c: c.data == "dev_create_test_order")
@handle_errors
async def callback_create_test_order(callback: CallbackQuery):
    """
    Создание тестовой заявки

    Args:
        callback: Callback query
    """
    await callback.answer("Создаю тестовую заявку...")

    # Генерация случайных данных для заявки
    equipment_types = EquipmentType.all_types()
    equipment = random.choice(equipment_types)  # noqa: S311

    test_clients = [
        "Иван Петров",
        "Мария Сидорова",
        "Алексей Смирнов",
        "Екатерина Иванова",
        "Дмитрий Козлов",
    ]

    test_addresses = [
        "ул. Ленина, д. 10, кв. 5",
        "пр. Мира, д. 25, кв. 12",
        "ул. Гагарина, д. 7, кв. 3",
        "ул. Советская, д. 45, кв. 18",
        "пр. Победы, д. 30, кв. 7",
    ]

    test_problems = [
        "Не включается",
        "Странные звуки при работе",
        "Не греет воду",
        "Протечка",
        "Ошибка на дисплее E03",
        "Не отжимает белье",
        "Не запускается программа",
        "Не сливает воду",
    ]

    client_name = random.choice(test_clients)  # noqa: S311
    client_address = random.choice(test_addresses)  # noqa: S311
    client_phone = f"+7{random.randint(9000000000, 9999999999)}"  # noqa: S311
    description = f"{equipment}: {random.choice(test_problems)}"  # noqa: S311

    # Создание заявки в БД
    db = Database()
    await db.connect()

    try:
        order = await db.create_order(
            equipment_type=equipment,
            description=description,
            client_name=client_name,
            client_address=client_address,
            client_phone=client_phone,
            dispatcher_id=callback.from_user.id,
            notes="[TEST] Тестовая заявка из dev режима",
        )

        await callback.message.edit_text(
            "✅ <b>Тестовая заявка создана!</b>\n\n"
            f"📋 Заявка #{order.id}\n"
            f"🔧 {order.equipment_type}\n"
            f"📝 {order.description}\n\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n"
            f"📞 Телефон: {order.client_phone}\n\n"
            f"🗓 Создана: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"💾 База данных: <code>{os.path.basename(Config.DATABASE_PATH)}</code>",
            parse_mode="HTML",
            reply_markup=get_dev_menu_keyboard(),
        )

        logger.info(f"[DEV] Создана тестовая заявка #{order.id}")

    except Exception as e:
        logger.error(f"[DEV] Ошибка создания тестовой заявки: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка при создании заявки</b>\n\n{e!s}",
            parse_mode="HTML",
            reply_markup=get_dev_menu_keyboard(),
        )
    finally:
        await db.disconnect()


@router.callback_query(lambda c: c.data == "dev_archive_orders")
@handle_errors
async def callback_dev_archive_orders(callback: CallbackQuery):
    """
    Архивирование старых заявок

    Args:
        callback: Callback query
    """
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    # Показываем меню выбора периода
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="📅 Старше 30 дней", callback_data="dev_archive_30"))
    builder.row(InlineKeyboardButton(text="📅 Старше 60 дней", callback_data="dev_archive_60"))
    builder.row(InlineKeyboardButton(text="📅 Старше 90 дней", callback_data="dev_archive_90"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="dev_back"))

    await callback.message.edit_text(
        "🗄️ <b>Архивирование старых заявок</b>\n\n"
        "Выберите период для архивирования завершенных и отклоненных заявок:\n\n"
        "⚠️ <b>Внимание:</b> Заявки будут удалены из базы данных,\n"
        "но сохранены в JSON файл в папке data/archive/",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("dev_archive_"))
@handle_errors
async def callback_dev_archive_execute(callback: CallbackQuery):
    """
    Выполнение архивирования

    Args:
        callback: Callback query
    """
    days = int(callback.data.split("_")[-1])

    await callback.message.edit_text(
        f"⏳ Архивирую заявки старше {days} дней...\n\n" "Это может занять некоторое время.",
        parse_mode="HTML",
    )

    from app.services.archive import ArchiveService

    db = Database()
    await db.connect()

    try:
        service = ArchiveService(db)
        result = await service.archive_old_orders(days_old=days)

        if result.get("error"):
            await callback.message.edit_text(
                f"❌ <b>Ошибка архивирования</b>\n\n" f"Ошибка: {result['error']}",
                parse_mode="HTML",
                reply_markup=get_dev_menu_keyboard(),
            )
        elif result["archived"] == 0:
            await callback.message.edit_text(
                f"ℹ️ <b>Архивирование завершено</b>\n\n" f"Заявок старше {days} дней не найдено.",
                parse_mode="HTML",
                reply_markup=get_dev_menu_keyboard(),
            )
        else:
            await callback.message.edit_text(
                f"✅ <b>Архивирование завершено!</b>\n\n"
                f"📦 Заархивировано заявок: <b>{result['archived']}</b>\n"
                f"📅 Старше: {days} дней\n"
                f"📁 Файл: <code>{result.get('archive_file', 'N/A')}</code>\n\n"
                f"Заявки удалены из базы данных и сохранены в архив.",
                parse_mode="HTML",
                reply_markup=get_dev_menu_keyboard(),
            )

        logger.info(
            f"Archive executed by {callback.from_user.id}: {result['archived']} orders archived"
        )

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(lambda c: c.data == "dev_back")
@handle_errors
async def callback_dev_back(callback: CallbackQuery):
    """
    Возврат в меню разработчика

    Args:
        callback: Callback query
    """
    db_name = os.path.basename(Config.DATABASE_PATH)

    await callback.message.edit_text(
        "🔧 <b>Developer Mode</b>\n\n"
        f"📊 База данных: <code>{db_name}</code>\n\n"
        "⚠️ Все тестовые данные создаются в отдельной dev БД.\n"
        "Production БД не затрагивается!\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_dev_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "dev_close")
@handle_errors
async def callback_dev_close(callback: CallbackQuery):
    """
    Закрытие меню разработчика

    Args:
        callback: Callback query
    """
    await callback.message.delete()
    await callback.answer("Меню закрыто")
