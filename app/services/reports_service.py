"""
Сервис для генерации и отправки отчетов
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.database import Database
from app.repositories.order_repository_extended import OrderRepositoryExtended
from app.utils.helpers import get_now


logger = logging.getLogger(__name__)


class ReportsService:
    """Сервис для генерации отчетов"""

    def __init__(self):
        self.db = Database()
        self._order_repo_extended = None

    async def _get_extended_repo(self) -> OrderRepositoryExtended:
        """Получить расширенный репозиторий"""
        if self._order_repo_extended is None:
            self._order_repo_extended = OrderRepositoryExtended(self.db.connection)
        return self._order_repo_extended

    async def generate_daily_report(self) -> dict[str, Any]:
        """Генерирует ежедневный отчет"""
        await self.db.connect()

        try:
            today = get_now().date()
            yesterday = today - timedelta(days=1)

            # Статистика за вчера
            orders_stats = await self._get_orders_stats(yesterday, today)
            masters_stats = await self._get_masters_stats(yesterday, today)
            closed_orders = await self._get_closed_orders_list(yesterday, today)

            return {
                "type": "daily",
                "period": f"{yesterday.strftime('%d.%m.%Y')}",
                "date_generated": get_now().isoformat(),
                "start_date": yesterday,
                "end_date": today,
                "orders": orders_stats,
                "masters": masters_stats,
                "summary": await self._get_summary_stats(yesterday, today),
                "closed_orders": closed_orders,
            }

        finally:
            await self.db.disconnect()

    async def generate_weekly_report(self) -> dict[str, Any]:
        """Генерирует еженедельный отчет"""
        await self.db.connect()

        try:
            today = get_now().date()
            current_week_start = today - timedelta(
                days=today.weekday()
            )  # понедельник текущей недели
            prev_week_end = current_week_start - timedelta(days=1)  # воскресенье прошлой недели
            prev_week_start = prev_week_end - timedelta(days=6)  # понедельник прошлой недели

            orders_stats = await self._get_orders_stats(
                prev_week_start, prev_week_end + timedelta(days=1)
            )
            masters_stats = await self._get_masters_stats(
                prev_week_start, prev_week_end + timedelta(days=1)
            )
            closed_orders = await self._get_closed_orders_list(
                prev_week_start, prev_week_end + timedelta(days=1)
            )

            return {
                "type": "weekly",
                "period": f"{prev_week_start.strftime('%d.%m.%Y')} - {prev_week_end.strftime('%d.%m.%Y')}",
                "date_generated": get_now().isoformat(),
                "orders": orders_stats,
                "masters": masters_stats,
                "summary": await self._get_summary_stats(
                    prev_week_start, prev_week_end + timedelta(days=1)
                ),
                "closed_orders": closed_orders,
            }

        finally:
            await self.db.disconnect()

    async def generate_monthly_report(self) -> dict[str, Any]:
        """Генерирует ежемесячный отчет"""
        await self.db.connect()

        try:
            today = get_now().date()
            month_start = today.replace(day=1)
            if today.month == 12:
                month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

            orders_stats = await self._get_orders_stats(month_start, month_end + timedelta(days=1))
            masters_stats = await self._get_masters_stats(
                month_start, month_end + timedelta(days=1)
            )
            closed_orders = await self._get_closed_orders_list(
                month_start, month_end + timedelta(days=1)
            )

            return {
                "type": "monthly",
                "period": f"{month_start.strftime('%d.%m.%Y')} - {month_end.strftime('%d.%m.%Y')}",
                "date_generated": get_now().isoformat(),
                "orders": orders_stats,
                "masters": masters_stats,
                "summary": await self._get_summary_stats(
                    month_start, month_end + timedelta(days=1)
                ),
                "closed_orders": closed_orders,
            }

        finally:
            await self.db.disconnect()

    async def _get_orders_stats(self, start_date, end_date) -> dict[str, Any]:
        """Получает статистику по заказам за период"""
        cursor = await self.db.connection.execute(
            """
            SELECT
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'NEW' THEN 1 ELSE 0 END) as new_orders,
                SUM(CASE WHEN status = 'ASSIGNED' THEN 1 ELSE 0 END) as assigned_orders,
                SUM(CASE WHEN status = 'ACCEPTED' THEN 1 ELSE 0 END) as accepted_orders,
                SUM(CASE WHEN status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress_orders,
                SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed_orders,
                SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) as cancelled_orders,
                SUM(CASE WHEN out_of_city = 1 THEN 1 ELSE 0 END) as out_of_city_orders,
                SUM(CASE WHEN has_review = 1 THEN 1 ELSE 0 END) as review_orders,
                SUM(CASE WHEN status = 'CLOSED' THEN total_amount ELSE 0 END) as total_amount,
                SUM(CASE WHEN status = 'CLOSED' THEN materials_cost ELSE 0 END) as total_materials_cost,
                SUM(CASE WHEN status = 'CLOSED' THEN master_profit ELSE 0 END) as total_master_profit,
                SUM(CASE WHEN status = 'CLOSED' THEN company_profit ELSE 0 END) as total_company_profit
            FROM orders
            WHERE DATE(created_at) >= ? AND DATE(created_at) <= ?
        """,
            (start_date, end_date),
        )

        row = await cursor.fetchone()

        return {
            "total_orders": row["total_orders"] or 0,
            "new_orders": row["new_orders"] or 0,
            "assigned_orders": row["assigned_orders"] or 0,
            "accepted_orders": row["accepted_orders"] or 0,
            "in_progress_orders": row["in_progress_orders"] or 0,
            "closed_orders": row["closed_orders"] or 0,
            "cancelled_orders": row["cancelled_orders"] or 0,
            "out_of_city_orders": row["out_of_city_orders"] or 0,
            "review_orders": row["review_orders"] or 0,
            "total_amount": float(row["total_amount"] or 0),
            "total_materials_cost": float(row["total_materials_cost"] or 0),
            "total_master_profit": float(row["total_master_profit"] or 0),
            "total_company_profit": float(row["total_company_profit"] or 0),
        }

    async def _get_masters_stats(self, start_date, end_date) -> list[dict[str, Any]]:
        """Получает статистику по мастерам за период"""
        cursor = await self.db.connection.execute(
            """
            SELECT
                m.id,
                u.first_name || ' ' || COALESCE(u.last_name, '') as master_name,
                COUNT(o.id) as orders_count,
                SUM(CASE WHEN o.status = 'CLOSED' THEN 1 ELSE 0 END) as closed_orders,
                SUM(CASE WHEN o.out_of_city = 1 THEN 1 ELSE 0 END) as out_of_city_count,
                SUM(CASE WHEN o.has_review = 1 THEN 1 ELSE 0 END) as reviews_count,
                SUM(CASE WHEN o.status = 'CLOSED' THEN o.master_profit ELSE 0 END) as total_profit,
                AVG(CASE WHEN o.status = 'CLOSED' THEN o.total_amount ELSE NULL END) as avg_order_amount
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            LEFT JOIN orders o ON m.id = o.assigned_master_id
                AND DATE(o.created_at) >= ? AND DATE(o.created_at) <= ?
            WHERE m.is_active = 1
            GROUP BY m.id, u.first_name, u.last_name
            ORDER BY total_profit DESC
        """,
            (start_date, end_date),
        )

        rows = await cursor.fetchall()

        masters = []
        for row in rows:
            masters.append(
                {
                    "id": row["id"],
                    "name": row["master_name"],
                    "orders_count": row["orders_count"] or 0,
                    "closed_orders": row["closed_orders"] or 0,
                    "out_of_city_count": row["out_of_city_count"] or 0,
                    "reviews_count": row["reviews_count"] or 0,
                    "total_profit": float(row["total_profit"] or 0),
                    "avg_order_amount": float(row["avg_order_amount"] or 0),
                }
            )

        return masters

    async def _get_accepted_orders_details(self, start_date, end_date) -> list[dict[str, Any]]:
        """Получает детальную информацию о принятых заказах за период"""
        cursor = await self.db.connection.execute(
            """
            SELECT
                o.id,
                o.equipment_type,
                o.client_name,
                o.client_address,
                o.client_phone,
                o.created_at,
                o.scheduled_time,
                o.notes,
                u.first_name || ' ' || COALESCE(u.last_name, '') as master_name
            FROM orders o
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE o.status = 'ACCEPTED'
                AND DATE(o.created_at) >= ? AND DATE(o.created_at) <= ?
            ORDER BY o.created_at DESC
        """,
            (start_date, end_date),
        )

        rows = await cursor.fetchall()

        orders_list = []
        for row in rows:
            orders_list.append(
                {
                    "id": row["id"],
                    "equipment_type": row["equipment_type"],
                    "client_name": row["client_name"],
                    "client_address": row["client_address"],
                    "client_phone": row["client_phone"],
                    "created_at": row["created_at"],
                    "scheduled_time": row["scheduled_time"],
                    "notes": row["notes"],
                    "master_name": row["master_name"] or "Не назначен",
                }
            )

        return orders_list

    async def _get_summary_stats(self, start_date, end_date) -> dict[str, Any]:
        """Получает общую статистику за период"""
        cursor = await self.db.connection.execute(
            """
            SELECT
                COUNT(DISTINCT assigned_master_id) as active_masters,
                AVG(CASE WHEN status = 'CLOSED' THEN total_amount ELSE NULL END) as avg_order_amount,
                MAX(CASE WHEN status = 'CLOSED' THEN total_amount ELSE NULL END) as max_order_amount,
                MIN(CASE WHEN status = 'CLOSED' THEN total_amount ELSE NULL END) as min_order_amount
            FROM orders
            WHERE DATE(created_at) >= ? AND DATE(created_at) <= ?
        """,
            (start_date, end_date),
        )

        row = await cursor.fetchone()

        return {
            "active_masters": row["active_masters"] or 0,
            "avg_order_amount": float(row["avg_order_amount"] or 0),
            "max_order_amount": float(row["max_order_amount"] or 0),
            "min_order_amount": float(row["min_order_amount"] or 0),
        }

    async def _get_closed_orders_list(self, start_date, end_date) -> list[dict[str, Any]]:
        """Получает список закрытых заказов за период с историей"""
        cursor = await self.db.connection.execute(
            """
            SELECT
                o.id,
                o.equipment_type,
                o.client_name,
                o.client_address,
                o.total_amount,
                o.materials_cost,
                o.master_profit,
                o.company_profit,
                o.out_of_city,
                o.has_review,
                o.created_at,
                o.updated_at,
                u.first_name || ' ' || COALESCE(u.last_name, '') as master_name
            FROM orders o
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE o.status = 'CLOSED'
                AND DATE(o.updated_at) >= ?
                AND DATE(o.updated_at) <= ?
            ORDER BY o.updated_at DESC
        """,
            (start_date, end_date),
        )

        rows = await cursor.fetchall()

        # Получаем расширенный репозиторий
        order_repo = await self._get_extended_repo()

        orders_list = []
        for row in rows:
            order_id = row["id"]

            # Получаем историю статусов для каждой заявки
            status_history = await order_repo.get_status_history(order_id)

            # Считаем статистику по истории
            history_stats = {
                "total_changes": len(status_history),
                "days_to_complete": 0,
                "status_changes": [],
            }

            if status_history:
                # Берем первые 3 изменения для отчета
                history_stats["status_changes"] = [
                    {
                        "from": h["old_status"],
                        "to": h["new_status"],
                        "date": h["changed_at"],
                        "changed_by": h.get("username", "Система"),
                    }
                    for h in status_history[:3]
                ]

                # Считаем дни от создания до закрытия
                from datetime import datetime

                if row["created_at"] and row["updated_at"]:
                    created = datetime.fromisoformat(row["created_at"])
                    updated = datetime.fromisoformat(row["updated_at"])
                    # Удаляем timezone информацию для корректного вычитания
                    if created.tzinfo is not None:
                        created = created.replace(tzinfo=None)
                    if updated.tzinfo is not None:
                        updated = updated.replace(tzinfo=None)
                    history_stats["days_to_complete"] = (updated - created).days

            orders_list.append(
                {
                    "id": order_id,
                    "equipment_type": row["equipment_type"],
                    "client_name": row["client_name"],
                    "client_address": row["client_address"],
                    "master_name": row["master_name"] or "Не назначен",
                    "total_amount": float(row["total_amount"] or 0),
                    "materials_cost": float(row["materials_cost"] or 0),
                    "master_profit": float(row["master_profit"] or 0),
                    "company_profit": float(row["company_profit"] or 0),
                    "out_of_city": bool(row["out_of_city"]),
                    "has_review": bool(row["has_review"]),
                    "created_at": row["created_at"],
                    "closed_at": row["updated_at"],
                    "history": history_stats,  # ✨ НОВОЕ: История изменений
                }
            )

        return orders_list

    async def _get_order_history_summary(self, order_id: int) -> str:
        """
        Получает краткую историю заявки для включения в отчет

        Args:
            order_id: ID заявки

        Returns:
            Текстовое описание истории
        """
        order_repo = await self._get_extended_repo()

        try:
            status_history = await order_repo.get_status_history(order_id)

            if not status_history:
                return "История изменений отсутствует"

            # Формируем краткую историю
            summary = f"Изменений: {len(status_history)}\n"

            for i, h in enumerate(status_history[:3], 1):  # Первые 3 изменения
                summary += f"  {i}. {h['changed_at'][:16]}: {h['old_status']} → {h['new_status']}\n"

            if len(status_history) > 3:
                summary += f"  ... и еще {len(status_history) - 3} изменений\n"

            return summary
        except Exception as e:
            logger.error(f"Ошибка получения истории для заявки #{order_id}: {e}")
            return "Ошибка получения истории"

    async def format_report_to_text(self, report: dict[str, Any]) -> str:
        """Форматирует отчет в текстовый вид"""
        report_type = report["type"]
        period = report["period"]
        orders = report["orders"]
        masters = report["masters"]
        summary = report["summary"]

        if report_type == "daily":
            title = "📊 ЕЖЕДНЕВНЫЙ ОТЧЕТ"
            icon = "📅"
        elif report_type == "weekly":
            title = "📊 ЕЖЕНЕДЕЛЬНЫЙ ОТЧЕТ"
            icon = "📆"
        else:
            title = "📊 ЕЖЕМЕСЯЧНЫЙ ОТЧЕТ"
            icon = "🗓️"

        text = f"{title}\n"
        text += f"{icon} Период: {period}\n"
        text += f"📅 Сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"

        # Статистика по заказам
        text += "📋 СТАТИСТИКА ПО ЗАКАЗАМ:\n"
        text += f"• Всего заказов: {orders['total_orders']}\n"
        text += f"• Новых: {orders['new_orders']}\n"
        text += f"• Назначенных: {orders['assigned_orders']}\n"
        text += f"• Принятых: {orders['accepted_orders']}\n"
        text += f"• В работе: {orders['in_progress_orders']}\n"
        text += f"• Завершенных: {orders['closed_orders']}\n"
        text += f"• Отмененных: {orders['cancelled_orders']}\n"
        text += f"• С выездом за город: {orders['out_of_city_orders']}\n"
        text += f"• С отзывами: {orders['review_orders']}\n\n"

        # Детальная информация о принятых заказах
        if orders["accepted_orders"] > 0:
            text += "✅ ПРИНЯТЫЕ ЗАКАЗЫ (детали в Excel):\n"
            # Получаем детальную информацию о принятых заказах
            accepted_orders_details = await self._get_accepted_orders_details(
                report.get("start_date", ""), report.get("end_date", "")
            )
            for order in accepted_orders_details[:10]:  # Показываем первые 10
                text += f"• #{order['id']} - {order['equipment_type']} | {order['client_name']} | {order['master_name']}\n"
            if len(accepted_orders_details) > 10:
                text += f"... и еще {len(accepted_orders_details) - 10} заказов\n"
            text += "\n"

        # Финансовая информация
        if orders["closed_orders"] > 0:
            text += "💰 ФИНАНСОВАЯ ИНФОРМАЦИЯ:\n"
            text += f"• Общая сумма: {orders['total_amount']:.2f} ₽\n"
            text += f"• Расходы на материалы: {orders['total_materials_cost']:.2f} ₽\n"
            text += f"• Прибыль мастеров: {orders['total_master_profit']:.2f} ₽\n"
            text += f"• Прибыль компании: {orders['total_company_profit']:.2f} ₽\n"
            text += f"• Средний чек: {summary['avg_order_amount']:.2f} ₽\n"
            text += f"• Максимальный чек: {summary['max_order_amount']:.2f} ₽\n\n"

        # Статистика по мастерам
        if masters:
            text += "👨‍🔧 ТОП МАСТЕРОВ:\n"
            for i, master in enumerate(masters[:5], 1):  # Топ 5
                text += f"{i}. {master['name']}\n"
                text += (
                    f"   Заказов: {master['orders_count']} | Завершено: {master['closed_orders']}\n"
                )
                text += f"   Выездов: {master['out_of_city_count']} | Отзывов: {master['reviews_count']}\n"
                text += f"   Прибыль: {master['total_profit']:.2f} ₽\n\n"

        text += f"👥 Активных мастеров: {summary['active_masters']}\n\n"

        # Информация о детализации
        closed_orders = report.get("closed_orders", [])
        if closed_orders:
            text += f"📋 Детальная информация по {len(closed_orders)} закрытым заказам доступна в Excel файле.\n\n"

            # ✨ НОВОЕ: Добавляем статистику по истории изменений
            total_changes = sum(
                order.get("history", {}).get("total_changes", 0) for order in closed_orders
            )
            avg_days = (
                sum(order.get("history", {}).get("days_to_complete", 0) for order in closed_orders)
                / len(closed_orders)
                if closed_orders
                else 0
            )

            text += "📊 ИСТОРИЯ ИЗМЕНЕНИЙ:\n"
            text += f"• Всего изменений статусов: {total_changes}\n"
            text += f"• Среднее время выполнения: {avg_days:.1f} дней\n\n"

            # Показываем примеры быстрых и медленных заявок
            orders_with_days = [
                (o["id"], o.get("history", {}).get("days_to_complete", 0)) for o in closed_orders
            ]
            orders_with_days.sort(key=lambda x: x[1])

            if orders_with_days:
                fastest = orders_with_days[0]
                slowest = orders_with_days[-1]
                text += f"• Самая быстрая: #{fastest[0]} ({fastest[1]} дн.)\n"
                text += f"• Самая долгая: #{slowest[0]} ({slowest[1]} дн.)\n"

        return text

    async def save_report_to_file(self, report: dict[str, Any], filename: str | None = None) -> str:
        """Сохраняет отчет в текстовый файл"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{report['type']}_{timestamp}.txt"

        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        file_path = reports_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.format_report_to_text(report))

        logger.info(f"Отчет сохранен в файл: {file_path}")
        return str(file_path)

    async def save_report_to_excel(
        self, report: dict[str, Any], filename: str | None = None
    ) -> str:
        """Сохраняет отчет в Excel файл с детализацией"""
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        if not filename:
            # Фиксированное имя файла (обновляется каждый раз)
            filename = f"report_{report['type']}.xlsx"

        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        file_path = reports_dir / filename

        wb = Workbook()

        # Стили
        header_font = Font(bold=True, size=14, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        subheader_font = Font(bold=True, size=12)
        subheader_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        center_alignment = Alignment(horizontal="center", vertical="center")
        left_alignment = Alignment(horizontal="left", vertical="center")
        right_alignment = Alignment(horizontal="right", vertical="center")
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # Лист 1: Общая статистика
        ws1 = wb.active
        ws1.title = "Статистика"

        row = 1
        ws1.merge_cells(f"A{row}:F{row}")
        cell = ws1[f"A{row}"]
        cell.value = f"{report['type'].upper()} ОТЧЕТ"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        ws1.row_dimensions[row].height = 25

        row += 1
        ws1.merge_cells(f"A{row}:F{row}")
        cell = ws1[f"A{row}"]
        cell.value = f"Период: {report['period']}"
        cell.font = Font(bold=True, size=11)
        cell.alignment = center_alignment

        row += 2

        # Статистика по заказам
        orders = report["orders"]
        ws1[f"A{row}"] = "СТАТИСТИКА ПО ЗАКАЗАМ"
        ws1[f"A{row}"].font = subheader_font
        ws1[f"A{row}"].fill = subheader_fill
        ws1.merge_cells(f"A{row}:F{row}")

        row += 1
        stats_data = [
            ["Показатель", "Значение"],
            ["Всего заказов", orders["total_orders"]],
            ["Новых", orders["new_orders"]],
            ["Назначенных", orders["assigned_orders"]],
            ["Принятых", orders["accepted_orders"]],
            ["В работе", orders["in_progress_orders"]],
            ["Завершенных", orders["closed_orders"]],
            ["Отмененных", orders["cancelled_orders"]],
            ["С выездом за город", orders["out_of_city_orders"]],
            ["С отзывами", orders["review_orders"]],
        ]

        for row_data in stats_data:
            for col_idx, value in enumerate(row_data, start=1):
                cell = ws1.cell(row=row, column=col_idx, value=value)
                cell.border = thin_border
                if row_data == stats_data[0]:
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(
                        start_color="E7E6E6", end_color="E7E6E6", fill_type="solid"
                    )
                cell.alignment = left_alignment if col_idx == 1 else right_alignment
            row += 1

        row += 1

        # Финансовая информация
        if orders["closed_orders"] > 0:
            ws1[f"A{row}"] = "ФИНАНСОВАЯ ИНФОРМАЦИЯ"
            ws1[f"A{row}"].font = subheader_font
            ws1[f"A{row}"].fill = subheader_fill
            ws1.merge_cells(f"A{row}:F{row}")

            row += 1
            financial_data = [
                ["Показатель", "Значение"],
                ["Общая сумма", f"{orders['total_amount']:.2f} ₽"],
                ["Расходы на материалы", f"{orders['total_materials_cost']:.2f} ₽"],
                ["Прибыль мастеров", f"{orders['total_master_profit']:.2f} ₽"],
                ["Прибыль компании", f"{orders['total_company_profit']:.2f} ₽"],
                ["Средний чек", f"{report['summary']['avg_order_amount']:.2f} ₽"],
                ["Максимальный чек", f"{report['summary']['max_order_amount']:.2f} ₽"],
            ]

            for row_data in financial_data:
                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws1.cell(row=row, column=col_idx, value=value)
                    cell.border = thin_border
                    if row_data == financial_data[0]:
                        cell.font = Font(bold=True)
                        cell.fill = PatternFill(
                            start_color="E7E6E6", end_color="E7E6E6", fill_type="solid"
                        )
                    cell.alignment = left_alignment if col_idx == 1 else right_alignment
                row += 1

        # Ширина столбцов
        ws1.column_dimensions["A"].width = 30
        ws1.column_dimensions["B"].width = 20

        # Лист 2: Детализация по заказам
        closed_orders = report.get("closed_orders", [])
        if closed_orders:
            ws2 = wb.create_sheet(title="Заказы")

            row = 1
            ws2.merge_cells(f"A{row}:K{row}")
            cell = ws2[f"A{row}"]
            cell.value = "ДЕТАЛИЗАЦИЯ ПО ЗАКАЗАМ"
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            ws2.row_dimensions[row].height = 25

            row += 1
            headers = [
                "ID",
                "Техника",
                "Клиент",
                "Мастер",
                "Создано",
                "Закрыто",
                "Сумма",
                "Материалы",
                "Прибыль мастера",
                "Прибыль компании",
                "Доп. инфо",
            ]
            for col_idx, header in enumerate(headers, start=1):
                cell = ws2.cell(row=row, column=col_idx, value=header)
                cell.font = Font(bold=True)
                cell.fill = subheader_fill
                cell.alignment = center_alignment
                cell.border = thin_border

            row += 1

        # Данные по заказам
        for order in closed_orders:
            additional_info = []
            if order["out_of_city"]:
                additional_info.append("Выезд за город")
            if order["has_review"]:
                additional_info.append("Отзыв")

            # Безопасное форматирование строк
            equipment_type = (
                str(order["equipment_type"] or "").encode("utf-8", errors="ignore").decode("utf-8")
            )
            client_name = (
                str(order["client_name"] or "").encode("utf-8", errors="ignore").decode("utf-8")
            )
            master_name = (
                str(order["master_name"] or "Не назначен")
                .encode("utf-8", errors="ignore")
                .decode("utf-8")
            )

            data = [
                order["id"],
                equipment_type,
                client_name,
                master_name,
                order.get("created_at"),
                order.get("closed_at"),
                order["total_amount"],
                order["materials_cost"],
                order["master_profit"],
                order["company_profit"],
                ", ".join(additional_info) if additional_info else "-",
            ]

            for col_idx, value in enumerate(data, start=1):
                cell = ws2.cell(row=row, column=col_idx, value=value)
                cell.border = thin_border
                if col_idx == 1:
                    cell.alignment = center_alignment
                elif col_idx in [2, 3, 4, 5, 6, 11]:
                    cell.alignment = left_alignment
                else:
                    cell.alignment = right_alignment
                    if col_idx >= 7 and col_idx <= 10:
                        cell.number_format = "#,##0.00 ₽"
            row += 1

            # Итоги
            row += 1
            ws2[f"A{row}"] = "ИТОГО:"
            ws2[f"A{row}"].font = Font(bold=True)
            ws2[f"G{row}"] = sum(o["total_amount"] for o in closed_orders)
            ws2[f"G{row}"].font = Font(bold=True)
            ws2[f"G{row}"].number_format = "#,##0.00 ₽"
            ws2[f"H{row}"] = sum(o["materials_cost"] for o in closed_orders)
            ws2[f"H{row}"].font = Font(bold=True)
            ws2[f"H{row}"].number_format = "#,##0.00 ₽"
            ws2[f"I{row}"] = sum(o["master_profit"] for o in closed_orders)
            ws2[f"I{row}"].font = Font(bold=True)
            ws2[f"I{row}"].number_format = "#,##0.00 ₽"
            ws2[f"J{row}"] = sum(o["company_profit"] for o in closed_orders)
            ws2[f"J{row}"].font = Font(bold=True)
            ws2[f"J{row}"].number_format = "#,##0.00 ₽"

            # Ширина столбцов
            ws2.column_dimensions["A"].width = 8
            ws2.column_dimensions["B"].width = 25
            ws2.column_dimensions["C"].width = 20
            ws2.column_dimensions["D"].width = 20
            ws2.column_dimensions["E"].width = 18
            ws2.column_dimensions["F"].width = 18
            ws2.column_dimensions["G"].width = 15
            ws2.column_dimensions["H"].width = 15
            ws2.column_dimensions["I"].width = 18
            ws2.column_dimensions["J"].width = 18
            ws2.column_dimensions["K"].width = 22

        # ✨ НОВЫЙ ЛИСТ 3: Детализация по мастерам
        masters = report.get("masters", [])
        if masters:
            ws3 = wb.create_sheet(title="Мастера")

            # Заголовок
            row = 1
            ws3.merge_cells(f"A{row}:K{row}")
            cell = ws3[f"A{row}"]
            cell.value = "ДЕТАЛИЗАЦИЯ ПО МАСТЕРАМ"
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            ws3.row_dimensions[row].height = 25

            # Заголовки колонок
            row += 1
            master_headers = [
                "ID",
                "Мастер",
                "Заявок всего",
                "Завершено",
                "В работе",
                "Отказано",
                "Общая сумма",
                "Материалы",
                "Чистая прибыль",
                "Прибыль компании",
                "Сдача в кассу",
                "Средний чек",
                "Выездов",
                "Отзывов",
            ]

            for col_idx, header in enumerate(master_headers, start=1):
                cell = ws3.cell(row=row, column=col_idx, value=header)
                cell.font = Font(bold=True)
                cell.fill = subheader_fill
                cell.alignment = center_alignment
                cell.border = thin_border

            row += 1

            # Получаем детальную информацию по каждому мастеру
            for master in masters:
                master_id = master["id"]

                # Получаем детальную статистику мастера
                cursor = await self.db.connection.execute(
                    """
                    SELECT
                        COUNT(*) as total_orders,
                        SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed,
                        SUM(CASE WHEN status IN ('ASSIGNED', 'IN_PROGRESS', 'ACCEPTED') THEN 1 ELSE 0 END) as in_work,
                        SUM(CASE WHEN status = 'REFUSED' THEN 1 ELSE 0 END) as refused,
                        SUM(CASE WHEN status = 'CLOSED' THEN total_amount ELSE 0 END) as total_sum,
                        SUM(CASE WHEN status = 'CLOSED' THEN materials_cost ELSE 0 END) as materials_sum,
                        SUM(CASE WHEN status = 'CLOSED' THEN master_profit ELSE 0 END) as master_profit_sum,
                        SUM(CASE WHEN status = 'CLOSED' THEN company_profit ELSE 0 END) as company_profit_sum,
                        SUM(CASE WHEN status = 'CLOSED' AND out_of_city = 1 THEN 1 ELSE 0 END) as out_of_city,
                        SUM(CASE WHEN status = 'CLOSED' AND has_review = 1 THEN 1 ELSE 0 END) as reviews,
                        AVG(CASE WHEN status = 'CLOSED' THEN total_amount ELSE NULL END) as avg_check
                    FROM orders
                    WHERE assigned_master_id = ?
                    """,
                    (master_id,),
                )

                stats_row = await cursor.fetchone()

                if not stats_row:
                    continue

                # Вычисляем чистую прибыль (общая сумма - материалы)
                total_sum = float(stats_row["total_sum"] or 0)
                materials = float(stats_row["materials_sum"] or 0)
                net_profit = total_sum - materials

                # Сдача в кассу = прибыль компании
                cash_to_company = float(stats_row["company_profit_sum"] or 0)

                # Данные по мастеру
                master_name = (
                    str(master["name"] or "Неизвестен")
                    .encode("utf-8", errors="ignore")
                    .decode("utf-8")
                )
                master_data = [
                    master_id,
                    master_name,
                    stats_row["total_orders"] or 0,
                    stats_row["closed"] or 0,
                    stats_row["in_work"] or 0,
                    stats_row["refused"] or 0,
                    total_sum,
                    materials,
                    net_profit,
                    cash_to_company,
                    cash_to_company,  # Сдача в кассу = прибыль компании
                    float(stats_row["avg_check"] or 0),
                    stats_row["out_of_city"] or 0,
                    stats_row["reviews"] or 0,
                ]

                for col_idx, value in enumerate(master_data, start=1):
                    cell = ws3.cell(row=row, column=col_idx, value=value)
                    cell.border = thin_border

                    # Форматирование
                    if col_idx == 1:  # ID
                        cell.alignment = center_alignment
                    elif col_idx in [2]:  # Имя
                        cell.alignment = left_alignment
                    elif col_idx in [3, 4, 5, 6, 13, 14]:  # Счетчики
                        cell.alignment = center_alignment
                    else:  # Деньги
                        cell.alignment = right_alignment
                        if col_idx >= 7 and col_idx <= 12:
                            cell.number_format = "#,##0.00 ₽"

                row += 1

            # ИТОГО по всем мастерам
            row += 1
            ws3[f"A{row}"] = "ИТОГО:"
            ws3[f"A{row}"].font = Font(bold=True, size=12)
            ws3.merge_cells(f"A{row}:B{row}")

            # Считаем итоги
            total_orders = sum(m["orders_count"] for m in masters)
            total_closed = sum(m["closed_orders"] for m in masters)

            # Итоги по финансам из закрытых заявок
            total_sum_all = sum(o["total_amount"] for o in closed_orders)
            total_materials_all = sum(o["materials_cost"] for o in closed_orders)
            total_net_profit = total_sum_all - total_materials_all
            total_company = sum(o["company_profit"] for o in closed_orders)

            ws3[f"C{row}"] = total_orders
            ws3[f"C{row}"].font = Font(bold=True)
            ws3[f"C{row}"].alignment = center_alignment

            ws3[f"D{row}"] = total_closed
            ws3[f"D{row}"].font = Font(bold=True)
            ws3[f"D{row}"].alignment = center_alignment

            ws3[f"G{row}"] = total_sum_all
            ws3[f"G{row}"].font = Font(bold=True)
            ws3[f"G{row}"].number_format = "#,##0.00 ₽"

            ws3[f"H{row}"] = total_materials_all
            ws3[f"H{row}"].font = Font(bold=True)
            ws3[f"H{row}"].number_format = "#,##0.00 ₽"

            ws3[f"I{row}"] = total_net_profit
            ws3[f"I{row}"].font = Font(bold=True)
            ws3[f"I{row}"].number_format = "#,##0.00 ₽"

            ws3[f"J{row}"] = total_company
            ws3[f"J{row}"].font = Font(bold=True)
            ws3[f"J{row}"].number_format = "#,##0.00 ₽"

            ws3[f"K{row}"] = total_company
            ws3[f"K{row}"].font = Font(bold=True)
            ws3[f"K{row}"].number_format = "#,##0.00 ₽"

            # Ширина столбцов
            ws3.column_dimensions["A"].width = 6
            ws3.column_dimensions["B"].width = 25
            ws3.column_dimensions["C"].width = 12
            ws3.column_dimensions["D"].width = 12
            ws3.column_dimensions["E"].width = 12
            ws3.column_dimensions["F"].width = 12
            ws3.column_dimensions["G"].width = 15
            ws3.column_dimensions["H"].width = 15
            ws3.column_dimensions["I"].width = 15
            ws3.column_dimensions["J"].width = 18
            ws3.column_dimensions["K"].width = 15
            ws3.column_dimensions["L"].width = 15
            ws3.column_dimensions["M"].width = 10
            ws3.column_dimensions["N"].width = 10

        # ✨ НОВЫЙ ЛИСТ 4: Все заявки по мастерам (активные и закрытые)
        if masters:
            ws4 = wb.create_sheet(title="Заявки по мастерам")

            # Заголовок
            row = 1
            ws4.merge_cells(f"A{row}:N{row}")
            cell = ws4[f"A{row}"]
            cell.value = "ДЕТАЛИЗАЦИЯ ЗАЯВОК ПО МАСТЕРАМ"
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            ws4.row_dimensions[row].height = 25

            row += 1

            # Заголовки колонок
            order_headers = [
                "Мастер",
                "ID",
                "Статус",
                "Тип техники",
                "Клиент",
                "Адрес",
                "Телефон",
                "Создана",
                "Обновлена",
                "Сумма",
                "Материалы",
                "Прибыль мастера",
                "Сдача в кассу",
                "Примечания",
            ]

            for col_idx, header in enumerate(order_headers, start=1):
                cell = ws4.cell(row=row, column=col_idx, value=header)
                cell.font = Font(bold=True)
                cell.fill = subheader_fill
                cell.alignment = center_alignment
                cell.border = thin_border

            row += 1

            # Получаем все заявки для каждого мастера
            for master in masters:
                master_id = master["id"]
                master_name = (
                    str(master["name"] or "Неизвестен")
                    .encode("utf-8", errors="ignore")
                    .decode("utf-8")
                )

                # Получаем ВСЕ заявки мастера (активные и закрытые)
                cursor = await self.db.connection.execute(
                    """
                    SELECT
                        o.id,
                        o.status,
                        o.equipment_type,
                        o.client_name,
                        o.client_address,
                        o.client_phone,
                        o.created_at,
                        o.updated_at,
                        o.total_amount,
                        o.materials_cost,
                        o.master_profit,
                        o.company_profit,
                        o.notes,
                        o.scheduled_time,
                        o.out_of_city,
                        o.has_review
                    FROM orders o
                    WHERE o.assigned_master_id = ?
                        AND o.status IN ('ASSIGNED', 'ACCEPTED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED', 'REFUSED')
                        AND o.deleted_at IS NULL
                    ORDER BY
                        CASE o.status
                            WHEN 'IN_PROGRESS' THEN 1
                            WHEN 'ACCEPTED' THEN 2
                            WHEN 'ASSIGNED' THEN 3
                            WHEN 'COMPLETED' THEN 4
                            WHEN 'CLOSED' THEN 5
                            WHEN 'REFUSED' THEN 6
                            ELSE 7
                        END,
                        o.created_at DESC
                    """,
                    (master_id,),
                )

                orders_rows = await cursor.fetchall()

                if not orders_rows:
                    continue

                # Добавляем заголовок мастера
                cell_master = ws4[f"A{row}"]
                cell_master.value = f"👨‍🔧 {master_name}"
                cell_master.font = Font(bold=True, size=11, color="FFFFFF")
                cell_master.fill = PatternFill(
                    start_color="70AD47", end_color="70AD47", fill_type="solid"
                )
                cell_master.alignment = left_alignment
                ws4.merge_cells(f"A{row}:N{row}")
                ws4.row_dimensions[row].height = 20
                row += 1

                # Заявки мастера
                for order_row in orders_rows:
                    # Эмодзи для статуса
                    status_emoji = {
                        "ASSIGNED": "🆕",
                        "ACCEPTED": "✅",
                        "IN_PROGRESS": "⚙️",
                        "COMPLETED": "✔️",
                        "CLOSED": "🔒",
                        "REFUSED": "❌",
                    }.get(order_row["status"], "❓")

                    # Форматируем примечания
                    notes = []
                    if order_row["out_of_city"]:
                        notes.append("Выезд за город")
                    if order_row["has_review"]:
                        notes.append("Есть отзыв")
                    if order_row["scheduled_time"] and order_row["scheduled_time"] != 'None':
                        scheduled_time = (
                            str(order_row["scheduled_time"] or "")
                            .encode("utf-8", errors="ignore")
                            .decode("utf-8")
                        )
                        notes.append(f"Время: {scheduled_time}")
                    if order_row["notes"]:
                        notes_text = (
                            str(order_row["notes"] or "")
                            .encode("utf-8", errors="ignore")
                            .decode("utf-8")
                        )
                        notes.append(notes_text[:50])

                    # Безопасное форматирование строк
                    equipment_type = (
                        str(order_row["equipment_type"] or "")
                        .encode("utf-8", errors="ignore")
                        .decode("utf-8")
                    )
                    client_name = (
                        str(order_row["client_name"] or "")
                        .encode("utf-8", errors="ignore")
                        .decode("utf-8")
                    )
                    client_address = (
                        str(order_row["client_address"] or "")
                        .encode("utf-8", errors="ignore")
                        .decode("utf-8")
                    )
                    client_phone = (
                        str(order_row["client_phone"] or "")
                        .encode("utf-8", errors="ignore")
                        .decode("utf-8")
                    )

                    # Безопасное обрезание адреса
                    if len(client_address) > 30:
                        client_address = client_address[:30] + "..."

                    # Безопасное форматирование дат
                    created_at = ""
                    updated_at = ""
                    if order_row["created_at"]:
                        try:
                            created_at = str(order_row["created_at"])[:16]
                        except Exception:
                            created_at = ""
                    if order_row["updated_at"]:
                        try:
                            updated_at = str(order_row["updated_at"])[:16]
                        except Exception:
                            updated_at = ""

                    order_data = [
                        "",  # Пустая колонка для мастера (он в заголовке)
                        order_row["id"],
                        f"{status_emoji} {order_row['status']}",
                        equipment_type,
                        client_name,
                        client_address,
                        client_phone,
                        created_at,
                        updated_at,
                        float(order_row["total_amount"] or 0),
                        float(order_row["materials_cost"] or 0),
                        float(order_row["master_profit"] or 0),
                        float(order_row["company_profit"] or 0),  # Сдача в кассу
                        "; ".join(notes) if notes else "-",
                    ]

                    for col_idx, value in enumerate(order_data, start=1):
                        cell = ws4.cell(row=row, column=col_idx, value=value)
                        cell.border = thin_border

                        # Форматирование
                        if col_idx == 2:  # ID
                            cell.alignment = center_alignment
                            cell.font = Font(bold=True)
                        elif col_idx == 3:  # Статус
                            cell.alignment = center_alignment
                            # Цвет фона в зависимости от статуса
                            status = order_row["status"]
                            if status == "IN_PROGRESS":
                                cell.fill = PatternFill(
                                    start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"
                                )
                            elif status == "CLOSED":
                                cell.fill = PatternFill(
                                    start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"
                                )
                            elif status == "REFUSED":
                                cell.fill = PatternFill(
                                    start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"
                                )
                        elif col_idx in [4, 5, 6, 7, 8, 14]:  # Текст
                            cell.alignment = left_alignment
                        else:  # Числа и деньги
                            cell.alignment = right_alignment
                            if col_idx >= 10 and col_idx <= 13:
                                cell.number_format = "#,##0.00 ₽"

                    row += 1

                # Итоги по мастеру
                cursor = await self.db.connection.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'CLOSED' THEN total_amount ELSE 0 END) as sum_total,
                        SUM(CASE WHEN status = 'CLOSED' THEN materials_cost ELSE 0 END) as sum_materials,
                        SUM(CASE WHEN status = 'CLOSED' THEN master_profit ELSE 0 END) as sum_master,
                        SUM(CASE WHEN status = 'CLOSED' THEN company_profit ELSE 0 END) as sum_company
                    FROM orders
                    WHERE assigned_master_id = ?
                        AND deleted_at IS NULL
                    """,
                    (master_id,),
                )

                totals = await cursor.fetchone()

                cell_total = ws4[f"A{row}"]
                cell_total.value = f"Итого по {master_name}:"
                cell_total.font = Font(bold=True, italic=True)
                ws4.merge_cells(f"A{row}:I{row}")

                cell_j = ws4[f"J{row}"]
                cell_j.value = float(totals["sum_total"] or 0)
                cell_j.font = Font(bold=True)
                cell_j.number_format = "#,##0.00 ₽"

                cell_k = ws4[f"K{row}"]
                cell_k.value = float(totals["sum_materials"] or 0)
                cell_k.font = Font(bold=True)
                cell_k.number_format = "#,##0.00 ₽"

                cell_l = ws4[f"L{row}"]
                cell_l.value = float(totals["sum_master"] or 0)
                cell_l.font = Font(bold=True)
                cell_l.number_format = "#,##0.00 ₽"

                cell_m = ws4[f"M{row}"]
                cell_m.value = float(totals["sum_company"] or 0)
                cell_m.font = Font(bold=True)
                cell_m.number_format = "#,##0.00 ₽"

                row += 2  # Пустая строка между мастерами

            # Ширина столбцов
            ws4.column_dimensions["A"].width = 25
            ws4.column_dimensions["B"].width = 6
            ws4.column_dimensions["C"].width = 15
            ws4.column_dimensions["D"].width = 20
            ws4.column_dimensions["E"].width = 20
            ws4.column_dimensions["F"].width = 30
            ws4.column_dimensions["G"].width = 15
            ws4.column_dimensions["H"].width = 18
            ws4.column_dimensions["I"].width = 18
            ws4.column_dimensions["J"].width = 15
            ws4.column_dimensions["K"].width = 15
            ws4.column_dimensions["L"].width = 18
            ws4.column_dimensions["M"].width = 18
            ws4.column_dimensions["N"].width = 35

        # Сохраняем файл
        wb.save(file_path)
        logger.info(f"Excel отчет сохранен: {file_path}")

        return str(file_path)
