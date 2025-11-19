"""
Сервис для генерации финансовых отчетов
"""

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.database import DatabaseType, get_database
from app.database.models import FinancialReport, MasterFinancialReport, Order
from app.utils.helpers import get_now


if TYPE_CHECKING:
    from app.database.db import Database as LegacyDatabase


logger = logging.getLogger(__name__)


class FinancialReportsService:
    """Сервис для работы с финансовыми отчетами"""

    def __init__(self) -> None:
        self.db: DatabaseType = get_database()

    def _get_legacy_db(self) -> "LegacyDatabase":
        """
        Получить legacy-реализацию БД для финансовых отчетов.
        """
        from app.database.db import Database as LegacyDatabaseRuntime

        if not isinstance(self.db, LegacyDatabaseRuntime):
            raise RuntimeError("FinancialReportsService поддерживает только legacy Database")

        return self.db

    async def generate_daily_report(self, date: datetime) -> FinancialReport:
        """
        Генерация ежедневного отчета

        Args:
            date: Дата отчета

        Returns:
            Объект финансового отчета
        """
        # Сохраняем часовой пояс при замене времени
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        if date.tzinfo and not start_date.tzinfo:
            start_date = start_date.replace(tzinfo=date.tzinfo)
        end_date = start_date + timedelta(days=1)

        return await self._generate_report(
            report_type="DAILY", period_start=start_date, period_end=end_date
        )

    async def generate_weekly_report(self, week_start: datetime) -> FinancialReport:
        """
        Генерация еженедельного отчета

        Args:
            week_start: Начало недели (понедельник)

        Returns:
            Объект финансового отчета
        """
        # Сохраняем часовой пояс при замене времени
        start_date = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        if week_start.tzinfo and not start_date.tzinfo:
            start_date = start_date.replace(tzinfo=week_start.tzinfo)
        end_date = start_date + timedelta(days=7)

        return await self._generate_report(
            report_type="WEEKLY", period_start=start_date, period_end=end_date
        )

    async def generate_monthly_report(self, year: int, month: int) -> FinancialReport:
        """
        Генерация месячного отчета

        Args:
            year: Год
            month: Месяц (1-12)

        Returns:
            Объект финансового отчета
        """
        from app.utils.helpers import MOSCOW_TZ

        # Создаем даты с московским часовым поясом
        start_date = datetime(year, month, 1, tzinfo=MOSCOW_TZ)
        if month == 12:
            end_date = datetime(year + 1, 1, 1, tzinfo=MOSCOW_TZ)
        else:
            end_date = datetime(year, month + 1, 1, tzinfo=MOSCOW_TZ)

        return await self._generate_report(
            report_type="MONTHLY", period_start=start_date, period_end=end_date
        )

    async def _generate_report(
        self, report_type: str, period_start: datetime, period_end: datetime
    ) -> FinancialReport:
        """
        Генерация отчета за указанный период

        Args:
            report_type: Тип отчета (DAILY, WEEKLY, MONTHLY)
            period_start: Начало периода
            period_end: Конец периода

        Returns:
            Объект финансового отчета
        """
        await self.db.connect()

        try:
            legacy_db = self._get_legacy_db()

            # Получаем все завершенные заказы за период
            orders = await legacy_db.get_orders_by_period(period_start, period_end, status="CLOSED")

            if not orders:
                # Создаем пустой отчет
                report = FinancialReport(
                    report_type=report_type,
                    period_start=period_start,
                    period_end=period_end,
                    created_at=get_now(),
                )
                legacy_db = self._get_legacy_db()
                report.id = await legacy_db.create_financial_report(report)
                return report

            # Подсчитываем общие показатели
            total_orders = len(orders)
            # Общая сумма включает расходный материал
            total_amount = sum(
                (order.total_amount or 0) + (order.materials_cost or 0) for order in orders
            )
            total_materials_cost = sum(order.materials_cost or 0 for order in orders)
            total_net_profit = total_amount - total_materials_cost
            total_company_profit = sum(order.company_profit or 0 for order in orders)
            total_master_profit = sum(order.master_profit or 0 for order in orders)
            average_check = total_amount / total_orders if total_orders > 0 else 0

            # Создаем основной отчет
            report = FinancialReport(
                report_type=report_type,
                period_start=period_start,
                period_end=period_end,
                total_orders=total_orders,
                total_amount=total_amount,
                total_materials_cost=total_materials_cost,
                total_net_profit=total_net_profit,
                total_company_profit=total_company_profit,
                total_master_profit=total_master_profit,
                average_check=average_check,
                created_at=get_now(),
            )

            # Сохраняем отчет в базу (legacy)
            report.id = await legacy_db.create_financial_report(report)

            # Генерируем отчеты по мастерам
            await self._generate_master_reports(report.id, orders)

            return report

        finally:
            await self.db.disconnect()

    async def _generate_master_reports(self, report_id: int, orders: list[Order]):
        """
        Генерация отчетов по мастерам

        Args:
            report_id: ID основного отчета
            orders: Список заказов
        """
        # Группируем заказы по мастерам
        masters_orders: dict[int, list[Order]] = {}
        for order in orders:
            if order.assigned_master_id:
                if order.assigned_master_id not in masters_orders:
                    masters_orders[order.assigned_master_id] = []
                masters_orders[order.assigned_master_id].append(order)

        # Создаем отчеты для каждого мастера
        for master_id, master_orders in masters_orders.items():
            # Получаем информацию о мастере
            legacy_db = self._get_legacy_db()
            master = await legacy_db.get_master_by_id(master_id)
            if not master:
                continue

            # Подсчитываем показатели мастера
            orders_count = len(master_orders)
            # Общая сумма включает расходный материал
            total_amount = sum(
                (order.total_amount or 0) + (order.materials_cost or 0) for order in master_orders
            )
            total_materials_cost = sum(order.materials_cost or 0 for order in master_orders)
            total_net_profit = total_amount - total_materials_cost
            total_company_profit = sum(order.company_profit or 0 for order in master_orders)
            total_master_profit = sum(order.master_profit or 0 for order in master_orders)
            average_check = total_amount / orders_count if orders_count > 0 else 0
            reviews_count = sum(1 for order in master_orders if order.has_review is True)
            out_of_city_count = sum(1 for order in master_orders if order.out_of_city is True)

            # Создаем отчет по мастеру
            master_report = MasterFinancialReport(
                report_id=report_id,
                master_id=master_id,
                master_name=master.get_display_name(),
                orders_count=orders_count,
                total_amount=total_amount,
                total_materials_cost=total_materials_cost,
                total_net_profit=total_net_profit,
                total_master_profit=total_master_profit,
                total_company_profit=total_company_profit,
                average_check=average_check,
                reviews_count=reviews_count,
                out_of_city_count=out_of_city_count,
            )

            await legacy_db.create_master_financial_report(master_report)

    async def get_report_summary(self, report_id: int) -> dict[str, Any]:
        """
        Получение сводки отчета

        Args:
            report_id: ID отчета

        Returns:
            Словарь с данными отчета
        """
        await self.db.connect()

        try:
            legacy_db = self._get_legacy_db()

            report = await legacy_db.get_financial_report_by_id(report_id)
            if not report:
                return {}

            master_reports = await legacy_db.get_master_reports_by_report_id(report_id)

            return {
                "report": report,
                "master_reports": master_reports,
                "summary": {
                    "total_masters": len(master_reports),
                    "most_profitable_master": (
                        max(master_reports, key=lambda x: x.total_master_profit)
                        if master_reports
                        else None
                    ),
                    "highest_average_check": (
                        max(master_reports, key=lambda x: x.average_check)
                        if master_reports
                        else None
                    ),
                },
            }

        finally:
            await self.db.disconnect()

    async def format_report_for_display(self, report_id: int) -> str:
        """
        Форматирование отчета для отображения в Telegram

        Args:
            report_id: ID отчета

        Returns:
            Отформатированный текст отчета
        """
        data = await self.get_report_summary(report_id)
        if not data:
            return "❌ Отчет не найден"

        report = data["report"]
        master_reports = data["master_reports"]

        # Определяем тип отчета
        period_text = ""
        if report.report_type == "DAILY":
            period_text = f"за {report.period_start.strftime('%d.%m.%Y')}"
        elif report.report_type == "WEEKLY":
            period_text = f"за неделю {report.period_start.strftime('%d.%m')} - {report.period_end.strftime('%d.%m.%Y')}"
        elif report.report_type == "MONTHLY":
            period_text = f"за {report.period_start.strftime('%B %Y')}"

        # Заголовок отчета
        text = f"📊 <b>Финансовый отчет {period_text}</b>\n\n"

        # Общие показатели
        text += "📈 <b>Общие показатели:</b>\n"
        text += f"• Заказов: {report.total_orders}\n"
        text += f"• Общая сумма: {report.total_amount:,.2f} ₽\n"
        text += f"• Расходный материал: {report.total_materials_cost:,.2f} ₽\n"
        text += f"• Чистая прибыль: {report.total_net_profit:,.2f} ₽\n"
        text += f"• Средний чек: {report.average_check:,.2f} ₽\n\n"

        # Распределение прибыли
        text += "💰 <b>Распределение прибыли:</b>\n"
        text += f"• Компания: {report.total_company_profit:,.2f} ₽\n"
        text += f"• Мастера: {report.total_master_profit:,.2f} ₽\n\n"

        # Статистика по типам техники
        await self.db.connect()
        try:
            legacy_db = self._get_legacy_db()
            orders = await legacy_db.get_orders_by_period(
                report.period_start, report.period_end, status="CLOSED"
            )
            if orders:
                # Подсчитываем количество заказов по типам техники
                equipment_stats: dict[str, int] = {}
                for order in orders:
                    equipment_type = order.equipment_type or "Не указано"
                    equipment_stats[equipment_type] = equipment_stats.get(equipment_type, 0) + 1

                if equipment_stats:
                    text += "🔧 <b>По типам техники:</b>\n"
                    # Сортируем по количеству (по убыванию)
                    sorted_equipment = sorted(
                        equipment_stats.items(), key=lambda x: x[1], reverse=True
                    )
                    for equipment_type, count in sorted_equipment:
                        percentage = (count / len(orders) * 100) if len(orders) > 0 else 0
                        text += f"• {equipment_type}: {count} ({percentage:.1f}%)\n"
                    text += "\n"
        finally:
            await self.db.disconnect()

        # Отчеты по мастерам
        if master_reports:
            text += f"👨‍🔧 <b>По мастерам ({len(master_reports)}):</b>\n"
            text += f"{'='*40}\n\n"

            for idx, master_report in enumerate(
                sorted(master_reports, key=lambda x: x.total_master_profit, reverse=True), 1
            ):
                text += f"<b>{idx}. {master_report.master_name}</b>\n"
                text += f"├ Заказов: {master_report.orders_count}\n"
                text += f"├ Общая сумма: {master_report.total_amount:,.2f} ₽\n"
                text += f"├ Расходники: {master_report.total_materials_cost:,.2f} ₽\n"
                text += f"├ Чистая прибыль: {master_report.total_net_profit:,.2f} ₽\n"
                text += f"├ Средний чек: {master_report.average_check:,.2f} ₽\n"
                text += f"├ К выплате мастеру: <b>{master_report.total_master_profit:,.2f} ₽</b>\n"
                text += f"└ Компания получила: {master_report.total_company_profit:,.2f} ₽\n"

                # Дополнительная информация
                extras = []
                if master_report.reviews_count > 0:
                    extras.append(f"⭐ Отзывы: {master_report.reviews_count}")
                if master_report.out_of_city_count > 0:
                    extras.append(f"🚗 Выезды: {master_report.out_of_city_count}")

                if extras:
                    text += f"  {' | '.join(extras)}\n"

                text += "\n"

        return text
