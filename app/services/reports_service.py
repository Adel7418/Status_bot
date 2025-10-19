"""
Сервис для генерации и отправки отчетов
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.database import Database
from app.utils.helpers import get_now


logger = logging.getLogger(__name__)


class ReportsService:
    """Сервис для генерации отчетов"""

    def __init__(self):
        self.db = Database()

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

            report = {
                "type": "daily",
                "period": f"{yesterday.strftime('%d.%m.%Y')}",
                "date_generated": get_now().isoformat(),
                "orders": orders_stats,
                "masters": masters_stats,
                "summary": await self._get_summary_stats(yesterday, today),
                "closed_orders": closed_orders,
            }

            return report

        finally:
            await self.db.disconnect()

    async def generate_weekly_report(self) -> dict[str, Any]:
        """Генерирует еженедельный отчет"""
        await self.db.connect()

        try:
            today = get_now().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)

            orders_stats = await self._get_orders_stats(week_start, week_end + timedelta(days=1))
            masters_stats = await self._get_masters_stats(week_start, week_end + timedelta(days=1))
            closed_orders = await self._get_closed_orders_list(
                week_start, week_end + timedelta(days=1)
            )

            report = {
                "type": "weekly",
                "period": f"{week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')}",
                "date_generated": get_now().isoformat(),
                "orders": orders_stats,
                "masters": masters_stats,
                "summary": await self._get_summary_stats(week_start, week_end + timedelta(days=1)),
                "closed_orders": closed_orders,
            }

            return report

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

            report = {
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

            return report

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
        """Получает список закрытых заказов за период"""
        cursor = await self.db.connection.execute(
            """
            SELECT
                o.id,
                o.equipment_type,
                o.client_name,
                o.total_amount,
                o.materials_cost,
                o.master_profit,
                o.company_profit,
                o.out_of_city,
                o.has_review,
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

        orders_list = []
        for row in rows:
            orders_list.append(
                {
                    "id": row["id"],
                    "equipment_type": row["equipment_type"],
                    "client_name": row["client_name"],
                    "master_name": row["master_name"] or "Не назначен",
                    "total_amount": float(row["total_amount"] or 0),
                    "materials_cost": float(row["materials_cost"] or 0),
                    "master_profit": float(row["master_profit"] or 0),
                    "company_profit": float(row["company_profit"] or 0),
                    "out_of_city": bool(row["out_of_city"]),
                    "has_review": bool(row["has_review"]),
                    "closed_at": row["updated_at"],
                }
            )

        return orders_list

    def format_report_to_text(self, report: dict[str, Any]) -> str:
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
            text += f"📋 Детальная информация по {len(closed_orders)} закрытым заказам доступна в Excel файле.\n"

        return text

    async def save_report_to_file(self, report: dict[str, Any], filename: str = None) -> str:
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

    async def save_report_to_excel(self, report: dict[str, Any], filename: str = None) -> str:
        """Сохраняет отчет в Excel файл с детализацией"""
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{report['type']}_{timestamp}.xlsx"

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
            ws2.merge_cells(f"A{row}:I{row}")
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

                data = [
                    order["id"],
                    order["equipment_type"],
                    order["client_name"],
                    order["master_name"],
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
                    elif col_idx in [2, 3, 4, 9]:
                        cell.alignment = left_alignment
                    else:
                        cell.alignment = right_alignment
                        if col_idx >= 5 and col_idx <= 8:
                            cell.number_format = "#,##0.00 ₽"
                row += 1

            # Итоги
            row += 1
            ws2[f"A{row}"] = "ИТОГО:"
            ws2[f"A{row}"].font = Font(bold=True)
            ws2[f"E{row}"] = sum(o["total_amount"] for o in closed_orders)
            ws2[f"E{row}"].font = Font(bold=True)
            ws2[f"E{row}"].number_format = "#,##0.00 ₽"
            ws2[f"F{row}"] = sum(o["materials_cost"] for o in closed_orders)
            ws2[f"F{row}"].font = Font(bold=True)
            ws2[f"F{row}"].number_format = "#,##0.00 ₽"
            ws2[f"G{row}"] = sum(o["master_profit"] for o in closed_orders)
            ws2[f"G{row}"].font = Font(bold=True)
            ws2[f"G{row}"].number_format = "#,##0.00 ₽"
            ws2[f"H{row}"] = sum(o["company_profit"] for o in closed_orders)
            ws2[f"H{row}"].font = Font(bold=True)
            ws2[f"H{row}"].number_format = "#,##0.00 ₽"

            # Ширина столбцов
            ws2.column_dimensions["A"].width = 8
            ws2.column_dimensions["B"].width = 25
            ws2.column_dimensions["C"].width = 20
            ws2.column_dimensions["D"].width = 20
            ws2.column_dimensions["E"].width = 15
            ws2.column_dimensions["F"].width = 15
            ws2.column_dimensions["G"].width = 18
            ws2.column_dimensions["H"].width = 18
            ws2.column_dimensions["I"].width = 20

        # Сохраняем файл
        wb.save(file_path)
        logger.info(f"Excel отчет сохранен: {file_path}")

        return str(file_path)
