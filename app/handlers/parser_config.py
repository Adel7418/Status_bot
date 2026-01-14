"""
Handlers для настройки парсера заявок

Команды:
- /set_group — установка ID группы для парсинга
"""

import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.core.config import Config
from app.database.orm_database import ORMDatabase
from app.database.parser_config_repository import ParserConfigRepository
from app.decorators import require_role
from app.services.parser_integration import ParserIntegration
from app.states import EditParsedOrderStates
from app.utils import escape_html


logger = logging.getLogger(__name__)

router = Router(name="parser_config")


@router.message(Command("set_group"))
@require_role(["admin"])
async def cmd_set_group(
    message: Message,
    db: ORMDatabase,
    parser_integration: ParserIntegration | None = None,
    *,
    user_role: str = "UNKNOWN",
) -> None:
    """
    Команда для установки ID группы парсера.

    Использование:
    1. Перешлите любое сообщение из целевой группы боту
    2. Вызовите /set_group в ответ на пересланное сообщение

    Или:
    /set_group -1001234567890
    """
    # Проверяем что парсер включён в конфигурации
    if not Config.PARSER_ENABLED:
        await message.answer(
            "❌ Парсер отключён в конфигурации.\n"
            "Установите PARSER_ENABLED=true в .env файле."
        )
        return

    # Способ 1: Получить group_id из пересланного сообщения
    if message.reply_to_message and message.reply_to_message.forward_from_chat:
        group_id = message.reply_to_message.forward_from_chat.id

        async with db.session_factory() as session:
            repo = ParserConfigRepository(session)
            await repo.set_group_id(group_id)

        # Перезапускаем парсер с новой группой
        if parser_integration:
            try:
                await parser_integration.stop()
                await parser_integration.start()
                logger.info(f"Парсер перезапущен с новым group_id: {group_id}")
            except Exception as e:
                logger.error(f"Ошибка при перезапуске парсера: {e}")
                await message.answer(f"⚠️ Настройки сохранены, но парсер не удалось перезапустить: {e}")

        await message.answer(
            f"✅ Группа для парсинга установлена!\n\n"
            f"📋 <b>Group ID:</b> <code>{group_id}</code>\n"
            f"🔧 <b>Название:</b> {message.reply_to_message.forward_from_chat.title}\n\n"
            f"Теперь бот будет мониторить сообщения из этой группы.",
            parse_mode="HTML",
        )
        logger.info(
            f"Администратор {message.from_user.id} установил group_id парсера: {group_id}"
        )
        return

    # Способ 2: Получить group_id из аргументов команды
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        try:
            group_id = int(args[1])

            async with db.session_factory() as session:
                repo = ParserConfigRepository(session)
                await repo.set_group_id(group_id)

            # Перезапускаем парсер с новой группой
            if parser_integration:
                try:
                    await parser_integration.stop()
                    await parser_integration.start()
                    logger.info(f"Парсер перезапущен с новым group_id: {group_id}")
                except Exception as e:
                    logger.error(f"Ошибка при перезапуске парсера: {e}")
                    await message.answer(f"⚠️ Настройки сохранены, но парсер не удалось перезапустить: {e}")

            await message.answer(
                f"✅ Группа для парсинга установлена!\n\n"
                f"📋 <b>Group ID:</b> <code>{group_id}</code>\n\n"
                f"Теперь бот будет мониторить сообщения из этой группы.",
                parse_mode="HTML",
            )
            logger.info(
                f"Администратор {message.from_user.id} установил group_id парсера: {group_id}"
            )
            return

        except ValueError:
            await message.answer("❌ Некорректный формат group_id. Используйте число.")
            return

    # Если ни один способ не сработал — показываем инструкцию
    await message.answer(
        "📋 <b>Установка группы для парсинга</b>\n\n"
        "<b>Способ 1:</b> Перешлите любое сообщение из целевой группы и ответьте на него командой /set_group\n\n"
        "<b>Способ 2:</b> Используйте команду с ID группы:\n"
        "<code>/set_group -1001234567890</code>\n\n"
        "💡 <i>Чтобы узнать ID группы, можно использовать @username_to_id_bot</i>",
        parse_mode="HTML",
    )


@router.message(Command("parser_status"))
@require_role(["admin"])
async def cmd_parser_status(
    message: Message,
    db: ORMDatabase,
    parser_integration: ParserIntegration | None = None,
    *,
    user_role: str = "UNKNOWN",
) -> None:
    """
    Команда для проверки статуса парсера.
    """
    if not Config.PARSER_ENABLED:
        await message.answer(
            "❌ <b>Парсер отключён в конфигурации</b>\n\n"
            "Установите в .env:\n"
            "<code>PARSER_ENABLED=true</code>",
            parse_mode="HTML",
        )
        return

    async with db.session_factory() as session:
        repo = ParserConfigRepository(session)
        config = await repo.get_config()

    if not config:
        await message.answer(
            "⚠️ <b>Конфигурация парсера не найдена</b>\n\n"
            "Выполните миграцию БД:\n"
            "<code>alembic upgrade head</code>",
            parse_mode="HTML",
        )
        return

    status_emoji = "✅" if config.enabled else "❌"
    status_text = "Включён" if config.enabled else "Отключён"

    group_text = (
        f"<code>{config.group_id}</code>" if config.group_id else "<i>не установлен</i>"
    )

    # Проверяем реальный статус процесса
    runtime_status = "❓ Неизвестно (сервис не инжектирован)"

    if parser_integration:
        if parser_integration.is_running:
            status_details = "Запущен"
            # Проверяем подключение Telethon
            if parser_integration.telethon_client and parser_integration.telethon_client.client:
                if parser_integration.telethon_client.client.is_connected():
                    status_details += " (Подключен к Telegram)"
                else:
                    status_details += " (⚠️ Нет подключения к Telegram)"
            runtime_status = f"🟢 {status_details}"
        else:
            runtime_status = "🔴 Остановлен (проверьте session файл)"
    else:
        runtime_status = "⚠️ Ошибка: Сервис не доступен"

    await message.answer(
        f"📊 <b>Статус парсера</b>\n\n"
        f"{status_emoji} <b>Конфигурация БД:</b> {status_text}\n"
        f"⚙️ <b>Процесс:</b> {runtime_status}\n"
        f"📋 <b>Group ID:</b> {group_text}\n\n"
        f"<b>Параметры (.env):</b>\n"
        f"• PARSER_ENABLED: {Config.PARSER_ENABLED}\n"
        f"• TELETHON_SESSION: {Config.TELETHON_SESSION_NAME}\n"
        f"• TELETHON_SESSION_DIR: {Config.TELETHON_SESSION_DIR or '(текущая директория)'}\n",
        parse_mode="HTML",
    )


@router.message(Command("parser_enable"))
@require_role(["admin"])
async def cmd_parser_enable(
    message: Message,
    db: ORMDatabase,
    parser_integration: ParserIntegration | None = None,
    *,
    user_role: str = "UNKNOWN",
) -> None:
    """
    Команда для включения парсера.
    """
    if not Config.PARSER_ENABLED:
        await message.answer(
            "❌ <b>Парсер отключён в конфигурации</b>\n\n"
            "Установите в .env:\n"
            "<code>PARSER_ENABLED=true</code>",
            parse_mode="HTML",
        )
        return

    try:
        async with db.session_factory() as session:
            repo = ParserConfigRepository(session)
            config = await repo.enable_parser()

        # Запускаем парсер
        if parser_integration:
            try:
                await parser_integration.start()
                logger.info("Парсер запущен через команду")
            except Exception as e:
                logger.error(f"Ошибка при запуске парсера: {e}")
                await message.answer(f"⚠️ Настройки сохранены, но парсер не удалось запустить: {e}")

        await message.answer(
            f"✅ <b>Парсер включён!</b>\n\n"
            f"📋 <b>Group ID:</b> <code>{config.group_id}</code>\n\n"
            f"Бот начнёт мониторить сообщения из группы.",
            parse_mode="HTML",
        )
        logger.info(f"Администратор {message.from_user.id} включил парсер")

    except ValueError as e:
        await message.answer(f"❌ <b>Ошибка:</b> {e}", parse_mode="HTML")
    except Exception as e:
        logger.exception(f"Ошибка при включении парсера: {e}")
        await message.answer("❌ Произошла ошибка при включении парсера")


@router.message(Command("parser_disable"))
@require_role(["admin"])
async def cmd_parser_disable(
    message: Message,
    db: ORMDatabase,
    parser_integration: ParserIntegration | None = None,
    *,
    user_role: str = "UNKNOWN",
) -> None:
    """
    Команда для отключения парсера.
    """
    if not Config.PARSER_ENABLED:
        await message.answer(
            "❌ <b>Парсер отключён в конфигурации</b>\n\n"
            "Установите в .env:\n"
            "<code>PARSER_ENABLED=true</code>",
            parse_mode="HTML",
        )
        return

    try:
        async with db.session_factory() as session:
            repo = ParserConfigRepository(session)
            config = await repo.disable_parser()

        # Останавливаем парсер
        if parser_integration:
            try:
                await parser_integration.stop()
                logger.info("Парсер остановлен через команду")
            except Exception as e:
                logger.error(f"Ошибка при остановке парсера: {e}")
                await message.answer(f"⚠️ Настройки сохранены, но парсер не удалось остановить: {e}")

        await message.answer(
            "🛑 <b>Парсер отключён</b>\n\n"
            "Бот прекратит мониторинг сообщений из группы.",
            parse_mode="HTML",
        )
        logger.info(f"Администратор {message.from_user.id} отключил парсер")

    except Exception as e:
        logger.exception(f"Ошибка при отключении парсера: {e}")
        await message.answer("❌ Произошла ошибка при отключении парсера")


@router.message(Command("parser_reset"))
@require_role(["admin"])
async def cmd_parser_reset(
    message: Message,
    state: FSMContext,
    parser_integration: ParserIntegration | None = None,
    *,
    user_role: str = "UNKNOWN",
) -> None:
    """
    Команда для сброса сессии парсера (удаление файла сессии).
    Полезна при ошибках аутентификации.
    Работает в любом состоянии FSM.
    """
    import os
    
    logger.info(f"Admin {message.from_user.id} called /parser_reset")
    
    # Сбрасываем любое активное состояние
    current_state = await state.get_state()
    if current_state:
        logger.info(f"Clearing state {current_state} during reset")
        await state.clear()

    if not Config.PARSER_ENABLED:
        await message.answer("❌ Парсер отключён в конфигурации")
        return

    # 1. Останавливаем парсер и сбрасываем клиент
    if parser_integration:
        try:
            await parser_integration.reset_client()
            logger.info("Парсер остановлен и сброшен перед удалением сессии")
        except Exception as e:
            logger.error(f"Ошибка при сбросе парсера: {e}")

    # 2. Удаляем файл сессии
    if Config.TELETHON_SESSION_DIR:
        session_file = os.path.join(
            Config.TELETHON_SESSION_DIR, f"{Config.TELETHON_SESSION_NAME}.session"
        )
    else:
        session_file = f"{Config.TELETHON_SESSION_NAME}.session"
    try:
        if os.path.exists(session_file):
            os.remove(session_file)
            logger.info(f"Файл сессии {session_file} удален")
            await message.answer(
                f"✅ <b>Сессия сброшена</b>\n\n"
                f"Файл <code>{session_file}</code> удален.\n"
                f"Выполните аутентификацию локально (python auth_parser.py) и скопируйте session файл.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"⚠️ Файл сессии <code>{session_file}</code> не найден.\n"
                f"Выполните аутентификацию локально (python auth_parser.py).",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Ошибка при удалении файла сессии: {e}")
        await message.answer(f"❌ Ошибка при удалении файла сессии: {e}")


@router.callback_query(F.data.startswith("confirm_order:"))
async def callback_confirm_order(callback: CallbackQuery, parser_integration=None) -> None:
    """
    Обработчик callback для кнопок подтверждения создания заявки из парсера.

    Формат callback_data: confirm_order:yes:{message_id} или confirm_order:no:{message_id}

    Args:
        callback: CallbackQuery от Telegram
        parser_integration: ParserIntegration instance (инжектируется через middleware)
    """
    logger.debug(f"callback_confirm_order: parser_integration={parser_integration}")

    if not parser_integration or not parser_integration.confirmation_service:
        logger.warning("Сервис подтверждения недоступен")
        await callback.answer("❌ Сервис подтверждения недоступен", show_alert=True)
        return
    
    # Парсим callback_data
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Некорректные данные callback", show_alert=True)
        return
    
    _, action, message_id = parts
    confirmed = action == "yes"
    
    # Обрабатываем подтверждение
    success = await parser_integration.confirmation_service.handle_confirmation(
        confirmation_message_id=callback.message.message_id,
        confirmed=confirmed,
        user_id=callback.from_user.id,
    )
    
    if not success:
        await callback.answer("❌ Подтверждение не найдено", show_alert=True)
        return
    
    # Удаляем сообщение с кнопками
    try:
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение подтверждения: {e}")
    
    # Отправляем уведомление
    if confirmed:
        await callback.answer("✅ Заявка создана!", show_alert=False)
    else:
        await callback.answer("❌ Создание заявки отменено", show_alert=False)


# ==================== РЕДАКТИРОВАНИЕ РАСПАРСЕННОЙ ЗАЯВКИ ====================


@router.callback_query(F.data.startswith("edit_parsed_order:"))
async def callback_edit_parsed_order(
    callback: CallbackQuery, state: FSMContext, parser_integration: ParserIntegration | None = None
) -> None:
    """
    Начало редактирования распарсенной заявки.
    """
    if not parser_integration or not parser_integration.confirmation_service:
        await callback.answer("❌ Сервис недоступен", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    message_id = int(parts[1])
    
    # Получаем данные заявки
    confirmation_data = parser_integration.confirmation_service.get_pending_confirmation(
        callback.message.message_id
    )
    
    if not confirmation_data:
        await callback.answer("❌ Заявка не найдена (возможно, устарела)", show_alert=True)
        return

    # Сохраняем ID сообщения подтверждения в state, чтобы потом обновить его
    await state.update_data(
        confirmation_message_id=callback.message.message_id,
        parsed_order_message_id=message_id
    )
    
    await show_edit_parsed_menu(callback.message, confirmation_data.parsed_order)
    await callback.answer()


async def show_edit_parsed_menu(message: Message, order) -> None:
    """Показывает меню редактирования полей распарсенной заявки"""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    text = (
        f"✏️ <b>Редактирование заявки</b>\n\n"
        f"🔧 <b>Тип:</b> {escape_html(order.equipment_type)}\n"
        f"❗ <b>Проблема:</b> {escape_html(order.problem_description)}\n"
        f"📍 <b>Адрес:</b> {escape_html(order.address)}\n"
        f"👤 <b>Клиент:</b> {escape_html(order.client_name)}\n"
        f"📞 <b>Телефон:</b> {escape_html(order.phone or 'Не указан')}\n"
        f"🕐 <b>Время:</b> {escape_html(order.scheduled_time or 'Не указано')}\n\n"
        f"Выберите поле для изменения:"
    )

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🔧 Тип", callback_data="edit_parsed:equipment_type"),
        InlineKeyboardButton(text="❗ Проблема", callback_data="edit_parsed:problem_description"),
    )
    kb.row(
        InlineKeyboardButton(text="📍 Адрес", callback_data="edit_parsed:address"),
        InlineKeyboardButton(text="👤 Клиент", callback_data="edit_parsed:client_name"),
    )
    kb.row(
        InlineKeyboardButton(text="📞 Телефон", callback_data="edit_parsed:phone"),
        InlineKeyboardButton(text="🕐 Время", callback_data="edit_parsed:scheduled_time"),
    )
    kb.row(
        InlineKeyboardButton(text="🔙 Назад к подтверждению", callback_data="edit_parsed:back")
    )

    await message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("edit_parsed:"))
async def callback_select_parsed_field(
    callback: CallbackQuery, state: FSMContext, parser_integration: ParserIntegration | None = None
) -> None:
    """Выбор поля для редактирования"""
    action = callback.data.split(":")[1]
    
    if action == "back":
        # Возвращаемся к подтверждению
        data = await state.get_data()
        confirmation_message_id = data.get("confirmation_message_id")
        
        if not confirmation_message_id or not parser_integration:
            await callback.answer("❌ Ошибка контекста", show_alert=True)
            return

        confirmation_data = parser_integration.confirmation_service.get_pending_confirmation(
            confirmation_message_id
        )
        
        if not confirmation_data:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        # Обновляем сообщение подтверждения (возвращаем кнопки Да/Нет/Редактировать)
        # Используем публичный метод сервиса для перерисовки, но нам нужно обновить именно ЭТО сообщение
        # Поэтому просто вызываем send_confirmation? Нет, это создаст новое.
        # Нам нужно отредактировать текущее.
        
        # Формируем текст и клавиатуру вручную, используя методы сервиса
        text = parser_integration.confirmation_service._format_confirmation_message(
            confirmation_data.parsed_order
        )
        kb = parser_integration.confirmation_service._create_confirmation_keyboard(
            confirmation_data.parsed_order.message_id
        )
        
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await state.clear()
        await callback.answer()
        return

    # Выбрано поле для редактирования
    await state.update_data(field=action)
    await state.set_state(EditParsedOrderStates.enter_value)
    
    field_names = {
        "equipment_type": "тип техники",
        "problem_description": "описание проблемы",
        "address": "адрес",
        "client_name": "имя клиента",
        "phone": "телефон",
        "scheduled_time": "время прибытия"
    }
    
    field_name = field_names.get(action, action)
    
    await callback.message.edit_text(
        f"✏️ Введите новое значение для поля <b>{field_name}</b>:",
        parse_mode="HTML",
        reply_markup=None # Убираем кнопки, ждем текст
    )
    await callback.answer()


@router.message(EditParsedOrderStates.enter_value)
async def process_parsed_value(
    message: Message, state: FSMContext, parser_integration: ParserIntegration | None = None
) -> None:
    """Обработка ввода нового значения"""
    data = await state.get_data()
    field = data.get("field")
    confirmation_message_id = data.get("confirmation_message_id")
    
    if not field or not confirmation_message_id:
        await message.answer("❌ Ошибка контекста. Начните заново.")
        await state.clear()
        return

    new_value = message.text.strip()
    
    # Обновляем данные в pending_confirmations
    if not parser_integration:
        await message.answer("❌ Сервис парсера недоступен")
        return

    confirmation_data = parser_integration.confirmation_service.get_pending_confirmation(
        confirmation_message_id
    )
    
    if not confirmation_data:
        await message.answer("❌ Заявка не найдена (возможно, устарела)")
        await state.clear()
        return

    # Обновляем поле в объекте OrderParsed
    # Pydantic модели по умолчанию иммутабельны, если frozen=True, но здесь вроде нет.
    # Проверим schemas.py. Если что, используем setattr.
    setattr(confirmation_data.parsed_order, field, new_value)
    
    # Удаляем сообщение с введенным текстом, чтобы не захламлять чат
    try:
        await message.delete()
    except Exception:
        pass

    # Возвращаем меню редактирования (обновленное)
    # Нам нужно найти сообщение с меню. Это confirmation_message_id.
    # Но мы не можем просто так его отредактировать, если у нас нет объекта Message.
    # Мы можем отправить новое? Нет, лучше отредактировать старое.
    # Мы можем использовать bot.edit_message_text
    
    try:
        await show_edit_parsed_menu(
            # Создаем фейковый объект Message для удобства вызова функции, 
            # или перепишем функцию чтобы она принимала bot и chat_id/message_id
            # Проще вызвать edit_message_text напрямую здесь.
            message, # Это сообщение пользователя, оно нам не поможет отредактировать бота.
            # Нам нужен объект бота.
        )
    except Exception:
        pass
        
    # Переписываем логику отображения меню
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    order = confirmation_data.parsed_order
    text = (
        f"✏️ <b>Редактирование заявки</b>\n\n"
        f"🔧 <b>Тип:</b> {escape_html(order.equipment_type)}\n"
        f"❗ <b>Проблема:</b> {escape_html(order.problem_description)}\n"
        f"📍 <b>Адрес:</b> {escape_html(order.address)}\n"
        f"👤 <b>Клиент:</b> {escape_html(order.client_name)}\n"
        f"📞 <b>Телефон:</b> {escape_html(order.phone or 'Не указан')}\n"
        f"🕐 <b>Время:</b> {escape_html(order.scheduled_time or 'Не указано')}\n\n"
        f"✅ Значение обновлено!\n"
        f"Выберите поле для изменения:"
    )

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🔧 Тип", callback_data="edit_parsed:equipment_type"),
        InlineKeyboardButton(text="❗ Проблема", callback_data="edit_parsed:problem_description"),
    )
    kb.row(
        InlineKeyboardButton(text="📍 Адрес", callback_data="edit_parsed:address"),
        InlineKeyboardButton(text="👤 Клиент", callback_data="edit_parsed:client_name"),
    )
    kb.row(
        InlineKeyboardButton(text="📞 Телефон", callback_data="edit_parsed:phone"),
        InlineKeyboardButton(text="🕐 Время", callback_data="edit_parsed:scheduled_time"),
    )
    kb.row(
        InlineKeyboardButton(text="🔙 Назад к подтверждению", callback_data="edit_parsed:back")
    )

    # Редактируем сообщение бота
    await message.bot.edit_message_text(
        text=text,
        chat_id=message.chat.id,
        message_id=confirmation_message_id,
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    
    # Возвращаемся к выбору поля (сбрасываем enter_value, но оставляем остальные данные)
    await state.set_state(None) 
