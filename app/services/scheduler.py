"""
Планировщик задач
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import Config, OrderStatus
from app.database import Database
from app.utils import get_now, safe_send_message
from app.utils.helpers import MOSCOW_TZ


logger = logging.getLogger(__name__)


class TaskScheduler:
    """Планировщик задач для бота"""

    def __init__(self, bot, db: Database):
        """
        Инициализация планировщика

        Args:
            bot: Экземпляр бота
            db: Shared Database instance (избегаем race conditions)
        """
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.db = db

    async def start(self):
        """Запуск планировщика"""
        # БД уже подключена в main(), не создаем новое соединение

        # Проверка SLA заявок
        self.scheduler.add_job(
            self.check_order_sla,
            trigger=IntervalTrigger(minutes=Config.SLA_CHECK_INTERVAL),
            id="check_order_sla",
            name="Проверка SLA заявок",
            replace_existing=True,
        )

        # Ежедневный отчет (в 8:00 каждый день)
        self.scheduler.add_job(
            self.send_daily_report,
            trigger=CronTrigger(hour=8, minute=0),
            id="daily_report",
            name="Ежедневный отчет",
            replace_existing=True,
        )

        # Еженедельный отчет (в понедельник в 9:00)
        self.scheduler.add_job(
            self.send_weekly_report,
            trigger=CronTrigger(day_of_week=0, hour=9, minute=0),
            id="weekly_report",
            name="Еженедельный отчет",
            replace_existing=True,
        )

        # Ежемесячный отчет (1 числа каждого месяца в 10:00)
        self.scheduler.add_job(
            self.send_monthly_report,
            trigger=CronTrigger(day=1, hour=10, minute=0),
            id="monthly_report",
            name="Ежемесячный отчет",
            replace_existing=True,
        )

        # Ежедневная сводка (в 9:00 каждый день)
        self.scheduler.add_job(
            self.send_daily_summary,
            trigger=CronTrigger(hour=9, minute=0),
            id="daily_summary",
            name="Ежедневная сводка",
            replace_existing=True,
        )

        # Напоминание о непринятых заявках
        self.scheduler.add_job(
            self.remind_assigned_orders,
            trigger=IntervalTrigger(minutes=Config.REMINDER_INTERVAL),
            id="remind_assigned_orders",
            name="Напоминание о непринятых заявках",
            replace_existing=True,
        )

        # Напоминание о неназначенных заявках
        self.scheduler.add_job(
            self.remind_unassigned_orders,
            trigger=IntervalTrigger(minutes=Config.REMINDER_INTERVAL),
            id="remind_unassigned_orders",
            name="Напоминание о неназначенных заявках",
            replace_existing=True,
        )

        # Архивирование отчетов мастеров (каждые 30 дней, 1 числа каждого месяца в 02:00)
        self.scheduler.add_job(
            self.archive_master_reports,
            trigger=CronTrigger(day=1, hour=2, minute=0),
            id="archive_master_reports",
            name="Архивирование отчетов мастеров",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Планировщик задач запущен")

    async def stop(self):
        """Остановка планировщика"""
        self.scheduler.shutdown(wait=True)  # Ждем завершения всех джоб
        # БД будет отключена в main(), не закрываем здесь
        logger.info("Планировщик задач остановлен")

    async def _send_scheduled_time_reminder(self, order, scheduled_datetime: datetime):
        """
        Отправка напоминания за 2 часа до визита

        Args:
            order: Заявка
            scheduled_datetime: Запланированное время визита
        """
        try:
            # Получаем мастера
            master = await self.db.get_master_by_id(order.assigned_master_id)
            if not master:
                return

            reminder_text = (
                f"⏰ <b>Напоминание о визите через 2 часа!</b>\n\n"
                f"📋 Заявка #{order.id}\n"
                f"🔧 {order.equipment_type}\n"
                f"👤 Клиент: {order.client_name}\n"
                f"📍 Адрес: {order.client_address}\n"
                f"📞 Телефон: {order.client_phone}\n\n"
                f"⏰ Запланированное время: {scheduled_datetime.strftime('%H:%M')}\n\n"
                f"Не забудьте подготовиться к выезду!"
            )

            # Определяем, куда отправлять
            target_chat_id = master.work_chat_id if master.work_chat_id else master.telegram_id

            await safe_send_message(
                self.bot, target_chat_id, reminder_text, parse_mode="HTML", max_attempts=3
            )

            logger.info(
                f"2-hour reminder sent for order #{order.id} to {'group' if master.work_chat_id else 'DM'} {target_chat_id}"
            )

        except Exception as e:
            logger.error(f"Failed to send scheduled time reminder for order #{order.id}: {e}")

    def _check_scheduled_time_alert(self, order, now: datetime) -> bool:
        """
        Проверка запланированного времени для перенесенных заявок.
        Отправляет напоминание за 2 часа до визита.

        Args:
            order: Заявка
            now: Текущее время

        Returns:
            True если напоминание было отправлено или время еще не подошло
        """
        import re
        from datetime import datetime, timedelta

        scheduled_time = order.scheduled_time.lower().strip()

        # Пытаемся найти время в формате HH:MM
        time_pattern = r"(\d{1,2}):(\d{2})"
        time_match = re.search(time_pattern, scheduled_time)

        if not time_match:
            return False  # Не удалось распарсить время

        hour = int(time_match.group(1))
        minute = int(time_match.group(2))

        # Определяем дату
        target_date = now.date()

        # Ключевые слова для определения даты
        if "завтра" in scheduled_time:
            target_date = (now + timedelta(days=1)).date()
        elif "послезавтра" in scheduled_time:
            target_date = (now + timedelta(days=2)).date()
        elif "через" in scheduled_time and "дн" in scheduled_time:
            # Пытаемся найти количество дней
            days_match = re.search(r"через\s+(\d+)\s+дн", scheduled_time)
            if days_match:
                days = int(days_match.group(1))
                target_date = (now + timedelta(days=days)).date()

        # Пытаемся найти дату в формате DD.MM.YYYY
        date_pattern = r"(\d{1,2})\.(\d{1,2})\.(\d{4})"
        date_match = re.search(date_pattern, scheduled_time)
        if date_match:
            day = int(date_match.group(1))
            month = int(date_match.group(2))
            year = int(date_match.group(3))
            try:
                target_date = datetime(year, month, day).date()
            except ValueError:
                pass  # Неверная дата

        # Создаем целевое время визита
        try:
            scheduled_datetime = datetime.combine(
                target_date, datetime.min.time().replace(hour=hour, minute=minute)
            )
            # Добавляем timezone как у now
            scheduled_datetime = scheduled_datetime.replace(tzinfo=now.tzinfo)
        except ValueError:
            return False  # Неверное время

        # Если время визита уже прошло, не отправляем напоминание
        if scheduled_datetime <= now:
            return False

        # Проверяем, осталось ли менее 2 часов до визита
        time_until_visit = scheduled_datetime - now

        # Если осталось от 1:30 до 2:30 часов - отправляем напоминание
        if timedelta(hours=1, minutes=30) <= time_until_visit <= timedelta(hours=2, minutes=30):
            logger.info(
                f"Sending 2-hour reminder for rescheduled order #{order.id}, scheduled at {scheduled_datetime}"
            )
            # Отправляем напоминание асинхронно
            import asyncio

            try:
                asyncio.create_task(self._send_scheduled_time_reminder(order, scheduled_datetime))
            except Exception as e:
                logger.error(f"Failed to create reminder task: {e}")
            return True

        # Если до визита больше 2:30 часов - ждем
        if time_until_visit > timedelta(hours=2, minutes=30):
            return True  # Не проверяем по стандартному SLA

        return False

    async def check_order_sla(self):
        """
        Проверка SLA заявок
        Уведомляет администраторов о заявках, которые находятся
        в одном статусе слишком долго
        """
        try:
            # Получаем все активные заявки
            orders = await self.db.get_all_orders()

            now = get_now()
            alerts = []

            for order in orders:
                if order.status in [OrderStatus.CLOSED, OrderStatus.REFUSED]:
                    continue

                if not order.updated_at:
                    continue

                time_in_status = now - order.updated_at

                # SLA правила
                sla_rules = {
                    OrderStatus.NEW: timedelta(hours=2),  # Новая заявка > 2 часов
                    OrderStatus.ASSIGNED: timedelta(hours=4),  # Назначена > 4 часов
                    OrderStatus.ACCEPTED: timedelta(hours=8),  # Принята > 8 часов
                    OrderStatus.ONSITE: timedelta(hours=12),  # На объекте > 12 часов
                }

                sla_limit = sla_rules.get(order.status)

                # Для заявок с указанным временем прибытия - используем умные напоминания
                # Работает для статусов ASSIGNED и ACCEPTED
                if order.scheduled_time and order.status in [
                    OrderStatus.ASSIGNED,
                    OrderStatus.ACCEPTED,
                ]:
                    scheduled_alert_sent = self._check_scheduled_time_alert(order, now)
                    if scheduled_alert_sent:
                        continue  # Пропускаем стандартную проверку SLA для этой заявки

                if sla_limit and time_in_status > sla_limit:
                    alerts.append({"order": order, "time": time_in_status})

            # Отправляем уведомления администраторам
            if alerts:
                for admin_id in Config.ADMIN_IDS:
                    text = "⚠️ <b>Превышение SLA</b>\n\n"
                    text += f"Найдено заявок с превышением SLA: {len(alerts)}\n\n"

                    for alert in alerts[:5]:  # Показываем первые 5
                        order = alert["order"]
                        hours = int(alert["time"].total_seconds() / 3600)

                        status_name = OrderStatus.get_status_name(order.status)
                        text += (
                            f"📋 Заявка #{order.id}\n"
                            f"   Статус: {status_name}\n"
                            f"   В статусе: {hours} ч.\n\n"
                        )

                    if len(alerts) > 5:
                        text += f"<i>И еще {len(alerts) - 5} заявок...</i>"

                    await safe_send_message(
                        self.bot, admin_id, text, parse_mode="HTML", max_attempts=5
                    )

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
            yesterday = get_now() - timedelta(days=1)

            new_orders = [o for o in all_orders if o.created_at and o.created_at > yesterday]

            # Активные заявки
            active_orders = [
                o for o in all_orders if o.status not in [OrderStatus.CLOSED, OrderStatus.REFUSED]
            ]

            text = (
                "📊 <b>Ежедневная сводка</b>\n"
                f"📅 {get_now().strftime('%d.%m.%Y')}\n\n"
                f"<b>За последние 24 часа:</b>\n"
                f"• Новых заявок: {len(new_orders)}\n\n"
                f"<b>Текущее состояние:</b>\n"
                f"• Активных заявок: {len(active_orders)}\n"
                f"• Всего заявок: {stats.get('total_orders', 0)}\n"
                f"• Активных мастеров: {stats.get('active_masters', 0)}\n\n"
            )

            # По статусам
            orders_by_status = stats.get("orders_by_status", {})
            if orders_by_status:
                text += "<b>По статусам:</b>\n"
                for status in [
                    OrderStatus.NEW,
                    OrderStatus.ASSIGNED,
                    OrderStatus.ACCEPTED,
                    OrderStatus.ONSITE,
                ]:
                    if status in orders_by_status:
                        emoji = OrderStatus.get_status_emoji(status)
                        name = OrderStatus.get_status_name(status)
                        count = orders_by_status[status]
                        text += f"{emoji} {name}: {count}\n"

            # Отправляем администраторам
            for admin_id in Config.ADMIN_IDS:
                await safe_send_message(self.bot, admin_id, text, parse_mode="HTML", max_attempts=5)

            # Отправляем диспетчерам
            for dispatcher_id in Config.DISPATCHER_IDS:
                await safe_send_message(
                    self.bot, dispatcher_id, text, parse_mode="HTML", max_attempts=5
                )

            logger.info("Daily summary sent")

        except Exception as e:
            logger.error(f"Error in send_daily_summary: {e}")

    async def remind_assigned_orders(self):
        """
        Напоминание мастерам о непринятых заявках
        """
        try:
            # Получаем заявки со статусом ASSIGNED старше 15 минут
            orders = await self.db.get_all_orders(status=OrderStatus.ASSIGNED)

            now = get_now()
            # Для перенесенных заявок увеличиваем порог напоминания до 30 минут
            base_remind_threshold = timedelta(minutes=15)

            for order in orders:
                if not order.updated_at:
                    continue

                # Конвертируем naive datetime в aware для корректного сравнения
                order_updated_at = order.updated_at
                if order_updated_at.tzinfo is None:
                    order_updated_at = order_updated_at.replace(tzinfo=MOSCOW_TZ)

                time_assigned = now - order_updated_at

                # Для заявок с указанным временем прибытия - используем умные напоминания
                if order.scheduled_time:
                    scheduled_alert_sent = self._check_scheduled_time_alert(order, now)
                    if scheduled_alert_sent:
                        continue  # Пропускаем напоминание для этой заявки

                # Используем стандартный порог напоминания
                remind_threshold = base_remind_threshold

                logger.debug(
                    f"Order #{order.id}: updated_at={order.updated_at}, now={now}, time_assigned={time_assigned}, "
                    f"rescheduled={order.rescheduled_count}, threshold={remind_threshold}"
                )

                if time_assigned > remind_threshold and order.assigned_master_id:
                    master = await self.db.get_master_by_id(order.assigned_master_id)

                    if master:
                        minutes = int(time_assigned.total_seconds() / 60)

                        logger.info(
                            f"Sending reminder for order #{order.id}: assigned {minutes} minutes ago"
                        )

                        # Определяем, куда отправлять напоминание
                        # Если есть work_chat_id - отправляем в рабочую группу
                        # Иначе - в личные сообщения мастеру
                        target_chat_id = (
                            master.work_chat_id if master.work_chat_id else master.telegram_id
                        )

                        if master.work_chat_id:
                            # Отправляем в группу с упоминанием мастера
                            reminder_text = (
                                f"⏰ <b>Напоминание</b>\n\n"
                                f"У вас есть непринятая заявка #{order.id}\n"
                                f"🔧 {order.equipment_type}\n"
                                f"⏱ Назначена {minutes} мин. назад\n\n"
                            )

                            # Упоминаем мастера в группе (ORM: через master.user)
                            master_username = master.user.username if hasattr(master, 'user') and master.user else None
                            if master_username:
                                reminder_text += f"👨‍🔧 Мастер: @{master_username}\n\n"
                            else:
                                reminder_text += f"👨‍🔧 Мастер: {master.get_display_name()}\n\n"

                            reminder_text += "Пожалуйста, примите или отклоните заявку."

                            result = await safe_send_message(
                                self.bot,
                                target_chat_id,
                                reminder_text,
                                parse_mode="HTML",
                                max_attempts=5,
                            )

                            if result:
                                logger.info(
                                    f"Reminder sent to group {target_chat_id} for master {master.telegram_id}"
                                )
                        else:
                            # Отправляем в личные сообщения
                            result = await safe_send_message(
                                self.bot,
                                target_chat_id,
                                f"⏰ <b>Напоминание</b>\n\n"
                                f"У вас есть непринятая заявка #{order.id}\n"
                                f"🔧 {order.equipment_type}\n"
                                f"⏱ Назначена {minutes} мин. назад\n\n"
                                f"Пожалуйста, примите или отклоните заявку.",
                                parse_mode="HTML",
                                max_attempts=5,
                            )

                            if result:
                                logger.info(
                                    f"Reminder sent to DM {target_chat_id} for master {master.telegram_id}"
                                )

            logger.info(
                f"Reminders check completed. Found {len(orders)} assigned orders, threshold: 15 minutes"
            )

        except Exception as e:
            logger.error(f"Error in remind_assigned_orders: {e}")

    async def remind_unassigned_orders(self):
        """
        Напоминание о неназначенных заявках (статус NEW старше 15 минут)
        Отправляет уведомления всем админам и диспетчерам
        """
        try:
            # Получаем заявки со статусом NEW
            orders = await self.db.get_all_orders(status=OrderStatus.NEW)

            # Используем get_now() для правильного часового пояса
            now = get_now()
            remind_threshold = timedelta(minutes=15)
            unassigned_alerts = []

            for order in orders:
                if not order.created_at:
                    continue

                # Конвертируем naive datetime в aware для корректного сравнения
                order_created_at = order.created_at
                if order_created_at.tzinfo is None:
                    order_created_at = order_created_at.replace(tzinfo=MOSCOW_TZ)

                time_unassigned = now - order_created_at

                if time_unassigned > remind_threshold:
                    unassigned_alerts.append({"order": order, "time": time_unassigned})

            # Отправляем уведомления если есть неназначенные заявки
            if unassigned_alerts:
                # Получаем всех админов и диспетчеров
                admins_and_dispatchers = await self.db.get_admins_and_dispatchers()

                # Формируем текст уведомления
                text = "⚠️ <b>Неназначенные заявки!</b>\n\n"
                text += f"Найдено заявок без мастера: {len(unassigned_alerts)}\n\n"

                for alert in unassigned_alerts[:5]:  # Показываем первые 5
                    order = alert["order"]
                    minutes = int(alert["time"].total_seconds() / 60)

                    text += (
                        f"📋 <b>Заявка #{order.id}</b>\n"
                        f"   🔧 {order.equipment_type}\n"
                        f"   👤 {order.client_name}\n"
                        f"   ⏱ Создана {minutes} мин. назад\n\n"
                    )

                if len(unassigned_alerts) > 5:
                    text += f"<i>И еще {len(unassigned_alerts) - 5} заявок...</i>\n\n"

                text += "⚠️ <b>Требуется назначить мастеров!</b>"

                # Отправляем всем админам и диспетчерам
                for user in admins_and_dispatchers:
                    try:
                        await safe_send_message(
                            self.bot, user.telegram_id, text, parse_mode="HTML", max_attempts=3
                        )
                        logger.info(f"Unassigned order reminder sent to {user.telegram_id}")
                    except Exception as e:
                        logger.error(f"Failed to send reminder to {user.telegram_id}: {e}")

                logger.info(
                    f"Unassigned orders check completed. Found {len(unassigned_alerts)} unassigned orders older than 15 minutes"
                )
            else:
                logger.debug("No unassigned orders older than 15 minutes")

        except Exception as e:
            logger.error(f"Error in remind_unassigned_orders: {e}")

    # ==================== ОТЧЕТЫ ====================

    async def send_daily_report(self):
        """Отправляет ежедневный отчет"""
        try:
            from app.services.reports_notifier import ReportsNotifier

            notifier = ReportsNotifier(self.bot)
            await notifier.send_daily_report()

            logger.info("Ежедневный отчет отправлен")

        except Exception as e:
            logger.error(f"Ошибка отправки ежедневного отчета: {e}")

    async def send_weekly_report(self):
        """Отправляет еженедельный отчет"""
        try:
            from app.services.reports_notifier import ReportsNotifier

            notifier = ReportsNotifier(self.bot)
            await notifier.send_weekly_report()

            logger.info("Еженедельный отчет отправлен")

        except Exception as e:
            logger.error(f"Ошибка отправки еженедельного отчета: {e}")

    async def send_monthly_report(self):
        """Отправляет ежемесячный отчет"""
        try:
            from app.services.reports_notifier import ReportsNotifier

            notifier = ReportsNotifier(self.bot)
            await notifier.send_monthly_report()

            logger.info("Ежемесячный отчет отправлен")

        except Exception as e:
            logger.error(f"Ошибка отправки ежемесячного отчета: {e}")

    async def archive_master_reports(self):
        """Создание архивных отчетов для всех мастеров (раз в 30 дней)"""
        try:
            from datetime import timedelta
            from app.services.master_reports import MasterReportsService
            
            logger.info("Начало архивирования отчетов мастеров...")
            
            # Получаем всех активных мастеров
            masters = await self.db.get_all_masters(only_approved=True)
            
            if not masters:
                logger.info("Нет мастеров для архивирования отчетов")
                return
            
            reports_service = MasterReportsService(self.db)
            
            # Период: последние 30 дней
            now = get_now()
            period_end = now
            period_start = now - timedelta(days=30)
            
            archived_count = 0
            failed_count = 0
            
            for master in masters:
                try:
                    # Генерируем и сохраняем отчет в архив
                    await reports_service.generate_master_report_excel(
                        master_id=master.id,
                        save_to_archive=True,
                        period_start=period_start,
                        period_end=period_end
                    )
                    
                    archived_count += 1
                    logger.info(f"Отчет для мастера {master.id} ({master.get_display_name()}) архивирован")
                    
                    # Отправляем уведомление мастеру
                    notification = (
                        f"📚 <b>Ежемесячный отчет готов!</b>\n\n"
                        f"Создан архивный отчет за период:\n"
                        f"📅 {period_start.strftime('%d.%m.%Y')} - {period_end.strftime('%d.%m.%Y')}\n\n"
                        f"Вы можете скачать его через:\n"
                        f"📊 Моя статистика → 📚 Архив отчетов"
                    )
                    
                    # Пробуем отправить уведомление (если у мастера есть telegram_id)
                    if hasattr(master, 'telegram_id') and master.telegram_id:
                        try:
                            await safe_send_message(
                                self.bot,
                                master.telegram_id,
                                notification,
                                parse_mode="HTML",
                                max_attempts=2
                            )
                        except Exception as notify_error:
                            logger.warning(
                                f"Не удалось отправить уведомление мастеру {master.id}: {notify_error}"
                            )
                    
                except Exception as master_error:
                    failed_count += 1
                    logger.error(f"Ошибка архивирования отчета для мастера {master.id}: {master_error}")
            
            logger.info(
                f"Архивирование отчетов завершено. "
                f"Успешно: {archived_count}, Ошибок: {failed_count}"
            )
            
            # Отправляем уведомление админам о результате
            try:
                admins = await self.db.get_users_by_role("ADMIN")
                
                admin_notification = (
                    f"📊 <b>Архивирование отчетов мастеров</b>\n\n"
                    f"✅ Успешно: {archived_count}\n"
                    f"❌ Ошибок: {failed_count}\n\n"
                    f"📅 Период: {period_start.strftime('%d.%m.%Y')} - {period_end.strftime('%d.%m.%Y')}"
                )
                
                for admin in admins:
                    try:
                        await safe_send_message(
                            self.bot,
                            admin.telegram_id,
                            admin_notification,
                            parse_mode="HTML",
                            max_attempts=2
                        )
                    except Exception:
                        pass
                        
            except Exception as admin_notify_error:
                logger.warning(f"Не удалось отправить уведомление админам: {admin_notify_error}")
            
        except Exception as e:
            logger.error(f"Критическая ошибка при архивировании отчетов мастеров: {e}")
