"""
Сервис для экспорта финансовых отчетов в Excel
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.database.db import Database
from app.database.models import FinancialReport, MasterFinancialReport
from app.utils.helpers import get_now

logger = logging.getLogger(__name__)


class ExcelExportService:
    """Сервис для экспорта отчетов в Excel"""

    def __init__(self):
        self.db = Database()

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
            subheader_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            total_font = Font(bold=True, size=11)
            total_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
            
            center_alignment = Alignment(horizontal="center", vertical="center")
            left_alignment = Alignment(horizontal="left", vertical="center")
            right_alignment = Alignment(horizontal="right", vertical="center")
            
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
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
            ws.merge_cells(f'A{row}:H{row}')
            cell = ws[f'A{row}']
            cell.value = f"ФИНАНСОВЫЙ ОТЧЕТ - {report.report_type}"
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            ws.row_dimensions[row].height = 25

            row += 1
            ws.merge_cells(f'A{row}:H{row}')
            cell = ws[f'A{row}']
            cell.value = f"Период: {period_text}"
            cell.font = Font(bold=True, size=12)
            cell.alignment = center_alignment
            ws.row_dimensions[row].height = 20

            row += 2

            # Общие показатели
            ws.merge_cells(f'A{row}:H{row}')
            cell = ws[f'A{row}']
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
                        cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
                    if col_idx == 2:
                        cell.alignment = right_alignment
                    else:
                        cell.alignment = left_alignment
                row += 1

            row += 1

            # Отчеты по мастерам
            if master_reports:
                ws.merge_cells(f'A{row}:H{row}')
                cell = ws[f'A{row}']
                cell.value = "ОТЧЁТ ПО МАСТЕРАМ"
                cell.font = subheader_font
                cell.fill = subheader_fill
                cell.alignment = center_alignment
                cell.border = thin_border

                row += 1
                headers = ["Мастер", "Заказов", "Сумма", "К сдаче", "Средний чек", "Отзывы", "Выезды", "Прибыль компании"]
                for col_idx, header in enumerate(headers, start=1):
                    cell = ws.cell(row=row, column=col_idx, value=header)
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
                    cell.alignment = center_alignment
                    cell.border = thin_border

                row += 1

                # Данные по мастерам
                for master_report in sorted(master_reports, key=lambda x: x.total_master_profit, reverse=True):
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
                            cell.alignment = right_alignment if isinstance(value, str) and '₽' in value else center_alignment
                    row += 1

            # Устанавливаем ширину столбцов
            column_widths = {
                'A': 25,  # Мастер/Показатель
                'B': 12,  # Заказов/Значение
                'C': 15,  # Сумма
                'D': 15,  # К сдаче
                'E': 15,  # Средний чек
                'F': 12,  # Отзывы
                'G': 12,  # Выезды
                'H': 18,  # Прибыль компании
            }
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width

            # Создаем директорию для отчетов
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)

            # Генерируем имя файла
            timestamp = get_now().strftime("%Y%m%d_%H%M%S")
            filename = f"financial_report_{report.report_type.lower()}_{timestamp}.xlsx"
            filepath = reports_dir / filename

            # Сохраняем файл
            wb.save(filepath)
            logger.info(f"Excel report saved: {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"Error exporting report to Excel: {e}")
            return None

        finally:
            await self.db.disconnect()

