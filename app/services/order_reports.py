"""
Сервис для записи отчетов по отдельным заказам
"""

import logging
from datetime import datetime

from app.database.models import Master, Order, User
from app.database.orm_database import ORMDatabase


logger = logging.getLogger(__name__)


class OrderReportsService:
    """Сервис для создания отчетов по закрытым заказам"""

    def __init__(self):
        self.db = ORMDatabase()

    async def create_order_report(
        self, order: Order, master: Master | None = None, dispatcher: User | None = None
    ) -> bool:
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
                        created_dt = datetime.fromisoformat(order.created_at.replace("Z", "+00:00"))
                    else:
                        created_dt = order.created_at

                    if isinstance(order.updated_at, str):
                        updated_dt = datetime.fromisoformat(order.updated_at.replace("Z", "+00:00"))
                    else:
                        updated_dt = order.updated_at

                    # Удаляем timezone информацию для корректного вычитания
                    if created_dt.tzinfo is not None:
                        created_dt = created_dt.replace(tzinfo=None)
                    if updated_dt.tzinfo is not None:
                        updated_dt = updated_dt.replace(tzinfo=None)

                    time_diff = updated_dt - created_dt
                    completion_time_hours = time_diff.total_seconds() / 3600  # в часах
                except Exception as e:
                    logger.warning(f"Не удалось вычислить время выполнения заказа {order.id}: {e}")

            # Создаем запись в таблице order_reports
            async with self.db.get_session() as session:
                from sqlalchemy import text

                await session.execute(
                    text(
                        """
                        INSERT INTO order_reports (
                            order_id, equipment_type, client_name, client_address,
                            master_id, master_name, dispatcher_id, dispatcher_name,
                            total_amount, materials_cost, master_profit, company_profit,
                            out_of_city, has_review, created_at, closed_at, completion_time_hours
                        ) VALUES (:order_id, :equipment_type, :client_name, :client_address,
                                 :master_id, :master_name, :dispatcher_id, :dispatcher_name,
                                 :total_amount, :materials_cost, :master_profit, :company_profit,
                                 :out_of_city, :has_review, :created_at, :closed_at, :completion_time_hours)
                    """
                    ),
                    {
                        "order_id": order.id,
                        "equipment_type": order.equipment_type,
                        "client_name": order.client_name,
                        "client_address": order.client_address,
                        "master_id": order.assigned_master_id,
                        "master_name": master_name,
                        "dispatcher_id": order.dispatcher_id,
                        "dispatcher_name": dispatcher_name,
                        "total_amount": order.total_amount or 0.0,
                        "materials_cost": order.materials_cost or 0.0,
                        "master_profit": order.master_profit or 0.0,
                        "company_profit": order.company_profit or 0.0,
                        "out_of_city": 1 if order.out_of_city else 0,
                        "has_review": 1 if order.has_review else 0,
                        "created_at": order.created_at,
                        "closed_at": order.updated_at,
                        "completion_time_hours": completion_time_hours,
                    },
                )
                await session.commit()

            logger.info(f"Создан отчет по заказу #{order.id}")
            return True

        except Exception as e:
            logger.error(f"Ошибка создания отчета по заказу {order.id}: {e}")
            return False

        finally:
            await self.db.disconnect()

    async def get_order_reports(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        master_id: int | None = None,
    ) -> list:
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
            params: dict[str, object] = {}

            if start_date:
                query += " AND DATE(closed_at) >= :start_date"
                params["start_date"] = start_date

            if end_date:
                query += " AND DATE(closed_at) <= :end_date"
                params["end_date"] = end_date

            if master_id:
                query += " AND master_id = :master_id"
                params["master_id"] = master_id

            query += " ORDER BY closed_at DESC"

            async with self.db.get_session() as session:
                from sqlalchemy import text

                result = await session.execute(text(query), params)
                rows = result.fetchall()

                reports = []
                for row in rows:
                    reports.append(
                        {
                            "id": row.id,
                            "order_id": row.order_id,
                            "equipment_type": row.equipment_type,
                            "client_name": row.client_name,
                            "client_address": row.client_address,
                            "master_id": row.master_id,
                            "master_name": row.master_name,
                            "dispatcher_id": row.dispatcher_id,
                            "dispatcher_name": row.dispatcher_name,
                            "total_amount": row.total_amount,
                            "materials_cost": row.materials_cost,
                            "master_profit": row.master_profit,
                            "company_profit": row.company_profit,
                            "out_of_city": bool(row.out_of_city),
                            "has_review": bool(row.has_review),
                            "created_at": row.created_at,
                            "closed_at": row.closed_at,
                            "completion_time_hours": row.completion_time_hours,
                        }
                    )

            return reports

        except Exception as e:
            logger.error(f"Ошибка получения отчетов по заказам: {e}")
            return []

        finally:
            await self.db.disconnect()

    async def upsert_order_report(
        self,
        order: Order,
        master: Master | None = None,
        dispatcher: User | None = None,
    ) -> bool:
        """Обновить существующий отчет по заказу или создать, если его нет.

        Используется при админ-редактировании закрытой заявки для синхронизации отчетов.
        """
        await self.db.connect()
        try:
            master_name = None
            dispatcher_name = None

            if master and hasattr(master, "telegram_id"):
                master_user = await self.db.get_user_by_telegram_id(master.telegram_id)
                if master_user:
                    master_name = f"{master_user.first_name} {master_user.last_name}"

            if dispatcher:
                dispatcher_name = f"{dispatcher.first_name} {dispatcher.last_name}"

            # Пересчитываем время выполнения
            completion_time_hours = None
            try:
                created_dt = order.created_at
                closed_dt = order.updated_at
                if isinstance(created_dt, str):
                    created_dt = datetime.fromisoformat(created_dt.replace("Z", "+00:00"))
                if isinstance(closed_dt, str):
                    closed_dt = datetime.fromisoformat(closed_dt.replace("Z", "+00:00"))
                if created_dt and closed_dt:
                    if getattr(created_dt, "tzinfo", None) is not None:
                        created_dt = created_dt.replace(tzinfo=None)
                    if getattr(closed_dt, "tzinfo", None) is not None:
                        closed_dt = closed_dt.replace(tzinfo=None)
                    completion_time_hours = (closed_dt - created_dt).total_seconds() / 3600
            except (
                Exception
            ):  # nosec B110 - игнорирование ошибок при расчете времени выполнения заказа не критично
                pass

            async with self.db.get_session() as session:
                from sqlalchemy import text

                # Удаляем существующую запись и вставляем новую (простой UPSERT для SQLite)
                await session.execute(
                    text("DELETE FROM order_reports WHERE order_id = :oid"), {"oid": order.id}
                )
                await session.execute(
                    text(
                        """
                        INSERT INTO order_reports (
                            order_id, equipment_type, client_name, client_address,
                            master_id, master_name, dispatcher_id, dispatcher_name,
                            total_amount, materials_cost, master_profit, company_profit,
                            out_of_city, has_review, created_at, closed_at, completion_time_hours
                        ) VALUES (:order_id, :equipment_type, :client_name, :client_address,
                                 :master_id, :master_name, :dispatcher_id, :dispatcher_name,
                                 :total_amount, :materials_cost, :master_profit, :company_profit,
                                 :out_of_city, :has_review, :created_at, :closed_at, :completion_time_hours)
                        """
                    ),
                    {
                        "order_id": order.id,
                        "equipment_type": order.equipment_type,
                        "client_name": order.client_name,
                        "client_address": order.client_address,
                        "master_id": order.assigned_master_id,
                        "master_name": master_name,
                        "dispatcher_id": order.dispatcher_id,
                        "dispatcher_name": dispatcher_name,
                        "total_amount": order.total_amount or 0.0,
                        "materials_cost": order.materials_cost or 0.0,
                        "master_profit": order.master_profit or 0.0,
                        "company_profit": order.company_profit or 0.0,
                        "out_of_city": 1 if order.out_of_city else 0,
                        "has_review": 1 if order.has_review else 0,
                        "created_at": order.created_at,
                        "closed_at": order.updated_at,
                        "completion_time_hours": completion_time_hours,
                    },
                )
                await session.commit()

            logger.info(f"Upsert отчета по заказу #{order.id} выполнен")
            return True
        except Exception as e:
            logger.error(f"Ошибка upsert отчета по заказу {order.id}: {e}")
            return False
        finally:
            await self.db.disconnect()

    async def get_order_reports_summary(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> dict:
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
            params = {}

            if start_date:
                query += " AND DATE(closed_at) >= :start_date"
                params["start_date"] = start_date

            if end_date:
                query += " AND DATE(closed_at) <= :end_date"
                params["end_date"] = end_date

            async with self.db.get_session() as session:
                from sqlalchemy import text

                result = await session.execute(text(query), params)
                rows = result.fetchall()

                if not rows:
                    return {
                        "total_orders": 0,
                        "total_amount": 0.0,
                        "total_materials_cost": 0.0,
                        "total_master_profit": 0.0,
                        "total_company_profit": 0.0,
                        "out_of_city_count": 0,
                        "reviews_count": 0,
                        "avg_completion_time": 0.0,
                    }

                total_orders = len(rows)
                total_amount = sum(row.total_amount for row in rows)
                total_materials_cost = sum(row.materials_cost for row in rows)
                total_master_profit = sum(row.master_profit for row in rows)
                total_company_profit = sum(row.company_profit for row in rows)
                out_of_city_count = sum(1 for row in rows if row.out_of_city)
                reviews_count = sum(1 for row in rows if row.has_review)

                completion_times = [
                    row.completion_time_hours
                    for row in rows
                    if row.completion_time_hours is not None
                ]
                avg_completion_time = (
                    sum(completion_times) / len(completion_times) if completion_times else 0.0
                )

            return {
                "total_orders": total_orders,
                "total_amount": total_amount,
                "total_materials_cost": total_materials_cost,
                "total_master_profit": total_master_profit,
                "total_company_profit": total_company_profit,
                "out_of_city_count": out_of_city_count,
                "reviews_count": reviews_count,
                "avg_completion_time": avg_completion_time,
            }

        except Exception as e:
            logger.error(f"Ошибка получения сводной статистики: {e}")
            return {}

        finally:
            await self.db.disconnect()
