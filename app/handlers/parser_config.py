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
from app.states import ParserAuthState


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
        elif getattr(parser_integration, "waiting_for_auth", False):
            runtime_status = "🔴 Остановлен (Требуется аутентификация /parser_auth)"
        else:
            runtime_status = "🔴 Остановлен"
    else:
        runtime_status = "⚠️ Ошибка: Сервис не доступен"

    await message.answer(
        f"📊 <b>Статус парсера</b>\n\n"
        f"{status_emoji} <b>Конфигурация БД:</b> {status_text}\n"
        f"⚙️ <b>Процесс:</b> {runtime_status}\n"
        f"📋 <b>Group ID:</b> {group_text}\n\n"
        f"<b>Параметры (.env):</b>\n"
        f"• PARSER_ENABLED: {Config.PARSER_ENABLED}\n"
        f"• TELETHON_SESSION: {Config.TELETHON_SESSION_NAME}\n",
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
    session_file = f"{Config.TELETHON_SESSION_NAME}.session"
    try:
        if os.path.exists(session_file):
            os.remove(session_file)
            logger.info(f"Файл сессии {session_file} удален")
            await message.answer(
                f"✅ <b>Сессия сброшена</b>\n\n"
                f"Файл <code>{session_file}</code> удален.\n"
                f"Теперь вы можете заново пройти аутентификацию через /parser_auth",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"⚠️ Файл сессии <code>{session_file}</code> не найден.\n"
                f"Можно пробовать /parser_auth",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Ошибка при удалении файла сессии: {e}")
        await message.answer(f"❌ Ошибка при удалении файла сессии: {e}")


@router.message(Command("parser_auth"))
@require_role(["admin"])
async def cmd_parser_auth(
    message: Message,
    state: FSMContext,
    parser_integration: ParserIntegration | None = None,
    *,
    user_role: str = "UNKNOWN",
) -> None:
    """
    Команда для интерактивной аутентификации парсера.
    """
    logger.info(f"Admin {message.from_user.id} called /parser_auth in chat {message.chat.type}")

    if not Config.PARSER_ENABLED:
        await message.answer("❌ Парсер отключён в конфигурации (.env)")
        return

    if not parser_integration:
        await message.answer("⚠️ Сервис парсера недоступен")
        return

    # Принудительно отправляем в ЛС, чтобы не путать контекст FSM
    if message.chat.type != "private":
        bot_username = (await message.bot.get_me()).username
        await message.answer(
            f"⚠️ В целях безопасности и корректной работы, пожалуйста, выполните эту команду в личных сообщениях боту:\n"
            f"👉 @{bot_username}"
        )
        return

    await message.answer(
        "🔄 Начинаю процесс аутентификации...\n\n"
        "❗️ <b>Важно:</b> Telegram может заблокировать вход, если вы отправите код «как есть».\n"
        "Чтобы этого избежать, напишите код <b>через пробелы или дефисы</b>.\n\n"
        "Пример: <code>1 2 3 4 5</code> или <code>1-2-3-4-5</code>",
        parse_mode="HTML"
    )
    
    # Устанавливаем состояние ожидания кода
    await state.set_state(ParserAuthState.waiting_for_code)
    # Форсируем обновление данных, чтобы состояние точно сохранилось
    await state.update_data(auth_started=True)
    # Даем время на сохранение состояния перед блокирующим вызовом
    await asyncio.sleep(0.5)
    
    try:
        logger.info("Calling authenticate_user...")
        # Это заблокирует выполнение до завершения auth (или ошибки)
        await parser_integration.authenticate_user(message.from_user.id)
        # Если метод вернулся без исключений - значит auth успешен
        logger.info("Authentication successful")
        await message.answer("✅ Аутентификация успешно завершена! Парсер запущен.")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        await message.answer(f"❌ Ошибка аутентификации: {e}")
    finally:
        logger.info("Clearing auth state")
        await state.clear()


@router.message(ParserAuthState.waiting_for_code)
async def process_auth_code(
    message: Message,
    state: FSMContext,
    parser_integration: ParserIntegration | None = None,
) -> None:
    """
    Обработчик ввода кода подтверждения.
    """
    logger.info(f"Received message in waiting_for_code state from {message.from_user.id}")

    # Если это команда, игнорируем (пусть обрабатывается другими хендлерами)
    if message.text.startswith("/"):
        logger.info("Message is a command, ignoring in auth handler")
        return

    if not parser_integration:
        await message.answer("⚠️ Сервис парсера недоступен")
        return

    # Очищаем код от всего, кроме цифр (чтобы обойти защиту Telegram)
    raw_code = message.text.strip()
    code = "".join(filter(str.isdigit, raw_code))

    if not code:
        await message.answer("⚠️ Не удалось распознать цифры кода. Попробуйте еще раз (например: 1-2-3-4-5).")
        return

    logger.info(f"Submitting auth code: {code} (raw: {raw_code})")
    
    # Мы не можем знать наверняка, запросит ли Telethon пароль, 
    # поэтому мы просто отправляем код. 
    # Если Telethon запросит пароль, сработает callback в ParserIntegration,
    # который отправит сообщение "Требуется пароль".
    # Нам нужно перехватить это сообщение или просто разрешить ввод пароля.
    
    # ХАК: Мы переходим в состояние ожидания пароля СРАЗУ, 
    # но с возможностью вернуться, если это была ошибка кода.
    # Но лучше просто добавить хендлер для пароля и переключать состояние
    # когда пользователь увидит сообщение о пароле? 
    # Нет, FSM так не работает.
    
    # Решение: ParserIntegration.authenticate_user блокирует выполнение.
    # Внутри него вызывается password_callback.
    # Мы можем попытаться определить, что сейчас происходит, но это сложно.
    
    # Проще всего: добавить хендлер для пароля, который будет активен
    # если мы перейдем в состояние waiting_for_password.
    # А переход в это состояние мы сделаем... Хм.
    # Мы не можем изменить состояние из callback-а, так как у нас нет доступа к FSMContext там.
    
    # ВАРИАНТ: Разрешить ввод пароля в том же состоянии waiting_for_code?
    # Нет, это грязно.
    
    # ВАРИАНТ: Использовать магию.
    # Когда ParserIntegration отправляет сообщение "Требуется пароль",
    # мы можем (теоретически) перехватить это? Нет.
    
    # ВАРИАНТ: Просто добавить хендлер на waiting_for_code, который
    # если это не цифры, пробует считать это паролем?
    # Нет, пароль может быть цифрами.
    
    # ПРАВИЛЬНЫЙ ВАРИАНТ:
    # В ParserIntegration.authenticate_user мы передаем callback.
    # В этом callback мы можем отправить сообщение.
    # Пользователь увидит "Введите пароль".
    # Но бот все еще в waiting_for_code.
    
    # Мы добавим хендлер, который ловит ВСЕ в waiting_for_code.
    # Если это похоже на код (цифры, дефисы) -> submit_auth_code.
    # Если это НЕ похоже на код -> submit_password?
    # А если пароль "12345"?
    
    # ДАВАЙТЕ СДЕЛАЕМ ТАК:
    # Мы добавим состояние waiting_for_password.
    # Но как в него перейти?
    # Мы можем сделать это "вслепую".
    # После отправки кода, мы можем предположить, что следующее сообщение - это либо
    # новый код (если ошибка), либо пароль.
    
    # НО! У нас есть проблема: authenticate_user блокирует хендлер cmd_parser_auth.
    # Мы не можем там менять состояние.
    
    # РЕШЕНИЕ:
    # Мы просто добавим хендлер для waiting_for_password.
    # А переключать состояние будет... ПОЛЬЗОВАТЕЛЬ? Нет.
    
    # А что если мы будем принимать пароль в waiting_for_code?
    # Если submit_auth_code вызывается второй раз?
    
    # Давайте сделаем так:
    # В process_auth_code мы отправляем код.
    # И СРАЗУ переводим состояние в waiting_for_password.
    # Если аутентификация завершится успешно, cmd_parser_auth сделает state.clear().
    # Если потребуется пароль, пользователь напишет его, и мы поймаем его в waiting_for_password.
    # Если код был неверен, Telethon выбросит ошибку, cmd_parser_auth поймает её и сбросит стейт.
    # Пользователю придется начать заново. Это приемлемо.
    
    parser_integration.submit_auth_code(code)
    
    # Переходим в состояние ожидания пароля (на всякий случай)
    await state.set_state(ParserAuthState.waiting_for_password)
    await message.answer("⏳ Код принят. Если у вас включена 2FA, введите пароль следующим сообщением.")


@router.message(ParserAuthState.waiting_for_password)
async def process_auth_password(
    message: Message,
    state: FSMContext,
    parser_integration: ParserIntegration | None = None,
) -> None:
    """
    Обработчик ввода пароля 2FA.
    """
    logger.info(f"Received message in waiting_for_password state from {message.from_user.id}")

    if message.text.startswith("/"):
        return

    if not parser_integration:
        await message.answer("⚠️ Сервис парсера недоступен")
        return

    password = message.text.strip()
    logger.info("Submitting 2FA password")
    
    parser_integration.submit_password(password)
    await message.answer("⏳ Пароль принят, проверяю...")


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
