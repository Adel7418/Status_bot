"""
Обработчики для поиска заказов
"""

import logging
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import UserRole
from app.database import Database
from app.decorators import handle_errors, require_role
from app.keyboards.inline import get_search_type_keyboard
from app.keyboards.reply import get_cancel_keyboard
from app.services.order_search import OrderSearchService
from app.states import SearchOrderStates
from app.utils import escape_html, format_phone, validate_phone


logger = logging.getLogger(__name__)

router = Router(name="order_search")


@router.message(F.text == "🔍 Поиск заказов")
@handle_errors
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
async def btn_search_orders(message: Message, state: FSMContext, user_role: str):
    """
    Начало процесса поиска заказов

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    await state.clear()
    await state.set_state(SearchOrderStates.select_search_type)

    await message.answer(
        "🔍 <b>Поиск заказов</b>\n\n" "Выберите тип поиска:",
        parse_mode="HTML",
        reply_markup=get_search_type_keyboard(),
    )


@router.callback_query(F.data == "search_by_phone")
@handle_errors
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
async def callback_search_by_phone(callback: CallbackQuery, state: FSMContext, user_role: str):
    """
    Выбор поиска по телефону

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    await callback.answer()
    await state.set_state(SearchOrderStates.enter_phone)

    await callback.message.edit_text(
        "📞 <b>Поиск по номеру телефона</b>\n\n"
        "Введите номер телефона клиента:\n"
        "<i>(в формате +7XXXXXXXXXX, 8XXXXXXXXXX или XXXXXXXXXX)</i>",
        parse_mode="HTML",
    )

    await callback.message.answer(
        "Введите номер телефона:",
        reply_markup=get_cancel_keyboard(),
    )


@router.callback_query(F.data == "search_by_address")
@handle_errors
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
async def callback_search_by_address(callback: CallbackQuery, state: FSMContext, user_role: str):
    """
    Выбор поиска по адресу

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    await callback.answer()
    await state.set_state(SearchOrderStates.enter_address)

    await callback.message.edit_text(
        "🏠 <b>Поиск по адресу</b>\n\n"
        "Введите адрес клиента:\n"
        "<i>(можно ввести часть адреса)</i>",
        parse_mode="HTML",
    )

    await callback.message.answer(
        "Введите адрес:",
        reply_markup=get_cancel_keyboard(),
    )


@router.callback_query(F.data == "search_by_phone_and_address")
@handle_errors
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
async def callback_search_by_phone_and_address(
    callback: CallbackQuery, state: FSMContext, user_role: str
):
    """
    Выбор поиска по телефону и адресу

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    await callback.answer()
    await state.set_state(SearchOrderStates.enter_phone_and_address)

    await callback.message.edit_text(
        "📞🏠 <b>Поиск по телефону и адресу</b>\n\n" "Введите номер телефона и адрес клиента:",
        parse_mode="HTML",
    )

    await callback.message.answer(
        "Введите номер телефона:",
        reply_markup=get_cancel_keyboard(),
    )


@router.callback_query(F.data == "search_cancel")
@handle_errors
async def callback_search_cancel(callback: CallbackQuery, state: FSMContext):
    """
    Отмена поиска

    Args:
        callback: Callback query
        state: FSM контекст
    """
    await callback.answer()
    await state.clear()

    await callback.message.edit_text(
        "❌ Поиск отменен.",
    )


@router.message(SearchOrderStates.enter_phone, F.text != "❌ Отмена")
@handle_errors
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
async def process_search_phone(message: Message, state: FSMContext, user_role: str):
    """
    Обработка ввода номера телефона для поиска

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    phone = message.text.strip()

    # Валидация телефона
    if not validate_phone(phone):
        await message.answer(
            "❌ Неверный формат номера телефона.\n\n"
            "Пожалуйста, введите номер в одном из форматов:\n"
            "• +7XXXXXXXXXX\n"
            "• 8XXXXXXXXXX\n"
            "• XXXXXXXXXX",
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Нормализуем номер телефона
    normalized_phone = re.sub(r"\D", "", phone)
    if normalized_phone.startswith("8") and len(normalized_phone) == 11:
        normalized_phone = "7" + normalized_phone[1:]
    elif len(normalized_phone) == 10:
        normalized_phone = "7" + normalized_phone

    # Выполняем поиск
    db = Database()
    await db.connect()

    try:
        search_service = OrderSearchService(db)
        orders = await search_service.search_orders_by_phone(normalized_phone)

        if orders:
            result_text = search_service.format_search_results(orders, "поиска по телефону")
            await message.answer(
                result_text,
                parse_mode="HTML",
            )
        else:
            await message.answer(
                f"🔍 <b>Результаты поиска по телефону</b>\n\n"
                f"📞 <b>Поиск по номеру:</b> {format_phone(normalized_phone)}\n\n"
                f"❌ Заказы не найдены.",
                parse_mode="HTML",
            )

    finally:
        # ORMDatabase не имеет метода close, только engine
        if hasattr(db, 'engine') and db.engine:
            await db.engine.dispose()

    await state.clear()


@router.message(SearchOrderStates.enter_address, F.text != "❌ Отмена")
@handle_errors
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
async def process_search_address(message: Message, state: FSMContext, user_role: str):
    """
    Обработка ввода адреса для поиска

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    address = message.text.strip()

    if len(address) < 3:
        await message.answer(
            "❌ Адрес слишком короткий. Введите минимум 3 символа.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Выполняем поиск
    db = Database()
    await db.connect()

    try:
        search_service = OrderSearchService(db)
        orders = await search_service.search_orders_by_address(address)

        if orders:
            result_text = search_service.format_search_results(orders, "поиска по адресу")
            await message.answer(
                result_text,
                parse_mode="HTML",
            )
        else:
            await message.answer(
                f"🔍 <b>Результаты поиска по адресу</b>\n\n"
                f"🏠 <b>Поиск по адресу:</b> {escape_html(address)}\n\n"
                f"❌ Заказы не найдены.",
                parse_mode="HTML",
            )

    finally:
        # ORMDatabase не имеет метода close, только engine
        if hasattr(db, 'engine') and db.engine:
            await db.engine.dispose()

    await state.clear()


@router.message(SearchOrderStates.enter_phone_and_address, F.text != "❌ Отмена")
@handle_errors
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
async def process_search_phone_and_address(message: Message, state: FSMContext, user_role: str):
    """
    Обработка ввода телефона и адреса для поиска

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    data = await state.get_data()

    if "phone" not in data:
        # Первый ввод - телефон
        phone = message.text.strip()

        # Валидация телефона
        if not validate_phone(phone):
            await message.answer(
                "❌ Неверный формат номера телефона.\n\n"
                "Пожалуйста, введите номер в одном из форматов:\n"
                "• +7XXXXXXXXXX\n"
                "• 8XXXXXXXXXX\n"
                "• XXXXXXXXXX",
                reply_markup=get_cancel_keyboard(),
            )
            return

        # Нормализуем номер телефона
        normalized_phone = re.sub(r"\D", "", phone)
        if normalized_phone.startswith("8") and len(normalized_phone) == 11:
            normalized_phone = "7" + normalized_phone[1:]
        elif len(normalized_phone) == 10:
            normalized_phone = "7" + normalized_phone

        await state.update_data(phone=normalized_phone)
        await message.answer(
            f"📞 <b>Телефон:</b> {format_phone(normalized_phone)}\n\n" "Теперь введите адрес:",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Второй ввод - адрес
    address = message.text.strip()

    if len(address) < 3:
        await message.answer(
            "❌ Адрес слишком короткий. Введите минимум 3 символа.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    phone = data["phone"]

    # Выполняем поиск
    db = Database()
    await db.connect()

    try:
        search_service = OrderSearchService(db)
        orders = await search_service.search_orders_by_phone_and_address(phone, address)

        if orders:
            result_text = search_service.format_search_results(
                orders, "поиска по телефону и адресу"
            )
            await message.answer(
                result_text,
                parse_mode="HTML",
            )
        else:
            await message.answer(
                f"🔍 <b>Результаты поиска по телефону и адресу</b>\n\n"
                f"📞 <b>Телефон:</b> {format_phone(phone)}\n"
                f"🏠 <b>Адрес:</b> {escape_html(address)}\n\n"
                f"❌ Заказы не найдены.",
                parse_mode="HTML",
            )

    finally:
        # ORMDatabase не имеет метода close, только engine
        if hasattr(db, 'engine') and db.engine:
            await db.engine.dispose()

    await state.clear()


@router.message(SearchOrderStates.enter_phone, F.text == "❌ Отмена")
@router.message(SearchOrderStates.enter_address, F.text == "❌ Отмена")
@router.message(SearchOrderStates.enter_phone_and_address, F.text == "❌ Отмена")
@handle_errors
async def cancel_search(message: Message, state: FSMContext):
    """
    Отмена поиска

    Args:
        message: Сообщение
        state: FSM контекст
    """
    await state.clear()
    await message.answer(
        "❌ Поиск отменен.",
        reply_markup=None,  # Убираем клавиатуру
    )
