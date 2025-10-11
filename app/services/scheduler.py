"""
Планировщик задач
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.database import Database
from app.config import Config, OrderStatus

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Планировщик задач для бота"""
    
    def __init__(self, bot):
        """
        Инициализация планировщика
        
        Args:
            bot: Экземпляр бота
        """
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.db = Database()
    
    async def start(self):
        """Запуск планировщика"""
        await self.db.connect()
        
        # Проверка SLA заявок (каждые 30 минут)
        self.scheduler.add_job(
            self.check_order_sla,
            trigger=IntervalTrigger(minutes=30),
            id="check_order_sla",
            name="Проверка SLA заявок",
            replace_existing=True
        )
        
        # Ежедневная сводка (в 9:00 каждый день)
        self.scheduler.add_job(
            self.send_daily_summary,
            trigger=CronTrigger(hour=9, minute=0),
            id="daily_summary",
            name="Ежедневная сводка",
            replace_existing=True
        )
        
        # Напоминание о непринятых заявках (каждый час)
        self.scheduler.add_job(
            self.remind_assigned_orders,
            trigger=IntervalTrigger(hours=1),
            id="remind_assigned_orders",
            name="Напоминание о непринятых заявках",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Планировщик задач запущен")
    
    async def stop(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
        await self.db.disconnect()
        logger.info("Планировщик задач остановлен")
    
    async def check_order_sla(self):
        """
        Проверка SLA заявок
        Уведомляет администраторов о заявках, которые находятся
        в одном статусе слишком долго
        """
        try:
            # Получаем все активные заявки
            orders = await self.db.get_all_orders()
            
            now = datetime.now()
            alerts = []
            
            for order in orders:
                if order.status in [OrderStatus.CLOSED, OrderStatus.REFUSED]:
                    continue
                
                if not order.updated_at:
                    continue
                
                time_in_status = now - order.updated_at
                
                # SLA правила
                sla_rules = {
                    OrderStatus.NEW: timedelta(hours=2),      # Новая заявка > 2 часов
                    OrderStatus.ASSIGNED: timedelta(hours=4), # Назначена > 4 часов
                    OrderStatus.ACCEPTED: timedelta(hours=8), # Принята > 8 часов
                    OrderStatus.ONSITE: timedelta(hours=12),  # На объекте > 12 часов
                }
                
                sla_limit = sla_rules.get(order.status)
                
                if sla_limit and time_in_status > sla_limit:
                    alerts.append({
                        'order': order,
                        'time': time_in_status
                    })
            
            # Отправляем уведомления администраторам
            if alerts:
                for admin_id in Config.ADMIN_IDS:
                    try:
                        text = "⚠️ <b>Превышение SLA</b>\n\n"
                        text += f"Найдено заявок с превышением SLA: {len(alerts)}\n\n"
                        
                        for alert in alerts[:5]:  # Показываем первые 5
                            order = alert['order']
                            hours = int(alert['time'].total_seconds() / 3600)
                            
                            status_name = OrderStatus.get_status_name(order.status)
                            text += (
                                f"📋 Заявка #{order.id}\n"
                                f"   Статус: {status_name}\n"
                                f"   В статусе: {hours} ч.\n\n"
                            )
                        
                        if len(alerts) > 5:
                            text += f"<i>И еще {len(alerts) - 5} заявок...</i>"
                        
                        await self.bot.send_message(
                            admin_id,
                            text,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send SLA alert to admin {admin_id}: {e}")
            
            logger.info(f"SLA check completed. Found {len(alerts)} alerts")
            
        except Exception as e:
            logger.error(f"Error in check_order_sla: {e}")
    
    async def send_daily_summary(self):
        """
        Отправка ежедневной сводки администраторам и диспетчерам
        """
        try:
            # Получаем статистику
            stats = await self.db.get_statistics()
            
            # Получаем заявки за последние 24 часа
            all_orders = await self.db.get_all_orders()
            yesterday = datetime.now() - timedelta(days=1)
            
            new_orders = [
                o for o in all_orders
                if o.created_at and o.created_at > yesterday
            ]
            
            # Активные заявки
            active_orders = [
                o for o in all_orders
                if o.status not in [OrderStatus.CLOSED, OrderStatus.REFUSED]
            ]
            
            text = (
                "📊 <b>Ежедневная сводка</b>\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
                f"<b>За последние 24 часа:</b>\n"
                f"• Новых заявок: {len(new_orders)}\n\n"
                f"<b>Текущее состояние:</b>\n"
                f"• Активных заявок: {len(active_orders)}\n"
                f"• Всего заявок: {stats.get('total_orders', 0)}\n"
                f"• Активных мастеров: {stats.get('active_masters', 0)}\n\n"
            )
            
            # По статусам
            orders_by_status = stats.get('orders_by_status', {})
            if orders_by_status:
                text += "<b>По статусам:</b>\n"
                for status in [OrderStatus.NEW, OrderStatus.ASSIGNED, OrderStatus.ACCEPTED, OrderStatus.ONSITE]:
                    if status in orders_by_status:
                        emoji = OrderStatus.get_status_emoji(status)
                        name = OrderStatus.get_status_name(status)
                        count = orders_by_status[status]
                        text += f"{emoji} {name}: {count}\n"
            
            # Отправляем администраторам
            for admin_id in Config.ADMIN_IDS:
                try:
                    await self.bot.send_message(
                        admin_id,
                        text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Failed to send daily summary to admin {admin_id}: {e}")
            
            # Отправляем диспетчерам
            for dispatcher_id in Config.DISPATCHER_IDS:
                try:
                    await self.bot.send_message(
                        dispatcher_id,
                        text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Failed to send daily summary to dispatcher {dispatcher_id}: {e}")
            
            logger.info("Daily summary sent")
            
        except Exception as e:
            logger.error(f"Error in send_daily_summary: {e}")
    
    async def remind_assigned_orders(self):
        """
        Напоминание мастерам о непринятых заявках
        """
        try:
            # Получаем заявки со статусом ASSIGNED старше 2 часов
            orders = await self.db.get_all_orders(status=OrderStatus.ASSIGNED)
            
            now = datetime.now()
            remind_threshold = timedelta(hours=2)
            
            for order in orders:
                if not order.updated_at:
                    continue
                
                time_assigned = now - order.updated_at
                
                if time_assigned > remind_threshold and order.assigned_master_id:
                    master = await self.db.get_master_by_id(order.assigned_master_id)
                    
                    if master:
                        try:
                            hours = int(time_assigned.total_seconds() / 3600)
                            
                            await self.bot.send_message(
                                master.telegram_id,
                                f"⏰ <b>Напоминание</b>\n\n"
                                f"У вас есть непринятая заявка #{order.id}\n"
                                f"🔧 {order.equipment_type}\n"
                                f"⏱ Назначена {hours} ч. назад\n\n"
                                f"Пожалуйста, примите или отклоните заявку.",
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.error(f"Failed to send reminder to master {master.telegram_id}: {e}")
            
            logger.info(f"Reminders sent for {len(orders)} assigned orders")
            
        except Exception as e:
            logger.error(f"Error in remind_assigned_orders: {e}")

