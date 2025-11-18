"""
Хэндлеры для работы с финансовыми отчетами
"""

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import UserRole
from app.database.db import Database
from app.decorators import handle_errors, require_role
from app.services.financial_reports import FinancialReportsService
from app.services.master_reports_detailed import MasterReportsService
from app.utils.helpers import get_now


logger = logging.getLogger(__name__)
router = Router()


async def safe_edit_message(
    callback: CallbackQuery, text: str, reply_markup=None, parse_mode="HTML"
):
    """
    Безопасное редактирование сообщения с обработкой различных типов сообщений

    Args:
        callback: Callback query
        text: Текст для отображения
        reply_markup: Клавиатура
        parse_mode: Режим парсинга
    """
    message = callback.message
    if not isinstance(message, Message):
        logger.warning("Callback has no accessible message to edit")
        try:
            await callback.answer()
        except Exception:
            # Игнорируем ошибки ответа на callback
            pass
        return

    try:
        # Сначала пытаемся отредактировать текст сообщения
        await message.edit_text(
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.warning(f"Could not edit message text: {e}")
        # Если не удалось отредактировать текст, пытаемся отредактировать caption
        try:
            await message.edit_caption(
                text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
        except Exception as e2:
            logger.warning(f"Could not edit message caption: {e2}")
            # Если и это не удалось, удаляем старое сообщение и отправляем новое
            try:
                await message.delete()
            except Exception as e3:
                logger.warning(f"Could not delete message: {e3}")

            # Отправляем новое сообщение
            await message.answer(
                text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )


def get_reports_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню отчетов"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="📋 Активные заявки (Excel)", callback_data="report_active_orders_excel"
            ),
        ],
        [
            InlineKeyboardButton(
                text="📊 Ежедневная сводка", callback_data="report_daily_master_summary"
            ),
        ],
        [
            InlineKeyboardButton(
                text="📈 Еженедельная сводка", callback_data="report_weekly_master_summary"
            ),
        ],
        [
            InlineKeyboardButton(
                text="📊 Ежемесячная сводка", callback_data="report_monthly_master_summary"
            ),
        ],
        [
            InlineKeyboardButton(
                text="👨‍🔧 Статистика мастеров (Excel)", callback_data="report_masters_stats_excel"
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_daily_report_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора дня отчета"""
    today = get_now()
    yesterday = today - timedelta(days=1)

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"📅 Сегодня ({today.strftime('%d.%m')})",
                callback_data=f"daily_report_{today.strftime('%Y-%m-%d')}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"📅 Вчера ({yesterday.strftime('%d.%m')})",
                callback_data=f"daily_report_{yesterday.strftime('%Y-%m-%d')}",
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_weekly_report_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора недели отчета"""
    today = get_now()
    current_week_start = today - timedelta(days=today.weekday())
    last_week_start = current_week_start - timedelta(days=7)

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"📅 Текущая неделя ({current_week_start.strftime('%d.%m')} - {(current_week_start + timedelta(days=6)).strftime('%d.%m')})",
                callback_data=f"weekly_report_{current_week_start.strftime('%Y-%m-%d')}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"📅 Прошлая неделя ({last_week_start.strftime('%d.%m')} - {(last_week_start + timedelta(days=6)).strftime('%d.%m')})",
                callback_data=f"weekly_report_{last_week_start.strftime('%Y-%m-%d')}",
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_monthly_report_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора месяца отчета"""
    today = get_now()
    current_month = today.replace(day=1)
    last_month = (current_month - timedelta(days=1)).replace(day=1)

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"📅 Текущий месяц ({current_month.strftime('%B %Y')})",
                callback_data=f"monthly_report_{current_month.strftime('%Y-%m')}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"📅 Прошлый месяц ({last_month.strftime('%B %Y')})",
                callback_data=f"monthly_report_{last_month.strftime('%Y-%m')}",
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_daily_master_report_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора дня отчета по мастерам"""
    today = get_now()
    yesterday = today - timedelta(days=1)

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"Сегодня ({today.strftime('%d.%m')})",
                callback_data=f"daily_master_report_{today.strftime('%Y-%m-%d')}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Вчера ({yesterday.strftime('%d.%m')})",
                callback_data=f"daily_master_report_{yesterday.strftime('%Y-%m-%d')}",
            ),
        ],
        [
            InlineKeyboardButton(text="📅 Выбрать дату", callback_data="select_daily_master_date"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_weekly_master_report_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора недели отчета по мастерам"""
    today = get_now()
    # Находим начало текущей недели (понедельник)
    days_since_monday = today.weekday()
    current_week_start = today - timedelta(days=days_since_monday)
    previous_week_start = current_week_start - timedelta(days=7)

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"Эта неделя ({current_week_start.strftime('%d.%m')} - {(current_week_start + timedelta(days=6)).strftime('%d.%m')})",
                callback_data=f"weekly_master_report_{current_week_start.strftime('%Y-%m-%d')}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Прошлая неделя ({previous_week_start.strftime('%d.%m')} - {(previous_week_start + timedelta(days=6)).strftime('%d.%m')})",
                callback_data=f"weekly_master_report_{previous_week_start.strftime('%Y-%m-%d')}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📅 Выбрать неделю", callback_data="select_weekly_master_date"
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_monthly_master_report_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора месяца отчета по мастерам"""
    today = get_now()
    current_month = today.replace(day=1)
    previous_month = (current_month - timedelta(days=1)).replace(day=1)

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"Этот месяц ({current_month.strftime('%B %Y')})",
                callback_data=f"monthly_master_report_{current_month.strftime('%Y-%m-%d')}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Прошлый месяц ({previous_month.strftime('%B %Y')})",
                callback_data=f"monthly_master_report_{previous_month.strftime('%Y-%m-%d')}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📅 Выбрать месяц", callback_data="select_monthly_master_date"
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_report_actions_keyboard(report_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с отчетом"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="📄 Скачать Excel", callback_data=f"export_excel_{report_id}"
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад к отчетам", callback_data="reports_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(Command("reports"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def cmd_reports(message: Message, user_role: str):
    """
    Команда для просмотра финансовых отчетов

    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    await message.answer(
        "📊 <b>Генерация отчетов</b>\n\n" "Выберите тип отчета для генерации:",
        parse_mode="HTML",
        reply_markup=get_reports_menu_keyboard(),
    )


@router.message(F.text == "📊 Отчеты")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def btn_reports_direct(message: Message, user_role: str):
    """
    Кнопка для просмотра финансовых отчетов

    Args:
        message: Сообщение
        user_role: Роль пользователя
    """
    logger.info(f"DEBUG: btn_reports_direct called, user_role={user_role}")
    await message.answer(
        "📊 <b>Генерация отчетов</b>\n\n" "Выберите тип отчета для генерации:",
        parse_mode="HTML",
        reply_markup=get_reports_menu_keyboard(),
    )


@router.callback_query(F.data == "reports_menu")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_reports_menu(callback: CallbackQuery, user_role: str):
    """Возврат в главное меню отчетов"""
    await safe_edit_message(
        callback,
        "📊 <b>Генерация отчетов</b>\n\n" "Выберите тип отчета для генерации:",
        reply_markup=get_reports_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "report_daily")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_report_daily(callback: CallbackQuery, user_role: str):
    """Выбор ежедневного отчета"""
    await safe_edit_message(
        callback,
        "📅 <b>Ежедневный отчет</b>\n\n" "Выберите день:",
        reply_markup=get_daily_report_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "report_weekly")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_report_weekly(callback: CallbackQuery, user_role: str):
    """Выбор еженедельного отчета"""
    await safe_edit_message(
        callback,
        "📊 <b>Еженедельный отчет</b>\n\n" "Выберите неделю:",
        reply_markup=get_weekly_report_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "report_monthly")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_report_monthly(callback: CallbackQuery, user_role: str):
    """Выбор месячного отчета"""
    await safe_edit_message(
        callback,
        "📈 <b>Месячный отчет</b>\n\n" "Выберите месяц:",
        reply_markup=get_monthly_report_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("daily_report_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_generate_daily_report(callback: CallbackQuery, user_role: str):
    """Генерация ежедневного отчета"""
    from app.utils.helpers import MOSCOW_TZ

    data = callback.data or ""
    try:
        date_str = data.split("_")[-1]
    except IndexError:
        await callback.answer("❌ Некорректные данные отчета", show_alert=True)
        return
    report_date = datetime.strptime(date_str, "%Y-%m-%d")
    # Добавляем московский часовой пояс
    report_date = report_date.replace(tzinfo=MOSCOW_TZ)

    await safe_edit_message(callback, "⏳ Генерирую ежедневный отчет...")

    service = FinancialReportsService()
    report = await service.generate_daily_report(report_date)

    if report.id is None:
        await safe_edit_message(
            callback,
            "❌ Не удалось сохранить отчет в базе данных.",
            reply_markup=get_reports_menu_keyboard(),
        )
        await callback.answer()
        return

    if report.total_orders == 0:
        await safe_edit_message(
            callback,
            f"📅 <b>Ежедневный отчет за {report_date.strftime('%d.%m.%Y')}</b>\n\n"
            f"❌ За этот день не было завершенных заказов.",
            reply_markup=get_report_actions_keyboard(report.id),
        )
    else:
        report_text = await service.format_report_for_display(report.id)
        await safe_edit_message(
            callback,
            report_text,
            reply_markup=get_report_actions_keyboard(
                report.id,
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("weekly_report_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_generate_weekly_report(callback: CallbackQuery, user_role: str):
    """Генерация еженедельного отчета"""
    from app.utils.helpers import MOSCOW_TZ

    data = callback.data or ""
    try:
        date_str = data.split("_")[-1]
    except IndexError:
        await callback.answer("❌ Некорректные данные отчета", show_alert=True)
        return
    week_start = datetime.strptime(date_str, "%Y-%m-%d")
    # Добавляем московский часовой пояс
    week_start = week_start.replace(tzinfo=MOSCOW_TZ)

    await safe_edit_message(callback, "⏳ Генерирую еженедельный отчет...")

    service = FinancialReportsService()
    report = await service.generate_weekly_report(week_start)

    if report.id is None:
        await safe_edit_message(
            callback,
            "❌ Не удалось сохранить отчет в базе данных.",
            reply_markup=get_reports_menu_keyboard(),
        )
        await callback.answer()
        return

    if report.total_orders == 0:
        await safe_edit_message(
            callback,
            f"📊 <b>Еженедельный отчет за {week_start.strftime('%d.%m')} - {(week_start + timedelta(days=6)).strftime('%d.%m.%Y')}</b>\n\n"
            f"❌ За эту неделю не было завершенных заказов.",
            reply_markup=get_report_actions_keyboard(
                report.id,
            ),
        )
    else:
        report_text = await service.format_report_for_display(report.id)
        await safe_edit_message(
            callback,
            report_text,
            reply_markup=get_report_actions_keyboard(
                report.id,
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("monthly_report_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_generate_monthly_report(callback: CallbackQuery, user_role: str):
    """Генерация месячного отчета"""
    data = callback.data or ""
    try:
        parts = data.split("_")[-2:]
        year = int(parts[0])
        month = int(parts[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Некорректные данные отчета", show_alert=True)
        return

    await safe_edit_message(callback, "⏳ Генерирую месячный отчет...")

    service = FinancialReportsService()
    report = await service.generate_monthly_report(year, month)

    if report.id is None:
        await safe_edit_message(
            callback,
            "❌ Не удалось сохранить отчет в базе данных.",
            reply_markup=get_reports_menu_keyboard(),
        )
        await callback.answer()
        return

    if report.total_orders == 0:
        month_name = datetime(year, month, 1).strftime("%B %Y")
        await safe_edit_message(
            callback,
            f"📈 <b>Месячный отчет за {month_name}</b>\n\n"
            f"❌ За этот месяц не было завершенных заказов.",
            reply_markup=get_report_actions_keyboard(
                report.id,
            ),
        )
    else:
        report_text = await service.format_report_for_display(report.id)
        await safe_edit_message(
            callback,
            report_text,
            reply_markup=get_report_actions_keyboard(
                report.id,
            ),
        )

    await callback.answer()


@router.callback_query(F.data == "reports_list")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_reports_list(callback: CallbackQuery, user_role: str, db: Database):
    """Список последних отчетов"""
    reports = await db.get_latest_reports(limit=10)

    if not reports:
        await safe_edit_message(
            callback,
            "📋 <b>Последние отчеты</b>\n\n" "❌ Отчетов пока нет.",
            reply_markup=get_reports_menu_keyboard(),
        )
        return

    text = "📋 <b>Последние отчеты:</b>\n\n"
    keyboard = []

    for i, report in enumerate(reports[:5], 1):
        period_text = ""
        if report.report_type == "DAILY":
            if report.period_start is not None:
                period_text = report.period_start.strftime("%d.%m.%Y")
        elif report.report_type == "WEEKLY":
            if report.period_start is not None and report.period_end is not None:
                period_text = (
                    f"{report.period_start.strftime('%d.%m')} - "
                    f"{report.period_end.strftime('%d.%m.%Y')}"
                )
        elif report.report_type == "MONTHLY":
            if report.period_start is not None:
                period_text = report.period_start.strftime("%B %Y")

        text += (
            f"{i}. {report.report_type.lower()} ({period_text}) - {report.total_orders} заказов\n"
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{report.report_type.lower()} {period_text}",
                    callback_data=f"view_report_{report.id}",
                )
            ]
        )

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu")])

    await safe_edit_message(
        callback,
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard,
        ),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("view_report_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_view_report(callback: CallbackQuery, user_role: str):
    """Просмотр существующего отчета"""
    data = callback.data or ""
    try:
        report_id = int(data.split("_")[-1])
    except (IndexError, ValueError):
        await callback.answer("❌ Некорректный идентификатор отчета", show_alert=True)
        return

    service = FinancialReportsService()
    report_text = await service.format_report_for_display(report_id)

    if not report_text or "не найден" in report_text:
        await safe_edit_message(
            callback,
            "❌ Отчет не найден.",
            reply_markup=get_reports_menu_keyboard(),
        )
    else:
        await safe_edit_message(
            callback,
            report_text,
            reply_markup=get_report_actions_keyboard(
                report_id,
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("export_excel_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_export_excel(callback: CallbackQuery, user_role: str):
    """Экспорт отчета в Excel"""
    data = callback.data or ""
    try:
        report_id = int(data.split("_")[-1])
    except (IndexError, ValueError):
        await callback.answer("❌ Некорректный идентификатор отчета", show_alert=True)
        return

    await callback.answer("⏳ Создаю Excel файл...")
    await safe_edit_message(callback, "📊 Генерирую Excel отчет, подождите...")

    try:
        from aiogram.types import FSInputFile

        from app.services.excel_export import ExcelExportService

        excel_service = ExcelExportService()
        filepath = await excel_service.export_report_to_excel(report_id)

        if not filepath:
            await safe_edit_message(
                callback,
                "❌ Ошибка при создании Excel файла.",
                reply_markup=get_reports_menu_keyboard(),
            )
            return

        # Отправляем файл пользователю
        file = FSInputFile(filepath)
        message_obj = callback.message
        if isinstance(message_obj, Message):
            await message_obj.answer_document(file, caption="📄 Финансовый отчет в формате Excel")

        # Возвращаем меню
        await safe_edit_message(
            callback,
            "✅ Excel файл успешно создан и отправлен!",
            reply_markup=get_reports_menu_keyboard(),
        )

        # Удаляем временный файл
        import os

        if os.path.exists(filepath):
            os.remove(filepath)

    except Exception as e:
        logger.error(f"Error exporting to Excel: {e}")
        await safe_edit_message(
            callback,
            f"❌ Ошибка при экспорте: {e!s}",
            reply_markup=get_reports_menu_keyboard(),
        )


@router.callback_query(F.data == "report_active_orders_excel")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_report_active_orders_excel(callback: CallbackQuery, user_role: str):
    """
    Экспорт активных заявок в Excel

    Args:
        callback: Callback query
        user_role: Роль пользователя
    """

    await callback.answer("📊 Генерирую отчет...", show_alert=False)

    try:
        from app.services.realtime_active_orders import realtime_active_orders_service

        # Обновляем таблицу активных заказов
        await realtime_active_orders_service.update_table()

        # Получаем путь к текущей таблице
        filepath = await realtime_active_orders_service.get_current_table_path()

        if filepath:
            # Отправляем файл
            from aiogram.types import FSInputFile

            file = FSInputFile(filepath)
            message_obj = callback.message
            if isinstance(message_obj, Message):
                await message_obj.answer_document(
                    file,
                    caption="📋 <b>Отчет по активным заявкам</b>\n\n"
                    "В файле указаны все незакрытые заявки:\n"
                    "• Сводный лист со всеми заявками\n"
                    "• Отдельные листы для каждого мастера\n"
                    "• Статус и время создания\n"
                    "• Назначенный мастер\n"
                    "• Контакты клиента\n"
                    "• Запланированное время\n\n"
                    "Таблица обновляется при каждом запросе.",
                    parse_mode="HTML",
                )

            if callback.from_user:
                logger.info(f"Active orders report sent to {callback.from_user.id}")
        else:
            await callback.answer("❌ Нет активных заявок", show_alert=True)

    except Exception as e:
        logger.error(f"Error generating active orders report: {e}")
        await callback.answer("❌ Ошибка при создании отчета", show_alert=True)


@router.callback_query(F.data == "back_to_main_menu")
@handle_errors
async def callback_back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    message_obj = callback.message
    if isinstance(message_obj, Message):
        await message_obj.delete()
    await callback.answer()


@router.callback_query(F.data == "report_closed_orders_excel")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_closed_orders_excel(callback: CallbackQuery, user_role: str):
    """Генерация Excel с закрытыми заказами"""
    await safe_edit_message(callback, "⏳ Генерирую отчет по закрытым заказам...")

    from app.services.excel_export import ExcelExportService

    excel_service = ExcelExportService()
    filepath = await excel_service.export_closed_orders_to_excel(period_days=30)

    if not filepath:
        await safe_edit_message(
            callback,
            "❌ Не удалось создать отчет.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu")]
                ]
            ),
        )
        return

    # Отправляем файл
    from pathlib import Path

    from aiogram.types import FSInputFile

    file = FSInputFile(filepath, filename=Path(filepath).name)

    message_obj = callback.message
    if isinstance(message_obj, Message):
        await message_obj.answer_document(
            document=file,
            caption="✅ Закрытые заказы за 30 дней",
        )

    await safe_edit_message(
        callback,
        "✅ Отчет создан!",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu")]]
        ),
    )

    await callback.answer()


@router.callback_query(F.data == "report_masters_stats_excel")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_masters_stats_excel(callback: CallbackQuery, user_role: str, db: Database):
    """Показать список мастеров для выбора"""
    # Получаем всех утвержденных мастеров через ORM
    masters_data = await db.get_all_masters(only_approved=True, only_active=True)

    # Преобразуем в формат для совместимости
    masters = [{"id": master.id, "full_name": master.get_display_name()} for master in masters_data]

    if not masters:
        await safe_edit_message(
            callback,
            "❌ Нет утвержденных мастеров.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu")]
                ]
            ),
        )
        return

    # Создаем клавиатуру с мастерами (по 2 в ряд)
    keyboard = []
    for i in range(0, len(masters), 2):
        row = []
        for j in range(2):
            if i + j < len(masters):
                master = masters[i + j]
                row.append(
                    InlineKeyboardButton(
                        text=f"👨‍🔧 {master['full_name']}",
                        callback_data=f"master_stat:{master['id']}",
                    )
                )
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu")])

    await safe_edit_message(
        callback,
        "👨‍🔧 <b>Выберите мастера:</b>\n\n"
        "Будет создан отчет со всеми заявками выбранного мастера.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard,
        ),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("master_stat:"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_master_stat(callback: CallbackQuery, user_role: str):
    """Генерация отчета по выбранному мастеру"""
    data = callback.data or ""
    try:
        master_id = int(data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Некорректный идентификатор мастера", show_alert=True)
        return

    await safe_edit_message(callback, "⏳ Генерирую отчет по мастеру...")

    from app.services.excel_export import ExcelExportService

    excel_service = ExcelExportService()
    filepath = await excel_service.export_master_orders_to_excel(master_id)

    if not filepath:
        await safe_edit_message(
            callback,
            "❌ Не удалось создать отчет.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 Назад", callback_data="report_masters_stats_excel"
                        )
                    ]
                ]
            ),
        )
        return

    # Отправляем файл
    import logging
    from pathlib import Path

    from aiogram.types import FSInputFile

    logger = logging.getLogger(__name__)

    try:
        # Проверяем, что файл существует
        if not Path(filepath).exists():
            logger.error(f"Excel файл не найден: {filepath}")
            await safe_edit_message(
                callback,
                "❌ Файл отчета не найден.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🔙 Назад", callback_data="report_masters_stats_excel"
                            )
                        ]
                    ]
                ),
            )
            return

        # Создаем безопасное имя файла
        safe_filename = str(Path(filepath).name).encode("utf-8", errors="ignore").decode("utf-8")
        file = FSInputFile(filepath, filename=safe_filename)

        logger.info(
            f"Отправляем Excel файл: {filepath} (размер: {Path(filepath).stat().st_size} байт)"
        )

        message_obj = callback.message
        if isinstance(message_obj, Message):
            await message_obj.answer_document(
                document=file,
                caption="✅ Отчет по мастеру готов!",
            )

        logger.info(f"Excel файл успешно отправлен: {filepath}")

    except Exception as e:
        logger.error(f"Ошибка отправки Excel файла {filepath}: {e}")
        await safe_edit_message(
            callback,
            f"❌ Ошибка отправки файла: {e!s}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 Назад", callback_data="report_masters_stats_excel"
                        )
                    ]
                ]
            ),
        )
        return

    await safe_edit_message(
        callback,
        "✅ Отчет создан!",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 К списку мастеров", callback_data="report_masters_stats_excel"
                    )
                ]
            ]
        ),
    )

    await callback.answer()


# ==================== НОВЫЕ ОТЧЕТЫ ПО МАСТЕРАМ ====================


@router.callback_query(F.data == "report_daily_master_summary")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_report_daily_master_summary(callback: CallbackQuery, user_role: str):
    """Выбор ежедневной сводки по мастерам"""
    await safe_edit_message(
        callback,
        "📊 <b>Ежедневная сводка по мастерам</b>\n\n" "Выберите день:",
        reply_markup=get_daily_master_report_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "report_weekly_master_summary")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_report_weekly_master_summary(callback: CallbackQuery, user_role: str):
    """Выбор еженедельной сводки по мастерам"""
    await safe_edit_message(
        callback,
        "📈 <b>Еженедельная сводка по мастерам</b>\n\n" "Выберите неделю:",
        reply_markup=get_weekly_master_report_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "report_monthly_master_summary")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_report_monthly_master_summary(callback: CallbackQuery, user_role: str):
    """Выбор ежемесячной сводки по мастерам"""
    await safe_edit_message(
        callback,
        "📊 <b>Ежемесячная сводка по мастерам</b>\n\n" "Выберите месяц:",
        reply_markup=get_monthly_master_report_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("daily_master_report_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_generate_daily_master_report(callback: CallbackQuery, user_role: str):
    """Генерация ежедневной сводки по мастерам"""
    from app.utils.helpers import MOSCOW_TZ

    data = callback.data or ""
    try:
        date_str = data.split("_")[-1]
    except IndexError:
        await callback.answer("❌ Некорректные данные отчета", show_alert=True)
        return
    report_date = datetime.strptime(date_str, "%Y-%m-%d")
    # Добавляем московский часовой пояс
    report_date = report_date.replace(tzinfo=MOSCOW_TZ)

    try:
        await safe_edit_message(callback, "⏳ Генерирую ежедневную сводку по мастерам...")
    except Exception as e:
        logger.warning(f"Could not edit message: {e}")
        # Продолжаем выполнение, даже если не удалось отредактировать сообщение

    service = MasterReportsService()
    filepath = await service.generate_daily_master_report(report_date)

    if not filepath:
        try:
            await safe_edit_message(
                callback,
                f"📊 <b>Ежедневная сводка за {report_date.strftime('%d.%m.%Y')}</b>\n\n"
                f"❌ За этот день не было завершенных заказов.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🔙 Назад",
                                callback_data="reports_menu",
                            )
                        ]
                    ]
                ),
            )
        except Exception as e:
            logger.warning(f"Could not edit message for no data: {e}")
            message_obj = callback.message
            if isinstance(message_obj, Message):
                await message_obj.answer(
                    f"📊 <b>Ежедневная сводка за {report_date.strftime('%d.%m.%Y')}</b>\n\n"
                    f"❌ За этот день не было завершенных заказов.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu")]
                        ]
                    ),
                )
        await callback.answer()
        return

    # Отправляем файл
    from aiogram.types import BufferedInputFile

    with open(filepath, "rb") as f:
        file_data = f.read()

    file_input = BufferedInputFile(file_data, filename=f"daily_master_summary_{date_str}.xlsx")

    try:
        message_obj = callback.message
        if isinstance(message_obj, Message):
            await message_obj.answer_document(
                document=file_input,
                caption=f"📊 <b>Ежедневная сводка по мастерам за {report_date.strftime('%d.%m.%Y')}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu")]
                    ]
                ),
            )

            await message_obj.delete()
    except Exception as e:
        logger.warning(f"Could not send document or delete message: {e}")
        # Пытаемся отправить файл как обычное сообщение
        try:
            message_obj = callback.message
            if isinstance(message_obj, Message):
                await message_obj.answer(
                    f"📊 <b>Ежедневная сводка по мастерам за {report_date.strftime('%d.%m.%Y')}</b>\n\n"
                    f"Файл создан: {filepath}",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu")]
                        ]
                    ),
                )
        except Exception as e2:
            logger.error(f"Could not send fallback message: {e2}")

    await callback.answer()


@router.callback_query(F.data.startswith("weekly_master_report_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_generate_weekly_master_report(callback: CallbackQuery, user_role: str):
    """Генерация еженедельной сводки по мастерам"""
    from app.utils.helpers import MOSCOW_TZ

    data = callback.data or ""
    try:
        date_str = data.split("_")[-1]
    except IndexError:
        await callback.answer("❌ Некорректные данные отчета", show_alert=True)
        return
    week_start = datetime.strptime(date_str, "%Y-%m-%d")
    # Добавляем московский часовой пояс
    week_start = week_start.replace(tzinfo=MOSCOW_TZ)

    await safe_edit_message(callback, "⏳ Генерирую еженедельную сводку по мастерам...")

    service = MasterReportsService()
    filepath = await service.generate_weekly_master_report(week_start)

    if not filepath:
        await safe_edit_message(
            callback,
            f"📈 <b>Еженедельная сводка за {week_start.strftime('%d.%m.%Y')} - {(week_start + timedelta(days=6)).strftime('%d.%m.%Y')}</b>\n\n"
            f"❌ За эту неделю не было завершенных заказов.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 Назад",
                            callback_data="reports_menu",
                        )
                    ]
                ]
            ),
        )
        await callback.answer()
        return

    # Отправляем файл
    from aiogram.types import BufferedInputFile

    with open(filepath, "rb") as f:
        file_data = f.read()

    file_input = BufferedInputFile(file_data, filename=f"weekly_master_summary_{date_str}.xlsx")

    message_obj = callback.message
    if isinstance(message_obj, Message):
        await message_obj.answer_document(
            document=file_input,
            caption=f"📈 <b>Еженедельная сводка по мастерам за {week_start.strftime('%d.%m.%Y')} - {(week_start + timedelta(days=6)).strftime('%d.%m.%Y')}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu")]
                ]
            ),
        )

        await message_obj.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("monthly_master_report_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_generate_monthly_master_report(callback: CallbackQuery, user_role: str):
    """Генерация ежемесячной сводки по мастерам"""
    from app.utils.helpers import MOSCOW_TZ

    data = callback.data or ""
    try:
        date_str = data.split("_")[-1]
    except IndexError:
        await callback.answer("❌ Некорректные данные отчета", show_alert=True)
        return
    month_start = datetime.strptime(date_str, "%Y-%m-%d")
    # Добавляем московский часовой пояс
    month_start = month_start.replace(tzinfo=MOSCOW_TZ)

    await safe_edit_message(callback, "⏳ Генерирую ежемесячную сводку по мастерам...")

    service = MasterReportsService()
    filepath = await service.generate_monthly_master_report(month_start)

    if not filepath:
        await safe_edit_message(
            callback,
            f"📊 <b>Ежемесячная сводка за {month_start.strftime('%B %Y')}</b>\n\n"
            f"❌ За этот месяц не было завершенных заказов.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 Назад",
                            callback_data="reports_menu",
                        )
                    ]
                ]
            ),
        )
        await callback.answer()
        return

    # Отправляем файл
    from aiogram.types import BufferedInputFile

    with open(filepath, "rb") as f:
        file_data = f.read()

    file_input = BufferedInputFile(file_data, filename=f"monthly_master_summary_{date_str}.xlsx")

    message_obj = callback.message
    if isinstance(message_obj, Message):
        await message_obj.answer_document(
            document=file_input,
            caption=f"📊 <b>Ежемесячная сводка по мастерам за {month_start.strftime('%B %Y')}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu")]
                ]
            ),
        )

        await message_obj.delete()
    await callback.answer()


@router.callback_query(F.data == "close_menu")
@handle_errors
async def callback_close_menu(callback: CallbackQuery):
    """Закрытие меню"""
    message_obj = callback.message
    if isinstance(message_obj, Message):
        await message_obj.delete()
    await callback.answer()
