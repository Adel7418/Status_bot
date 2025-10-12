"""
Общие обработчики для всех пользователей
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.config import UserRole, Messages
from app.keyboards.reply import get_main_menu_keyboard
from app.database.models import User
from app.decorators import handle_errors

logger = logging.getLogger(__name__)

router = Router(name='common')


@router.message(CommandStart())
@handle_errors
async def cmd_start(message: Message, user: User, user_role: str, user_roles: list):
    """
    Обработчик команды /start
    
    Args:
        message: Сообщение
        user: Пользователь из БД
        user_role: Основная роль пользователя (для обратной совместимости)
        user_roles: Список всех ролей пользователя
    """
    logger.info(f"START command received from user {message.from_user.id}")
    logger.info(f"User roles: {user_roles}, User object: {user}")
    
    # Выбираем приветственное сообщение в зависимости от ролей
    welcome_messages = {
        UserRole.ADMIN: Messages.WELCOME_ADMIN,
        UserRole.DISPATCHER: Messages.WELCOME_DISPATCHER,
        UserRole.MASTER: Messages.WELCOME_MASTER,
        UserRole.UNKNOWN: Messages.WELCOME_UNKNOWN
    }
    
    # Если у пользователя несколько ролей, формируем комбинированное приветствие
    if UserRole.ADMIN in user_roles:
        welcome_text = welcome_messages[UserRole.ADMIN]
    elif UserRole.DISPATCHER in user_roles and UserRole.MASTER in user_roles:
        welcome_text = (
            "👋 Добро пожаловать!\n\n"
            "У вас есть доступ как диспетчера, так и мастера.\n"
            "Вы можете создавать заявки, назначать их мастерам и выполнять их самостоятельно.\n"
            "Используйте меню ниже для навигации."
        )
    elif UserRole.DISPATCHER in user_roles:
        welcome_text = welcome_messages[UserRole.DISPATCHER]
    elif UserRole.MASTER in user_roles:
        welcome_text = welcome_messages[UserRole.MASTER]
    else:
        welcome_text = welcome_messages.get(UserRole.UNKNOWN, Messages.WELCOME_UNKNOWN)
    
    logger.info(f"Sending welcome message...")
    
    # Отправляем приветствие с клавиатурой (передаем список ролей)
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(user_roles)
    )
    
    logger.info(f"User {message.from_user.id} ({', '.join(user_roles)}) started the bot")


@router.message(Command("help"))
@handle_errors
async def cmd_help(message: Message, user_role: str, user_roles: list):
    """
    Обработчик команды /help
    
    Args:
        message: Сообщение
        user_role: Основная роль пользователя
        user_roles: Список всех ролей пользователя
    """
    help_texts = {
        UserRole.ADMIN: (
            "📚 <b>Помощь для администратора</b>\n\n"
            "Доступные функции:\n"
            "• 📋 Все заявки - просмотр всех заявок в системе\n"
            "• ➕ Создать заявку - создание новой заявки\n"
            "• 👥 Мастера - управление мастерами\n"
            "• 📊 Отчеты - генерация различных отчетов\n"
            "• 👤 Пользователи - управление пользователями\n"
            "• ⚙️ Настройки - настройки бота\n\n"
            "Команды:\n"
            "/start - главное меню\n"
            "/help - эта справка\n"
            "/cancel - отмена текущего действия"
        ),
        UserRole.DISPATCHER: (
            "📚 <b>Помощь для диспетчера</b>\n\n"
            "Доступные функции:\n"
            "• 📋 Все заявки - просмотр всех заявок\n"
            "• ➕ Создать заявку - создание новой заявки\n"
            "• 👥 Мастера - просмотр списка мастеров\n"
            "• 📊 Отчеты - просмотр отчетов\n\n"
            "Команды:\n"
            "/start - главное меню\n"
            "/help - эта справка\n"
            "/cancel - отмена текущего действия"
        ),
        UserRole.MASTER: (
            "📚 <b>Помощь для мастера</b>\n\n"
            "Доступные функции:\n"
            "• 📋 Мои заявки - просмотр назначенных вам заявок\n"
            "• 📊 Моя статистика - ваша статистика работы\n\n"
            "Статусы заявок:\n"
            "• 🆕 Новая - заявка только что создана\n"
            "• 👨‍🔧 Назначена - заявка назначена вам\n"
            "• ✅ Принята - вы приняли заявку\n"
            "• 🏠 На объекте - вы на объекте\n"
            "• 💰 Завершена - работа выполнена\n"
            "• ⏳ Длительный ремонт - требуется больше времени\n\n"
            "Команды:\n"
            "/start - главное меню\n"
            "/help - эта справка\n"
            "/cancel - отмена текущего действия"
        ),
        UserRole.UNKNOWN: (
            "📚 <b>Информация о системе</b>\n\n"
            "Это система управления заявками на ремонт техники.\n\n"
            "Для получения доступа обратитесь к администратору.\n\n"
            "Команды:\n"
            "/start - главное меню\n"
            "/help - эта справка"
        )
    }
    
    # Формируем справку для пользователей с несколькими ролями
    if UserRole.ADMIN in user_roles:
        help_text = help_texts[UserRole.ADMIN]
    elif UserRole.DISPATCHER in user_roles and UserRole.MASTER in user_roles:
        help_text = (
            "📚 <b>Помощь (Диспетчер + Мастер)</b>\n\n"
            "Доступные функции:\n"
            "• 📋 Все заявки - просмотр всех заявок\n"
            "• ➕ Создать заявку - создание новой заявки\n"
            "• 📋 Мои заявки - просмотр назначенных вам заявок\n"
            "• 👥 Мастера - просмотр списка мастеров\n"
            "• 📊 Отчеты - просмотр отчетов\n"
            "• 📊 Моя статистика - ваша статистика работы\n\n"
            "Команды:\n"
            "/start - главное меню\n"
            "/help - эта справка\n"
            "/cancel - отмена текущего действия"
        )
    else:
        help_text = help_texts.get(user_role, help_texts[UserRole.UNKNOWN])
    
    await message.answer(help_text, parse_mode="HTML")
    
    logger.info(f"User {message.from_user.id} requested help")


@router.message(Command("cancel"))
@handle_errors
async def cmd_cancel(message: Message, state: FSMContext, user_role: str, user_roles: list):
    """
    Обработчик команды /cancel - отмена текущего действия
    
    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Основная роль пользователя
        user_roles: Список всех ролей пользователя
    """
    # Очищаем состояние
    await state.clear()
    
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=get_main_menu_keyboard(user_roles)
    )
    
    logger.info(f"User {message.from_user.id} cancelled action")


@router.message(F.text == "❌ Отмена")
@handle_errors
async def btn_cancel(message: Message, state: FSMContext, user_role: str, user_roles: list):
    """
    Обработчик кнопки отмены
    
    Args:
        message: Сообщение
        state: FSM контекст
        user_role: Основная роль пользователя
        user_roles: Список всех ролей пользователя
    """
    await cmd_cancel(message, state, user_role, user_roles)


@router.message(F.text == "⚙️ Настройки")
@handle_errors
async def btn_settings(message: Message, user: User):
    """
    Обработчик кнопки настроек
    
    Args:
        message: Сообщение
        user: Пользователь
    """
    # Получаем список ролей
    roles = user.get_roles()
    
    # Форматируем роли для отображения
    role_names = {
        UserRole.ADMIN: "Администратор",
        UserRole.DISPATCHER: "Диспетчер",
        UserRole.MASTER: "Мастер",
        UserRole.UNKNOWN: "Неизвестно"
    }
    
    roles_display = ", ".join([role_names.get(r, r) for r in roles])
    
    settings_text = (
        f"⚙️ <b>Настройки профиля</b>\n\n"
        f"👤 <b>Имя:</b> {user.get_full_name()}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
        f"👔 <b>Роли:</b> {roles_display}\n"
    )
    
    if user.username:
        settings_text += f"📱 <b>Username:</b> @{user.username}\n"
    
    await message.answer(settings_text, parse_mode="HTML")


@router.message(F.text == "ℹ️ Информация")
async def btn_info(message: Message):
    """
    Обработчик кнопки информации
    
    Args:
        message: Сообщение
    """
    info_text = (
        "ℹ️ <b>Информация о системе</b>\n\n"
        "Это автоматизированная система управления заявками на ремонт техники.\n\n"
        "<b>Основные возможности:</b>\n"
        "• Создание и управление заявками\n"
        "• Назначение мастеров\n"
        "• Отслеживание статусов\n"
        "• Генерация отчетов\n\n"
        "Для получения доступа обратитесь к администратору системы."
    )
    
    await message.answer(info_text, parse_mode="HTML")


@router.message(F.text == "📞 Связаться")
async def btn_contact(message: Message):
    """
    Обработчик кнопки связи
    
    Args:
        message: Сообщение
    """
    contact_text = (
        "📞 <b>Контактная информация</b>\n\n"
        "Для получения доступа к системе или по любым вопросам "
        "обращайтесь к администратору.\n\n"
        "Ваш Telegram ID для регистрации:\n"
        f"<code>{message.from_user.id}</code>\n\n"
        "<i>Нажмите на ID чтобы скопировать</i>"
    )
    
    await message.answer(contact_text, parse_mode="HTML")


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик callback кнопки отмены
    
    Args:
        callback: Callback query
        state: FSM контекст
    """
    await state.clear()
    await callback.message.delete()
    await callback.answer("Отменено")


@router.callback_query(F.data == "no_orders")
async def callback_no_orders(callback: CallbackQuery):
    """
    Обработчик callback для пустого списка заявок
    
    Args:
        callback: Callback query
    """
    await callback.answer("Заявок нет", show_alert=True)


@router.callback_query(F.data == "current_page")
async def callback_current_page(callback: CallbackQuery):
    """
    Обработчик callback для текущей страницы
    
    Args:
        callback: Callback query
    """
    await callback.answer()


@router.message(F.text)
async def handle_unknown_text(message: Message, user_role: str):
    """
    Обработчик неизвестного текста
    
    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    # Игнорируем сообщения в группах - бот должен отвечать только на команды
    if message.chat.type in ['group', 'supergroup']:
        return
    
    # Проверяем, что это действительно неизвестная команда
    # Исключаем кнопки, которые должны обрабатываться другими роутерами
    known_buttons = [
        "➕ Создать заявку",
        "📋 Все заявки", 
        "👥 Мастера",
        "📊 Отчеты",
        "👤 Пользователи",
        "⚙️ Настройки",
        "📋 Мои заявки",
        "📊 Моя статистика",
        "ℹ️ Информация",
        "📞 Связаться",
        "❌ Отмена",
        "⏭️ Пропустить",
        "✅ Подтвердить"
    ]
    
    # Если это известная кнопка, не обрабатываем здесь
    if message.text in known_buttons:
        return
    
    if user_role == UserRole.UNKNOWN:
        await message.answer(
            "❌ У вас нет доступа к системе.\n"
            "Обратитесь к администратору для получения доступа.",
            reply_markup=get_main_menu_keyboard(user_role)
        )
    else:
        await message.answer(
            "❓ Не понимаю эту команду. Используйте меню ниже или /help для справки.",
            reply_markup=get_main_menu_keyboard(user_role)
        )

