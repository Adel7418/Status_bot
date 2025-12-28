"""
Обработчики для команды /settings (настройки бота)
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import UserRole
from app.database import get_database
from app.database.orm_database import ORMDatabase
from app.decorators import handle_errors, require_role
from app.keyboards.reply import get_cancel_keyboard, get_main_menu_keyboard
from app.states import SettingsStates
from app.utils import get_city_key
from app.utils.helpers import log_action

logger = logging.getLogger(__name__)

router = Router(name="settings")


@router.message(Command("settings"))
@require_role(UserRole.ADMIN)
@handle_errors
async def cmd_settings(message: Message, state: FSMContext, user_role: str):
    """
    Команда /settings - главное меню настроек

    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Роль пользователя (инжектируется middleware)
    """
    # Получаем текущие настройки
    city_key = get_city_key()
    db = get_database()

    if not isinstance(db, ORMDatabase):
        await message.answer(
            "❌ Настройки доступны только при использовании ORM режима.\n"
            "Установите USE_ORM=true в .env файле."
        )
        return

    await db.connect()
    try:
        settings = await db.get_city_settings(city_key)
        current_threshold = settings.profit_rate_threshold if settings else 7000.0
    finally:
        await db.disconnect()

    # Формируем меню настроек
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Настройка процентной ставки",
                    callback_data="settings:profit_rate",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔧 Ставки по типам техники",
                    callback_data="settings:specialization_rates",
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ Текущие настройки", callback_data="settings:show_current"
                )
            ],
        ]
    )

    await message.answer(
        f"⚙️ <b>Панель настроек</b>\n\n"
        f"🏙 Город: <code>{city_key}</code>\n"
        f"💰 Порог процентной ставки: <b>{current_threshold:.2f} ₽</b>\n\n"
        f"Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    log_action(message.from_user.id, "OPEN_SETTINGS", f"City: {city_key}")


@router.callback_query(F.data == "settings:show_current")
@require_role(UserRole.ADMIN)
@handle_errors
async def callback_show_current_settings(callback: CallbackQuery, user_role: str):
    """
    Показать текущие настройки

    Args:
        callback: Callback query
        user_role: Роль пользователя (инжектируется middleware)
    """
    city_key = get_city_key()
    db = get_database()

    if not isinstance(db, ORMDatabase):
        await callback.answer("❌ Настройки недоступны в этом режиме", show_alert=True)
        return

    await db.connect()
    try:
        settings = await db.get_city_settings(city_key)
        current_threshold = settings.profit_rate_threshold if settings else 7000.0
    finally:
        await db.disconnect()

    info_text = (
        f"ℹ️ <b>Текущие настройки</b>\n\n"
        f"🏙 <b>Город:</b> <code>{city_key}</code>\n"
        f"💰 <b>Порог процентной ставки:</b> {current_threshold:.2f} ₽\n\n"
        f"📊 <b>Как это работает:</b>\n"
        f"• Если чистая прибыль ≥ {current_threshold:.2f} ₽ → ставка 50/50\n"
        f"• Если чистая прибыль < {current_threshold:.2f} ₽ → ставка 40/60\n\n"
        f"💡 <i>Чтобы изменить порог, нажмите кнопку ниже</i>"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить порог", callback_data="settings:profit_rate"
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="settings:back")],
        ]
    )

    await callback.message.edit_text(info_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "settings:profit_rate")
@require_role(UserRole.ADMIN)
@handle_errors
async def callback_set_profit_rate(callback: CallbackQuery, state: FSMContext, user_role: str):
    """
    Начало процесса настройки порога процентной ставки

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя (инжектируется middleware)
    """
    city_key = get_city_key()
    db = get_database()

    if not isinstance(db, ORMDatabase):
        await callback.answer("❌ Настройки недоступны в этом режиме", show_alert=True)
        return

    await db.connect()
    try:
        settings = await db.get_city_settings(city_key)
        current_threshold = settings.profit_rate_threshold if settings else 7000.0
    finally:
        await db.disconnect()

    await state.set_state(SettingsStates.enter_profit_rate_threshold)
    await state.update_data(city_key=city_key)

    await callback.message.answer(
        f"💰 <b>Настройка порога процентной ставки</b>\n\n"
        f"Текущий порог: <b>{current_threshold:.2f} ₽</b>\n\n"
        f"Введите новое значение порога в рублях.\n"
        f"Например: <code>8000</code> или <code>8000.50</code>\n\n"
        f"📊 <b>Как это работает:</b>\n"
        f"• Если мастер закрыл заявку на сумму ≥ порога → процентовка 50/50\n"
        f"• Если сумма < порога → процентовка 40/60\n\n"
        f"💡 <i>Для отмены нажмите кнопку ниже</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )

    await callback.answer()
    log_action(callback.from_user.id, "START_EDIT_PROFIT_RATE", f"City: {city_key}")


@router.message(SettingsStates.enter_profit_rate_threshold, ~F.text.startswith("/"))
@handle_errors
async def process_profit_rate_threshold(message: Message, state: FSMContext):
    """
    Обработка ввода нового порога процентной ставки

    Args:
        message: Сообщение
        state: FSM контекст
    """
    # Проверяем кнопку отмены
    if message.text == "❌ Отмена":
        await state.clear()
        await message.reply(
            "❌ Настройка порога отменена.",
            reply_markup=get_main_menu_keyboard([UserRole.ADMIN]),
        )
        return

    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.reply("❌ Пожалуйста, отправьте текстовое сообщение с числом.")
        return

    # Нормализация ввода
    raw_text = message.text.strip()
    normalized = (
        raw_text.replace("\u00a0", "")
        .replace(" ", "")
        .replace("₽", "")
        .replace("р.", "")
        .replace("р", "")
        .replace("RUB", "")
        .replace("rub", "")
    )

    # Заменяем запятую на точку
    normalized = normalized.replace(",", ".")

    # Проверяем корректность числа
    try:
        threshold = float(normalized)
        if threshold < 0:
            await message.reply("❌ Порог не может быть отрицательным.\nПопробуйте еще раз:")
            return
    except ValueError:
        await message.reply(
            "❌ Неверный формат.\n"
            "Пожалуйста, введите число (например: 8000 или 8000.50):"
        )
        return

    # Получаем city_key из состояния
    data = await state.get_data()
    city_key = data.get("city_key", get_city_key())

    # Обновляем настройки в БД
    db = get_database()
    if not isinstance(db, ORMDatabase):
        await message.reply("❌ Ошибка: ORM не доступна")
        await state.clear()
        return

    await db.connect()
    try:
        await db.create_or_update_city_settings(
            city_key=city_key, profit_rate_threshold=threshold
        )

        await message.answer(
            f"✅ <b>Порог процентной ставки обновлен!</b>\n\n"
            f"🏙 Город: <code>{city_key}</code>\n"
            f"💰 Новый порог: <b>{threshold:.2f} ₽</b>\n\n"
            f"📊 <b>Теперь:</b>\n"
            f"• Если чистая прибыль ≥ {threshold:.2f} ₽ → ставка 50/50\n"
            f"• Если чистая прибыль < {threshold:.2f} ₽ → ставка 40/60",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard([UserRole.ADMIN]),
        )

        log_action(
            message.from_user.id,
            "UPDATE_PROFIT_RATE",
            f"City: {city_key}, New threshold: {threshold}",
        )

    except Exception as e:
        logger.error(f"Ошибка при обновлении порога: {e}")
        await message.reply(
            f"❌ Ошибка при сохранении настроек: {e}",
            reply_markup=get_main_menu_keyboard([UserRole.ADMIN]),
        )
    finally:
        await db.disconnect()
        await state.clear()


@router.callback_query(F.data == "settings:back")
@require_role(UserRole.ADMIN)
@handle_errors
async def callback_settings_back(callback: CallbackQuery, user_role: str):
    """
    Возврат в главное меню настроек

    Args:
        callback: Callback query
        user_role: Роль пользователя (инжектируется middleware)
    """
    # Повторно вызываем главное меню настроек
    city_key = get_city_key()
    db = get_database()

    if not isinstance(db, ORMDatabase):
        await callback.answer("❌ Настройки недоступны в этом режиме", show_alert=True)
        return

    await db.connect()
    try:
        settings = await db.get_city_settings(city_key)
        current_threshold = settings.profit_rate_threshold if settings else 7000.0
    finally:
        await db.disconnect()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Настройка процентной ставки",
                    callback_data="settings:profit_rate",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔧 Ставки по типам техники",
                    callback_data="settings:specialization_rates",
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ Текущие настройки", callback_data="settings:show_current"
                )
            ],
        ]
    )

    await callback.message.edit_text(
        f"⚙️ <b>Панель настроек</b>\n\n"
        f"🏙 Город: <code>{city_key}</code>\n"
        f"💰 Порог процентной ставки: <b>{current_threshold:.2f} ₽</b>\n\n"
        f"Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    await callback.answer()


# ============== УПРАВЛЕНИЕ СТАВКАМИ ПО ТИПАМ ТЕХНИКИ ==============


@router.callback_query(F.data == "settings:specialization_rates")
@require_role(UserRole.ADMIN)
@handle_errors
async def callback_specialization_rates_menu(callback: CallbackQuery, user_role: str):
    """
    Меню управления ставками по типам техники

    Args:
        callback: Callback query
        user_role: Роль пользователя (инжектируется middleware)
    """
    db = get_database()

    if not isinstance(db, ORMDatabase):
        await callback.answer("❌ Функция недоступна в этом режиме", show_alert=True)
        return

    await db.connect()
    try:
        rates = await db.get_all_specialization_rates()

        # Формируем список ставок
        if rates:
            rates_text = ""
            for rate in rates:
                rates_text += (
                    f"\n<b>{rate.specialization_name}</b>\n"
                    f"  └ Мастер: {rate.master_percentage}% | "
                    f"Компания: {rate.company_percentage}%\n"
                )
        else:
            rates_text = "\n<i>Пока нет настроенных ставок</i>"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Добавить ставку", callback_data="settings:add_rate"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✏️ Редактировать ставку", callback_data="settings:edit_rate_list"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑 Удалить ставку", callback_data="settings:delete_rate_list"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="settings:back")],
            ]
        )

        await callback.message.edit_text(
            f"🔧 <b>Ставки по типам техники</b>\n"
            f"{rates_text}\n\n"
            f"Выберите действие:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data == "settings:add_rate")
@require_role(UserRole.ADMIN)
@handle_errors
async def callback_add_specialization_rate(callback: CallbackQuery, state: FSMContext, user_role: str):
    """
    Начало процесса добавления ставки

    Args:
        callback: Callback query
        state: FSM контекст
        user_role: Роль пользователя (инжектируется middleware)
    """
    await state.set_state(SettingsStates.enter_equipment_type)

    await callback.message.answer(
        "🔧 <b>Добавление новой ставки</b>\n\n"
        "Введите <b>тип техники</b>.\n"
        "Например: <code>Стиральные машины</code>, <code>Кондиционеры</code>\n\n"
        "💡 <i>Совет:</i> Используйте общее название, система будет искать совпадения автоматически",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )

    await callback.answer()
    log_action(callback.from_user.id, "START_ADD_SPEC_RATE", "")


@router.message(SettingsStates.enter_equipment_type, ~F.text.startswith("/"))
@handle_errors
async def process_equipment_type(message: Message, state: FSMContext):
    """
    Обработка ввода типа техники

    Args:
        message: Сообщение
        state: FSM контекст
    """
    # Проверяем кнопку отмены
    if message.text == "❌ Отмена":
        await state.clear()
        await message.reply(
            "❌ Добавление ставки отменено.",
            reply_markup=get_main_menu_keyboard([UserRole.ADMIN]),
        )
        return

    if not message.text:
        await message.reply("❌ Пожалуйста, отправьте текстовое сообщение.")
        return

    equipment_type = message.text.strip()

    # Проверяем, не существует ли уже такая ставка
    db = get_database()
    if not isinstance(db, ORMDatabase):
        await message.reply("❌ Ошибка: ORM недоступна")
        await state.clear()
        return

    await db.connect()
    try:
        existing_rate = await db.get_specialization_rate(equipment_type)
        if existing_rate:
            await message.reply(
                f"⚠️ Ставка для типа '<b>{equipment_type}</b>' уже существует:\n"
                f"Мастер: {existing_rate[0]}% | Компания: {existing_rate[1]}%\n\n"
                f"Используйте функцию редактирования для изменения.",
                parse_mode="HTML",
            )
            await state.clear()
            return
    finally:
        await db.disconnect()

    # Сохраняем тип техники
    await state.update_data(equipment_type=equipment_type)
    await state.set_state(SettingsStates.enter_master_percentage)

    await message.answer(
        f"✅ Тип техники: <b>{equipment_type}</b>\n\n"
        f"Теперь введите <b>процент мастера</b>.\n"
        f"Например: <code>50</code> или <code>60</code>\n\n"
        f"💡 Процент компании будет рассчитан автоматически (100 - процент мастера)",
        parse_mode="HTML",
    )


@router.message(SettingsStates.enter_master_percentage, ~F.text.startswith("/"))
@handle_errors
async def process_master_percentage(message: Message, state: FSMContext):
    """
    Обработка ввода процента мастера

    Args:
        message: Сообщение
        state: FSM контекст
    """
    # Проверяем кнопку отмены
    if message.text == "❌ Отмена":
        await state.clear()
        await message.reply(
            "❌ Добавление ставки отменено.",
            reply_markup=get_main_menu_keyboard([UserRole.ADMIN]),
        )
        return

    if not message.text:
        await message.reply("❌ Пожалуйста, отправьте текстовое сообщение с числом.")
        return

    # Парсим процент
    try:
        master_percentage = float(message.text.strip().replace(",", ".").replace("%", ""))
        if master_percentage < 0 or master_percentage > 100:
            await message.reply("❌ Процент должен быть от 0 до 100.\nПопробуйте еще раз:")
            return
    except ValueError:
        await message.reply(
            "❌ Неверный формат.\nПожалуйста, введите число (например: 50):"
        )
        return

    # Рассчитываем процент компании
    company_percentage = 100 - master_percentage

    # Получаем данные из состояния
    data = await state.get_data()
    equipment_type = data.get("equipment_type")

    # Сохраняем в БД
    db = get_database()
    if not isinstance(db, ORMDatabase):
        await message.reply("❌ Ошибка: ORM недоступна")
        await state.clear()
        return

    await db.connect()
    try:
        from app.database.orm_models import SpecializationRate
        from app.utils.helpers import get_now

        new_rate = SpecializationRate(
            specialization_name=equipment_type,
            master_percentage=master_percentage,
            company_percentage=company_percentage,
            is_default=False,
            created_at=get_now(),
            updated_at=get_now(),
        )

        async with db.get_session() as session:
            session.add(new_rate)
            await session.commit()

        await message.answer(
            f"✅ <b>Ставка успешно добавлена!</b>\n\n"
            f"🔧 <b>Тип техники:</b> {equipment_type}\n"
            f"📊 <b>Распределение:</b>\n"
            f"  └ Мастер: {master_percentage}%\n"
            f"  └ Компания: {company_percentage}%",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard([UserRole.ADMIN]),
        )

        log_action(
            message.from_user.id,
            "ADD_SPEC_RATE",
            f"Type: {equipment_type}, Master: {master_percentage}%",
        )

    except Exception as e:
        logger.error(f"Ошибка при добавлении ставки: {e}")
        await message.reply(
            f"❌ Ошибка при сохранении ставки: {e}",
            reply_markup=get_main_menu_keyboard([UserRole.ADMIN]),
        )
    finally:
        await db.disconnect()
        await state.clear()


@router.callback_query(F.data == "settings:delete_rate_list")
@require_role(UserRole.ADMIN)
@handle_errors
async def callback_delete_rate_list(callback: CallbackQuery, user_role: str):
    """
    Список ставок для удаления

    Args:
        callback: Callback query
        user_role: Роль пользователя (инжектируется middleware)
    """
    db = get_database()

    if not isinstance(db, ORMDatabase):
        await callback.answer("❌ Функция недоступна в этом режиме", show_alert=True)
        return

    await db.connect()
    try:
        rates = await db.get_all_specialization_rates()

        if not rates:
            await callback.answer("❌ Нет ставок для удаления", show_alert=True)
            return

        # Формируем кнопки для каждой ставки
        buttons = []
        for rate in rates:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"🗑 {rate.specialization_name} ({rate.master_percentage}/{rate.company_percentage})",
                        callback_data=f"settings:delete_rate:{rate.id}",
                    )
                ]
            )

        buttons.append(
            [InlineKeyboardButton(text="🔙 Назад", callback_data="settings:specialization_rates")]
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(
            "🗑 <b>Удаление ставки</b>\n\nВыберите ставку для удаления:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    finally:
        await db.disconnect()

    await callback.answer()


@router.callback_query(F.data.startswith("settings:delete_rate:"))
@require_role(UserRole.ADMIN)
@handle_errors
async def callback_delete_rate_confirm(callback: CallbackQuery, user_role: str):
    """
    Подтверждение удаления ставки

    Args:
        callback: Callback query
        user_role: Роль пользователя (инжектируется middleware)
    """
    if not callback.data:
        return

    rate_id = int(callback.data.split(":")[2])

    db = get_database()
    if not isinstance(db, ORMDatabase):
        await callback.answer("❌ Функция недоступна в этом режиме", show_alert=True)
        return

    await db.connect()
    try:
        success = await db.delete_specialization_rate(rate_id)

        if success:
            await callback.answer("✅ Ставка успешно удалена!", show_alert=True)
            log_action(callback.from_user.id, "DELETE_SPEC_RATE", f"Rate ID: {rate_id}")

            # Возвращаемся к списку ставок
            await callback_specialization_rates_menu(callback)
        else:
            await callback.answer("❌ Ошибка при удалении ставки", show_alert=True)
    finally:
        await db.disconnect()
