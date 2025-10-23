"""
Сервис автоматического обновления отчетов
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.database import Database
from app.services.excel_export import ExcelExportService

logger = logging.getLogger(__name__)


class AutoUpdateService:
    """Сервис для автоматического обновления отчетов"""

    def __init__(self):
        self.db = Database()
        self.excel_service = ExcelExportService()

    async def update_all_reports(self) -> dict[str, Any]:
        """
        Обновляет все отчеты автоматически
        
        Returns:
            Словарь с результатами обновления
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "updated_reports": [],
            "errors": [],
            "total_updated": 0
        }

        try:
            # Обновляем отчет по закрытым заказам
            await self._update_closed_orders_report()
            results["updated_reports"].append("closed_orders")
            results["total_updated"] += 1

            # Обновляем статистику мастеров
            await self._update_masters_statistics()
            results["updated_reports"].append("masters_statistics")
            results["total_updated"] += 1

            # Обновляем детализацию по мастерам
            await self._update_masters_detailed_report()
            results["updated_reports"].append("masters_detailed")
            results["total_updated"] += 1

            logger.info(f"Автоматическое обновление завершено. Обновлено отчетов: {results['total_updated']}")

        except Exception as e:
            error_msg = f"Ошибка при автоматическом обновлении: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        return results

    async def _update_closed_orders_report(self) -> None:
        """Обновляет отчет по закрытым заказам"""
        try:
            await self.excel_service.export_closed_orders_to_excel(period_days=30)
            logger.info("Отчет по закрытым заказам обновлен")
        except Exception as e:
            logger.error(f"Ошибка обновления отчета по закрытым заказам: {e}")
            raise

    async def _update_masters_statistics(self) -> None:
        """Обновляет статистику мастеров"""
        try:
            await self.excel_service.export_masters_statistics_to_excel()
            logger.info("Статистика мастеров обновлена")
        except Exception as e:
            logger.error(f"Ошибка обновления статистики мастеров: {e}")
            raise

    async def _update_masters_detailed_report(self) -> None:
        """Обновляет детализированный отчет по мастерам"""
        try:
            # Создаем временный отчет для детализации
            await self.db.connect()
            
            # Получаем всех мастеров
            masters = await self.db.get_all_masters(only_approved=True)
            
            if masters:
                # Создаем детализированный отчет
                await self.excel_service.export_master_orders_to_excel(master_id=None)  # Все мастера
                logger.info("Детализированный отчет по мастерам обновлен")
            
        except Exception as e:
            logger.error(f"Ошибка обновления детализированного отчета: {e}")
            raise
        finally:
            await self.db.disconnect()

    async def get_report_status(self) -> dict[str, Any]:
        """
        Получает статус всех отчетов
        
        Returns:
            Словарь со статусом отчетов
        """
        reports_dir = Path("reports")
        status = {
            "timestamp": datetime.now().isoformat(),
            "reports": {}
        }

        # Проверяем существование файлов отчетов
        report_files = {
            "closed_orders": "closed_orders.xlsx",
            "masters_statistics": "masters_statistics.xlsx",
            "masters_detailed": "masters_detailed.xlsx"
        }

        for report_name, filename in report_files.items():
            filepath = reports_dir / filename
            if filepath.exists():
                stat = filepath.stat()
                status["reports"][report_name] = {
                    "exists": True,
                    "size": stat.st_size,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "age_hours": (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).total_seconds() / 3600
                }
            else:
                status["reports"][report_name] = {
                    "exists": False,
                    "size": 0,
                    "last_modified": None,
                    "age_hours": None
                }

        return status

    async def cleanup_old_reports(self, max_age_hours: int = 168) -> dict[str, Any]:
        """
        Очищает старые отчеты
        
        Args:
            max_age_hours: Максимальный возраст файла в часах (по умолчанию 7 дней)
            
        Returns:
            Словарь с результатами очистки
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "deleted_files": [],
            "errors": [],
            "total_deleted": 0
        }

        try:
            reports_dir = Path("reports")
            if not reports_dir.exists():
                return results

            current_time = datetime.now()
            max_age = timedelta(hours=max_age_hours)

            for file_path in reports_dir.glob("*.xlsx"):
                try:
                    file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_age > max_age:
                        file_path.unlink()
                        results["deleted_files"].append(str(file_path))
                        results["total_deleted"] += 1
                        logger.info(f"Удален старый отчет: {file_path}")
                        
                except Exception as e:
                    error_msg = f"Ошибка удаления файла {file_path}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            logger.info(f"Очистка завершена. Удалено файлов: {results['total_deleted']}")

        except Exception as e:
            error_msg = f"Ошибка при очистке отчетов: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        return results
