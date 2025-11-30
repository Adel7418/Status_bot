"""
Handler для аналитики парсера

Команда /parser_stats для отображения статистики работы парсера.
"""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from app.decorators import require_role
from app.services.parser_analytics import ParserAnalyticsService
from app.database.orm_database import ORMDatabase


logger = logging.getLogger(__name__)
router = Router()


def create_bar_chart(value: float, max_value: float, width: int = 10) -> str:
    """
    Создать визуальный бар-график используя Unicode блоки.
    
    Args:
        value: Значение для отображения
        max_value: Максимальное значение (100%)
        width: Ширина графика в символах
        
    Returns:
        Строка с визуализацией
    """
    if max_value == 0:
        return "░" * width
    
    ratio = min(value / max_value, 1.0)
    filled = int(ratio * width)
    
    # Используем разные символы для визуализации
    bar = "█" * filled + "░" * (width - filled)
    return bar


def format_percentage(value: float) -> str:
    """Форматировать процент с цветовым индикатором"""
    if value >= 80:
        return f"🟢 {value:.1f}%"
    elif value >= 60:
        return f"🟡 {value:.1f}%"
    elif value >= 40:
        return f"🟠 {value:.1f}%"
    else:
        return f"🔴 {value:.1f}%"


@router.message(Command("parser_stats"))
@require_role(["admin", "dispatcher"])
async def cmd_parser_stats(message: Message, db: ORMDatabase, user_role: str = "UNKNOWN"):
    """
    Отображение статистики парсера.
    """
    analytics_service = ParserAnalyticsService(db.session_factory)
    
    try:
        # Получаем статистику за разные периоды
        stats_today = await analytics_service.get_stats(period_days=1)
        stats_week = await analytics_service.get_stats(period_days=7)
        stats_month = await analytics_service.get_stats(period_days=30)
        stats_all = await analytics_service.get_stats()
        
        # Формируем сообщение
        text = "📊 <b>Аналитика парсера заявок</b>\n\n"
        
        # Общая статистика
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📈 <b>Сегодня</b>\n"
        text += f"├ Всего: {stats_today['total_parses']}\n"
        text += f"├ Успешно: {stats_today['successful_parses']}\n"
        text += f"├ Ошибок: {stats_today['failed_parses']}\n"
        text += f"├ Успех: {format_percentage(stats_today['success_rate'])}\n"
        text += f"└ Подтверждено: {stats_today['confirmed']}/{stats_today['successful_parses']}\n"
        text += "\n"
        
        text += f"📅 <b>За неделю</b>\n"
        text += f"├ Всего: {stats_week['total_parses']}\n"
        text += f"├ Успешно: {stats_week['successful_parses']}\n"
        text += f"├ Успех: {format_percentage(stats_week['success_rate'])}\n"
        text += f"└ Подтверждено: {stats_week['confirmed']}/{stats_week['successful_parses']}\n"
        text += "\n"
        
        text += f"📊 <b>За месяц</b>\n"
        text += f"├ Всего: {stats_month['total_parses']}\n"
        text += f"├ Успешно: {stats_month['successful_parses']}\n"
        text += f"├ Успех: {format_percentage(stats_month['success_rate'])}\n"
        text += f"└ Подтверждено: {stats_month['confirmed']}/{stats_month['successful_parses']}\n"
        text += "\n"
        
        # Средняя скорость
        if stats_all['avg_processing_ms'] > 0:
            text += f"⚡ <b>Средняя скорость:</b> {stats_all['avg_processing_ms']:.0f}ms\n\n"
        
        # Топ типов техники
        if stats_week['equipment_breakdown']:
            text += "━━━━━━━━━━━━━━━━━━━━\n"
            text += "🔧 <b>Топ типов техники (неделя)</b>\n"
            equipment_sorted = sorted(
                stats_week['equipment_breakdown'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            max_count = equipment_sorted[0][1] if equipment_sorted else 1
            for equip_type, count in equipment_sorted:
                bar = create_bar_chart(count, max_count, width=8)
                text += f"├ {bar} {equip_type}: {count}\n"
            text += "\n"
        
        # Ошибки
        if stats_week['error_breakdown']:
            text += "━━━━━━━━━━━━━━━━━━━━\n"
            text += "⚠️ <b>Типы ошибок (неделя)</b>\n"
            error_sorted = sorted(
                stats_week['error_breakdown'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            for error_type, count in error_sorted:
                text += f"├ {error_type}: {count}\n"
            text += "\n"
        
        # Кнопки для детальной статистики
        kb = InlineKeyboardBuilder()
        kb.row(
            InlineKeyboardButton(text="📈 График за неделю", callback_data="parser_stats:timeline:7"),
            InlineKeyboardButton(text="📊 График за месяц", callback_data="parser_stats:timeline:30"),
        )
        kb.row(
            InlineKeyboardButton(text="🔄 Обновить", callback_data="parser_stats:refresh"),
        )
        
        await message.answer(text, parse_mode="HTML", reply_markup=kb.as_markup())
        
    except Exception as e:
        logger.exception("Ошибка при получении статистики парсера")
        await message.answer(f"❌ Ошибка при получении статистики: {str(e)}")


@router.callback_query(F.data.startswith("parser_stats:"))
async def callback_parser_stats(callback: CallbackQuery, db: ORMDatabase):
    """
    Обработка кнопок статистики парсера.
    """
    action = callback.data.split(":")[1]
    
    if action == "refresh":
        # Просто вызываем обновление
        analytics_service = ParserAnalyticsService(db.session_factory)
        stats_today = await analytics_service.get_stats(period_days=1)
        await callback.answer(f"🔄 Обновлено! Сегодня: {stats_today['total_parses']} парсингов")
        # Можно обновить сообщение, но это требует больше кода
        return
    
    elif action == "timeline":
        days = int(callback.data.split(":")[2])
        analytics_service = ParserAnalyticsService(db.session_factory)
        timeline = await analytics_service.get_timeline(days=days)
        
        # Формируем график
        text = f"📈 <b>График за {days} дней</b>\n\n"
        
        if timeline:
            max_total = max(day['total'] for day in timeline)
            
            for day in timeline[-7:]:  # Показываем последние 7 дней
                bar = create_bar_chart(day['total'], max_total, width=10)
                text += f"{day['date']}\n"
                text += f"{bar} {day['total']} ({format_percentage(day['success_rate'])})\n"
                text += f"✅{day['successful']} ❌{day['failed']} ☑️{day['confirmed']}\n\n"
        else:
            text += "Нет данных за этот период"
        
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="parser_stats:refresh"))
        
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.as_markup())
        await callback.answer()
