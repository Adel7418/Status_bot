"""
Сервис для экспорта финансовых отчетов в Excel
"""

import logging
from pathlib import Path
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app.database.db import Database
from app.repositories.order_repository_extended import OrderRepositoryExtended
from app.utils.helpers import get_now


logger = logging.getLogger(__name__)


class ExcelExportService:
    """Сервис для экспорта отчетов в Excel"""

    def __init__(self):
        self.db = Database()
        self._order_repo_extended = None

    async def _get_extended_repo(self) -> OrderRepositoryExtended:
        """Получить расширенный репозиторий"""
        if self._order_repo_extended is None:
            self._order_repo_extended = OrderRepositoryExtended(self.db.connection)
        return self._order_repo_extended

    async def export_report_to_excel(self, report_id: int) -> Optional[str]:
        """
        Экспорт финансового отчета в Excel

        Args:
            report_id: ID отчета

        Returns:
            Путь к созданному файлу или None
        """
        await self.db.connect()

        try:
            # Получаем данные отчета
            report = await self.db.get_financial_report_by_id(report_id)
            if not report:
                logger.error(f"Report {report_id} not found")
                return None

            master_reports = await self.db.get_master_reports_by_report_id(report_id)

            # Создаем Excel файл
            wb = Workbook()
            ws = wb.active
            ws.title = "Финансовый отчет"

            # Стили
            header_font = Font(bold=True, size=14, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            subheader_font = Font(bold=True, size=12)
            subheader_fill = PatternFill(
                start_color="D9E1F2", end_color="D9E1F2", fill_type="solid"
            )
            total_font = Font(bold=True, size=11)
            total_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

            center_alignment = Alignment(horizontal="center", vertical="center")
            left_alignment = Alignment(horizontal="left", vertical="center")
            right_alignment = Alignment(horizontal="right", vertical="center")

            thin_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            # Определяем тип отчета
            period_text = ""
            if report.report_type == "DAILY":
                period_text = f"{report.period_start.strftime('%d.%m.%Y')}"
            elif report.report_type == "WEEKLY":
                period_text = f"{report.period_start.strftime('%d.%m')} - {report.period_end.strftime('%d.%m.%Y')}"
            elif report.report_type == "MONTHLY":
                period_text = f"{report.period_start.strftime('%B %Y')}"

            # Заголовок
            row = 1
            ws.merge_cells(f"A{row}:H{row}")
            cell = ws[f"A{row}"]
            cell.value = f"ФИНАНСОВЫЙ ОТЧЕТ - {report.report_type}"
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            ws.row_dimensions[row].height = 25

            row += 1
            ws.merge_cells(f"A{row}:H{row}")
            cell = ws[f"A{row}"]
            cell.value = f"Период: {period_text}"
            cell.font = Font(bold=True, size=12)
            cell.alignment = center_alignment
            ws.row_dimensions[row].height = 20

            row += 2

            # Общие показатели
            ws.merge_cells(f"A{row}:H{row}")
            cell = ws[f"A{row}"]
            cell.value = "ОБЩИЕ ПОКАЗАТЕЛИ"
            cell.font = subheader_font
            cell.fill = subheader_fill
            cell.alignment = center_alignment
            cell.border = thin_border

            row += 1
            summary_data = [
                ["Показатель", "Значение"],
                ["Всего заказов", report.total_orders],
                ["Общая сумма", f"{report.total_amount:,.2f} ₽"],
                ["Расходный материал", f"{report.total_materials_cost:,.2f} ₽"],
                ["Чистая прибыль", f"{report.total_net_profit:,.2f} ₽"],
                ["Средний чек", f"{report.average_check:,.2f} ₽"],
                ["", ""],
                ["Прибыль компании", f"{report.total_company_profit:,.2f} ₽"],
                ["Прибыль мастеров", f"{report.total_master_profit:,.2f} ₽"],
            ]

            for row_data in summary_data:
                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws.cell(row=row, column=col_idx, value=value)
                    cell.border = thin_border
                    if row_data == summary_data[0]:  # Заголовок
                        cell.font = Font(bold=True)
                        cell.fill = PatternFill(
                            start_color="E7E6E6", end_color="E7E6E6", fill_type="solid"
                        )
                    if col_idx == 2:
                        cell.alignment = right_alignment
                    else:
                        cell.alignment = left_alignment
                row += 1

            row += 1

            # Отчеты по мастерам
            if master_reports:
                ws.merge_cells(f"A{row}:H{row}")
                cell = ws[f"A{row}"]
                cell.value = "ОТЧЁТ ПО МАСТЕРАМ"
                cell.font = subheader_font
                cell.fill = subheader_fill
                cell.alignment = center_alignment
                cell.border = thin_border

                row += 1
                headers = [
                    "Мастер",
                    "Заказов",
                    "Сумма",
                    "К сдаче",
                    "Средний чек",
                    "Отзывы",
                    "Выезды",
                    "Прибыль компании",
                ]
                for col_idx, header in enumerate(headers, start=1):
                    cell = ws.cell(row=row, column=col_idx, value=header)
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(
                        start_color="E7E6E6", end_color="E7E6E6", fill_type="solid"
                    )
                    cell.alignment = center_alignment
                    cell.border = thin_border

                row += 1

                # Данные по мастерам
                for master_report in sorted(
                    master_reports, key=lambda x: x.total_master_profit, reverse=True
                ):
                    data = [
                        master_report.master_name,
                        master_report.orders_count,
                        f"{master_report.total_amount:,.2f} ₽",
                        f"{master_report.total_master_profit:,.2f} ₽",
                        f"{master_report.average_check:,.2f} ₽",
                        master_report.reviews_count,
                        master_report.out_of_city_count,
                        f"{master_report.total_company_profit:,.2f} ₽",
                    ]
                    for col_idx, value in enumerate(data, start=1):
                        cell = ws.cell(row=row, column=col_idx, value=value)
                        cell.border = thin_border
                        if col_idx == 1:
                            cell.alignment = left_alignment
                        else:
                            cell.alignment = (
                                right_alignment
                                if isinstance(value, str) and "₽" in value
                                else center_alignment
                            )
                    row += 1

            # Устанавливаем ширину столбцов
            column_widths = {
                "A": 25,  # Мастер/Показатель
                "B": 12,  # Заказов/Значение
                "C": 15,  # Сумма
                "D": 15,  # К сдаче
                "E": 15,  # Средний чек
                "F": 12,  # Отзывы
                "G": 12,  # Выезды
                "H": 18,  # Прибыль компании
            }
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width

            # ✨ Добавляем лист "Заявки по мастерам"
            if master_reports:
                await self._add_orders_by_master_sheet(
                    wb,
                    master_reports,
                    thin_border,
                    header_font,
                    header_fill,
                    subheader_font,
                    subheader_fill,
                    center_alignment,
                    left_alignment,
                    right_alignment,
                )

            # Создаем директорию для отчетов
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)

            # Фиксированное имя файла (обновляется каждый раз)
            filename = f"financial_report_{report.report_type.lower()}.xlsx"
            filepath = reports_dir / filename

            # Сохраняем файл (перезаписываем)
            wb.save(filepath)
            logger.info(f"Excel report saved: {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"Error exporting report to Excel: {e}")
            return None

        finally:
            await self.db.disconnect()

    async def _add_orders_by_master_sheet(
        self,
        wb,
        master_reports,
        thin_border,
        header_font,
        header_fill,
        subheader_font,
        subheader_fill,
        center_alignment,
        left_alignment,
        right_alignment,
    ):
        """Добавляет лист с детализацией заявок по мастерам"""
        ws = wb.create_sheet(title="Заявки по мастерам")

        # Заголовок
        row = 1
        ws.merge_cells(f"A{row}:N{row}")
        cell = ws[f"A{row}"]
        cell.value = "ДЕТАЛИЗАЦИЯ ЗАЯВОК ПО МАСТЕРАМ"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        ws.row_dimensions[row].height = 25

        row += 1

        # Заголовки колонок
        headers = [
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

        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=header)
            cell.font = Font(bold=True)
            cell.fill = subheader_fill
            cell.alignment = center_alignment
            cell.border = thin_border

        row += 1

        # Получаем расширенный репозиторий
        order_repo = await self._get_extended_repo()

        # Для каждого мастера
        for master_report in master_reports:
            master_id = master_report.master_id
            master_name = master_report.master_name

            if not master_id:
                continue

            # Получаем все заявки мастера
            cursor = await self.db.connection.execute(
                """
                SELECT
                    o.id, o.status, o.equipment_type, o.client_name,
                    o.client_address, o.client_phone, o.created_at, o.updated_at,
                    o.total_amount, o.materials_cost, o.master_profit, o.company_profit,
                    o.notes, o.scheduled_time, o.out_of_city, o.has_review
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

            orders = await cursor.fetchall()

            if not orders:
                continue

            # Заголовок мастера
            cell_master = ws[f"A{row}"]
            cell_master.value = f"👨‍🔧 {master_name}"
            cell_master.font = Font(bold=True, size=11, color="FFFFFF")
            cell_master.fill = PatternFill(
                start_color="70AD47", end_color="70AD47", fill_type="solid"
            )
            cell_master.alignment = left_alignment
            ws.merge_cells(f"A{row}:N{row}")
            ws.row_dimensions[row].height = 20
            row += 1

            # Заявки мастера
            for order in orders:
                status_emoji = {
                    "ASSIGNED": "🆕",
                    "ACCEPTED": "✅",
                    "IN_PROGRESS": "⚙️",
                    "COMPLETED": "✔️",
                    "CLOSED": "🔒",
                    "REFUSED": "❌",
                }.get(order["status"], "❓")

                notes = []
                if order["out_of_city"]:
                    notes.append("Выезд")
                if order["has_review"]:
                    notes.append("Отзыв")
                if order["scheduled_time"]:
                    notes.append(f"Время: {order['scheduled_time']}")

                data = [
                    "",
                    order["id"],
                    f"{status_emoji} {order['status']}",
                    order["equipment_type"],
                    order["client_name"],
                    order["client_address"][:30] + "..."
                    if len(order["client_address"]) > 30
                    else order["client_address"],
                    order["client_phone"],
                    order["created_at"][:16] if order["created_at"] else "",
                    order["updated_at"][:16] if order["updated_at"] else "",
                    float(order["total_amount"] or 0),
                    float(order["materials_cost"] or 0),
                    float(order["master_profit"] or 0),
                    float(order["company_profit"] or 0),
                    "; ".join(notes) if notes else "-",
                ]

                for col_idx, value in enumerate(data, start=1):
                    cell = ws.cell(row=row, column=col_idx, value=value)
                    cell.border = thin_border

                    if col_idx == 2:  # ID
                        cell.alignment = center_alignment
                        cell.font = Font(bold=True)
                    elif col_idx == 3:  # Статус
                        cell.alignment = center_alignment
                        if order["status"] == "IN_PROGRESS":
                            cell.fill = PatternFill(
                                start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"
                            )
                        elif order["status"] == "CLOSED":
                            cell.fill = PatternFill(
                                start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"
                            )
                        elif order["status"] == "REFUSED":
                            cell.fill = PatternFill(
                                start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"
                            )
                    elif col_idx in [4, 5, 6, 7, 8, 14]:
                        cell.alignment = left_alignment
                    else:
                        cell.alignment = right_alignment
                        if col_idx >= 10 and col_idx <= 13:
                            cell.number_format = "#,##0.00 ₽"

                row += 1

            # Итоги по мастеру
            cursor = await self.db.connection.execute(
                """
                SELECT
                    SUM(CASE WHEN status = 'CLOSED' THEN total_amount ELSE 0 END) as sum_total,
                    SUM(CASE WHEN status = 'CLOSED' THEN materials_cost ELSE 0 END) as sum_materials,
                    SUM(CASE WHEN status = 'CLOSED' THEN master_profit ELSE 0 END) as sum_master,
                    SUM(CASE WHEN status = 'CLOSED' THEN company_profit ELSE 0 END) as sum_company
                FROM orders WHERE assigned_master_id = ? AND deleted_at IS NULL
                """,
                (master_id,),
            )
            totals = await cursor.fetchone()

            cell_total = ws[f"A{row}"]
            cell_total.value = f"Итого по {master_name}:"
            cell_total.font = Font(bold=True, italic=True)
            ws.merge_cells(f"A{row}:I{row}")

            for col, val in [
                (f"J{row}", totals["sum_total"]),
                (f"K{row}", totals["sum_materials"]),
                (f"L{row}", totals["sum_master"]),
                (f"M{row}", totals["sum_company"]),
            ]:
                cell = ws[col]
                cell.value = float(val or 0)
                cell.font = Font(bold=True)
                cell.number_format = "#,##0.00 ₽"

            row += 2

        # Ширина столбцов листа "Заявки по мастерам"
        widths = {
            "A": 25,
            "B": 6,
            "C": 15,
            "D": 20,
            "E": 20,
            "F": 30,
            "G": 15,
            "H": 18,
            "I": 18,
            "J": 15,
            "K": 15,
            "L": 18,
            "M": 18,
            "N": 35,
        }
        for col, width in widths.items():
            ws.column_dimensions[col].width = width

    async def export_closed_orders_to_excel(self, period_days: int = 30) -> Optional[str]:
        """
        Экспорт закрытых заказов в Excel (обновляет существующий файл)

        Args:
            period_days: За сколько дней показывать заказы

        Returns:
            Путь к файлу или None
        """
        await self.db.connect()

        try:
            # Имя файла
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / "closed_orders.xlsx"

            # Создаем новый workbook (перезаписываем файл)
            wb = Workbook()
            ws = wb.active
            ws.title = "Закрытые заказы"

            # Стили
            header_font = Font(bold=True, size=14, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            subheader_fill = PatternFill(
                start_color="D9E1F2", end_color="D9E1F2", fill_type="solid"
            )
            center_alignment = Alignment(horizontal="center", vertical="center")
            left_alignment = Alignment(horizontal="left", vertical="center")
            right_alignment = Alignment(horizontal="right", vertical="center")
            thin_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            # Заголовок
            row = 1
            ws.merge_cells(f"A{row}:K{row}")
            cell = ws[f"A{row}"]
            cell.value = f"ЗАКРЫТЫЕ ЗАКАЗЫ (за {period_days} дней)"
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            ws.row_dimensions[row].height = 25

            row += 1
            ws.merge_cells(f"A{row}:K{row}")
            cell = ws[f"A{row}"]
            cell.value = f"Обновлено: {get_now().strftime('%d.%m.%Y %H:%M')}"
            cell.font = Font(bold=True, size=10)
            cell.alignment = center_alignment

            row += 2

            # Заголовки колонок
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
                cell = ws.cell(row=row, column=col_idx, value=header)
                cell.font = Font(bold=True)
                cell.fill = subheader_fill
                cell.alignment = center_alignment
                cell.border = thin_border

            row += 1

            # Получаем закрытые заказы
            from datetime import timedelta

            start_date = get_now() - timedelta(days=period_days)

            cursor = await self.db.connection.execute(
                """
                SELECT
                    o.id, o.equipment_type, o.client_name, o.created_at, o.updated_at,
                    o.total_amount, o.materials_cost, o.master_profit, o.company_profit,
                    o.out_of_city, o.has_review,
                    u.first_name || ' ' || COALESCE(u.last_name, '') as master_name
                FROM orders o
                LEFT JOIN masters m ON o.assigned_master_id = m.id
                LEFT JOIN users u ON m.telegram_id = u.telegram_id
                WHERE o.status = 'CLOSED'
                    AND o.updated_at >= ?
                    AND o.deleted_at IS NULL
                ORDER BY o.updated_at DESC
                """,
                (start_date.isoformat(),),
            )

            orders = await cursor.fetchall()

            if not orders:
                ws[f"A{row}"] = "Нет закрытых заказов за этот период"
                ws[f"A{row}"].font = Font(italic=True)
                ws.merge_cells(f"A{row}:K{row}")
            else:
                # Выводим заказы
                for order in orders:
                    additional_info = []
                    if order["out_of_city"]:
                        additional_info.append("Выезд")
                    if order["has_review"]:
                        additional_info.append("Отзыв")

                    data = [
                        order["id"],
                        order["equipment_type"],
                        order["client_name"],
                        order["master_name"] or "Не назначен",
                        order["created_at"][:16] if order["created_at"] else "",
                        order["updated_at"][:16] if order["updated_at"] else "",
                        float(order["total_amount"] or 0),
                        float(order["materials_cost"] or 0),
                        float(order["master_profit"] or 0),
                        float(order["company_profit"] or 0),
                        ", ".join(additional_info) if additional_info else "-",
                    ]

                    for col_idx, value in enumerate(data, start=1):
                        cell = ws.cell(row=row, column=col_idx, value=value)
                        cell.border = thin_border

                        if col_idx == 1:
                            cell.alignment = center_alignment
                            cell.font = Font(bold=True)
                        elif col_idx in [2, 3, 4, 5, 6, 11]:
                            cell.alignment = left_alignment
                        else:
                            cell.alignment = right_alignment
                            if col_idx >= 7 and col_idx <= 10:
                                cell.number_format = "#,##0.00 ₽"

                    row += 1

                # Итоги
                row += 1
                ws[f"A{row}"] = "ИТОГО:"
                ws[f"A{row}"].font = Font(bold=True, size=11)

                total_sum = sum(float(o["total_amount"] or 0) for o in orders)
                total_materials = sum(float(o["materials_cost"] or 0) for o in orders)
                total_master_profit = sum(float(o["master_profit"] or 0) for o in orders)
                total_company_profit = sum(float(o["company_profit"] or 0) for o in orders)

                for col, val in [
                    (f"G{row}", total_sum),
                    (f"H{row}", total_materials),
                    (f"I{row}", total_master_profit),
                    (f"J{row}", total_company_profit),
                ]:
                    cell = ws[col]
                    cell.value = val
                    cell.font = Font(bold=True, size=11)
                    cell.number_format = "#,##0.00 ₽"
                    cell.fill = PatternFill(
                        start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"
                    )

            # Ширина столбцов
            widths = {
                "A": 8,
                "B": 25,
                "C": 20,
                "D": 20,
                "E": 18,
                "F": 18,
                "G": 15,
                "H": 15,
                "I": 18,
                "J": 18,
                "K": 22,
            }
            for col, width in widths.items():
                ws.column_dimensions[col].width = width

            # Сохраняем файл
            wb.save(filepath)
            logger.info(f"Closed orders Excel saved: {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"Error exporting closed orders: {e}")
            return None

        finally:
            await self.db.disconnect()

    async def export_masters_statistics_to_excel(self) -> Optional[str]:
        """
        Экспорт статистики по мастерам в Excel (обновляет существующий файл)

        Returns:
            Путь к файлу или None
        """
        await self.db.connect()

        try:
            # Имя файла
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / "masters_statistics.xlsx"

            # Создаем новый workbook (перезаписываем файл)
            wb = Workbook()
            ws = wb.active
            ws.title = "Статистика мастеров"

            # Стили
            header_font = Font(bold=True, size=14, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            subheader_fill = PatternFill(
                start_color="D9E1F2", end_color="D9E1F2", fill_type="solid"
            )
            center_alignment = Alignment(horizontal="center", vertical="center")
            left_alignment = Alignment(horizontal="left", vertical="center")
            right_alignment = Alignment(horizontal="right", vertical="center")
            thin_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            # Заголовок
            row = 1
            ws.merge_cells(f"A{row}:N{row}")
            cell = ws[f"A{row}"]
            cell.value = "СТАТИСТИКА ПО МАСТЕРАМ"
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            ws.row_dimensions[row].height = 25

            row += 1
            ws.merge_cells(f"A{row}:N{row}")
            cell = ws[f"A{row}"]
            cell.value = f"Обновлено: {get_now().strftime('%d.%m.%Y %H:%M')}"
            cell.font = Font(bold=True, size=10)
            cell.alignment = center_alignment

            row += 2

            # Заголовки колонок
            headers = [
                "ID",
                "Мастер",
                "Всего заявок",
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

            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=row, column=col_idx, value=header)
                cell.font = Font(bold=True)
                cell.fill = subheader_fill
                cell.alignment = center_alignment
                cell.border = thin_border

            row += 1

            # Получаем всех мастеров
            masters_cursor = await self.db.connection.execute(
                """
                SELECT
                    m.id,
                    u.first_name || ' ' || COALESCE(u.last_name, '') as full_name
                FROM masters m
                LEFT JOIN users u ON m.telegram_id = u.telegram_id
                WHERE m.is_approved = 1 AND m.deleted_at IS NULL
                ORDER BY u.first_name
                """
            )
            masters = await masters_cursor.fetchall()

            if not masters:
                ws[f"A{row}"] = "Нет утвержденных мастеров"
                ws[f"A{row}"].font = Font(italic=True)
                ws.merge_cells(f"A{row}:N{row}")
            else:
                # Данные по каждому мастеру
                for master in masters:
                    master_id = master["id"]
                    master_name = master["full_name"]

                    # Получаем статистику
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
                            AND deleted_at IS NULL
                        """,
                        (master_id,),
                    )

                    stats_row = await cursor.fetchone()

                    if not stats_row or not stats_row["total_orders"]:
                        continue

                    # Вычисляем данные
                    total_sum = float(stats_row["total_sum"] or 0)
                    materials = float(stats_row["materials_sum"] or 0)
                    net_profit = total_sum - materials
                    cash_to_company = float(stats_row["company_profit_sum"] or 0)

                    # Данные по мастеру
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
                        cash_to_company,
                        float(stats_row["avg_check"] or 0),
                        stats_row["out_of_city"] or 0,
                        stats_row["reviews"] or 0,
                    ]

                    for col_idx, value in enumerate(master_data, start=1):
                        cell = ws.cell(row=row, column=col_idx, value=value)
                        cell.border = thin_border

                        if col_idx == 1:
                            cell.alignment = center_alignment
                            cell.font = Font(bold=True)
                        elif col_idx == 2:
                            cell.alignment = left_alignment
                            cell.font = Font(bold=True)
                        elif col_idx in [3, 4, 5, 6, 13, 14]:
                            cell.alignment = center_alignment
                        else:
                            cell.alignment = right_alignment
                            if col_idx >= 7 and col_idx <= 12:
                                cell.number_format = "#,##0.00 ₽"

                    row += 1

                # ИТОГО
                row += 1
                ws[f"A{row}"] = "ИТОГО:"
                ws[f"A{row}"].font = Font(bold=True, size=12)
                ws[f"A{row}"].fill = PatternFill(
                    start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"
                )
                ws.merge_cells(f"A{row}:B{row}")

                # Суммы
                cursor = await self.db.connection.execute(
                    """
                    SELECT
                        COUNT(*) as total_orders,
                        SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed,
                        SUM(CASE WHEN status IN ('ASSIGNED', 'IN_PROGRESS', 'ACCEPTED') THEN 1 ELSE 0 END) as in_work,
                        SUM(CASE WHEN status = 'REFUSED' THEN 1 ELSE 0 END) as refused,
                        SUM(CASE WHEN status = 'CLOSED' THEN total_amount ELSE 0 END) as total_sum,
                        SUM(CASE WHEN status = 'CLOSED' THEN materials_cost ELSE 0 END) as materials_sum,
                        SUM(CASE WHEN status = 'CLOSED' THEN company_profit ELSE 0 END) as company_profit_sum,
                        AVG(CASE WHEN status = 'CLOSED' THEN total_amount ELSE NULL END) as avg_check,
                        SUM(CASE WHEN status = 'CLOSED' AND out_of_city = 1 THEN 1 ELSE 0 END) as out_of_city,
                        SUM(CASE WHEN status = 'CLOSED' AND has_review = 1 THEN 1 ELSE 0 END) as reviews
                    FROM orders
                    WHERE assigned_master_id IS NOT NULL
                        AND deleted_at IS NULL
                    """
                )

                totals = await cursor.fetchone()

                total_sum = float(totals["total_sum"] or 0)
                materials_sum = float(totals["materials_sum"] or 0)
                net_profit_total = total_sum - materials_sum

                totals_data = [
                    totals["total_orders"],
                    totals["closed"],
                    totals["in_work"],
                    totals["refused"],
                    total_sum,
                    materials_sum,
                    net_profit_total,
                    float(totals["company_profit_sum"] or 0),
                    float(totals["company_profit_sum"] or 0),
                    float(totals["avg_check"] or 0),
                    totals["out_of_city"],
                    totals["reviews"],
                ]

                for col_idx, value in enumerate(totals_data, start=3):
                    cell = ws.cell(row=row, column=col_idx, value=value)
                    cell.font = Font(bold=True, size=11)
                    cell.fill = PatternFill(
                        start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"
                    )
                    cell.border = thin_border

                    if col_idx in [3, 4, 5, 6, 13, 14]:
                        cell.alignment = center_alignment
                    else:
                        cell.alignment = right_alignment
                        if col_idx >= 7 and col_idx <= 12:
                            cell.number_format = "#,##0.00 ₽"

            # Ширина столбцов
            widths = {
                "A": 8,
                "B": 25,
                "C": 12,
                "D": 12,
                "E": 12,
                "F": 12,
                "G": 15,
                "H": 15,
                "I": 15,
                "J": 18,
                "K": 15,
                "L": 15,
                "M": 10,
                "N": 10,
            }
            for col, width in widths.items():
                ws.column_dimensions[col].width = width

            # Сохраняем файл
            wb.save(filepath)
            logger.info(f"Masters statistics Excel saved: {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"Error exporting masters statistics: {e}")
            return None

        finally:
            await self.db.disconnect()

    async def export_master_orders_to_excel(self, master_id: int) -> Optional[str]:
        """
        Экспорт всех заявок одного мастера в Excel

        Args:
            master_id: ID мастера

        Returns:
            Путь к файлу или None
        """
        await self.db.connect()

        try:
            # Получаем информацию о мастере
            cursor = await self.db.connection.execute(
                """
                SELECT
                    m.id,
                    u.first_name || ' ' || COALESCE(u.last_name, '') as full_name,
                    m.phone
                FROM masters m
                LEFT JOIN users u ON m.telegram_id = u.telegram_id
                WHERE m.id = ?
                """,
                (master_id,),
            )
            master = await cursor.fetchone()

            if not master:
                logger.error(f"Master {master_id} not found")
                return None

            master_name = master["full_name"]

            # Имя файла
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            safe_name = "".join(
                c for c in master_name if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            filepath = reports_dir / f"master_{master_id}_{safe_name}.xlsx"

            # Создаем workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Заявки мастера"

            # Стили
            header_font = Font(bold=True, size=14, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            subheader_fill = PatternFill(
                start_color="D9E1F2", end_color="D9E1F2", fill_type="solid"
            )
            stat_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
            center_alignment = Alignment(horizontal="center", vertical="center")
            left_alignment = Alignment(horizontal="left", vertical="center")
            right_alignment = Alignment(horizontal="right", vertical="center")
            thin_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            # Заголовок
            row = 1
            ws.merge_cells(f"A{row}:N{row}")
            cell = ws[f"A{row}"]
            cell.value = f"ОТЧЕТ ПО МАСТЕРУ: {master_name}"
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            ws.row_dimensions[row].height = 25

            row += 1
            ws.merge_cells(f"A{row}:N{row}")
            cell = ws[f"A{row}"]
            cell.value = (
                f"Обновлено: {get_now().strftime('%d.%m.%Y %H:%M')} | Телефон: {master['phone']}"
            )
            cell.font = Font(bold=True, size=10)
            cell.alignment = center_alignment

            row += 2

            # Статистика мастера
            stats_cursor = await self.db.connection.execute(
                """
                SELECT
                    COUNT(*) as total_orders,
                    SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed,
                    SUM(CASE WHEN status IN ('ASSIGNED', 'IN_PROGRESS', 'ACCEPTED') THEN 1 ELSE 0 END) as in_work,
                    SUM(CASE WHEN status = 'REFUSED' THEN 1 ELSE 0 END) as refused,
                    SUM(CASE WHEN status = 'CLOSED' THEN total_amount ELSE 0 END) as total_sum,
                    SUM(CASE WHEN status = 'CLOSED' THEN materials_cost ELSE 0 END) as materials_sum,
                    SUM(CASE WHEN status = 'CLOSED' THEN company_profit ELSE 0 END) as company_profit_sum,
                    AVG(CASE WHEN status = 'CLOSED' THEN total_amount ELSE NULL END) as avg_check
                FROM orders
                WHERE assigned_master_id = ? AND deleted_at IS NULL
                """,
                (master_id,),
            )
            stats = await stats_cursor.fetchone()

            # Блок статистики
            ws[f"A{row}"] = "СТАТИСТИКА:"
            ws[f"A{row}"].font = Font(bold=True, size=11)
            ws.merge_cells(f"A{row}:N{row}")
            row += 1

            stat_data = [
                ["Всего заявок:", stats["total_orders"] or 0],
                ["Завершено:", stats["closed"] or 0],
                ["В работе:", stats["in_work"] or 0],
                ["Отказано:", stats["refused"] or 0],
                ["Общая сумма:", f"{float(stats['total_sum'] or 0):,.2f} ₽"],
                ["Материалы:", f"{float(stats['materials_sum'] or 0):,.2f} ₽"],
                ["Сдача в кассу:", f"{float(stats['company_profit_sum'] or 0):,.2f} ₽"],
                ["Средний чек:", f"{float(stats['avg_check'] or 0):,.2f} ₽"],
            ]

            for label, value in stat_data:
                ws[f"A{row}"] = label
                ws[f"A{row}"].font = Font(bold=True)
                ws[f"B{row}"] = value
                ws[f"B{row}"].fill = stat_fill
                ws.merge_cells(f"B{row}:C{row}")
                row += 1

            row += 1

            # Заголовки колонок таблицы заявок
            headers = [
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
                "Прибыль компании",
                "Выезд",
                "Отзыв",
            ]

            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=row, column=col_idx, value=header)
                cell.font = Font(bold=True)
                cell.fill = subheader_fill
                cell.alignment = center_alignment
                cell.border = thin_border

            row += 1

            # Получаем все заявки мастера
            orders_cursor = await self.db.connection.execute(
                """
                SELECT
                    id, status, equipment_type, client_name, client_address, client_phone,
                    created_at, updated_at, total_amount, materials_cost,
                    master_profit, company_profit, out_of_city, has_review
                FROM orders
                WHERE assigned_master_id = ? AND deleted_at IS NULL
                ORDER BY
                    CASE status
                        WHEN 'IN_PROGRESS' THEN 1
                        WHEN 'ACCEPTED' THEN 2
                        WHEN 'ASSIGNED' THEN 3
                        WHEN 'COMPLETED' THEN 4
                        WHEN 'CLOSED' THEN 5
                        WHEN 'REFUSED' THEN 6
                        ELSE 7
                    END,
                    created_at DESC
                """,
                (master_id,),
            )

            orders = await orders_cursor.fetchall()

            if not orders:
                ws[f"A{row}"] = "У мастера пока нет заявок"
                ws[f"A{row}"].font = Font(italic=True)
                ws.merge_cells(f"A{row}:N{row}")
            else:
                # Выводим заявки
                for order in orders:
                    status_emoji = {
                        "NEW": "🆕",
                        "ASSIGNED": "📋",
                        "ACCEPTED": "✅",
                        "IN_PROGRESS": "⚙️",
                        "COMPLETED": "✔️",
                        "CLOSED": "🔒",
                        "REFUSED": "❌",
                    }.get(order["status"], "❓")

                    data = [
                        order["id"],
                        f"{status_emoji} {order['status']}",
                        order["equipment_type"],
                        order["client_name"],
                        order["client_address"][:30] + "..."
                        if len(order["client_address"] or "") > 30
                        else (order["client_address"] or ""),
                        order["client_phone"],
                        order["created_at"][:16] if order["created_at"] else "",
                        order["updated_at"][:16] if order["updated_at"] else "",
                        float(order["total_amount"] or 0),
                        float(order["materials_cost"] or 0),
                        float(order["master_profit"] or 0),
                        float(order["company_profit"] or 0),
                        "Да" if order["out_of_city"] else "",
                        "Да" if order["has_review"] else "",
                    ]

                    for col_idx, value in enumerate(data, start=1):
                        cell = ws.cell(row=row, column=col_idx, value=value)
                        cell.border = thin_border

                        if col_idx == 1:  # ID
                            cell.alignment = center_alignment
                            cell.font = Font(bold=True)
                        elif col_idx == 2:  # Статус
                            cell.alignment = center_alignment
                            # Цветовое кодирование
                            if order["status"] == "IN_PROGRESS":
                                cell.fill = PatternFill(
                                    start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"
                                )
                            elif order["status"] == "CLOSED":
                                cell.fill = PatternFill(
                                    start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"
                                )
                            elif order["status"] == "REFUSED":
                                cell.fill = PatternFill(
                                    start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"
                                )
                        elif col_idx in [3, 4, 5, 6, 7, 8]:  # Текстовые поля
                            cell.alignment = left_alignment
                        else:
                            cell.alignment = center_alignment if col_idx >= 13 else right_alignment
                            if col_idx >= 9 and col_idx <= 12:  # Денежные поля
                                cell.number_format = "#,##0.00 ₽"

                    row += 1

                # Итоги
                row += 1
                ws[f"A{row}"] = "ИТОГО:"
                ws[f"A{row}"].font = Font(bold=True, size=11)
                ws.merge_cells(f"A{row}:H{row}")

                total_sum = sum(
                    float(o["total_amount"] or 0) for o in orders if o["status"] == "CLOSED"
                )
                total_materials = sum(
                    float(o["materials_cost"] or 0) for o in orders if o["status"] == "CLOSED"
                )
                total_master_profit = sum(
                    float(o["master_profit"] or 0) for o in orders if o["status"] == "CLOSED"
                )
                total_company_profit = sum(
                    float(o["company_profit"] or 0) for o in orders if o["status"] == "CLOSED"
                )

                for col, val in [
                    (f"I{row}", total_sum),
                    (f"J{row}", total_materials),
                    (f"K{row}", total_master_profit),
                    (f"L{row}", total_company_profit),
                ]:
                    cell = ws[col]
                    cell.value = val
                    cell.font = Font(bold=True, size=11)
                    cell.number_format = "#,##0.00 ₽"
                    cell.fill = stat_fill
                    cell.border = thin_border

            # Ширина столбцов
            widths = {
                "A": 8,
                "B": 15,
                "C": 20,
                "D": 20,
                "E": 30,
                "F": 15,
                "G": 18,
                "H": 18,
                "I": 15,
                "J": 15,
                "K": 18,
                "L": 18,
                "M": 10,
                "N": 10,
            }
            for col, width in widths.items():
                ws.column_dimensions[col].width = width

            # Сохраняем файл
            wb.save(filepath)
            logger.info(f"Master orders Excel saved: {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"Error exporting master orders: {e}")
            return None

        finally:
            await self.db.disconnect()

    async def _add_closed_orders_sheet(
        self,
        wb,
        report,
        thin_border,
        header_font,
        header_fill,
        subheader_font,
        subheader_fill,
        center_alignment,
        left_alignment,
        right_alignment,
    ):
        """Добавляет лист с детализацией закрытых заказов"""
        ws = wb.create_sheet(title="Закрытые заказы")

        # Заголовок
        row = 1
        ws.merge_cells(f"A{row}:K{row}")
        cell = ws[f"A{row}"]
        cell.value = "ДЕТАЛИЗАЦИЯ ЗАКРЫТЫХ ЗАКАЗОВ"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        ws.row_dimensions[row].height = 25

        row += 1

        # Заголовки колонок
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
            cell = ws.cell(row=row, column=col_idx, value=header)
            cell.font = Font(bold=True)
            cell.fill = subheader_fill
            cell.alignment = center_alignment
            cell.border = thin_border

        row += 1

        # Получаем все закрытые заказы за период
        cursor = await self.db.connection.execute(
            """
            SELECT
                o.id, o.equipment_type, o.client_name, o.created_at, o.updated_at,
                o.total_amount, o.materials_cost, o.master_profit, o.company_profit,
                o.out_of_city, o.has_review,
                m.first_name || ' ' || m.last_name as master_name
            FROM orders o
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            WHERE o.status = 'CLOSED'
                AND o.updated_at >= ?
                AND o.updated_at <= ?
                AND o.deleted_at IS NULL
            ORDER BY o.updated_at DESC
            """,
            (report.period_start.isoformat(), report.period_end.isoformat()),
        )

        orders = await cursor.fetchall()

        if not orders:
            # Если нет заказов
            ws[f"A{row}"] = "Нет закрытых заказов за этот период"
            ws[f"A{row}"].font = Font(italic=True)
            ws.merge_cells(f"A{row}:K{row}")
        else:
            # Выводим заказы
            for order in orders:
                additional_info = []
                if order["out_of_city"]:
                    additional_info.append("Выезд за город")
                if order["has_review"]:
                    additional_info.append("Отзыв")

                data = [
                    order["id"],
                    order["equipment_type"],
                    order["client_name"],
                    order["master_name"] or "Не назначен",
                    order["created_at"][:16] if order["created_at"] else "",
                    order["updated_at"][:16] if order["updated_at"] else "",
                    float(order["total_amount"] or 0),
                    float(order["materials_cost"] or 0),
                    float(order["master_profit"] or 0),
                    float(order["company_profit"] or 0),
                    ", ".join(additional_info) if additional_info else "-",
                ]

                for col_idx, value in enumerate(data, start=1):
                    cell = ws.cell(row=row, column=col_idx, value=value)
                    cell.border = thin_border

                    if col_idx == 1:  # ID
                        cell.alignment = center_alignment
                        cell.font = Font(bold=True)
                    elif col_idx in [2, 3, 4, 5, 6, 11]:  # Текстовые поля
                        cell.alignment = left_alignment
                    else:
                        cell.alignment = right_alignment
                        if col_idx >= 7 and col_idx <= 10:  # Денежные поля
                            cell.number_format = "#,##0.00 ₽"

                row += 1

            # Итоги
            row += 1
            ws[f"A{row}"] = "ИТОГО:"
            ws[f"A{row}"].font = Font(bold=True, size=11)

            total_sum = sum(float(o["total_amount"] or 0) for o in orders)
            total_materials = sum(float(o["materials_cost"] or 0) for o in orders)
            total_master_profit = sum(float(o["master_profit"] or 0) for o in orders)
            total_company_profit = sum(float(o["company_profit"] or 0) for o in orders)

            for col, val in [
                (f"G{row}", total_sum),
                (f"H{row}", total_materials),
                (f"I{row}", total_master_profit),
                (f"J{row}", total_company_profit),
            ]:
                cell = ws[col]
                cell.value = val
                cell.font = Font(bold=True, size=11)
                cell.number_format = "#,##0.00 ₽"
                cell.fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

        # Ширина столбцов
        widths = {
            "A": 8,
            "B": 25,
            "C": 20,
            "D": 20,
            "E": 18,
            "F": 18,
            "G": 15,
            "H": 15,
            "I": 18,
            "J": 18,
            "K": 22,
        }
        for col, width in widths.items():
            ws.column_dimensions[col].width = width

    async def _add_masters_statistics_sheet(
        self,
        wb,
        master_reports,
        thin_border,
        header_font,
        header_fill,
        subheader_font,
        subheader_fill,
        center_alignment,
        left_alignment,
        right_alignment,
    ):
        """Добавляет лист со статистикой по мастерам"""
        ws = wb.create_sheet(title="Статистика мастеров")

        # Заголовок
        row = 1
        ws.merge_cells(f"A{row}:N{row}")
        cell = ws[f"A{row}"]
        cell.value = "РАСШИРЕННАЯ СТАТИСТИКА ПО МАСТЕРАМ"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        ws.row_dimensions[row].height = 25

        row += 1

        # Заголовки колонок
        headers = [
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

        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=header)
            cell.font = Font(bold=True)
            cell.fill = subheader_fill
            cell.alignment = center_alignment
            cell.border = thin_border

        row += 1

        # Данные по каждому мастеру
        for master_report in master_reports:
            master_id = master_report.master_id
            master_name = master_report.master_name

            if not master_id:
                continue

            # Получаем расширенную статистику по мастеру
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
                    AND deleted_at IS NULL
                """,
                (master_id,),
            )

            stats_row = await cursor.fetchone()

            if not stats_row:
                continue

            # Вычисляем данные
            total_sum = float(stats_row["total_sum"] or 0)
            materials = float(stats_row["materials_sum"] or 0)
            net_profit = total_sum - materials
            cash_to_company = float(stats_row["company_profit_sum"] or 0)

            # Данные по мастеру
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
                cell = ws.cell(row=row, column=col_idx, value=value)
                cell.border = thin_border

                # Форматирование
                if col_idx == 1:  # ID
                    cell.alignment = center_alignment
                    cell.font = Font(bold=True)
                elif col_idx == 2:  # Имя
                    cell.alignment = left_alignment
                    cell.font = Font(bold=True)
                elif col_idx in [3, 4, 5, 6, 13, 14]:  # Счетчики
                    cell.alignment = center_alignment
                else:  # Денежные поля
                    cell.alignment = right_alignment
                    if col_idx >= 7 and col_idx <= 12:
                        cell.number_format = "#,##0.00 ₽"

            row += 1

        # ИТОГО по всем мастерам
        row += 1
        ws[f"A{row}"] = "ИТОГО:"
        ws[f"A{row}"].font = Font(bold=True, size=12)
        ws[f"A{row}"].fill = PatternFill(
            start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"
        )
        ws.merge_cells(f"A{row}:B{row}")

        # Суммы по всем мастерам
        cursor = await self.db.connection.execute(
            """
            SELECT
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed,
                SUM(CASE WHEN status IN ('ASSIGNED', 'IN_PROGRESS', 'ACCEPTED') THEN 1 ELSE 0 END) as in_work,
                SUM(CASE WHEN status = 'REFUSED' THEN 1 ELSE 0 END) as refused,
                SUM(CASE WHEN status = 'CLOSED' THEN total_amount ELSE 0 END) as total_sum,
                SUM(CASE WHEN status = 'CLOSED' THEN materials_cost ELSE 0 END) as materials_sum,
                SUM(CASE WHEN status = 'CLOSED' THEN company_profit ELSE 0 END) as company_profit_sum,
                AVG(CASE WHEN status = 'CLOSED' THEN total_amount ELSE NULL END) as avg_check,
                SUM(CASE WHEN status = 'CLOSED' AND out_of_city = 1 THEN 1 ELSE 0 END) as out_of_city,
                SUM(CASE WHEN status = 'CLOSED' AND has_review = 1 THEN 1 ELSE 0 END) as reviews
            FROM orders
            WHERE assigned_master_id IS NOT NULL
                AND deleted_at IS NULL
            """
        )

        totals = await cursor.fetchone()

        total_sum = float(totals["total_sum"] or 0)
        materials_sum = float(totals["materials_sum"] or 0)
        net_profit_total = total_sum - materials_sum

        totals_data = [
            totals["total_orders"],
            totals["closed"],
            totals["in_work"],
            totals["refused"],
            total_sum,
            materials_sum,
            net_profit_total,
            float(totals["company_profit_sum"] or 0),
            float(totals["company_profit_sum"] or 0),
            float(totals["avg_check"] or 0),
            totals["out_of_city"],
            totals["reviews"],
        ]

        for col_idx, value in enumerate(totals_data, start=3):
            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.font = Font(bold=True, size=11)
            cell.fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
            cell.border = thin_border

            if col_idx in [3, 4, 5, 6, 13, 14]:  # Счетчики
                cell.alignment = center_alignment
            else:
                cell.alignment = right_alignment
                if col_idx >= 7 and col_idx <= 12:
                    cell.number_format = "#,##0.00 ₽"

        # Ширина столбцов
        widths = {
            "A": 8,
            "B": 25,
            "C": 12,
            "D": 12,
            "E": 12,
            "F": 12,
            "G": 15,
            "H": 15,
            "I": 15,
            "J": 18,
            "K": 15,
            "L": 15,
            "M": 10,
            "N": 10,
        }
        for col, width in widths.items():
            ws.column_dimensions[col].width = width
