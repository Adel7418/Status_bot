"""
Сервис для экспорта активных (незакрытых) заявок в Excel
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app.config import OrderStatus
from app.database.db import Database
from app.utils.helpers import get_now


logger = logging.getLogger(__name__)


class ActiveOrdersExportService:
    """Сервис для экспорта активных заявок в Excel"""

    def __init__(self):
        self.db = Database()

    async def export_active_orders_to_excel(self) -> Optional[str]:
        """
        Экспорт всех активных (незакрытых) заявок в Excel

        Returns:
            Путь к созданному файлу или None
        """
        await self.db.connect()

        try:
            # Получаем все активные заявки (не CLOSED и не REFUSED)
            all_orders = await self.db.get_all_orders()
            active_orders = [
                order
                for order in all_orders
                if order.status not in [OrderStatus.CLOSED, OrderStatus.REFUSED]
            ]

            if not active_orders:
                logger.info("No active orders found")
                return None

            # Создаем Excel файл
            wb = Workbook()
            ws = wb.active
            ws.title = "Активные заявки"

            # Стили
            header_font = Font(bold=True, size=12, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            status_fills = {
                OrderStatus.NEW: PatternFill(
                    start_color="FFE699", end_color="FFE699", fill_type="solid"
                ),
                OrderStatus.ASSIGNED: PatternFill(
                    start_color="C6E0B4", end_color="C6E0B4", fill_type="solid"
                ),
                OrderStatus.ACCEPTED: PatternFill(
                    start_color="A9D08E", end_color="A9D08E", fill_type="solid"
                ),
                OrderStatus.ONSITE: PatternFill(
                    start_color="70AD47", end_color="70AD47", fill_type="solid"
                ),
                OrderStatus.DR: PatternFill(
                    start_color="F4B084", end_color="F4B084", fill_type="solid"
                ),
            }

            center_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            left_alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

            thin_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            # Заголовок отчета
            row = 1
            ws.merge_cells(f"A{row}:K{row}")
            cell = ws[f"A{row}"]
            cell.value = f"АКТИВНЫЕ ЗАЯВКИ - {get_now().strftime('%d.%m.%Y %H:%M')}"
            cell.font = Font(bold=True, size=14)
            cell.fill = header_fill
            cell.alignment = center_alignment
            ws.row_dimensions[row].height = 25

            row += 1
            ws.merge_cells(f"A{row}:K{row}")
            cell = ws[f"A{row}"]
            cell.value = f"Всего активных заявок: {len(active_orders)}"
            cell.font = Font(bold=True, size=11)
            cell.alignment = center_alignment
            ws.row_dimensions[row].height = 20

            row += 2

            # Заголовки столбцов
            headers = [
                "№ Заявки",
                "Статус",
                "Оборудование",
                "Описание",
                "Клиент",
                "Адрес",
                "Телефон",
                "Мастер",
                "Диспетчер",
                "Время прибытия",
                "Создана",
            ]

            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=row, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_alignment
                cell.border = thin_border

            row += 1

            # Сортируем заявки по статусу и дате создания
            status_priority = {
                OrderStatus.NEW: 1,
                OrderStatus.ASSIGNED: 2,
                OrderStatus.ACCEPTED: 3,
                OrderStatus.ONSITE: 4,
                OrderStatus.DR: 5,
            }

            sorted_orders = sorted(
                active_orders,
                key=lambda x: (status_priority.get(x.status, 99), x.created_at or datetime.min),
            )

            # Данные по заявкам
            for order in sorted_orders:
                status_name = OrderStatus.get_status_name(order.status)
                status_emoji = OrderStatus.get_status_emoji(order.status)

                # Форматируем дату создания
                created_str = ""
                if order.created_at:
                    if isinstance(order.created_at, str):
                        try:
                            created_dt = datetime.fromisoformat(
                                order.created_at.replace("Z", "+00:00")
                            )
                            created_str = created_dt.strftime("%d.%m.%Y %H:%M")
                        except:
                            created_str = order.created_at
                    else:
                        created_str = order.created_at.strftime("%d.%m.%Y %H:%M")

                data = [
                    order.id,
                    f"{status_emoji} {status_name}",
                    order.equipment_type or "",
                    order.description or "",
                    order.client_name or "",
                    order.client_address or "",
                    order.client_phone or "",
                    order.master_name or "Не назначен",
                    order.dispatcher_name or "",
                    order.scheduled_time or "",
                    created_str,
                ]

                for col_idx, value in enumerate(data, start=1):
                    cell = ws.cell(row=row, column=col_idx, value=value)
                    cell.border = thin_border

                    # Выравнивание
                    if col_idx == 1:  # ID
                        cell.alignment = center_alignment
                    elif col_idx in [2]:  # Статус
                        cell.alignment = center_alignment
                    else:
                        cell.alignment = left_alignment

                    # Цвет фона по статусу
                    if col_idx <= 11:
                        cell.fill = status_fills.get(order.status, PatternFill())

                row += 1

            # Добавляем сводку по статусам внизу
            row += 1
            ws.merge_cells(f"A{row}:K{row}")
            cell = ws[f"A{row}"]
            cell.value = "СВОДКА ПО СТАТУСАМ"
            cell.font = Font(bold=True, size=11)
            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            cell.alignment = center_alignment
            cell.border = thin_border

            row += 1

            # Подсчитываем по статусам
            status_counts = {}
            for order in active_orders:
                status_counts[order.status] = status_counts.get(order.status, 0) + 1

            for status in [
                OrderStatus.NEW,
                OrderStatus.ASSIGNED,
                OrderStatus.ACCEPTED,
                OrderStatus.ONSITE,
                OrderStatus.DR,
            ]:
                if status in status_counts:
                    status_name = OrderStatus.get_status_name(status)
                    status_emoji = OrderStatus.get_status_emoji(status)
                    count = status_counts[status]

                    ws.merge_cells(f"A{row}:B{row}")
                    cell = ws[f"A{row}"]
                    cell.value = f"{status_emoji} {status_name}"
                    cell.alignment = left_alignment
                    cell.border = thin_border
                    cell.fill = status_fills.get(status, PatternFill())

                    cell = ws.cell(row=row, column=3, value=count)
                    cell.alignment = center_alignment
                    cell.border = thin_border
                    cell.fill = status_fills.get(status, PatternFill())
                    cell.font = Font(bold=True)

                    row += 1

            # Устанавливаем ширину столбцов
            column_widths = {
                "A": 10,  # № Заявки
                "B": 18,  # Статус
                "C": 20,  # Оборудование
                "D": 30,  # Описание
                "E": 20,  # Клиент
                "F": 30,  # Адрес
                "G": 15,  # Телефон
                "H": 20,  # Мастер
                "I": 20,  # Диспетчер
                "J": 20,  # Время прибытия
                "K": 18,  # Создана
            }
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width

            # Создаем директорию для отчетов
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)

            # Генерируем имя файла
            timestamp = get_now().strftime("%Y%m%d_%H%M%S")
            filename = f"active_orders_{timestamp}.xlsx"
            filepath = reports_dir / filename

            # Сохраняем файл
            wb.save(filepath)
            logger.info(f"Active orders Excel report saved: {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"Error exporting active orders to Excel: {e}")
            return None

        finally:
            await self.db.disconnect()
