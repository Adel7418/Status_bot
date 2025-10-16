"""
Хэндлеры для работы с финансовыми отчетами
"""

from datetime import datetime, timedelta
from typing import List
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.config import UserRole
from app.decorators import handle_errors, require_role
from app.database.db import Database
from app.services.financial_reports import FinancialReportsService
from app.states import ReportStates
from app.utils.helpers import get_now

logger = logging.getLogger(__name__)
router = Router()


def get_reports_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню отчетов"""
    keyboard = [
        [
            InlineKeyboardButton(text="📋 Активные заявки (Excel)", callback_data="report_active_orders_excel"),
        ],
        [
            InlineKeyboardButton(text="📅 Ежедневный", callback_data="report_daily"),
            InlineKeyboardButton(text="📊 Еженедельный", callback_data="report_weekly"),
        ],
        [
            InlineKeyboardButton(text="📈 Месячный", callback_data="report_monthly"),
            InlineKeyboardButton(text="📋 Последние отчеты", callback_data="reports_list"),
        ],
        [
            InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu"),
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
                text=f"Сегодня ({today.strftime('%d.%m')})", 
                callback_data=f"daily_report_{today.strftime('%Y-%m-%d')}"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Вчера ({yesterday.strftime('%d.%m')})", 
                callback_data=f"daily_report_{yesterday.strftime('%Y-%m-%d')}"
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
    # Находим начало текущей недели (понедельник)
    days_since_monday = today.weekday()
    current_week_start = today - timedelta(days=days_since_monday)
    previous_week_start = current_week_start - timedelta(days=7)
    
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"Эта неделя ({current_week_start.strftime('%d.%m')} - {(current_week_start + timedelta(days=6)).strftime('%d.%m')})", 
                callback_data=f"weekly_report_{current_week_start.strftime('%Y-%m-%d')}"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Прошлая неделя ({previous_week_start.strftime('%d.%m')} - {(previous_week_start + timedelta(days=6)).strftime('%d.%m')})", 
                callback_data=f"weekly_report_{previous_week_start.strftime('%Y-%m-%d')}"
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
    previous_month = (current_month - timedelta(days=1)).replace(day=1)
    
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"Этот месяц ({current_month.strftime('%B %Y')})", 
                callback_data=f"monthly_report_{current_month.year}_{current_month.month}"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Прошлый месяц ({previous_month.strftime('%B %Y')})", 
                callback_data=f"monthly_report_{previous_month.year}_{previous_month.month}"
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
            InlineKeyboardButton(text="📄 Скачать Excel", callback_data=f"export_excel_{report_id}"),
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
        "📊 <b>Финансовые отчеты</b>\n\n"
        "Выберите тип отчета:",
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
    await message.answer(
        "📊 <b>Финансовые отчеты</b>\n\n"
        "Выберите тип отчета:",
        parse_mode="HTML",
        reply_markup=get_reports_menu_keyboard(),
    )


@router.callback_query(F.data == "reports_menu")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_reports_menu(callback: CallbackQuery, user_role: str):
    """Возврат в главное меню отчетов"""
    await callback.message.edit_text(
        "📊 <b>Финансовые отчеты</b>\n\n"
        "Выберите тип отчета:",
        parse_mode="HTML",
        reply_markup=get_reports_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "report_daily")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_report_daily(callback: CallbackQuery, user_role: str):
    """Выбор ежедневного отчета"""
    await callback.message.edit_text(
        "📅 <b>Ежедневный отчет</b>\n\n"
        "Выберите день:",
        parse_mode="HTML",
        reply_markup=get_daily_report_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "report_weekly")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_report_weekly(callback: CallbackQuery, user_role: str):
    """Выбор еженедельного отчета"""
    await callback.message.edit_text(
        "📊 <b>Еженедельный отчет</b>\n\n"
        "Выберите неделю:",
        parse_mode="HTML",
        reply_markup=get_weekly_report_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "report_monthly")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_report_monthly(callback: CallbackQuery, user_role: str):
    """Выбор месячного отчета"""
    await callback.message.edit_text(
        "📈 <b>Месячный отчет</b>\n\n"
        "Выберите месяц:",
        parse_mode="HTML",
        reply_markup=get_monthly_report_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("daily_report_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_generate_daily_report(callback: CallbackQuery, user_role: str):
    """Генерация ежедневного отчета"""
    from app.utils.helpers import MOSCOW_TZ
    
    date_str = callback.data.split("_")[-1]
    report_date = datetime.strptime(date_str, "%Y-%m-%d")
    # Добавляем московский часовой пояс
    report_date = report_date.replace(tzinfo=MOSCOW_TZ)
    
    await callback.message.edit_text("⏳ Генерирую ежедневный отчет...")
    
    service = FinancialReportsService()
    report = await service.generate_daily_report(report_date)
    
    if report.total_orders == 0:
        await callback.message.edit_text(
            f"📅 <b>Ежедневный отчет за {report_date.strftime('%d.%m.%Y')}</b>\n\n"
            f"❌ За этот день не было завершенных заказов.",
            parse_mode="HTML",
            reply_markup=get_report_actions_keyboard(report.id),
        )
    else:
        report_text = await service.format_report_for_display(report.id)
        await callback.message.edit_text(
            report_text,
            parse_mode="HTML",
            reply_markup=get_report_actions_keyboard(report.id),
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("weekly_report_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_generate_weekly_report(callback: CallbackQuery, user_role: str):
    """Генерация еженедельного отчета"""
    from app.utils.helpers import MOSCOW_TZ
    
    date_str = callback.data.split("_")[-1]
    week_start = datetime.strptime(date_str, "%Y-%m-%d")
    # Добавляем московский часовой пояс
    week_start = week_start.replace(tzinfo=MOSCOW_TZ)
    
    await callback.message.edit_text("⏳ Генерирую еженедельный отчет...")
    
    service = FinancialReportsService()
    report = await service.generate_weekly_report(week_start)
    
    if report.total_orders == 0:
        await callback.message.edit_text(
            f"📊 <b>Еженедельный отчет за {week_start.strftime('%d.%m')} - {(week_start + timedelta(days=6)).strftime('%d.%m.%Y')}</b>\n\n"
            f"❌ За эту неделю не было завершенных заказов.",
            parse_mode="HTML",
            reply_markup=get_report_actions_keyboard(report.id),
        )
    else:
        report_text = await service.format_report_for_display(report.id)
        await callback.message.edit_text(
            report_text,
            parse_mode="HTML",
            reply_markup=get_report_actions_keyboard(report.id),
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("monthly_report_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_generate_monthly_report(callback: CallbackQuery, user_role: str):
    """Генерация месячного отчета"""
    parts = callback.data.split("_")[-2:]
    year = int(parts[0])
    month = int(parts[1])
    
    await callback.message.edit_text("⏳ Генерирую месячный отчет...")
    
    service = FinancialReportsService()
    report = await service.generate_monthly_report(year, month)
    
    if report.total_orders == 0:
        month_name = datetime(year, month, 1).strftime('%B %Y')
        await callback.message.edit_text(
            f"📈 <b>Месячный отчет за {month_name}</b>\n\n"
            f"❌ За этот месяц не было завершенных заказов.",
            parse_mode="HTML",
            reply_markup=get_report_actions_keyboard(report.id),
        )
    else:
        report_text = await service.format_report_for_display(report.id)
        await callback.message.edit_text(
            report_text,
            parse_mode="HTML",
            reply_markup=get_report_actions_keyboard(report.id),
        )
    
    await callback.answer()


@router.callback_query(F.data == "reports_list")
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_reports_list(callback: CallbackQuery, user_role: str):
    """Список последних отчетов"""
    db = Database()
    await db.connect()
    
    try:
        reports = await db.get_latest_reports(limit=10)
        
        if not reports:
            await callback.message.edit_text(
                "📋 <b>Последние отчеты</b>\n\n"
                "❌ Отчетов пока нет.",
                parse_mode="HTML",
                reply_markup=get_reports_menu_keyboard(),
            )
            return
        
        text = "📋 <b>Последние отчеты:</b>\n\n"
        keyboard = []
        
        for i, report in enumerate(reports[:5], 1):
            period_text = ""
            if report.report_type == "DAILY":
                period_text = report.period_start.strftime('%d.%m.%Y')
            elif report.report_type == "WEEKLY":
                period_text = f"{report.period_start.strftime('%d.%m')} - {report.period_end.strftime('%d.%m.%Y')}"
            elif report.report_type == "MONTHLY":
                period_text = report.period_start.strftime('%B %Y')
            
            text += f"{i}. {report.report_type.lower()} ({period_text}) - {report.total_orders} заказов\n"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{report.report_type.lower()} {period_text}",
                    callback_data=f"view_report_{report.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="reports_menu")])
        
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
        
    finally:
        await db.disconnect()
    
    await callback.answer()


@router.callback_query(F.data.startswith("view_report_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_view_report(callback: CallbackQuery, user_role: str):
    """Просмотр существующего отчета"""
    report_id = int(callback.data.split("_")[-1])
    
    service = FinancialReportsService()
    report_text = await service.format_report_for_display(report_id)
    
    if not report_text or "не найден" in report_text:
        await callback.message.edit_text(
            "❌ Отчет не найден.",
            reply_markup=get_reports_menu_keyboard(),
        )
    else:
        await callback.message.edit_text(
            report_text,
            parse_mode="HTML",
            reply_markup=get_report_actions_keyboard(report_id),
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("export_excel_"))
@require_role([UserRole.ADMIN, UserRole.DISPATCHER])
@handle_errors
async def callback_export_excel(callback: CallbackQuery, user_role: str):
    """Экспорт отчета в Excel"""
    report_id = int(callback.data.split("_")[-1])
    
    await callback.answer("⏳ Создаю Excel файл...")
    await callback.message.edit_text("📊 Генерирую Excel отчет, подождите...")
    
    try:
        from app.services.excel_export import ExcelExportService
        from aiogram.types import FSInputFile
        
        excel_service = ExcelExportService()
        filepath = await excel_service.export_report_to_excel(report_id)
        
        if not filepath:
            await callback.message.edit_text(
                "❌ Ошибка при создании Excel файла.",
                reply_markup=get_reports_menu_keyboard(),
            )
            return
        
        # Отправляем файл пользователю
        file = FSInputFile(filepath)
        await callback.message.answer_document(
            file,
            caption="📄 Финансовый отчет в формате Excel"
        )
        
        # Возвращаем меню
        await callback.message.edit_text(
            "✅ Excel файл успешно создан и отправлен!",
            reply_markup=get_reports_menu_keyboard(),
        )
        
        # Удаляем временный файл
        import os
        if os.path.exists(filepath):
            os.remove(filepath)
            
    except Exception as e:
        logger.error(f"Error exporting to Excel: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при экспорте: {str(e)}",
            reply_markup=get_reports_menu_keyboard(),
        )


@router.callback_query(F.data == "report_active_orders_excel")
@handle_errors
async def callback_report_active_orders_excel(callback: CallbackQuery, user_role: str):
    """
    Экспорт активных заявок в Excel
    
    Args:
        callback: Callback query
        user_role: Роль пользователя
    """
    if user_role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer("📊 Генерирую отчет...", show_alert=False)
    
    try:
        from app.services.active_orders_export import ActiveOrdersExportService
        
        export_service = ActiveOrdersExportService()
        filepath = await export_service.export_active_orders_to_excel()
        
        if filepath:
            # Отправляем файл
            from aiogram.types import FSInputFile
            
            file = FSInputFile(filepath)
            await callback.message.answer_document(
                file,
                caption="📋 <b>Отчет по активным заявкам</b>\n\n"
                        "В файле указаны все незакрытые заявки:\n"
                        "• Статус и время создания\n"
                        "• Назначенный мастер\n"
                        "• Контакты клиента\n"
                        "• Запланированное время\n\n"
                        "Сводка по статусам в конце файла.",
                parse_mode="HTML"
            )
            
            logger.info(f"Active orders report sent to {callback.from_user.id}")
        else:
            await callback.answer("❌ Нет активных заявок", show_alert=True)
    
    except Exception as e:
        logger.error(f"Error generating active orders report: {e}")
        await callback.answer("❌ Ошибка при создании отчета", show_alert=True)


@router.callback_query(F.data == "close_menu")
@handle_errors
async def callback_close_menu(callback: CallbackQuery):
    """Закрытие меню"""
    await callback.message.delete()
    await callback.answer()


