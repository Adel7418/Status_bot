"""
Обработчики для диспетчеров (и администраторов)
"""

import logging
import re

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
from app.keyboards.reply import (
    get_cancel_keyboard,
    get_client_data_confirm_keyboard,
    get_confirm_keyboard,
    get_skip_cancel_keyboard,
)
from app.schemas import OrderCreateSchema
from app.states import AdminCloseOrderStates, CreateOrderStates
from app.utils import (
    escape_html,
    format_datetime,
    format_datetime_for_storage,
    format_datetime_user_friendly,
    get_now,
    log_action,
    parse_natural_datetime,
    safe_send_message,
    should_parse_as_date,
    validate_parsed_datetime,
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

    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с описанием проблемы.\n"
            f"Минимум {4} символа, максимум {MAX_DESCRIPTION_LENGTH} символов."
        )
        return

    description = message.text.strip()

    # Валидация через Pydantic
    try:
        # Создаем временную схему для валидации только description
        from pydantic import BaseModel, Field, field_validator

        class DescriptionValidator(BaseModel):
            description: str = Field(..., min_length=4, max_length=MAX_DESCRIPTION_LENGTH)

            @field_validator("description")
            @classmethod
            def validate_description(cls, v: str) -> str:
                import re

                v = v.strip()
                if len(v) < 4:
                    raise ValueError("Описание слишком короткое. Минимум 4 символа")

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
    await state.set_state(CreateOrderStates.client_address)

    await message.answer(
        "📍 Шаг 3/7: Введите адрес клиента:",
        reply_markup=get_cancel_keyboard(),
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

    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с ФИО клиента.\n"
            "Минимум 2 символа, максимум 200 символов."
        )
        return

    client_name = message.text.strip()

    # Валидация через Pydantic
    try:
        import re

        from pydantic import BaseModel, Field, field_validator

        class ClientNameValidator(BaseModel):
            client_name: str = Field(..., min_length=2, max_length=200)

            @field_validator("client_name")
            @classmethod
            def validate_client_name(cls, v: str) -> str:
                v = v.strip()

                # Минимум 2 символа
                if len(v) < 2:
                    raise ValueError("Имя клиента слишком короткое (минимум 2 символа)")

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
    await state.set_state(CreateOrderStates.client_phone)

    await message.answer(
        "📞 Шаг 5/7: Введите телефон клиента:\n" "<i>(в формате +7XXXXXXXXXX)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


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
    logger.info(f"[CLIENT_ADDRESS] Processing client address: '{message.text}'")

    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с адресом клиента.\n"
            "Минимум 5 символов, максимум 200 символов."
        )
        return

    client_address = message.text.strip()

    # Валидация через Pydantic
    try:
        import re

        from pydantic import BaseModel, Field, field_validator

        class ClientAddressValidator(BaseModel):
            client_address: str = Field(..., min_length=4, max_length=500)

            @field_validator("client_address")
            @classmethod
            def validate_client_address(cls, v: str) -> str:
                v = v.strip()

                if len(v) < 4:
                    raise ValueError("Адрес слишком короткий. Минимум 4 символа")

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
    await state.set_state(CreateOrderStates.client_name)

    await message.answer(
        "👤 Шаг 4/7: Введите имя клиента:",
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
    logger.info(f"[CLIENT_PHONE] Начало обработки телефона: {message.text}, роль: {user_role}")

    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        logger.warning(f"[CLIENT_PHONE] Недостаточно прав: {user_role}")
        return

    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с номером телефона.\n"
            "Формат: +7XXXXXXXXXX или 8XXXXXXXXXX"
        )
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
        logger.info(f"[CLIENT_PHONE] Валидация прошла успешно: {phone}")

    except ValidationError as e:
        error_msg = e.errors()[0]["msg"]
        await message.answer(
            f"❌ {error_msg}\n\nПопробуйте еще раз:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Ищем существующие данные клиента по номеру телефона
    try:
        from app.database import Database

        db = Database()
        await db.connect()

        # Ищем заявки с таким номером телефона
        existing_orders = await db.get_orders_by_client_phone(phone)
        await db.disconnect()

        if existing_orders:
            # Найдены существующие заявки - показываем данные клиента
            latest_order = existing_orders[0]  # Берем самую последнюю заявку

            await message.answer(
                f"🔍 <b>Найдены данные клиента:</b>\n\n"
                f"👤 <b>Имя:</b> {escape_html(latest_order.client_name)}\n"
                f"📞 <b>Телефон:</b> {escape_html(latest_order.client_phone)}\n"
                f"🏠 <b>Адрес:</b> {escape_html(latest_order.client_address)}\n\n"
                f"📊 <b>Всего заявок:</b> {len(existing_orders)}\n"
                f"📋 <b>Последняя заявка:</b> #{latest_order.id} ({latest_order.status})\n\n"
                f"<i>Используем эти данные для новой заявки?</i>",
                parse_mode="HTML",
                reply_markup=get_client_data_confirm_keyboard(),
            )

            # Сохраняем найденные данные и переходим к состоянию подтверждения
            await state.update_data(
                client_phone=phone,
                found_client_name=latest_order.client_name,
                found_client_address=latest_order.client_address,
                existing_orders_count=len(existing_orders),
            )
            await state.set_state(CreateOrderStates.confirm_client_data)
            return
        else:
            # Данные не найдены - это новый клиент
            await message.answer(
                "✅ <b>Новый клиент</b>\n\n"
                "Клиент с таким номером телефона не найден в базе данных.\n"
                "Это означает, что это новый клиент.\n"
                "Продолжаем создание заявки.",
                parse_mode="HTML",
            )
            logger.info(f"Новый клиент с телефоном {phone} - продолжаем создание заявки")

    except Exception as e:
        logger.error(f"Ошибка при поиске клиента по телефону {phone}: {e}")
        await message.answer(
            "⚠️ <b>Ошибка поиска</b>\n\n"
            "Не удалось проверить существующие данные клиента.\n"
            "Продолжаем создание новой заявки.",
            parse_mode="HTML",
        )

    logger.info(f"Переходим к следующему шагу для телефона {phone}")
    await state.update_data(client_phone=phone)
    await state.set_state(CreateOrderStates.notes)

    await message.answer(
        "📝 Шаг 6/7: Введите дополнительные заметки (необязательно):\n"
        f"<i>(максимум {MAX_NOTES_LENGTH} символов)</i>\n\n"
        "Или нажмите 'Пропустить'.",
        parse_mode="HTML",
        reply_markup=get_skip_cancel_keyboard(),
    )
    logger.info("Отправлено сообщение с запросом заметок")


@router.message(CreateOrderStates.confirm_client_data, F.text == "✅ Да, использовать")
@handle_errors
async def confirm_client_data(message: Message, state: FSMContext, user_role: str):
    """
    Подтверждение использования найденных данных клиента

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    # Получаем данные из состояния
    data = await state.get_data()

    # Используем найденные данные клиента
    await state.update_data(
        client_name=data["found_client_name"], client_address=data["found_client_address"]
    )

    await state.set_state(CreateOrderStates.notes)

    await message.answer(
        "✅ <b>Данные клиента сохранены</b>\n\n"
        f"👤 <b>Имя:</b> {escape_html(data['found_client_name'])}\n"
        f"🏠 <b>Адрес:</b> {escape_html(data['found_client_address'])}\n"
        f"📞 <b>Телефон:</b> {escape_html(data['client_phone'])}\n\n"
        "📝 Шаг 6/7: Введите дополнительные заметки (необязательно):\n"
        f"<i>(максимум {MAX_NOTES_LENGTH} символов)</i>\n\n"
        "Или нажмите 'Пропустить'.",
        parse_mode="HTML",
        reply_markup=get_skip_cancel_keyboard(),
    )


@router.message(CreateOrderStates.confirm_client_data, F.text == "❌ Нет, ввести заново")
@handle_errors
async def reject_client_data(message: Message, state: FSMContext, user_role: str):
    """
    Отклонение найденных данных клиента - переход к вводу имени

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    await state.set_state(CreateOrderStates.client_name)

    await message.answer(
        "👤 Шаг 3/7: Введите ФИО клиента:\n" "<i>(минимум 4 символа, максимум 200 символов)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
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

    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с заметками.\n"
            f"Максимум {MAX_NOTES_LENGTH} символов."
        )
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
        "Или нажмите '⏭️ Пропустить' если не требуется.",
        parse_mode="HTML",
        reply_markup=get_skip_cancel_keyboard(),
    )


@router.message(CreateOrderStates.scheduled_time, F.text != "❌ Отмена")
@handle_errors
async def process_scheduled_time(message: Message, state: FSMContext, user_role: str):
    """
    Обработка времени прибытия к клиенту с автоопределением даты

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с временем прибытия.\n"
            "Примеры: завтра в 15:00, через 3 дня, 25.10.2025 14:00"
        )
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

        if len(scheduled_time) > 150:  # Увеличили лимит для хранения распарсенной даты
            await message.answer(
                "❌ Время/инструкция слишком длинные (максимум 150 символов)\n\n"
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
                    "❌ Недопустимые символы в тексте\n\n" "Попробуйте еще раз:",
                    reply_markup=get_skip_cancel_keyboard(),
                )
                return

        # 🆕 АВТООПРЕДЕЛЕНИЕ ДАТЫ из естественного языка
        if should_parse_as_date(scheduled_time):
            logger.info(f"[SCHEDULED_TIME] Attempting to parse date: '{scheduled_time}'")
            parsed_dt, user_friendly_text = parse_natural_datetime(scheduled_time, validate=True)
            logger.info(f"[SCHEDULED_TIME] Parsed result: {parsed_dt}, user_friendly: {user_friendly_text}")

            # Проверяем, является ли user_friendly интервалом
            is_interval = user_friendly_text and "с" in user_friendly_text and "до" in user_friendly_text
            
            if parsed_dt or is_interval:
                # Проверяем валидацию (может быть warning) только если есть parsed_dt
                if parsed_dt:
                    validation = validate_parsed_datetime(parsed_dt, scheduled_time)
                else:
                    validation = {"is_valid": True, "error": None, "warning": None}

                # Проверяем, является ли user_friendly интервалом
                if is_interval:
                    # Это интервал времени - сохраняем его как есть
                    formatted_time = user_friendly_text
                    user_friendly = user_friendly_text
                else:
                    # Обычная дата - форматируем как обычно
                    formatted_time = format_datetime_for_storage(parsed_dt, scheduled_time)
                    user_friendly = format_datetime_user_friendly(parsed_dt, scheduled_time)

                # Формируем сообщение с предупреждением если есть
                confirmation_text = f"✅ <b>Дата распознана:</b>\n\n{user_friendly}"

                if validation.get("warning"):
                    confirmation_text += f"\n\n⚠️ <i>{validation['warning']}</i>"

                confirmation_text += (
                    "\n\nЕсли дата правильная, продолжайте создание заявки.\n"
                    "Для изменения введите время заново."
                )

                # Подтверждаем распознавание пользователю
                await message.answer(
                    confirmation_text,
                    parse_mode="HTML",
                )

                # Сохраняем отформатированное время и переходим к подтверждению
                await state.update_data(scheduled_time=formatted_time)
                logger.info("[SCHEDULED_TIME] Setting state to confirm after date recognition")
                await state.set_state(CreateOrderStates.confirm)
                logger.info("[SCHEDULED_TIME] Calling show_order_confirmation")
                await show_order_confirmation(message, state)
                logger.info(f"Автоопределение даты: '{message.text}' -> '{formatted_time}'")
                return
            else:
                # Не смогли распознать дату - переспрашиваем с примерами
                logger.info(f"[SCHEDULED_TIME] Failed to parse date: '{scheduled_time}'")
                await message.answer(
                    f"❓ <b>Не удалось распознать дату:</b> {scheduled_time}\n\n"
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
                    reply_markup=get_skip_cancel_keyboard(),
                )
                return

    # Если не похоже на дату - проверяем, не является ли это простой цифрой
    if re.match(r"^\d{1,2}$", scheduled_time.strip()):
        # Простая цифра - показываем примеры
        await message.answer(
            f"❌ <b>Введенный текст не похож на дату:</b> '{scheduled_time}'\n\n"
            f"<b>Примеры правильного ввода:</b>\n"
            f"• завтра в 15:00\n"
            f"• через 3 дня\n"
            f"• через неделю\n"
            f"• 25.12.2025\n"
            f"• послезавтра в 15:00\n\n"
            f"Пожалуйста, введите дату в одном из указанных форматов.",
            parse_mode="HTML",
            reply_markup=get_skip_cancel_keyboard(),
        )
        return

    await state.update_data(scheduled_time=scheduled_time)
    await state.set_state(CreateOrderStates.confirm)
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

    from app.handlers.common import get_menu_with_counter

    menu_keyboard = await get_menu_with_counter([user_role])
    await message.answer("❌ Создание заявки отменено.", reply_markup=menu_keyboard)

    log_action(message.from_user.id, "CANCEL_CREATE_ORDER", "Order creation cancelled")


async def show_order_confirmation(message: Message, state: FSMContext):
    """
    Показ подтверждения создания заявки

    Args:
        message: Сообщение
        state: FSMContext контекст
    """
    logger.info("[SHOW_CONFIRMATION] Starting order confirmation")
    data = await state.get_data()
    logger.info(f"[SHOW_CONFIRMATION] Got data: {list(data.keys())}")

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

    logger.info("[SHOW_CONFIRMATION] Sending confirmation message")
    await message.answer(text, parse_mode="HTML", reply_markup=get_confirm_keyboard())
    logger.info("[SHOW_CONFIRMATION] Confirmation message sent")


# Отладочный обработчик удален - он перехватывал все сообщения


@router.message(CreateOrderStates.confirm)
@handle_errors
async def debug_confirm_state(message: Message, state: FSMContext, user_role: str):
    """
    Отладочный обработчик для состояния подтверждения
    """
    logger.info(
        f"[DEBUG_CONFIRM] Received message in confirm state: '{message.text}' (type: {type(message.text)})"
    )

    # Если это кнопка подтверждения, передаем в основной обработчик
    if message.text == "✅ Подтвердить":
        await confirm_create_order(message, state, user_role)
        return

    # Если это кнопка отмены, передаем в обработчик отмены
    if message.text == "❌ Отмена":
        # Здесь должен быть обработчик отмены
        await message.answer("❌ Создание заявки отменено.")
        await state.clear()
        return

    # Если это что-то другое, обрабатываем как изменение времени
    await handle_time_change_in_confirm(message, state, user_role)


async def handle_time_change_in_confirm(message: Message, state: FSMContext, user_role: str):
    """
    Обработка изменения времени прибытия в состоянии подтверждения

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply("❌ Пожалуйста, отправьте текстовое сообщение с временем прибытия.")
        return

    # Проверяем, что это не кнопка подтверждения
    if message.text.strip() == "✅ Подтвердить":
        return

    scheduled_time = message.text.strip()
    logger.info(f"[CONFIRM_TIME_CHANGE] User wants to change time to: '{scheduled_time}'")

    # Возвращаемся к состоянию ввода времени
    await state.set_state(CreateOrderStates.scheduled_time)

    # Обрабатываем новое время
    await process_scheduled_time(message, state, user_role)


async def confirm_create_order(message: Message, state: FSMContext, user_role: str):
    """
    Подтверждение создания заявки с полной Pydantic валидацией

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
    """
    logger.info(f"[CONFIRM_ORDER] User clicked confirm button: '{message.text}'")
    data = await state.get_data()

    # ЗАЩИТА ОТ ДУБЛИРОВАНИЯ: проверяем флаг создания заявки
    if data.get("creating_order"):
        # Заявка уже создается, игнорируем повторный клик
        logger.warning(f"Duplicate order creation attempt by user {message.from_user.id}")
        return

    # Устанавливаем флаг, что заявка создается
    await state.update_data(creating_order=True)

    db = None
    order = None

    try:
        # КРИТИЧНО: Финальная валидация всех данных через Pydantic перед сохранением в БД
        try:
            # Детальное логирование данных перед валидацией
            logger.info(
                f"[VALIDATION_DEBUG] client_name: '{data.get('client_name')}', length: {len(data.get('client_name', ''))}"
            )
            logger.info(f"[VALIDATION_DEBUG] All data: {data}")

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
            logger.info(f"Order data validated successfully for dispatcher {message.from_user.id}")
        except ValidationError as e:
            # Если валидация не прошла - отменяем создание
            logger.error(f"Ошибка валидации заявки: {e}")

            from app.handlers.common import get_menu_with_counter

            error_details = "\n".join([f"• {err['msg']}" for err in e.errors()])
            menu_keyboard = await get_menu_with_counter([user_role])
            await message.answer(
                f"❌ <b>Ошибка валидации данных заявки:</b>\n\n{error_details}\n\n"
                "Пожалуйста, начните создание заявки заново.",
                parse_mode="HTML",
                reply_markup=menu_keyboard,
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

        # Отправляем уведомления всем админам и диспетчерам (кроме создателя)
        admins_and_dispatchers = await db.get_admins_and_dispatchers(
            exclude_user_id=message.from_user.id
        )

        notification_text = (
            f"🆕 <b>Новая заявка #{order.id}</b>\n\n"
            f"👤 Создал: {escape_html(message.from_user.full_name)}\n"
            f"🔧 Тип: {escape_html(order.equipment_type)}\n"
            f"📝 {escape_html(order.description)}\n\n"
            f"👤 Клиент: {escape_html(order.client_name)}\n"
            f"📍 {escape_html(order.client_address)}\n"
            f"📞 {order.client_phone}\n"
        )

        if order.scheduled_time:
            notification_text += f"\n⏰ Прибытие: {escape_html(order.scheduled_time)}"

        if order.notes:
            notification_text += f"\n\n📝 Заметки: {escape_html(order.notes)}"

        notification_text += "\n\n⚠️ <b>Требует назначения мастера!</b>"

        # Отправляем уведомления (используем бот из контекста сообщения)
        for user in admins_and_dispatchers:
            # Пропускаем создателя заявки
            if user.telegram_id == message.from_user.id:
                continue
            try:
                await safe_send_message(
                    message.bot, user.telegram_id, notification_text, parse_mode="HTML"
                )
                logger.info(f"Notification sent to {user.telegram_id} about order #{order.id}")
            except Exception as e:
                logger.error(f"Не удалось уведомить пользователя {user.telegram_id}: {e}")

    except Exception as e:
        logger.error(f"Ошибка при подтверждении создания заявки: {e}")
        # Отправляем сообщение об ошибке
        await message.answer(
            "❌ <b>Ошибка при создании заявки</b>\n\n"
            "Пожалуйста, попробуйте еще раз или обратитесь к администратору.",
            parse_mode="HTML",
        )
        return
    finally:
        # Гарантированная очистка ресурсов
        if db:
            await db.disconnect()
        # ВСЕГДА очищаем FSM state
        await state.clear()

    # Создаем inline кнопки для назначения мастера
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

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

    # Обновляем reply клавиатуру главного меню
    from app.handlers.common import get_menu_with_counter

    menu_keyboard = await get_menu_with_counter([user_role])
    await message.answer("Главное меню:", reply_markup=menu_keyboard)


# ==================== ПРОСМОТР ЗАЯВОК ====================


@router.message(F.text.startswith("📋 Все заявки"))
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

    # Получаем счетчики заявок по статусам (включая завершенные)
    db = Database()
    await db.connect()
    try:
        counts = {}
        for status in [
            OrderStatus.NEW,
            OrderStatus.ASSIGNED,
            OrderStatus.ACCEPTED,
            OrderStatus.ONSITE,
            OrderStatus.DR,
            OrderStatus.CLOSED,
        ]:
            orders = await db.get_all_orders(status=status)
            counts[status] = len(orders)
    finally:
        await db.disconnect()

    await message.answer(
        "📋 <b>Все заявки</b>\n\n" "Выберите фильтр:",
        parse_mode="HTML",
        reply_markup=get_orders_filter_keyboard(counts),
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

        # Показываем информацию о длительном ремонте
        if order.status == OrderStatus.DR:
            if order.estimated_completion_date:
                text += f"⏰ <b>Примерный срок окончания:</b> {escape_html(order.estimated_completion_date)}\n"
            if order.prepayment_amount:
                text += f"💰 <b>Предоплата:</b> {order.prepayment_amount:.2f} ₽\n"

        # Показываем финансовую информацию для закрытых заявок
        if order.status == OrderStatus.CLOSED and order.total_amount:
            net_profit = order.total_amount - (order.materials_cost or 0)

            # Определяем базовую ставку
            base_rate = "50/50" if net_profit >= 7000 else "40/60"

            text += "\n💰 <b>Финансовая информация:</b>\n"
            text += f"• Сумма заказа: <b>{order.total_amount:.2f} ₽</b>\n"
            text += f"• Чистая прибыль: <b>{net_profit:.2f} ₽</b>\n"
            text += f"\n📊 <b>Распределение ({base_rate}):</b>\n"

            if order.master_profit:
                master_percent = (order.master_profit / net_profit * 100) if net_profit > 0 else 0
                text += f"• Прибыль мастера: <b>{order.master_profit:.2f} ₽</b> ({master_percent:.0f}%)\n"
            if order.company_profit:
                company_percent = (order.company_profit / net_profit * 100) if net_profit > 0 else 0
                text += f"• Прибыль компании: <b>{order.company_profit:.2f} ₽</b> ({company_percent:.0f}%)\n"

            # Надбавки и бонусы (показываем только если явно True)
            bonuses = []
            if order.has_review is True:
                bonuses.append("✅ Отзыв (+10% мастеру)")
            if order.out_of_city is True:
                bonuses.append("✅ Выезд за город")

            if bonuses:
                text += f"\n🎁 <b>Надбавки:</b> {', '.join(bonuses)}\n"

            text += "\n"

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
async def callback_select_master_for_order(
    callback: CallbackQuery, user_role: str, user_roles: list
):
    """
    Назначение выбранного мастера на заявку

    Args:
        callback: Callback query
        user_roles: Список ролей пользователя
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
        # Получаем информацию о мастере ДО назначения
        master = await db.get_master_by_id(master_id)

        # ПРОВЕРЯЕМ НАЛИЧИЕ РАБОЧЕЙ ГРУППЫ ДО НАЗНАЧЕНИЯ
        if not master.work_chat_id:
            logger.warning(
                f"ASSIGNMENT BLOCKED: Master {master.id} ({master.get_display_name()}) has no work_chat_id set."
            )
            await callback.answer(
                f"❌ ОТКАЗАНО В НАЗНАЧЕНИИ\n\n"
                f"У мастера {master.get_display_name()} не настроена рабочая группа.\n\n"
                f"Пожалуйста, сначала настройте рабочую группу для этого мастера.",
                show_alert=True,
            )
            # Не назначаем мастера, возвращаемся
            return

        # Назначаем мастера (только если есть work_chat_id) с валидацией
        await db.assign_master_to_order(
            order_id=order_id,
            master_id=master_id,
            user_roles=user_roles,  # Передаём роли для валидации
        )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="ASSIGN_MASTER",
            details=f"Assigned master {master_id} to order #{order_id}",
        )

        # Уведомляем мастера с retry
        order = await db.get_order_by_id(order_id)

        # Отправляем уведомление в рабочую группу
        # (проверку work_chat_id уже сделали выше)
        from app.keyboards.inline import get_group_order_keyboard

        target_chat_id = master.work_chat_id

        logger.info(f"Attempting to send notification to group {target_chat_id}")

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

        # Упоминаем мастера в группе (ORM: через master.user)
        master_username = master.user.username if hasattr(master, "user") and master.user else None
        if master_username:
            notification_text += f"👨‍🔧 <b>Мастер:</b> @{master_username}\n\n"
        else:
            notification_text += f"👨‍🔧 <b>Мастер:</b> {master.get_display_name()}\n\n"

        notification_text += f"📅 <b>Создана:</b> {format_datetime(order.created_at)}\n"
        notification_text += f"🔄 <b>Назначена:</b> {format_datetime(get_now())}"

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
            # Сохраняем message_id для последующего удаления при снятии мастера
            try:
                # ORM: сохраняем в таблицу order_group_messages
                if hasattr(db, "save_order_group_message"):
                    await db.save_order_group_message(
                        order_id=order_id,
                        master_id=master_id,
                        chat_id=target_chat_id,
                        message_id=result.message_id,
                    )
            except Exception as e:
                logger.warning(
                    f"Не удалось сохранить групповое сообщение для заявки {order_id}: {e}"
                )
        else:
            logger.error(f"КРИТИЧНО: Не удалось уведомить мастера в группе {target_chat_id}")

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
async def callback_select_new_master_for_order(
    callback: CallbackQuery, user_role: str, user_roles: list
):
    """
    Назначение нового мастера на заявку (переназначение)

    Args:
        callback: Callback query
        user_role: Роль пользователя (основная)
        user_roles: Список ролей пользователя
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

        # Получаем информацию о новом мастере ДО переназначения
        new_master = await db.get_master_by_id(new_master_id)

        # ПРОВЕРЯЕМ НАЛИЧИЕ РАБОЧЕЙ ГРУППЫ ДО ПЕРЕНАЗНАЧЕНИЯ
        if not new_master.work_chat_id:
            logger.warning(
                f"REASSIGNMENT BLOCKED: Master {new_master.id} ({new_master.get_display_name()}) has no work_chat_id set."
            )
            await callback.answer(
                f"❌ ОТКАЗАНО В ПЕРЕНАЗНАЧЕНИИ\n\n"
                f"У мастера {new_master.get_display_name()} не настроена рабочая группа.\n\n"
                f"Пожалуйста, сначала настройте рабочую группу для этого мастера.",
                show_alert=True,
            )
            # Не переназначаем мастера, возвращаемся
            return

        # Переназначаем мастера (только если есть work_chat_id) с валидацией
        await db.assign_master_to_order(
            order_id=order_id,
            master_id=new_master_id,
            user_roles=user_roles,  # Передаём роли для валидации
        )

        # Добавляем в лог
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="REASSIGN_MASTER",
            details=f"Reassigned order #{order_id} from master {old_master_id} to master {new_master_id}",
        )

        # Уведомляем старого мастера о снятии заявки с retry
        if old_master and old_master.work_chat_id:
            target_chat_id = old_master.work_chat_id
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

        # Уведомляем нового мастера в рабочую группу
        # (проверку work_chat_id уже сделали выше)
        from app.keyboards.inline import get_group_order_keyboard

        target_chat_id = new_master.work_chat_id

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

        # Упоминаем мастера в группе (ORM: через master.user)
        new_master_username = (
            new_master.user.username if hasattr(new_master, "user") and new_master.user else None
        )
        if new_master_username:
            notification_text += f"👨‍🔧 <b>Мастер:</b> @{new_master_username}\n\n"
        else:
            notification_text += f"👨‍🔧 <b>Мастер:</b> {new_master.get_display_name()}\n\n"

        notification_text += f"📅 <b>Создана:</b> {format_datetime(order.created_at)}\n"
        notification_text += f"🔄 <b>Переназначена:</b> {format_datetime(get_now())}"

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
            try:
                if hasattr(db, "save_order_group_message"):
                    await db.save_order_group_message(
                        order_id=order_id,
                        master_id=new_master_id,
                        chat_id=target_chat_id,
                        message_id=result.message_id,
                    )
            except Exception as e:
                logger.warning(
                    f"Не удалось сохранить групповое сообщение для переназначенной заявки {order_id}: {e}"
                )
        else:
            logger.warning(
                f"Не удалось отправить уведомление новому мастеру в группе {target_chat_id}"
            )

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

        # Снимаем мастера и возвращаем статус в NEW (ORM compatible)
        if hasattr(db, "unassign_master_from_order"):
            # ORM: используем специальный метод
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
            action="UNASSIGN_MASTER",
            details=f"Unassigned master {order.assigned_master_id} from order #{order_id}",
        )

        # Меню обновится автоматически в update_order_status

        # Удаляем сообщение о заявке в рабочей группе мастера, если ранее отправляли
        try:
            if hasattr(db, "get_active_group_messages_by_order"):
                messages = await db.get_active_group_messages_by_order(order_id)
                if messages:
                    from app.utils.retry import safe_delete_message

                    for m in messages:
                        # Пытаемся удалить сообщение
                        deleted = await safe_delete_message(callback.bot, m.chat_id, m.message_id)
                        if deleted:
                            logger.info(
                                f"Deleted group message {m.message_id} for order {order_id} in chat {m.chat_id}"
                            )
                    # Помечаем записи неактивными
                    await db.deactivate_group_messages(order_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить групповые сообщения для заявки {order_id}: {e}")

        # Уведомляем мастера только в рабочей группе (личка отключена)
        if master and master.work_chat_id:
            await safe_send_message(
                callback.bot,
                master.work_chat_id,
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
async def callback_close_order(callback: CallbackQuery, user_role: str, state: FSMContext):
    """
    Закрытие заявки с вводом финансовых данных

    Args:
        callback: Callback query
        user_role: Роль пользователя
        state: FSM контекст
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    order_id = int(callback.data.split(":")[1])

    # Сохраняем order_id в state для последующих шагов
    await state.update_data(order_id=order_id)

    # Переходим к вводу общей суммы
    await state.set_state(AdminCloseOrderStates.enter_total_amount)

    await callback.message.edit_text(
        f"💰 <b>Закрытие заявки #{order_id}</b>\n\n"
        "Введите общую сумму заказа в рублях:\n"
        "(например: 5000, 5000.50 или 0)",
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data.startswith("refuse_order:"))
async def callback_refuse_order(callback: CallbackQuery, user_role: str, user_roles: list):
    """
    Отклонение заявки

    Args:
        callback: Callback query
        user_role: Роль пользователя (основная, для обратной совместимости)
        user_roles: Список ролей пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    order_id = int(callback.data.split(":")[1])

    db = Database()
    await db.connect()

    try:
        order = await db.get_order_by_id(order_id)
        await db.update_order_status(
            order_id=order_id,
            status=OrderStatus.REFUSED,
            changed_by=callback.from_user.id,
            user_roles=user_roles,  # Передаём роли для валидации
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


@router.callback_query(F.data.startswith("client_waiting:"))
@handle_errors
async def callback_client_waiting(callback: CallbackQuery, user_role: str):
    """
    Уведомление мастера о том, что клиент ждет

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

        if not order or not order.assigned_master_id:
            await callback.answer("❌ Заявка не найдена или мастер не назначен", show_alert=True)
            return

        master = await db.get_master_by_id(order.assigned_master_id)

        if not master:
            await callback.answer("❌ Мастер не найден", show_alert=True)
            return

        # Отправляем ВАЖНОЕ уведомление мастеру
        # Это уведомление отправляется в ЛИЧКУ как важное/срочное
        urgent_notification = (
            f"📞 <b>СРОЧНО: Клиент ждет!</b>\n\n"
            f"📋 <b>Заявка #{order.id}</b>\n"
            f"🔧 {order.equipment_type}\n"
            f"👤 Клиент: {order.client_name}\n"
            f"📍 Адрес: {order.client_address}\n\n"
            f"⚠️ <b>Клиент звонил и спрашивал где мастер!</b>\n"
            f"Пожалуйста, свяжитесь с клиентом как можно скорее.\n\n"
            f"📞 Телефон: {order.client_phone}"
        )

        # Отправляем в ЛИЧКУ как важное уведомление
        result = await safe_send_message(
            callback.bot, master.telegram_id, urgent_notification, parse_mode="HTML", max_attempts=5
        )

        # Также дублируем в рабочую группу если она есть
        if master.work_chat_id:
            # ORM: через master.user
            master_mention = (
                f"@{master.user.username}"
                if (hasattr(master, "user") and master.user and master.user.username)
                else master.get_display_name()
            )
            group_notification = (
                f"📞 <b>ВАЖНО: Клиент ждет!</b>\n\n"
                f"📋 Заявка #{order.id}\n"
                f"👨‍🔧 Мастер: {master_mention}\n\n"
                f"⚠️ Клиент звонил и спрашивает где мастер.\n"
                f"Пожалуйста, свяжитесь с клиентом."
            )

            await safe_send_message(
                callback.bot,
                master.work_chat_id,
                group_notification,
                parse_mode="HTML",
                max_attempts=3,
            )

        # Логируем действие
        await db.add_audit_log(
            user_id=callback.from_user.id,
            action="CLIENT_WAITING_NOTIFICATION",
            details=f"Sent 'client waiting' notification for order #{order_id} to master {master.id}",
        )

        log_action(
            callback.from_user.id, "CLIENT_WAITING", f"Order #{order_id}, Master {master.id}"
        )

        if result:
            await callback.answer(
                f"✅ Уведомление отправлено мастеру {master.get_display_name()}", show_alert=True
            )
        else:
            await callback.answer("⚠️ Не удалось отправить уведомление мастеру", show_alert=True)

    finally:
        await db.disconnect()


@router.callback_query(F.data == "back_to_orders")
async def callback_back_to_orders(callback: CallbackQuery, user_role: str):
    """
    Возврат к списку заявок (для диспетчеров и мастеров)

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    # Для диспетчеров и админов - возврат к фильтру заявок
    if user_role in [UserRole.ADMIN, UserRole.DISPATCHER]:
        # Получаем счетчики заявок (без завершённых)
        db = Database()
        await db.connect()
        try:
            counts = {}
            for status in [
                OrderStatus.NEW,
                OrderStatus.ASSIGNED,
                OrderStatus.ACCEPTED,
                OrderStatus.ONSITE,
                OrderStatus.DR,
            ]:
                orders = await db.get_all_orders(status=status)
                counts[status] = len(orders)
        finally:
            await db.disconnect()

        await callback.message.edit_text(
            "📋 <b>Все заявки</b>\n\n" "Выберите фильтр:",
            parse_mode="HTML",
            reply_markup=get_orders_filter_keyboard(counts),
        )
    # Для мастеров - возврат к списку своих заявок
    elif user_role == UserRole.MASTER:
        db = Database()
        await db.connect()

        try:
            # Получаем мастера
            master = await db.get_master_by_telegram_id(callback.from_user.id)

            if not master:
                await callback.answer("❌ Вы не зарегистрированы как мастер", show_alert=True)
                return

            # Получаем заявки мастера
            orders = await db.get_orders_by_master(master.id, exclude_closed=True)

            if not orders:
                await callback.message.edit_text(
                    "📭 У вас пока нет активных заявок.\n\n" "Заявки будут назначаться диспетчером."
                )
                await callback.answer()
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
                        scheduled_time = (
                            f" ({order.scheduled_time})" if order.scheduled_time else ""
                        )
                        text += f"  • Заявка #{order.id} - {order.equipment_type}{scheduled_time}\n"

                    text += "\n"

            keyboard = get_order_list_keyboard(orders, for_master=True)

            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

        finally:
            await db.disconnect()

    await callback.answer()


# ==================== ОТЧЕТЫ ====================


@router.message(F.text == "📊 Отчеты")
async def btn_reports(message: Message, user_role: str, user_roles: list):
    """
    Меню финансовых отчетов (новая система)

    Args:
        message: Сообщение
        user_role: Роль пользователя
        user_roles: Список ролей пользователя
    """
    logger.info(f"DEBUG dispatcher.btn_reports: user_role='{user_role}', user_roles={user_roles}")

    # Проверка роли (проверяем весь список ролей)
    if not any(role in user_roles for role in [UserRole.ADMIN, UserRole.DISPATCHER]):
        logger.warning(f"Access denied in dispatcher.btn_reports: user_roles={user_roles}")
        return

    # Вызываем команду /reports из системы отчетов
    from app.handlers.financial_reports import cmd_reports

    logger.info(f"DEBUG calling cmd_reports with user_role='{user_role}'")
    await cmd_reports(message, user_role)


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
@handle_errors
async def btn_settings_dispatcher(message: Message, user_role: str):
    """
    Обработчик кнопки настроек для диспетчеров

    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    # Проверка роли
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return

    from app.database.orm_database import ORMDatabase

    db = ORMDatabase()
    await db.connect()

    try:
        user = await db.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден в системе.")
            return

        settings_text = (
            f"⚙️ <b>Настройки профиля</b>\n\n"
            f"👤 <b>Имя:</b> {user.get_display_name()}\n"
            f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
            f"👔 <b>Роль:</b> {user.role}\n"
        )

        if user.username:
            settings_text += f"📱 <b>Username:</b> @{user.username}\n"

        await message.answer(settings_text, parse_mode="HTML")

    finally:
        await db.disconnect()


# ==================== FSM: ЗАКРЫТИЕ ЗАЯВКИ С ФИНАНСАМИ ====================


@router.message(AdminCloseOrderStates.enter_total_amount)
async def admin_process_total_amount(message: Message, state: FSMContext):
    """
    Обработка ввода общей суммы заказа админом/диспетчером

    Args:
        message: Сообщение
        state: FSM контекст
    """
    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с суммой.\n"
            "Введите число (например: 5000, 5000.50 или 0):"
        )
        return

    # Проверяем, что введена корректная сумма
    try:
        total_amount = float(message.text.replace(",", ".").strip())
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

    # Если сумма 0 рублей, автоматически завершаем как отказ
    if total_amount == 0:
        # Устанавливаем значения по умолчанию для отказа
        await state.update_data(materials_cost=0.0, has_review=False, out_of_city=False)

        # Получаем данные из состояния
        data = await state.get_data()
        order_id = data.get("order_id")

        # Завершаем заказ как отказ
        from app.handlers.master import complete_order_as_refusal

        await complete_order_as_refusal(message, state, order_id)
        return

    # Переходим к запросу суммы расходного материала
    await state.set_state(AdminCloseOrderStates.enter_materials_cost)

    await message.reply(
        f"✅ Общая сумма заказа: <b>{total_amount:.2f} ₽</b>\n\n"
        f"Теперь введите <b>сумму расходного материала</b> (в рублях):\n"
        f"Например: 1500 или 1500.50\n\n"
        f"Если расходного материала не было, введите: 0",
        parse_mode="HTML",
    )


@router.message(AdminCloseOrderStates.enter_materials_cost)
async def admin_process_materials_cost(message: Message, state: FSMContext):
    """
    Обработка ввода суммы расходного материала админом/диспетчером

    Args:
        message: Сообщение
        state: FSM контекст
    """
    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, отправьте текстовое сообщение с суммой.\n"
            "Введите число (например: 500, 0):"
        )
        return

    logger.info(f"Processing materials cost: {message.text}")

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

    # Получаем ID заказа для inline кнопок
    data = await state.get_data()
    order_id = data.get("order_id")
    logger.info(f"Order ID from state: {order_id}")

    # Переходим к подтверждению материалов
    await state.set_state(AdminCloseOrderStates.confirm_materials)

    from app.keyboards.inline import get_yes_no_keyboard

    logger.info(f"Creating yes/no keyboard for order {order_id}")
    keyboard = get_yes_no_keyboard("admin_confirm_materials", order_id)
    logger.info(f"Keyboard created: {keyboard}")

    await message.reply(
        f"💰 <b>Подтвердите сумму расходных материалов:</b>\n\n"
        f"Сумма: <b>{materials_cost:.2f} ₽</b>\n\n"
        f"Верно ли указана сумма?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    logger.info("Message with keyboard sent successfully")


@router.callback_query(lambda c: c.data.startswith("admin_confirm_materials"))
async def admin_process_materials_confirmation_callback(
    callback_query: CallbackQuery, state: FSMContext
):
    """
    Обработка подтверждения суммы материалов админом/диспетчером
    """
    from app.utils import parse_callback_data

    parsed_data = parse_callback_data(callback_query.data)
    action = parsed_data.get("action")
    params = parsed_data.get("params", [])
    answer = params[0] if len(params) > 0 else None  # yes/no
    order_id = params[1] if len(params) > 1 else None  # order_id

    if answer == "yes":
        # Подтверждаем сумму материалов и переходим к отзыву
        await state.set_state(AdminCloseOrderStates.confirm_review)

        from app.keyboards.inline import get_yes_no_keyboard

        await callback_query.message.edit_text(
            "✅ Сумма расходного материала подтверждена\n\n"
            "❓ <b>Взял ли мастер отзыв у клиента?</b>\n"
            "(За отзыв мастер получит дополнительно +10% к прибыли)",
            parse_mode="HTML",
            reply_markup=get_yes_no_keyboard("admin_confirm_review", order_id),
        )
    elif answer == "no":
        # Возвращаемся к вводу суммы материалов
        await state.set_state(AdminCloseOrderStates.enter_materials_cost)

        await callback_query.message.edit_text(
            "💰 <b>Введите сумму расходного материала:</b>\n\n" "Введите число (например: 500, 0):",
            parse_mode="HTML",
            reply_markup=None,
        )

    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith("admin_confirm_review"))
async def admin_process_review_confirmation_callback(
    callback_query: CallbackQuery, state: FSMContext
):
    """
    Обработка подтверждения наличия отзыва админом/диспетчером через inline кнопки

    Args:
        callback_query: Callback запрос
        state: FSM контекст
    """
    # Извлекаем данные из callback
    from app.utils import parse_callback_data

    callback_data = parse_callback_data(callback_query.data)
    order_id = callback_data["params"][0] if len(callback_data["params"]) > 0 else None
    answer = callback_data["params"][1] if len(callback_data["params"]) > 1 else None

    # Определяем ответ
    has_review = answer == "yes"

    # Сохраняем ответ об отзыве
    await state.update_data(has_review=has_review)

    # Переходим к запросу выезда за город
    await state.set_state(AdminCloseOrderStates.confirm_out_of_city)

    review_text = "✅ Отзыв взят!" if has_review else "❌ Отзыв не взят"

    from app.keyboards.inline import get_yes_no_keyboard

    # Получаем order_id из состояния, так как в callback data он может быть перепутан
    data = await state.get_data()
    order_id_from_state = data.get("order_id")

    await callback_query.message.edit_text(
        f"{review_text}\n\n"
        f"🚗 <b>Был ли выезд за город?</b>\n"
        f"(За выезд за город мастер получит дополнительно +10% к прибыли)",
        parse_mode="HTML",
        reply_markup=get_yes_no_keyboard("admin_confirm_out_of_city", order_id_from_state),
    )

    await callback_query.answer()


@router.message(AdminCloseOrderStates.confirm_review)
async def admin_process_review_confirmation_fallback(message: Message, state: FSMContext):
    """
    Fallback обработка для текстовых сообщений (на случай если кнопки не работают)

    Args:
        message: Сообщение
        state: FSM контекст
    """
    await message.reply(
        "❌ Пожалуйста, используйте кнопки для ответа.\n"
        "Если кнопки не отображаются, попробуйте перезапустить процесс завершения заказа."
    )


@router.callback_query(lambda c: c.data.startswith("admin_confirm_out_of_city"))
async def admin_process_out_of_city_confirmation_callback(
    callback_query: CallbackQuery, state: FSMContext, user_roles: list
):
    """
    Обработка подтверждения выезда за город через inline кнопки и завершение заказа админом/диспетчером

    Args:
        callback_query: Callback запрос
        state: FSM контекст
        user_roles: Список ролей пользователя
    """
    # Извлекаем данные из callback
    from app.utils import parse_callback_data

    callback_data = parse_callback_data(callback_query.data)
    order_id = callback_data["params"][0] if len(callback_data["params"]) > 0 else None
    answer = callback_data["params"][1] if len(callback_data["params"]) > 1 else None

    # Определяем ответ
    out_of_city = answer == "yes"

    # Получаем данные из состояния
    data = await state.get_data()
    total_amount = data.get("total_amount")
    materials_cost = data.get("materials_cost")
    has_review = data.get("has_review")

    db = Database()
    await db.connect()

    # Получаем order_id из состояния, так как в callback data он может быть перепутан
    data = await state.get_data()
    order_id_from_state = data.get("order_id")

    try:
        order = await db.get_order_by_id(order_id_from_state)

        if not order:
            await callback_query.message.edit_text("❌ Заявка не найдена.")
            await state.clear()
            return

        # Расчет прибыли
        from app.utils.helpers import calculate_profit_split

        master_profit, company_profit = calculate_profit_split(
            total_amount, materials_cost, has_review, out_of_city
        )

        # Обновляем заявку
        await db.update_order_amounts(
            order_id=order_id_from_state,
            total_amount=total_amount,
            materials_cost=materials_cost,
            master_profit=master_profit,
            company_profit=company_profit,
            has_review=has_review,
            out_of_city=out_of_city,
        )

        # Меняем статус на CLOSED (с валидацией через State Machine)
        from app.config import OrderStatus

        await db.update_order_status(
            order_id=order_id_from_state,
            status=OrderStatus.CLOSED,
            changed_by=callback_query.from_user.id,
            user_roles=user_roles,  # Передаём роли для валидации
        )

        # Создаем отчет по заказу
        try:
            from app.services.order_reports import OrderReportsService

            order_reports_service = OrderReportsService()

            # Получаем актуальные данные заказа
            updated_order = await db.get_order_by_id(order_id_from_state)

            # Получаем данные мастера и диспетчера
            master = None
            dispatcher = None

            if updated_order.assigned_master_id:
                master = await db.get_master_by_id(updated_order.assigned_master_id)

            if updated_order.dispatcher_id:
                dispatcher = await db.get_user_by_telegram_id(updated_order.dispatcher_id)

            # Создаем запись в отчете
            await order_reports_service.create_order_report(updated_order, master, dispatcher)
            logger.info(f"Order report created for order #{order_id_from_state}")

        except Exception as e:
            logger.error(f"Не удалось создать отчет для заявки #{order_id_from_state}: {e}")

        # Логирование
        await db.add_audit_log(
            user_id=callback_query.from_user.id,
            action="CLOSE_ORDER",
            details=f"Closed order #{order_id_from_state} with financials",
        )

        # Расчет чистой прибыли
        net_profit = total_amount - materials_cost

        # Формируем сообщение для админа/диспетчера
        out_of_city_text = "🚗 Да" if out_of_city else "❌ Нет"
        review_text = "⭐ Да" if has_review else "❌ Нет"

        summary_message = (
            f"✅ <b>Заявка #{order_id_from_state} успешно закрыта!</b>\n\n"
            f"💰 <b>Финансы:</b>\n"
            f"├ Общая сумма: {total_amount:.2f} ₽\n"
            f"├ Расходники: {materials_cost:.2f} ₽\n"
            f"├ Чистая прибыль: {net_profit:.2f} ₽\n"
            f"├ К выплате мастеру: <b>{master_profit:.2f} ₽</b>\n"
            f"└ Прибыль компании: <b>{company_profit:.2f} ₽</b>\n\n"
            f"📊 <b>Дополнительно:</b>\n"
            f"├ Отзыв: {review_text}\n"
            f"└ Выезд за город: {out_of_city_text}"
        )

        await callback_query.message.edit_text(summary_message, parse_mode="HTML")

        # Уведомление мастера (если есть)
        if order.assigned_master_id:
            master = await db.get_master_by_id(order.assigned_master_id)
            if master and master.work_chat_id:
                master_message = (
                    f"✅ <b>Заявка #{order_id} закрыта!</b>\n\n"
                    f"💰 <b>Финансы:</b>\n"
                    f"├ Общая сумма: {total_amount:.2f} ₽\n"
                    f"├ Расходники: {materials_cost:.2f} ₽\n"
                    f"├ Чистая прибыль: {net_profit:.2f} ₽\n"
                    f"└ К выплате вам: <b>{master_profit:.2f} ₽</b>\n\n"
                    f"📊 <b>Дополнительно:</b>\n"
                    f"├ Отзыв: {review_text}\n"
                    f"└ Выезд за город: {out_of_city_text}"
                )

                from aiogram import Bot

                from app.config import Config

                bot = Bot(token=Config.BOT_TOKEN)
                await safe_send_message(bot, master.work_chat_id, master_message, parse_mode="HTML")

        await callback_query.answer("✅ Заявка успешно закрыта!")
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при закрытии заявки: {e}")
        await callback_query.message.edit_text(f"❌ Ошибка при закрытии заявки: {e!s}")
    finally:
        await db.disconnect()


@router.message(AdminCloseOrderStates.confirm_out_of_city)
async def admin_process_out_of_city_confirmation_fallback(message: Message, state: FSMContext):
    """
    Fallback обработка для текстовых сообщений (на случай если кнопки не работают)

    Args:
        message: Сообщение
        state: FSM контекст
    """
    await message.reply(
        "❌ Пожалуйста, используйте кнопки для ответа.\n"
        "Если кнопки не отображаются, попробуйте перезапустить процесс завершения заказа."
    )
