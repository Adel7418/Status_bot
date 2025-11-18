"""
Обработчики для редактирования заявок
"""

import logging
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pydantic import ValidationError

from app.config import MAX_DESCRIPTION_LENGTH, MAX_NOTES_LENGTH, OrderStatus, UserRole
from app.database import Database
from app.decorators import handle_errors
from app.keyboards.reply import get_cancel_keyboard
from app.states import EditOrderStates
from app.utils import (
    escape_html,
    format_datetime_for_storage,
    format_datetime_user_friendly,
    log_action,
    parse_natural_datetime,
    should_parse_as_date,
    validate_parsed_datetime,
)


logger = logging.getLogger(__name__)

router = Router(name="order_edit")


# Поля, которые можно редактировать, и их отображение
EDITABLE_FIELDS = {
    "equipment_type": "📱 Тип техники",
    "description": "📝 Описание проблемы",
    "client_name": "👤 Имя клиента",
    "client_address": "📍 Адрес",
    "client_phone": "📞 Телефон",
    "notes": "📋 Заметки",
    "scheduled_time": "⏰ Время прибытия",
    "estimated_completion_date": "📅 Срок окончания (DR)",
    "prepayment_amount": "💰 Предоплата (DR)",
}


async def show_edit_order_menu(message: Message, order, user_role: str, allow_closed: bool = False):
    """
    Показать меню редактирования заявки

    Args:
        message: Сообщение
        order: Заявка
        user_role: Роль пользователя
        allow_closed: Разрешить редактирование закрытых заявок
    """
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    # Проверка прав
    can_edit, error_msg = can_edit_order(order, user_role, allow_closed)
    if not can_edit:
        await message.reply(f"❌ {error_msg}")
        return

    # Формируем информацию о заявке
    status_names = {
        OrderStatus.NEW: "🆕 Новая",
        OrderStatus.ASSIGNED: "👨‍🔧 Назначена",
        OrderStatus.ACCEPTED: "✅ Принята",
        OrderStatus.ONSITE: "🏠 На объекте",
        OrderStatus.DR: "⏳ ДР",
        OrderStatus.CLOSED: "✅ Закрыта",
        OrderStatus.REFUSED: "❌ Отклонена",
    }

    order_text = (
        f"📋 <b>Заявка #{order.id}</b>\n"
        f"📱 <b>Тип техники:</b> {order.equipment_type}\n"
        f"📝 <b>Описание:</b> {order.description}\n"
        f"👤 <b>Клиент:</b> {order.client_name}\n"
        f"📍 <b>Адрес:</b> {order.client_address}\n"
        f"📞 <b>Телефон:</b> {order.client_phone}\n"
        f"📊 <b>Статус:</b> {status_names.get(order.status, order.status)}\n"
    )

    if order.notes:
        order_text += f"📋 <b>Заметки:</b> {order.notes}\n"

    if order.scheduled_time:
        order_text += f"⏰ <b>Время прибытия:</b> {order.scheduled_time}\n"

    if order.estimated_completion_date:
        order_text += f"📅 <b>Срок окончания (DR):</b> {order.estimated_completion_date}\n"

    if order.prepayment_amount:
        order_text += f"💰 <b>Предоплата (DR):</b> {order.prepayment_amount} ₽\n"

    order_text += "\n✏️ <b>Выберите поле для редактирования:</b>"

    # Создаем клавиатуру с полями для редактирования
    builder = InlineKeyboardBuilder()

    for field_key, field_name in EDITABLE_FIELDS.items():
        # Показываем поля DR только для заявок в статусе DR
        if field_key in ["estimated_completion_date", "prepayment_amount"]:
            if order.status != OrderStatus.DR:
                continue  # Пропускаем DR поля для других статусов

        builder.row(
            InlineKeyboardButton(
                text=field_name,
                callback_data=f"edit_field:{field_key}",
            )
        )

    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit"))

    await message.reply(order_text, parse_mode="HTML", reply_markup=builder.as_markup())


def can_edit_order(order, user_role: str, allow_closed: bool = False) -> tuple[bool, str | None]:
    """
    Проверка прав на редактирование заявки

    Args:
        order: Заявка
        user_role: Роль пользователя
        allow_closed: Разрешить редактирование закрытых заявок (только для админов)

    Returns:
        (can_edit, error_message)
    """
    # Закрытые и отклоненные заявки редактировать нельзя (кроме специального случая)
    if order.status in [OrderStatus.CLOSED, OrderStatus.REFUSED]:
        if allow_closed and user_role == UserRole.ADMIN and order.status == OrderStatus.CLOSED:
            return True, None
        return False, "Нельзя редактировать закрытые или отклоненные заявки"

    # Админы и диспетчеры могут редактировать на любом статусе
    if user_role in [UserRole.ADMIN, UserRole.DISPATCHER]:
        return True, None

    # Мастера могут редактировать только на определенных статусах
    # if user_role == UserRole.MASTER:
    #     if order.status in [OrderStatus.ASSIGNED, OrderStatus.ACCEPTED, OrderStatus.ONSITE]:
    #         return True, None
    #     return False, "Вы можете редактировать заявку только в статусах: Назначена, Принята, На объекте"

    # По умолчанию запрещаем
    return False, "У вас нет прав на редактирование заявок"


@router.callback_query(F.data.startswith("edit_order:"))
@handle_errors
async def callback_edit_order(
    callback: CallbackQuery, state: FSMContext, user_role: str, db: Database
):
    """
    Начало редактирования заявки - выбор поля

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
        db: Database instance (injected)
    """
    data_cb = callback.data or ""
    parts = data_cb.split(":")
    if len(parts) < 2:
        await callback.answer("Некорректный формат callback данных", show_alert=True)
        return
    order_id = int(parts[1])

    order = await db.get_order_by_id(order_id)

    if not order:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    # Проверка прав
    can_edit, error_msg = can_edit_order(order, user_role, allow_closed=False)
    if not can_edit:
        await callback.answer(error_msg, show_alert=True)
        return

    # Сохраняем order_id в state
    await state.update_data(order_id=order_id)
    await state.set_state(EditOrderStates.select_field)

    # Создаем клавиатуру с полями для редактирования
    builder = InlineKeyboardBuilder()

    for field_key, field_name in EDITABLE_FIELDS.items():
        # Показываем поля DR только для заявок в статусе DR
        if field_key in ["estimated_completion_date", "prepayment_amount"]:
            if order.status != OrderStatus.DR:
                continue  # Пропускаем DR поля для других статусов

        builder.row(
            InlineKeyboardButton(
                text=field_name,
                callback_data=f"edit_field:{field_key}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"view_order:{order_id}",
        )
    )

    message = callback.message
    if not isinstance(message, Message):
        await callback.answer("Сообщение недоступно", show_alert=True)
        return

    await message.edit_text(
        f"✏️ <b>Редактирование заявки #{order_id}</b>\n\n" f"Выберите поле для редактирования:",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("edit_field:"), EditOrderStates.select_field)
@handle_errors
async def callback_select_field(
    callback: CallbackQuery, state: FSMContext, user_role: str, db: Database
):
    """
    Выбор поля для редактирования

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя
        db: Database instance (injected)
    """
    data_cb = callback.data or ""
    parts = data_cb.split(":")
    if len(parts) < 2:
        await callback.answer("Некорректный формат callback данных", show_alert=True)
        return
    field = parts[1]
    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await callback.answer("Ошибка: заявка не найдена", show_alert=True)
        await state.clear()
        return

    # Сохраняем выбранное поле
    await state.update_data(field=field)
    await state.set_state(EditOrderStates.enter_value)

    # Получаем текущее значение поля
    order = await db.get_order_by_id(order_id)
    current_value = getattr(order, field, "Не указано")

    field_name = EDITABLE_FIELDS.get(field, field)

    # Формируем подсказку в зависимости от поля
    prompt = f"✏️ <b>Редактирование: {field_name}</b>\n\n"
    prompt += f"<b>Текущее значение:</b>\n{escape_html(str(current_value)) if current_value else 'Не указано'}\n\n"
    prompt += "<b>Введите новое значение:</b>\n\n"

    # Специфичные подсказки для разных полей
    if field == "equipment_type":
        from app.core.constants import EquipmentType

        types = EquipmentType.all_types()
        prompt += "<b>Доступные типы:</b>\n"
        for eq_type in types:
            prompt += f"• {eq_type}\n"
        prompt += "\n<i>Введите точное название типа техники</i>"

    elif field == "description":
        prompt += f"<i>Минимум 4 символа, максимум {MAX_DESCRIPTION_LENGTH}</i>"

    elif field == "client_name":
        prompt += "<i>Минимум 5 символов</i>"

    elif field == "client_address":
        prompt += "<i>Минимум 4 символа</i>"

    elif field == "client_phone":
        prompt += "<i>Формат: +7 (xxx) xxx-xx-xx или 8xxxxxxxxxx</i>"

    elif field == "notes":
        prompt += f"<i>Максимум {MAX_NOTES_LENGTH} символов. Для очистки введите '-'</i>"

    elif field == "estimated_completion_date":
        prompt += (
            "<b>🤖 Примеры:</b>\n"
            "• <code>завтра в 15:00</code>\n"
            "• <code>через 3 дня</code>\n"
            "• <code>через неделю</code>\n"
            "• <code>20.10.2025</code>\n\n"
            "<i>Для очистки введите '-'</i>"
        )

    elif field == "prepayment_amount":
        prompt += (
            "<b>Примеры:</b>\n"
            "• <code>2000</code>\n"
            "• <code>1500.50</code>\n\n"
            "<i>Для очистки введите '-' или '0'</i>"
        )

    elif field == "scheduled_time":
        prompt += "<i>Для очистки введите '-'</i>"

    message = callback.message
    if not isinstance(message, Message):
        await callback.answer("Сообщение недоступно", show_alert=True)
        return

    await message.edit_text(
        prompt,
        parse_mode="HTML",
    )

    await message.answer(
        "Для отмены нажмите кнопку ниже:",
        reply_markup=get_cancel_keyboard(),
    )

    await callback.answer()


@router.message(EditOrderStates.enter_value, F.text == "❌ Отмена")
@handle_errors
async def cancel_edit(message: Message, state: FSMContext):
    """Отмена редактирования"""
    data = await state.get_data()
    order_id = data.get("order_id")
    await state.clear()

    if order_id:
        await message.answer(
            "❌ Редактирование отменено",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Можно вернуть к просмотру заявки
        # TODO: показать клавиатуру с заявкой
    else:
        await message.answer("Редактирование отменено")


@router.callback_query(F.data == "cancel_edit")
@handle_errors
async def callback_cancel_edit(callback: CallbackQuery, state: FSMContext):
    """Отмена редактирования через callback"""
    data = await state.get_data()
    order_id = data.get("order_id")
    await state.clear()

    message = callback.message
    if not isinstance(message, Message):
        await callback.answer()
        return

    if order_id:
        await message.edit_text("❌ Редактирование отменено", reply_markup=None)
    else:
        await message.edit_text("Редактирование отменено")

    await callback.answer()


@router.message(EditOrderStates.enter_value, F.text)
@handle_errors
async def process_new_value(message: Message, state: FSMContext, user_role: str, db: Database):
    """
    Обработка нового значения поля.

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя
        db: Database instance (injected)
    """
    data = await state.get_data()
    order_id = data.get("order_id")
    field = data.get("field")

    if not order_id or not field:
        await message.answer("❌ Ошибка: данные не найдены. Начните заново.")
        await state.clear()
        return

    new_value: str | None = (message.text or "").strip()

    # Специальная обработка для очистки поля
    if new_value == "-" and field in ["notes", "scheduled_time", "estimated_completion_date"]:
        new_value = None
    if (new_value == "-" or new_value == "0") and field == "prepayment_amount":
        new_value = None

    # Валидация нового значения
    try:
        new_value = await validate_field_value(field, new_value, message)
        if new_value is False:  # Валидация не прошла (сообщение уже отправлено)
            return
    except ValueError as e:
        await message.answer(
            f"❌ {e!s}\n\nПопробуйте еще раз:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Обновляем заявку в БД
    order = await db.get_order_by_id(order_id)

    if not order:
        await message.answer("❌ Ошибка: заявка не найдена")
        await state.clear()
        return

    # Проверяем права еще раз
    can_edit, error_msg = can_edit_order(order, user_role)
    if not can_edit:
        await message.answer(f"❌ {error_msg}")
        await state.clear()
        return

    # Сохраняем старое значение для лога
    old_value = getattr(order, field, None)

    # Обновляем поле (и ORMDatabase, и Database имеют метод update_order_field)
    await db.update_order_field(order_id, field, new_value)

    # Логируем изменение
    user = message.from_user
    if user:
        await db.add_audit_log(
            user_id=user.id,
            action="EDIT_ORDER",
            details=f"Order #{order_id}: {field} changed from '{old_value}' to '{new_value}'",
        )

    field_name = EDITABLE_FIELDS.get(field, field)

    await message.answer(
        f"✅ <b>Заявка #{order_id} обновлена</b>\n\n"
        f"<b>Поле:</b> {field_name}\n"
        f"<b>Старое значение:</b> {escape_html(str(old_value)) if old_value else 'Не указано'}\n"
        f"<b>Новое значение:</b> {escape_html(str(new_value)) if new_value else 'Не указано'}",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )

    if user:
        log_action(user.id, "EDIT_ORDER", f"Order #{order_id}, field: {field}")

    await state.clear()


async def validate_field_value(field: str, value: str | None, message: Message):
    """
    Валидация значения поля

    Args:
        field: Название поля
        value: Новое значение
        message: Сообщение (для отправки подтверждений)

    Returns:
        Валидированное значение или False если валидация не прошла

    Raises:
        ValueError: Если значение невалидно
    """
    if value is None:
        return None

    # Валидация для каждого типа поля
    if field == "equipment_type":
        from app.core.constants import EquipmentType

        types = EquipmentType.all_types()
        if value not in types:
            raise ValueError(f"Неверный тип техники. Доступные: {', '.join(types)}")
        return value

    elif field == "description":
        if len(value) < 4:
            raise ValueError("Описание слишком короткое (минимум 4 символа)")
        if len(value) > MAX_DESCRIPTION_LENGTH:
            raise ValueError(
                f"Описание слишком длинное (максимум {MAX_DESCRIPTION_LENGTH} символов)"
            )

        # Базовая защита от SQL injection
        suspicious_patterns = [
            r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER)\s+",
            r"--",
            r"/\*.*\*/",
            r"UNION\s+SELECT",
        ]
        for pattern in suspicious_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Описание содержит недопустимые символы")
        return value

    if field == "client_name":
        if len(value) < 5:
            raise ValueError("Имя клиента слишком короткое (минимум 5 символов)")
        if len(value) > 100:
            raise ValueError("Имя клиента слишком длинное (максимум 100 символов)")
        return value

    if field == "client_address":
        if len(value) < 4:
            raise ValueError("Адрес слишком короткий (минимум 4 символа)")
        if len(value) > 200:
            raise ValueError("Адрес слишком длинный (максимум 200 символов)")
        return value

    if field == "client_phone":
        # Валидация телефона (та же логика что при создании заявки)
        from pydantic import BaseModel, Field, field_validator

        class PhoneValidator(BaseModel):
            phone: str = Field(..., min_length=10, max_length=20)

            @field_validator("phone")
            @classmethod
            def validate_phone(cls, v: str) -> str:
                v = v.strip()
                phone_pattern = (
                    r"^(?:\+7|8|7)?[\s\-]?(?:\(?\d{3}\)?[\s\-]?)?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$"
                )
                if not re.match(phone_pattern, v):
                    raise ValueError(
                        "Неверный формат телефона. Используйте +7 (xxx) xxx-xx-xx или 8xxxxxxxxxx"
                    )
                return v

        try:
            validated = PhoneValidator(phone=value)
            return validated.phone
        except ValidationError as e:
            error_msg = e.errors()[0]["msg"]
            raise ValueError(error_msg) from e

    if field == "notes":
        if len(value) > MAX_NOTES_LENGTH:
            raise ValueError(f"Заметки слишком длинные (максимум {MAX_NOTES_LENGTH} символов)")
        return value

    if field == "scheduled_time":
        # Автоопределение даты
        if should_parse_as_date(value):
            parsed_dt, _ = parse_natural_datetime(value, validate=True)

            if parsed_dt:
                validation = validate_parsed_datetime(parsed_dt, value)

                # Успешно распознали дату
                formatted_time = format_datetime_for_storage(parsed_dt, value)
                user_friendly = format_datetime_user_friendly(parsed_dt, value)

                logger.info(f"Автоопределение даты: '{value}' -> '{formatted_time}'")

                confirmation_text = f"✅ <b>Время прибытия распознано:</b>\n\n{user_friendly}"

                if validation.get("warning"):
                    confirmation_text += f"\n\n⚠️ <i>{validation['warning']}</i>"

                await message.answer(confirmation_text, parse_mode="HTML")

                return formatted_time
            else:
                # Не смогли распознать дату - переспрашиваем с примерами
                await message.answer(
                    f"❓ <b>Не удалось распознать дату:</b> {value}\n\n"
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
                # Возвращаем None чтобы пользователь мог ввести заново
                return None

        # Если не распознали как дату - сохраняем как текст
        if len(value) < 3:
            raise ValueError("Время/инструкция слишком короткие (минимум 3 символа)")
        if len(value) > 150:
            raise ValueError("Время/инструкция слишком длинные (максимум 150 символов)")
        return value

    if field == "estimated_completion_date":
        # Автоопределение даты для срока окончания DR
        if should_parse_as_date(value):
            parsed_dt, _ = parse_natural_datetime(value, validate=True)

            if parsed_dt:
                validation = validate_parsed_datetime(parsed_dt, value)

                # Успешно распознали дату
                formatted_date = parsed_dt.strftime("%d.%m.%Y %H:%M")
                user_friendly = format_datetime_user_friendly(parsed_dt, value)

                logger.info(f"Автоопределение срока DR: '{value}' -> '{formatted_date}'")

                confirmation_text = f"✅ <b>Срок окончания распознан:</b>\n\n{user_friendly}"

                if validation.get("warning"):
                    confirmation_text += f"\n\n⚠️ <i>{validation['warning']}</i>"

                await message.answer(confirmation_text, parse_mode="HTML")

                return formatted_date

        # Если не распознали - сохраняем как текст
        return value

    if field == "prepayment_amount":
        # Валидация предоплаты
        try:
            amount = float(value.replace(",", "."))
            if amount < 0:
                raise ValueError("Предоплата не может быть отрицательной")
            if amount > 1000000:
                raise ValueError("Предоплата слишком большая (максимум 1 000 000 ₽)")
            return amount
        except ValueError:
            raise ValueError("Неверный формат суммы. Используйте число, например: 2000 или 1500.50")

    return value
