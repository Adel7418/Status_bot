"""
Сервис для записи отчетов по отдельным заказам
"""

import logging
from datetime import datetime
from typing import Optional

from app.database import Database
from app.database.models import Order, Master, User
from app.utils.helpers import get_now

logger = logging.getLogger(__name__)


class OrderReportsService:
    """Сервис для создания отчетов по закрытым заказам"""

    def __init__(self):
        self.db = Database()

    async def create_order_report(self, order: Order, master: Optional[Master] = None, dispatcher: Optional[User] = None) -> bool:
        """
        Создает запись в отчете для закрытого заказа
        
        Args:
            order: Заказ
            master: Мастер (опционально)
            dispatcher: Диспетчер (опционально)
            
        Returns:
            bool: True если запись создана успешно
        """
        await self.db.connect()
        
        try:
            # Получаем имена мастера и диспетчера
            master_name = None
            dispatcher_name = None
            
            if master:
                # Получаем имя мастера из таблицы users
                master_user = await self.db.get_user_by_telegram_id(master.telegram_id)
                if master_user:
                    master_name = f"{master_user.first_name} {master_user.last_name}"
            
            if dispatcher:
                dispatcher_name = f"{dispatcher.first_name} {dispatcher.last_name}"
            
            # Вычисляем время выполнения заказа
            completion_time_hours = None
            if order.created_at and order.updated_at:
                try:
                    # Преобразуем в datetime если это строка
                    if isinstance(order.created_at, str):
                        created_dt = datetime.fromisoformat(order.created_at.replace('Z', '+00:00'))
                    else:
                        created_dt = order.created_at
                    
                    if isinstance(order.updated_at, str):
                        updated_dt = datetime.fromisoformat(order.updated_at.replace('Z', '+00:00'))
                    else:
                        updated_dt = order.updated_at
                    
                    time_diff = updated_dt - created_dt
                    completion_time_hours = time_diff.total_seconds() / 3600  # в часах
                except Exception as e:
                    logger.warning(f"Не удалось вычислить время выполнения заказа {order.id}: {e}")
            
            # Создаем запись в таблице order_reports
            cursor = await self.db.connection.execute("""
                INSERT INTO order_reports (
                    order_id, equipment_type, client_name, client_address,
                    master_id, master_name, dispatcher_id, dispatcher_name,
                    total_amount, materials_cost, master_profit, company_profit,
                    out_of_city, has_review, created_at, closed_at, completion_time_hours
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.id,
                order.equipment_type,
                order.client_name,
                order.client_address,
                order.assigned_master_id,
                master_name,
                order.dispatcher_id,
                dispatcher_name,
                order.total_amount or 0.0,
                order.materials_cost or 0.0,
                order.master_profit or 0.0,
                order.company_profit or 0.0,
                1 if order.out_of_city else 0,
                1 if order.has_review else 0,
                order.created_at,
                order.updated_at,
                completion_time_hours
            ))
            
            await self.db.connection.commit()
            
            logger.info(f"Создан отчет по заказу #{order.id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания отчета по заказу {order.id}: {e}")
            return False
            
        finally:
            await self.db.disconnect()

    async def get_order_reports(self, start_date: Optional[str] = None, end_date: Optional[str] = None, master_id: Optional[int] = None) -> list:
        """
        Получает отчеты по заказам за период
        
        Args:
            start_date: Начальная дата (YYYY-MM-DD)
            end_date: Конечная дата (YYYY-MM-DD)
            master_id: ID мастера для фильтрации
            
        Returns:
            list: Список отчетов по заказам
        """
        await self.db.connect()
        
        try:
            query = "SELECT * FROM order_reports WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND DATE(closed_at) >= ?"
                params.append(start_date)
                
            if end_date:
                query += " AND DATE(closed_at) <= ?"
                params.append(end_date)
                
            if master_id:
                query += " AND master_id = ?"
                params.append(master_id)
            
            query += " ORDER BY closed_at DESC"
            
            cursor = await self.db.connection.execute(query, params)
            rows = await cursor.fetchall()
            
            reports = []
            for row in rows:
                reports.append({
                    "id": row["id"],
                    "order_id": row["order_id"],
                    "equipment_type": row["equipment_type"],
                    "client_name": row["client_name"],
                    "client_address": row["client_address"],
                    "master_id": row["master_id"],
                    "master_name": row["master_name"],
                    "dispatcher_id": row["dispatcher_id"],
                    "dispatcher_name": row["dispatcher_name"],
                    "total_amount": row["total_amount"],
                    "materials_cost": row["materials_cost"],
                    "master_profit": row["master_profit"],
                    "company_profit": row["company_profit"],
                    "out_of_city": bool(row["out_of_city"]),
                    "has_review": bool(row["has_review"]),
                    "created_at": row["created_at"],
                    "closed_at": row["closed_at"],
                    "completion_time_hours": row["completion_time_hours"]
                })
            
            return reports
            
        except Exception as e:
            logger.error(f"Ошибка получения отчетов по заказам: {e}")
            return []
            
        finally:
            await self.db.disconnect()

    async def get_order_reports_summary(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
        """
        Получает сводную статистику по отчетам заказов
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            dict: Сводная статистика
        """
        await self.db.connect()
        
        try:
            query = "SELECT * FROM order_reports WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND DATE(closed_at) >= ?"
                params.append(start_date)
                
            if end_date:
                query += " AND DATE(closed_at) <= ?"
                params.append(end_date)
            
            cursor = await self.db.connection.execute(query, params)
            rows = await cursor.fetchall()
            
            if not rows:
                return {
                    "total_orders": 0,
                    "total_amount": 0.0,
                    "total_materials_cost": 0.0,
                    "total_master_profit": 0.0,
                    "total_company_profit": 0.0,
                    "out_of_city_count": 0,
                    "reviews_count": 0,
                    "avg_completion_time": 0.0
                }
            
            total_orders = len(rows)
            total_amount = sum(row["total_amount"] for row in rows)
            total_materials_cost = sum(row["materials_cost"] for row in rows)
            total_master_profit = sum(row["master_profit"] for row in rows)
            total_company_profit = sum(row["company_profit"] for row in rows)
            out_of_city_count = sum(1 for row in rows if row["out_of_city"])
            reviews_count = sum(1 for row in rows if row["has_review"])
            
            completion_times = [row["completion_time_hours"] for row in rows if row["completion_time_hours"] is not None]
            avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0.0
            
            return {
                "total_orders": total_orders,
                "total_amount": total_amount,
                "total_materials_cost": total_materials_cost,
                "total_master_profit": total_master_profit,
                "total_company_profit": total_company_profit,
                "out_of_city_count": out_of_city_count,
                "reviews_count": reviews_count,
                "avg_completion_time": avg_completion_time
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения сводной статистики: {e}")
            return {}
            
        finally:
            await self.db.disconnect()
