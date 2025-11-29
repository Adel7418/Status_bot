"""
Handlers для настройки парсера заявок

Команды:
- /set_group — установка ID группы для парсинга
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.core.config import Config
from app.database.orm_database import ORMDatabase
from app.database.parser_config_repository import ParserConfigRepository
from app.decorators import require_role


logger = logging.getLogger(__name__)

router = Router(name="parser_config")


@router.message(Command("set_group"))
@require_role(["admin"])
async def cmd_set_group(message: Message, db: ORMDatabase, *, user_role: str = "UNKNOWN") -> None:
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
async def cmd_parser_status(message: Message, db: ORMDatabase) -> None:
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

    await message.answer(
        f"📊 <b>Статус парсера</b>\n\n"
        f"{status_emoji} <b>Статус:</b> {status_text}\n"
        f"📋 <b>Group ID:</b> {group_text}\n\n"
        f"<b>Конфигурация (.env):</b>\n"
        f"• PARSER_ENABLED: {Config.PARSER_ENABLED}\n"
        f"• TELETHON_API_ID: {'✅ установлен' if Config.TELETHON_API_ID else '❌ не установлен'}\n"
        f"• TELETHON_API_HASH: {'✅ установлен' if Config.TELETHON_API_HASH else '❌ не установлен'}\n"
        f"• TELETHON_PHONE: {'✅ установлен' if Config.TELETHON_PHONE else '❌ не установлен'}",
        parse_mode="HTML",
    )


@router.message(Command("parser_enable"))
@require_role(["admin"])
async def cmd_parser_enable(message: Message, db: ORMDatabase, *, user_role: str = "UNKNOWN") -> None:
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
async def cmd_parser_disable(message: Message, db: ORMDatabase, *, user_role: str = "UNKNOWN") -> None:
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

        await message.answer(
            "🛑 <b>Парсер отключён</b>\n\n"
            "Бот прекратит мониторинг сообщений из группы.",
            parse_mode="HTML",
        )
        logger.info(f"Администратор {message.from_user.id} отключил парсер")

    except Exception as e:
        logger.exception(f"Ошибка при отключении парсера: {e}")
        await message.answer("❌ Произошла ошибка при отключении парсера")


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
