"""
Parser Analytics Service

Сервис для отслеживания и агрегации метрик парсера заявок из Telegram.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.orm_models import ParserAnalytics
from app.utils.helpers import get_now


logger = logging.getLogger(__name__)


class ParserAnalyticsService:
    """Сервис аналитики парсера"""

    def __init__(self, session_factory):
        """
        Args:
            session_factory: Фабрика сессий SQLAlchemy
        """
        self.session_factory = session_factory

    async def track_parse_event(
        self,
        message_id: int,
        group_id: int | None,
        success: bool,
        error_type: str | None = None,
       parsed_equipment_type: str | None = None,
        parsed_address: str | None = None,
        parsed_phone: str | None = None,
        processing_time_ms: int | None = None,
    ) -> None:
        """
        Записать событие парсинга в БД.

        Args:
            message_id: ID сообщения в Telegram
            group_id: ID группы-источника
            success: Успешно распарсено?
            error_type: Тип ошибки (если не успешно)
            parsed_equipment_type: Распознанный тип техники
            parsed_address: Распознанный адрес
            parsed_phone: Распознанный телефон
            processing_time_ms: Время обработки в миллисекундах
        """
        async with self.session_factory() as session:
            event = ParserAnalytics(
                message_id=message_id,
                group_id=group_id,
                success=success,
                error_type=error_type,
                parsed_equipment_type=parsed_equipment_type,
                parsed_address=parsed_address,
                parsed_phone=parsed_phone,
                processing_time_ms=processing_time_ms,
                created_at=get_now(),
            )
            session.add(event)
            await session.commit()
            logger.debug(f"Записано событие парсинга: message_id={message_id}, success={success}")

    async def mark_confirmed(self, message_id: int, confirmed: bool, created_order_id: int | None = None) -> None:
        """
        Отметить, что заявка была подтверждена/отклонена пользователем.

        Args:
            message_id: ID сообщения в Telegram
            confirmed: Подтверждено?
            created_order_id: ID созданной заявки (если подтверждено)
        """
        async with self.session_factory() as session:
            stmt = (
                select(ParserAnalytics)
                .where(ParserAnalytics.message_id == message_id)
                .order_by(ParserAnalytics.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            event = result.scalar_one_or_none()

            if event:
                event.confirmed = confirmed
                event.created_order_id = created_order_id
                await session.commit()
                logger.debug(f"Обновлено подтверждение: message_id={message_id}, confirmed={confirmed}")

    async def get_stats(self, period_days: int | None = None) -> dict[str, Any]:
        """
        Получить агрегированную статистику парсера.

        Args:
            period_days: Период в днях (None = все время)

        Returns:
            Словарь со статистикой
        """
        async with self.session_factory() as session:
            # Базовый запрос
            query = select(ParserAnalytics)

            # Фильтр по периоду
            if period_days:
                cutoff_date = get_now() - timedelta(days=period_days)
                query = query.where(ParserAnalytics.created_at >= cutoff_date)

            result = await session.execute(query)
            events = result.scalars().all()

            # Агрегация
            total = len(events)
            successful = sum(1 for e in events if e.success)
            failed = total - successful
            confirmed = sum(1 for e in events if e.confirmed is True)
            rejected = sum(1 for e in events if e.confirmed is False)
            pending = sum(1 for e in events if e.confirmed is None and e.success)

            # Средняя скорость
            processing_times = [e.processing_time_ms for e in events if e.processing_time_ms is not None]
            avg_processing_ms = sum(processing_times) / len(processing_times) if processing_times else 0

            # Типы ошибок
            error_breakdown = {}
            for event in events:
                if event.error_type:
                    error_breakdown[event.error_type] = error_breakdown.get(event.error_type, 0) + 1

            # Топ типов техники
            equipment_breakdown = {}
            for event in events:
                if event.parsed_equipment_type:
                    equip_type = event.parsed_equipment_type
                    equipment_breakdown[equip_type] = equipment_breakdown.get(equip_type, 0) + 1

            return {
                "total_parses": total,
                "successful_parses": successful,
                "failed_parses": failed,
                "success_rate": (successful / total * 100) if total > 0 else 0,
                "confirmed": confirmed,
                "rejected": rejected,
                "pending_confirmation": pending,
                "confirmation_rate": (confirmed / successful * 100) if successful > 0 else 0,
                "avg_processing_ms": round(avg_processing_ms, 2),
                "error_breakdown": error_breakdown,
                "equipment_breakdown": equipment_breakdown,
            }

    async def get_timeline(self, days: int = 7) -> list[dict[str, Any]]:
        """
        Получить временную линию парсингов.

        Args:
            days: Количество дней для анализа

        Returns:
            Список с данными по дням
        """
        async with self.session_factory() as session:
            cutoff_date = get_now() - timedelta(days=days)

            query = select(ParserAnalytics).where(ParserAnalytics.created_at >= cutoff_date)
            result = await session.execute(query)
            events = result.scalars().all()

            # Группировка по дням
            daily_stats = {}
            for event in events:
                day_key = event.created_at.date()
                if day_key not in daily_stats:
                    daily_stats[day_key] = {"total": 0, "successful": 0, "failed": 0, "confirmed": 0}

                daily_stats[day_key]["total"] += 1
                if event.success:
                    daily_stats[day_key]["successful"] += 1
                else:
                    daily_stats[day_key]["failed"] += 1
                if event.confirmed is True:
                    daily_stats[day_key]["confirmed"] += 1

            # Преобразование в список
            timeline = []
            for day in sorted(daily_stats.keys()):
                stats = daily_stats[day]
                timeline.append({
                    "date": day.strftime("%d.%m.%Y"),
                    "total": stats["total"],
                    "successful": stats["successful"],
                    "failed": stats["failed"],
                    "confirmed": stats["confirmed"],
                    "success_rate": (stats["successful"] / stats["total"] * 100) if stats["total"] > 0 else 0,
                })

            return timeline
