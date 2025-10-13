"""
Обработчики для диспетчеров (и администраторов)
"""

import logging
import re
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from pydantic import ValidationError

from app.config import MAX_DESCRIPTION_LENGTH, MAX_NOTES_LENGTH, OrderStatus, UserRole
from app.database import Database
from app.decorators import handle_errors
from app.keyboards.inline import (
    get_equipment_types_keyboard,
    get_masters_list_keyboard,
    get_order_actions_keyboard,
    get_order_list_keyboard,
    get_orders_filter_keyboard,
)
from app.keyboards.reply import get_cancel_keyboard, get_confirm_keyboard, get_skip_cancel_keyboard
from app.schemas import OrderCreateSchema
from app.states import CreateOrderStates
from app.utils import (
    escape_html,
    format_datetime,
    log_action,
    safe_send_message,
)


logger = logging.getLogger(__name__)

router = Router(name="dispatcher")
# Фильтры на уровне роутера НЕ работают, т.к. выполняются ДО middleware
# Проверка роли теперь в каждом обработчике через декоратор


# ==================== СОЗДАНИЕ ЗАЯВКИ ====================


@router.message(F.text == "➕ Создать заявку")
@handle_errors
async def btn_create_order(message: Message, state: FSMContext, user_role: str):
    """
    Начало создания новой заявки

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    # Проверка роли
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    await state.clear()
    await state.set_state(CreateOrderStates.equipment_type)

    await message.answer(
        "➕ <b>Создание новой заявки</b>\n\n" "Шаг 1/7: Выберите тип техники:",
        parse_mode="HTML",
        reply_markup=get_equipment_types_keyboard(),
    )


@router.callback_query(F.data.startswith("equipment:"), CreateOrderStates.equipment_type)
@handle_errors
async def process_equipment_type(callback: CallbackQuery, state: FSMContext, user_role: str):
    """
    Обработка выбора типа техники

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    equipment_type = callback.data.split(":", 1)[1]

    await state.update_data(equipment_type=equipment_type)
    await state.set_state(CreateOrderStates.description)

    await callback.message.edit_text(
        f"✅ Выбрано: {equipment_type}\n\n" f"Шаг 2/7: Опишите проблему:", parse_mode="HTML"
    )

    await callback.message.answer(
        "📝 Введите описание проблемы:\n" f"<i>(максимум {MAX_DESCRIPTION_LENGTH} символов)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )

    await callback.answer()


@router.message(CreateOrderStates.description, F.text != "❌ Отмена")
@handle_errors
async def process_description(message: Message, state: FSMContext, user_role: str):
    """
    Обработка описания проблемы с Pydantic валидацией

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    description = message.text.strip()

    # Валидация через Pydantic
    try:
        # Создаем временную схему для валидации только description
        from pydantic import BaseModel, Field, field_validator

        class DescriptionValidator(BaseModel):
            description: str = Field(..., min_length=10, max_length=MAX_DESCRIPTION_LENGTH)

            @field_validator("description")
            @classmethod
            def validate_description(cls, v: str) -> str:
                import re
                v = v.strip()
                if len(v) < 10:
                    raise ValueError("Описание слишком короткое. Минимум 10 символов")

                # Базовая защита от SQL injection
                suspicious_patterns = [
                    r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER)\s+",
                    r"--",
                    r"/\*.*\*/",
                    r"UNION\s+SELECT",
                ]
                for pattern in suspicious_patterns:
                    if re.search(pattern, v, re.IGNORECASE):
                        raise ValueError("Описание содержит недопустимые символы")

                return v

        validated = DescriptionValidator(description=description)
        description = validated.description

    except ValidationError as e:
        error_msg = e.errors()[0]["msg"]
        await message.answer(
            f"❌ {error_msg}\n\nПопробуйте еще раз:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(description=description)
    await state.set_state(CreateOrderStates.client_name)

    await message.answer(
        "👤 Шаг 3/6: Введите имя клиента:\n"
        "<i>(минимум 5 символов)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(CreateOrderStates.client_name, F.text != "❌ Отмена")
@handle_errors
async def process_client_name(message: Message, state: FSMContext, user_role: str):
    """
    Обработка ФИО клиента с Pydantic валидацией

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    client_name = message.text.strip()

    # Валидация через Pydantic
    try:
        import re

        from pydantic import BaseModel, Field, field_validator

        class ClientNameValidator(BaseModel):
            client_name: str = Field(..., min_length=5, max_length=200)

            @field_validator("client_name")
            @classmethod
            def validate_client_name(cls, v: str) -> str:
                v = v.strip()

                # Минимум 5 символов
                if len(v) < 5:
                    raise ValueError("Имя клиента слишком короткое (минимум 5 символов)")

                # Проверяем что содержит хотя бы одну букву
                if not re.search(r"[А-Яа-яЁёA-Za-z]", v):
                    raise ValueError("Имя должно содержать буквы")

                return v

        validated = ClientNameValidator(client_name=client_name)
        client_name = validated.client_name

    except ValidationError as e:
        error_msg = e.errors()[0]["msg"]
        await message.answer(
            f"❌ {error_msg}\n\nПопробуйте еще раз:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(client_name=client_name)
    await state.set_state(CreateOrderStates.client_address)

    await message.answer("📍 Шаг 4/7: Введите адрес клиента:", reply_markup=get_cancel_keyboard())


@router.message(CreateOrderStates.client_address, F.text != "❌ Отмена")
@handle_errors
async def process_client_address(message: Message, state: FSMContext, user_role: str):
    """
    Обработка адреса клиента с Pydantic валидацией

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    client_address = message.text.strip()

    # Валидация через Pydantic
    try:
        import re

        from pydantic import BaseModel, Field, field_validator

        class ClientAddressValidator(BaseModel):
            client_address: str = Field(..., min_length=10, max_length=500)

            @field_validator("client_address")
            @classmethod
            def validate_client_address(cls, v: str) -> str:
                v = v.strip()

                if len(v) < 10:
                    raise ValueError("Адрес слишком короткий. Минимум 10 символов")

                # Проверка что адрес содержит хотя бы одну цифру (номер дома)
                if not re.search(r"\d", v):
                    raise ValueError("Адрес должен содержать номер дома")

                return v

        validated = ClientAddressValidator(client_address=client_address)
        client_address = validated.client_address

    except ValidationError as e:
        error_msg = e.errors()[0]["msg"]
        await message.answer(
            f"❌ {error_msg}\n\nПопробуйте еще раз:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(client_address=client_address)
    await state.set_state(CreateOrderStates.client_phone)

    await message.answer(
        "📞 Шаг 5/7: Введите телефон клиента:\n" "<i>(в формате +7XXXXXXXXXX)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(CreateOrderStates.client_phone, F.text != "❌ Отмена")
@handle_errors
async def process_client_phone(message: Message, state: FSMContext, user_role: str):
    """
    Обработка телефона клиента с Pydantic валидацией

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    phone = message.text.strip()

    # Валидация через Pydantic (использует те же правила что и в схеме)
    try:
        import re

        from pydantic import BaseModel, Field, field_validator

        class ClientPhoneValidator(BaseModel):
            client_phone: str = Field(..., min_length=10, max_length=20)

            @field_validator("client_phone")
            @classmethod
            def validate_client_phone(cls, v: str) -> str:
                cleaned = re.sub(r"[^\d+]", "", v.strip())
                patterns = [r"^\+7\d{10}$", r"^8\d{10}$", r"^7\d{10}$"]

                if not any(re.match(pattern, cleaned) for pattern in patterns):
                    raise ValueError("Неверный формат телефона. Ожидается: +7XXXXXXXXXX")

                # Форматируем
                if cleaned.startswith("8") and len(cleaned) == 11:
                    cleaned = "+7" + cleaned[1:]
                elif cleaned.startswith("7") and len(cleaned) == 11:
                    cleaned = "+" + cleaned

                return cleaned

        validated = ClientPhoneValidator(client_phone=phone)
        phone = validated.client_phone

    except ValidationError as e:
        error_msg = e.errors()[0]["msg"]
        await message.answer(
            f"❌ {error_msg}\n\nПопробуйте еще раз:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(client_phone=phone)
    await state.set_state(CreateOrderStates.notes)

    await message.answer(
        "📝 Шаг 6/7: Введите дополнительные заметки (необязательно):\n"
        f"<i>(максимум {MAX_NOTES_LENGTH} символов)</i>\n\n"
        "Или нажмите 'Пропустить'.",
        parse_mode="HTML",
        reply_markup=get_skip_cancel_keyboard(),
    )


@router.message(CreateOrderStates.notes, F.text == "⏭️ Пропустить")
@handle_errors
async def skip_notes(message: Message, state: FSMContext, user_role: str):
    """
    Пропуск заметок и переход к времени прибытия

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    await state.update_data(notes=None)
    
    # Переходим к вводу времени прибытия (не пропускаем этот шаг!)
    await state.set_state(CreateOrderStates.scheduled_time)
    await message.answer(
        "⏰ <b>Время прибытия к клиенту</b>\n\n"
        "Укажите время или инструкцию для мастера:\n\n"
        "<b>Примеры времени:</b>\n"
        "• 14:30\n"
        "• завтра 10:00\n"
        "• 15.10.2025 16:00\n\n"
        "<b>Примеры инструкций:</b>\n"
        "• Набрать клиенту\n"
        "• После 14:00\n"
        "• Уточнить у клиента\n"
        "• В течение дня\n\n"
        "Или нажмите '⏭️ Пропустить' если не требуется.",
        parse_mode="HTML",
        reply_markup=get_skip_cancel_keyboard(),
    )


@router.message(CreateOrderStates.notes, F.text != "❌ Отмена")
@handle_errors
async def process_notes(message: Message, state: FSMContext, user_role: str):
    """
    Обработка заметок

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    notes = message.text.strip()

    if len(notes) > MAX_NOTES_LENGTH:
        await message.answer(
            f"❌ Заметки слишком длинные. Максимум {MAX_NOTES_LENGTH} символов:",
            reply_markup=get_skip_cancel_keyboard(),
        )
        return

    await state.update_data(notes=notes)

    # Переходим к вводу времени прибытия
    await state.set_state(CreateOrderStates.scheduled_time)
    await message.answer(
        "⏰ <b>Время прибытия к клиенту</b>\n\n"
        "Укажите время или инструкцию для мастера:\n\n"
        "<b>Примеры времени:</b>\n"
        "• 14:30\n"
        "• завтра 10:00\n"
        "• 15.10.2025 16:00\n\n"
        "<b>Примеры инструкций:</b>\n"
        "• Набрать клиенту\n"
        "• После 14:00\n"
        "• Уточнить у клиента\n"
        "• В течение дня\n\n"
        "Или нажмите '⏭️ Пропустить' если не требуется.",
        parse_mode="HTML",
        reply_markup=get_skip_cancel_keyboard(),
    )


@router.message(CreateOrderStates.scheduled_time, F.text != "❌ Отмена")
@handle_errors
async def process_scheduled_time(message: Message, state: FSMContext, user_role: str):
    """
    Обработка времени прибытия к клиенту

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    scheduled_time = message.text.strip()

    # Валидация времени прибытия
    if scheduled_time:
        # Проверка длины (минимум 3 символа, максимум 100)
        if len(scheduled_time) < 3:
            await message.answer(
                "❌ Время/инструкция слишком короткие (минимум 3 символа)\n\n"
                "Попробуйте еще раз:",
                reply_markup=get_skip_cancel_keyboard(),
            )
            return
        
        if len(scheduled_time) > 100:
            await message.answer(
                "❌ Время/инструкция слишком длинные (максимум 100 символов)\n\n"
                "Попробуйте еще раз:",
                reply_markup=get_skip_cancel_keyboard(),
            )
            return
        
        # Проверка на опасные символы и SQL injection
        dangerous_patterns = [
            r"\b(drop|delete|truncate|insert|update|alter)\b.*\b(table|from|into|database|set|where)\b",
            r";\s*(drop|delete|truncate|insert|update|alter)\s+",
            r"--",
            r"/\*.*\*/",
            r"\bxp_",
            r"\bsp_",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, scheduled_time, re.IGNORECASE):
                await message.answer(
                    "❌ Недопустимые символы в тексте\n\n"
                    "Попробуйте еще раз:",
                    reply_markup=get_skip_cancel_keyboard(),
                )
                return

    await state.update_data(scheduled_time=scheduled_time)
    await show_order_confirmation(message, state)


@router.message(CreateOrderStates.scheduled_time, F.text == "⏭️ Пропустить")
@handle_errors
async def skip_scheduled_time(message: Message, state: FSMContext, user_role: str):
    """
    Пропуск времени прибытия

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    await state.update_data(scheduled_time=None)
    await show_order_confirmation(message, state)


# ==================== ОТМЕНА СОЗДАНИЯ ЗАЯВКИ ====================


@router.message(CreateOrderStates.confirm, F.text == "❌ Отмена")
@handle_errors
async def cancel_create_order(message: Message, state: FSMContext, user_role: str):
    """
    Отмена создания заявки

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    await state.clear()

    from app.keyboards.reply import get_main_menu_keyboard

    await message.answer(
        "❌ Создание заявки отменено.", reply_markup=get_main_menu_keyboard(user_role)
    )

    log_action(message.from_user.id, "CANCEL_CREATE_ORDER", "Order creation cancelled")


async def show_order_confirmation(message: Message, state: FSMContext):
    """
    Показ подтверждения создания заявки

    Args:
        message: Сообщение
        state: FSMContext контекст
    """
    data = await state.get_data()

    text = (
        "📋 <b>Проверьте данные заявки:</b>\n\n"
        f"🔧 <b>Тип техники:</b> {escape_html(data['equipment_type'])}\n"
        f"📝 <b>Описание:</b> {escape_html(data['description'])}\n\n"
        f"👤 <b>Клиент:</b> {escape_html(data['client_name'])}\n"
        f"📍 <b>Адрес:</b> {escape_html(data['client_address'])}\n"
        f"📞 <b>Телефон:</b> {escape_html(data['client_phone'])}\n"
    )

    if data.get("notes"):
        text += f"\n📝 <b>Заметки:</b> {escape_html(data['notes'])}\n"

    if data.get("scheduled_time"):
        text += f"⏰ <b>Время прибытия:</b> {escape_html(data['scheduled_time'])}\n"

    await state.set_state(CreateOrderStates.confirm)

    await message.answer(text, parse_mode="HTML", reply_markup=get_confirm_keyboard())


@router.message(CreateOrderStates.confirm, F.text == "✅ Подтвердить")
@handle_errors
async def confirm_create_order(message: Message, state: FSMContext, user_role: str):
    """
    Подтверждение создания заявки с полной Pydantic валидацией

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    data = await state.get_data()
    db = None
    order = None

    try:
        # КРИТИЧНО: Финальная валидация всех данных через Pydantic перед сохранением в БД
        try:
            order_data = OrderCreateSchema(
                equipment_type=data["equipment_type"],
                description=data["description"],
                client_name=data["client_name"],
                client_address=data["client_address"],
                client_phone=data["client_phone"],
                dispatcher_id=message.from_user.id,
                notes=data.get("notes"),
                scheduled_time=data.get("scheduled_time"),
            )
            logger.info(
                f"Order data validated successfully for dispatcher {message.from_user.id}"
            )
        except ValidationError as e:
            # Если валидация не прошла - отменяем создание
            logger.error(f"Order validation failed: {e}")

            from app.keyboards.reply import get_main_menu_keyboard

            error_details = "\n".join([f"• {err['msg']}" for err in e.errors()])
            await message.answer(
                f"❌ <b>Ошибка валидации данных заявки:</b>\n\n{error_details}\n\n"
                "Пожалуйста, начните создание заявки заново.",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(user_role)
            )
            return

        db = Database()
        await db.connect()

        # Создаем заявку с валидированными данными
        order = await db.create_order(
            equipment_type=order_data.equipment_type,
            description=order_data.description,
            client_name=order_data.client_name,
            client_address=order_data.client_address,
            client_phone=order_data.client_phone,
            dispatcher_id=order_data.dispatcher_id,
            notes=order_data.notes,
            scheduled_time=order_data.scheduled_time,
        )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=message.from_user.id,
            action="CREATE_ORDER",
            details=f"Created order #{order.id}",
        )

        log_action(message.from_user.id, "CREATE_ORDER", f"Order #{order.id}")

    finally:
        # Гарантированная очистка ресурсов
        if db:
            await db.disconnect()
        # ВСЕГДА очищаем FSM state
        await state.clear()

    # Создаем inline кнопки для назначения мастера
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from app.keyboards.reply import get_main_menu_keyboard

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="👨‍🔧 Назначить мастера", callback_data=f"assign_master:{order.id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="📋 Просмотреть заявку", callback_data=f"view_order:{order.id}")
    )

    # Отправляем сообщение с inline кнопками
    await message.answer(
        f"✅ <b>Заявка #{order.id} успешно создана!</b>\n\n"
        f"Статус: 🆕 Новая\n\n"
        f"Теперь вы можете назначить на нее мастера или просмотреть детали заявки.",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )

    # Обновляем reply клавиатуру главного меню коротким сообщением
    await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard(user_role))


# ==================== ПРОСМОТР ЗАЯВОК ====================


@router.message(F.text == "📋 Все заявки")
@handle_errors
async def btn_all_orders(message: Message, state: FSMContext, user_role: str):
    """
    Просмотр всех заявок

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    # Проверка роли
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    await state.clear()

    await message.answer(
        "📋 <b>Все заявки</b>\n\n" "Выберите фильтр:",
        parse_mode="HTML",
        reply_markup=get_orders_filter_keyboard(),
    )


@router.callback_query(F.data.startswith("filter_orders:"))
@handle_errors
async def callback_filter_orders(callback: CallbackQuery, user_role: str):
    """
    Фильтрация заявок

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    filter_status = callback.data.split(":")[1]

    db = Database()
    await db.connect()

    try:
        if filter_status == "all":
            orders = await db.get_all_orders(limit=50)
            filter_name = "все"
        else:
            orders = await db.get_all_orders(status=filter_status, limit=50)
            filter_name = OrderStatus.get_status_name(filter_status)

        if not orders:
            await callback.message.edit_text(f"📭 Нет заявок со статусом '{filter_name}'.")
            await callback.answer()
            return

        text = f"📋 <b>Заявки ({filter_name}):</b>\n\n"

        for order in orders[:10]:  # Показываем первые 10
            status_emoji = OrderStatus.get_status_emoji(order.status)
            status_name = OrderStatus.get_status_name(order.status)

            text += (
                f"{status_emoji} <b>Заявка #{order.id}</b>\n"
                f"   🔧 {escape_html(order.equipment_type)}\n"
                f"   📊 {status_name}\n"
            )

            if order.master_name:
                text += f"   👨‍🔧 {escape_html(order.master_name)}\n"

            text += "\n"

        if len(orders) > 10:
            text += f"\n<i>Показано 10 из {len(orders)} заявок</i>"

        keyboard = get_order_list_keyboard(orders[:20])

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("view_order:"))
@handle_errors
async def callback_view_order(callback: CallbackQuery, user_role: str):
    """
    Просмотр детальной информации о заявке (для диспетчеров/админов)

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)

        if not order:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        status_emoji = OrderStatus.get_status_emoji(order.status)
        status_name = OrderStatus.get_status_name(order.status)

        text = (
            f"📋 <b>Заявка #{order.id}</b>\n\n"
            f"📊 <b>Статус:</b> {status_emoji} {status_name}\n"
            f"🔧 <b>Тип техники:</b> {escape_html(order.equipment_type)}\n"
            f"📝 <b>Описание:</b> {escape_html(order.description)}\n\n"
            f"👤 <b>Клиент:</b> {escape_html(order.client_name)}\n"
            f"📍 <b>Адрес:</b> {escape_html(order.client_address)}\n"
            f"📞 <b>Телефон:</b> {escape_html(order.client_phone)}\n\n"
        )

        if order.master_name:
            text += f"👨‍🔧 <b>Мастер:</b> {order.master_name}\n"

        if order.dispatcher_name:
            text += f"📋 <b>Диспетчер:</b> {order.dispatcher_name}\n"

        if order.notes:
            text += f"\n📝 <b>Заметки:</b> {order.notes}\n"

        if order.scheduled_time:
            text += f"⏰ <b>Время прибытия:</b> {order.scheduled_time}\n"

        if order.created_at:
            text += f"\n📅 <b>Создана:</b> {format_datetime(order.created_at)}\n"

        if order.updated_at and order.updated_at != order.created_at:
            text += f"🔄 <b>Обновлена:</b> {format_datetime(order.updated_at)}\n"

        keyboard = get_order_actions_keyboard(order, user_role)

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    finally:
        await db.disconnect()

    await callback.answer()


# ==================== НАЗНАЧЕНИЕ МАСТЕРА ====================


@router.callback_query(F.data.startswith("assign_master:"))
async def callback_assign_master(callback: CallbackQuery, state: FSMContext, user_role: str):
    """
    Начало процесса назначения мастера

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    order_id = int(callback.data.split(":")[1])

    await state.update_data(order_id=order_id)

    db = Database()
    await db.connect()

    try:
        # Получаем список активных и одобренных мастеров
        masters = await db.get_all_masters(only_approved=True, only_active=True)

        if not masters:
            await callback.answer("❌ Нет доступных мастеров", show_alert=True)
            return

        keyboard = get_masters_list_keyboard(
            masters, order_id=order_id, action="select_master_for_order"
        )

        await callback.message.edit_text(
            f"👨‍🔧 <b>Выберите мастера для заявки #{order_id}:</b>",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("select_master_for_order:"))
@handle_errors
async def callback_select_master_for_order(callback: CallbackQuery, user_role: str):
    """
    Назначение выбранного мастера на заявку

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    parts = callback.data.split(":")
    order_id = int(parts[1])
    master_id = int(parts[2])

    db = Database()
    await db.connect()

    try:
        # Назначаем мастера
        await db.assign_master_to_order(order_id, master_id)

        # Получаем информацию о мастере
        master = await db.get_master_by_id(master_id)

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ASSIGN_MASTER",
            details=f"Assigned master {master_id} to order #{order_id}",
        )

        # Уведомляем мастера с retry
        order = await db.get_order_by_id(order_id)

        # Определяем, куда отправлять уведомление
        # Если есть work_chat_id - отправляем в рабочую группу
        # Иначе - в личные сообщения мастеру
        target_chat_id = master.work_chat_id if master.work_chat_id else master.telegram_id

        logger.info(
            f"Attempting to send notification to {'group' if master.work_chat_id else 'DM'} {target_chat_id}"
        )

        # Если отправляем в группу, создаем полное сообщение с клавиатурой
        if master.work_chat_id:
            from app.keyboards.inline import get_group_order_keyboard

            notification_text = (
                f"🔔 <b>Новая заявка назначена!</b>\n\n"
                f"📋 <b>Заявка #{order.id}</b>\n"
                f"📊 <b>Статус:</b> {OrderStatus.get_status_name(OrderStatus.ASSIGNED)}\n"
                f"🔧 <b>Тип техники:</b> {order.equipment_type}\n"
                f"📝 <b>Описание:</b> {order.description}\n\n"
                f"👤 <b>Клиент:</b> {order.client_name}\n"
                f"📍 <b>Адрес:</b> {order.client_address}\n"
                f"📞 <b>Телефон:</b> <i>Будет доступен после прибытия на объект</i>\n\n"
            )

            if order.notes:
                notification_text += f"📄 <b>Заметки:</b> {order.notes}\n\n"

            if order.scheduled_time:
                notification_text += f"⏰ <b>Время прибытия:</b> {order.scheduled_time}\n\n"

            # Упоминаем мастера в группе
            if master.username:
                notification_text += f"👨‍🔧 <b>Мастер:</b> @{master.username}\n\n"
            else:
                notification_text += f"👨‍🔧 <b>Мастер:</b> {master.get_display_name()}\n\n"

            notification_text += f"📅 <b>Создана:</b> {format_datetime(order.created_at)}\n"
            notification_text += f"🔄 <b>Назначена:</b> {format_datetime(datetime.now())}"

            keyboard = get_group_order_keyboard(order, OrderStatus.ASSIGNED)

            logger.info(f"Notification text prepared: {len(notification_text)} chars")

            result = await safe_send_message(
                callback.bot,
                target_chat_id,
                notification_text,
                parse_mode="HTML",
                reply_markup=keyboard,
                max_attempts=5,
            )

            if result:
                logger.info(f"SUCCESS: Notification sent to group {target_chat_id}")
            else:
                logger.error(f"CRITICAL: Failed to notify master in group {target_chat_id}")
        else:
            # Отправляем в личные сообщения
            from app.keyboards.inline import get_group_order_keyboard

            notification_text = (
                f"🔔 <b>Новая заявка назначена!</b>\n\n"
                f"📋 <b>Заявка #{order.id}</b>\n"
                f"📊 <b>Статус:</b> {OrderStatus.get_status_name(OrderStatus.ASSIGNED)}\n"
                f"🔧 <b>Тип техники:</b> {order.equipment_type}\n"
                f"📝 <b>Описание:</b> {order.description}\n\n"
                f"👤 <b>Клиент:</b> {order.client_name}\n"
                f"📍 <b>Адрес:</b> {order.client_address}\n"
                f"📞 <b>Телефон:</b> <i>Будет доступен после прибытия на объект</i>\n\n"
            )

            if order.notes:
                notification_text += f"📄 <b>Заметки:</b> {order.notes}\n\n"

            if order.scheduled_time:
                notification_text += f"⏰ <b>Время прибытия:</b> {order.scheduled_time}\n\n"

            notification_text += f"📅 <b>Создана:</b> {format_datetime(order.created_at)}\n"
            notification_text += f"🔄 <b>Назначена:</b> {format_datetime(datetime.now())}"

            keyboard = get_group_order_keyboard(order, OrderStatus.ASSIGNED)

            result = await safe_send_message(
                callback.bot,
                target_chat_id,
                notification_text,
                parse_mode="HTML",
                reply_markup=keyboard,
                max_attempts=5,
            )

            if result:
                logger.info(f"SUCCESS: Notification sent to DM {target_chat_id}")
            else:
                logger.error(f"CRITICAL: Failed to notify master in DM {target_chat_id}")

        await callback.message.edit_text(
            f"✅ <b>Мастер назначен!</b>\n\n"
            f"📋 Заявка #{order_id}\n"
            f"👨‍🔧 Мастер: {master.get_display_name()}\n\n"
            f"Мастер получил уведомление о новой заявке.",
            parse_mode="HTML",
        )

        log_action(callback.from_user.id, "ASSIGN_MASTER", f"Order #{order_id}, Master {master_id}")

    finally:
        await db.disconnect()

    await callback.answer("Мастер назначен!")


# ==================== ПЕРЕНАЗНАЧЕНИЕ МАСТЕРА ====================


@router.callback_query(F.data.startswith("reassign_master:"))
async def callback_reassign_master(callback: CallbackQuery, state: FSMContext, user_role: str):
    """
    Переназначение мастера на заявку

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        # Получаем информацию о заявке
        order = await db.get_order_by_id(order_id)

        if not order:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        # Получаем список активных и одобренных мастеров
        masters = await db.get_all_masters(only_approved=True, only_active=True)

        if not masters:
            await callback.answer("❌ Нет доступных мастеров", show_alert=True)
            return

        # Фильтруем текущего мастера из списка
        available_masters = [m for m in masters if m.id != order.assigned_master_id]

        if not available_masters:
            await callback.answer(
                "❌ Нет других доступных мастеров для переназначения", show_alert=True
            )
            return

        keyboard = get_masters_list_keyboard(
            available_masters, order_id=order_id, action="select_new_master_for_order"
        )

        current_master_name = order.master_name if order.master_name else "Неизвестен"

        await callback.message.edit_text(
            f"🔄 <b>Переназначение мастера</b>\n\n"
            f"📋 Заявка #{order_id}\n"
            f"👨‍🔧 Текущий мастер: {current_master_name}\n\n"
            f"Выберите нового мастера:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("select_new_master_for_order:"))
async def callback_select_new_master_for_order(callback: CallbackQuery, user_role: str):
    """
    Назначение нового мастера на заявку (переназначение)

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    parts = callback.data.split(":")
    order_id = int(parts[1])
    new_master_id = int(parts[2])

    db = Database()
    await db.connect()

    try:
        # Получаем информацию о заявке и старом мастере
        order = await db.get_order_by_id(order_id)
        old_master_id = order.assigned_master_id
        old_master = await db.get_master_by_id(old_master_id) if old_master_id else None

        # Переназначаем мастера
        await db.assign_master_to_order(order_id, new_master_id)

        # Получаем информацию о новом мастере
        new_master = await db.get_master_by_id(new_master_id)

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="REASSIGN_MASTER",
            details=f"Reassigned order #{order_id} from master {old_master_id} to master {new_master_id}",
        )

        # Уведомляем старого мастера о снятии заявки с retry
        if old_master:
            target_chat_id = (
                old_master.work_chat_id if old_master.work_chat_id else old_master.telegram_id
            )
            await safe_send_message(
                callback.bot,
                target_chat_id,
                f"ℹ️ <b>Заявка переназначена</b>\n\n"
                f"📋 Заявка #{order_id} была переназначена на другого мастера.\n"
                f"🔧 {order.equipment_type}\n"
                f"📝 {order.description}",
                parse_mode="HTML",
                max_attempts=3,
            )

        # Уведомляем нового мастера с retry
        # Определяем, куда отправлять уведомление
        target_chat_id = (
            new_master.work_chat_id if new_master.work_chat_id else new_master.telegram_id
        )

        # Если отправляем в группу, создаем полное сообщение с клавиатурой
        if new_master.work_chat_id:
            from app.keyboards.inline import get_group_order_keyboard

            notification_text = (
                f"🔔 <b>Новая заявка назначена!</b>\n\n"
                f"📋 <b>Заявка #{order.id}</b>\n"
                f"📊 <b>Статус:</b> {OrderStatus.get_status_name(OrderStatus.ASSIGNED)}\n"
                f"🔧 <b>Тип техники:</b> {order.equipment_type}\n"
                f"📝 <b>Описание:</b> {order.description}\n\n"
                f"👤 <b>Клиент:</b> {order.client_name}\n"
                f"📍 <b>Адрес:</b> {order.client_address}\n"
                f"📞 <b>Телефон:</b> <i>Будет доступен после прибытия на объект</i>\n\n"
            )

            if order.notes:
                notification_text += f"📄 <b>Заметки:</b> {order.notes}\n\n"

            # Упоминаем мастера в группе
            if new_master.username:
                notification_text += f"👨‍🔧 <b>Мастер:</b> @{new_master.username}\n\n"
            else:
                notification_text += f"👨‍🔧 <b>Мастер:</b> {new_master.get_display_name()}\n\n"

            notification_text += f"📅 <b>Создана:</b> {format_datetime(order.created_at)}\n"
            notification_text += f"🔄 <b>Переназначена:</b> {format_datetime(datetime.now())}"

            keyboard = get_group_order_keyboard(order, OrderStatus.ASSIGNED)

            result = await safe_send_message(
                callback.bot,
                target_chat_id,
                notification_text,
                parse_mode="HTML",
                reply_markup=keyboard,
                max_attempts=5,
            )
            if result:
                logger.info(f"Notification sent to new master group {target_chat_id}")
        else:
            # Отправляем в личные сообщения
            notification_text = (
                f"🔔 <b>Новая заявка!</b>\n\n"
                f"📋 Заявка #{order.id}\n"
                f"🔧 {order.equipment_type}\n"
                f"📝 {order.description}\n\n"
                f"Используйте /start и 'Мои заявки' для просмотра деталей."
            )

            result = await safe_send_message(
                callback.bot, target_chat_id, notification_text, parse_mode="HTML", max_attempts=5
            )
            if result:
                logger.info(f"Notification sent to new master DM {target_chat_id}")

        old_master_name = old_master.get_display_name() if old_master else "Неизвестен"

        await callback.message.edit_text(
            f"✅ <b>Мастер переназначен!</b>\n\n"
            f"📋 Заявка #{order_id}\n"
            f"👨‍🔧 Старый мастер: {old_master_name}\n"
            f"👨‍🔧 Новый мастер: {new_master.get_display_name()}\n\n"
            f"Оба мастера получили уведомления.",
            parse_mode="HTML",
        )

        log_action(
            callback.from_user.id,
            "REASSIGN_MASTER",
            f"Order #{order_id}, Old Master {old_master_id}, New Master {new_master_id}",
        )

    finally:
        await db.disconnect()

    await callback.answer("Мастер переназначен!")


@router.callback_query(F.data.startswith("unassign_master:"))
async def callback_unassign_master(callback: CallbackQuery, user_role: str):
    """
    Снятие мастера с заявки (возврат в статус NEW)

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        # Получаем информацию о заявке и мастере
        order = await db.get_order_by_id(order_id)

        if not order or not order.assigned_master_id:
            await callback.answer("Заявка не найдена или мастер не назначен", show_alert=True)
            return

        master = await db.get_master_by_id(order.assigned_master_id)

        # Снимаем мастера и возвращаем статус в NEW
        await db.connection.execute(
            "UPDATE orders SET status = ?, assigned_master_id = NULL WHERE id = ?",
            (OrderStatus.NEW, order_id),
        )
        await db.connection.commit()

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="UNASSIGN_MASTER",
            details=f"Unassigned master {order.assigned_master_id} from order #{order_id}",
        )

        # Уведомляем мастера с retry
        if master:
            target_chat_id = master.work_chat_id if master.work_chat_id else master.telegram_id
            await safe_send_message(
                callback.bot,
                target_chat_id,
                f"ℹ️ <b>Заявка снята</b>\n\n"
                f"📋 Заявка #{order_id} была снята с вас диспетчером.\n"
                f"🔧 {order.equipment_type}\n"
                f"📝 {order.description}",
                parse_mode="HTML",
                max_attempts=3,
            )

        master_name = master.get_display_name() if master else "Неизвестен"

        await callback.message.edit_text(
            f"✅ <b>Мастер снят с заявки!</b>\n\n"
            f"📋 Заявка #{order_id}\n"
            f"👨‍🔧 Мастер: {master_name}\n\n"
            f"Заявка возвращена в статус 🆕 Новая.\n"
            f"Теперь можно назначить другого мастера.",
            parse_mode="HTML",
        )

        log_action(
            callback.from_user.id,
            "UNASSIGN_MASTER",
            f"Order #{order_id}, Master {order.assigned_master_id}",
        )

    finally:
        await db.disconnect()

    await callback.answer("Мастер снят с заявки")


# ==================== УПРАВЛЕНИЕ СТАТУСАМИ ====================


@router.callback_query(F.data.startswith("close_order:"))
async def callback_close_order(callback: CallbackQuery, user_role: str):
    """
    Закрытие заявки

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        await db.update_order_status(
            order_id, OrderStatus.CLOSED, changed_by=callback.from_user.id
        )

        await db.add_audit_log(
            user_id=callback.from_user.id, action="CLOSE_ORDER", details=f"Closed order #{order_id}"
        )

        await callback.message.edit_text(f"✅ Заявка #{order_id} закрыта.")

        log_action(callback.from_user.id, "CLOSE_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Заявка закрыта")


@router.callback_query(F.data.startswith("refuse_order:"))
async def callback_refuse_order(callback: CallbackQuery, user_role: str):
    """
    Отклонение заявки

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        await db.update_order_status(
            order_id, OrderStatus.REFUSED, changed_by=callback.from_user.id
        )

        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="REFUSE_ORDER",
            details=f"Refused order #{order_id}",
        )

        # Уведомляем мастера если он был назначен, с retry
        if order.assigned_master_id:
            master = await db.get_master_by_id(order.assigned_master_id)
            if master:
                await safe_send_message(
                    callback.bot,
                    master.telegram_id,
                    f"ℹ️ Заявка #{order_id} была отклонена диспетчером.",
                    parse_mode="HTML",
                    max_attempts=3,
                )

        await callback.message.edit_text(f"❌ Заявка #{order_id} отклонена.")

        log_action(callback.from_user.id, "REFUSE_ORDER", f"Order #{order_id}")

    finally:
        await db.disconnect()

    await callback.answer("Заявка отклонена")


@router.callback_query(F.data == "back_to_orders")
async def callback_back_to_orders(callback: CallbackQuery, user_role: str):
    """
    Возврат к списку заявок

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    await callback.message.edit_text(
        "📋 <b>Все заявки</b>\n\n" "Выберите фильтр:",
        parse_mode="HTML",
        reply_markup=get_orders_filter_keyboard(),
    )

    await callback.answer()


# ==================== ОТЧЕТЫ ====================


@router.message(F.text == "📊 Отчеты")
async def btn_reports(message: Message, user_role: str):
    """
    Меню отчетов

    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    # Проверка роли
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    from app.keyboards.inline import get_reports_keyboard

    await message.answer(
        "📊 <b>Отчеты</b>\n\n" "Выберите тип отчета:",
        parse_mode="HTML",
        reply_markup=get_reports_keyboard(),
    )


@router.callback_query(F.data == "report_masters")
async def callback_report_masters(callback: CallbackQuery, user_role: str):
    """
    Отчет по мастерам

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    db = Database()
    await db.connect()

    try:
        from app.services.reports import ReportsService

        reports = ReportsService(db)

        text = await reports.generate_masters_report()

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📥 Скачать Excel", callback_data="download_masters_excel")
        )
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_reports"))

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data == "report_statuses")
async def callback_report_statuses(callback: CallbackQuery, user_role: str):
    """
    Отчет по статусам

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    db = Database()
    await db.connect()

    try:
        from app.services.reports import ReportsService

        reports = ReportsService(db)

        text = await reports.generate_statuses_report()

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📥 Скачать Excel", callback_data="download_statuses_excel")
        )
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_reports"))

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data == "report_equipment")
async def callback_report_equipment(callback: CallbackQuery, user_role: str):
    """
    Отчет по типам техники

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    db = Database()
    await db.connect()

    try:
        from app.services.reports import ReportsService

        reports = ReportsService(db)

        text = await reports.generate_equipment_report()

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📥 Скачать Excel", callback_data="download_equipment_excel")
        )
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_reports"))

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data == "report_period")
async def callback_report_period(callback: CallbackQuery, user_role: str):
    """
    Выбор периода для отчета

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    from app.keyboards.inline import get_period_keyboard

    await callback.message.edit_text(
        "📅 <b>Выберите период:</b>", parse_mode="HTML", reply_markup=get_period_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data.startswith("period_"))
async def callback_period_selected(callback: CallbackQuery, user_role: str):
    """
    Обработка выбора периода

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    period = callback.data.split("_")[1]

    db = Database()
    await db.connect()

    try:
        from app.services.reports import ReportsService

        reports = ReportsService(db)

        start_date, end_date = ReportsService.get_period_dates(period)
        text = await reports.generate_period_report(start_date, end_date)

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="📥 Скачать Excel", callback_data=f"download_period_excel:{period}"
            )
        )
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_reports"))

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data == "download_masters_excel")
async def callback_download_masters_excel(callback: CallbackQuery, user_role: str):
    """
    Скачивание Excel отчета по мастерам

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    await callback.answer("Генерация отчета...")

    db = Database()
    await db.connect()

    try:
        from app.services.reports import ReportsService

        reports = ReportsService(db)

        excel_file = await reports.generate_excel_report(report_type="masters")

        await callback.message.answer_document(document=excel_file, caption="📊 Отчет по мастерам")

    finally:
        await db.disconnect()


@router.callback_query(F.data == "download_statuses_excel")
async def callback_download_statuses_excel(callback: CallbackQuery, user_role: str):
    """
    Скачивание Excel отчета по статусам

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    await callback.answer("Генерация отчета...")

    db = Database()
    await db.connect()

    try:
        from app.services.reports import ReportsService

        reports = ReportsService(db)

        excel_file = await reports.generate_excel_report(report_type="statuses")

        await callback.message.answer_document(document=excel_file, caption="📊 Отчет по статусам")

    finally:
        await db.disconnect()


@router.callback_query(F.data == "download_equipment_excel")
async def callback_download_equipment_excel(callback: CallbackQuery, user_role: str):
    """
    Скачивание Excel отчета по типам техники

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    await callback.answer("Генерация отчета...")

    db = Database()
    await db.connect()

    try:
        from app.services.reports import ReportsService

        reports = ReportsService(db)

        excel_file = await reports.generate_excel_report(report_type="equipment")

        await callback.message.answer_document(
            document=excel_file, caption="📊 Отчет по типам техники"
        )

    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("download_period_excel:"))
async def callback_download_period_excel(callback: CallbackQuery, user_role: str):
    """
    Скачивание Excel отчета за период

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    period = callback.data.split(":")[1]

    await callback.answer("Генерация отчета...")

    db = Database()
    await db.connect()

    try:
        from app.services.reports import ReportsService

        reports = ReportsService(db)

        start_date, end_date = ReportsService.get_period_dates(period)
        excel_file = await reports.generate_excel_report(
            report_type="all", start_date=start_date, end_date=end_date
        )

        await callback.message.answer_document(
            document=excel_file, caption=f"📊 Отчет за период ({period})"
        )

    finally:
        await db.disconnect()


@router.callback_query(F.data == "back_to_reports")
async def callback_back_to_reports(callback: CallbackQuery, user_role: str):
    """
    Возврат к меню отчетов

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    from app.keyboards.inline import get_reports_keyboard

    await callback.message.edit_text(
        "📊 <b>Отчеты</b>\n\n" "Выберите тип отчета:",
        parse_mode="HTML",
        reply_markup=get_reports_keyboard(),
    )

    await callback.answer()


@router.message(F.text == "👥 Мастера")
async def btn_masters_dispatcher(message: Message, user_role: str):
    """
    Обработчик кнопки мастеров для диспетчеров

    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    # Проверка роли
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    db = Database()
    await db.connect()

    try:
        # Получаем список активных и одобренных мастеров
        masters = await db.get_all_masters(only_approved=True, only_active=True)

        if not masters:
            await message.answer(
                "📝 В системе пока нет доступных мастеров.\n\n"
                "Обратитесь к администратору для добавления мастеров."
            )
            return

        text = "👥 <b>Доступные мастера:</b>\n\n"

        for master in masters:
            display_name = master.get_display_name()
            text += (
                f"👤 <b>{display_name}</b>\n"
                f"   📞 {master.phone}\n"
                f"   🔧 {master.specialization}\n\n"
            )

        await message.answer(text, parse_mode="HTML")

    finally:
        await db.disconnect()


@router.message(F.text == "⚙️ Настройки")
async def btn_settings_dispatcher(message: Message, user_role: str):
    """
    Обработчик кнопки настроек для диспетчеров

    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    from app.database import Database

    db = Database()
    await db.connect()

    try:
        user = await db.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден в системе.")
            return

        settings_text = (
            f"⚙️ <b>Настройки профиля</b>\n\n"
            f"👤 <b>Имя:</b> {user.get_full_name()}\n"
            f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
            f"👔 <b>Роль:</b> {user.role}\n"
        )

        if user.username:
            settings_text += f"📱 <b>Username:</b> @{user.username}\n"

        await message.answer(settings_text, parse_mode="HTML")

    finally:
        await db.disconnect()
