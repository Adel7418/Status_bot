"""
Сервис для отправки отчетов через Telegram
"""

import logging

from aiogram import Bot
from aiogram.types import FSInputFile

from app.database import DatabaseType, get_database


logger = logging.getLogger(__name__)


class ReportsNotifier:
    """Сервис для отправки отчетов"""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.db: DatabaseType = get_database()

    async def send_daily_report(self):
        """Отправляет ежедневный отчет"""
        try:
            from app.services.reports_service import ReportsService

            reports_service = ReportsService()
            report = await reports_service.generate_daily_report()

            # Отправляем текстовый отчет
            text = await reports_service.format_report_to_text(report)

            # Сохраняем Excel файл с детализацией
            excel_path = await reports_service.save_report_to_excel(report)

            # Получаем список администраторов и диспетчеров
            recipients = await self._get_report_recipients()

            # Отправляем всем получателям
            for recipient_id in recipients:
                try:
                    await self.bot.send_message(chat_id=recipient_id, text=text, parse_mode="HTML")

                    # Отправляем Excel файл
                    document = FSInputFile(excel_path)
                    await self.bot.send_document(
                        chat_id=recipient_id,
                        document=document,
                        caption=f"📊 Ежедневный отчет за {report['period']}",
                    )

                    logger.info(f"Ежедневный отчет отправлен пользователю {recipient_id}")

                except Exception as e:
                    logger.error(
                        f"Ошибка отправки ежедневного отчета пользователю {recipient_id}: {e}"
                    )

            logger.info("Ежедневный отчет успешно отправлен всем получателям")

        except Exception as e:
            logger.error(f"Ошибка генерации ежедневного отчета: {e}")

    async def send_weekly_report(self):
        """Отправляет еженедельный отчет"""
        try:
            from app.services.reports_service import ReportsService

            reports_service = ReportsService()
            report = await reports_service.generate_weekly_report()

            # Отправляем текстовый отчет
            text = await reports_service.format_report_to_text(report)

            # Сохраняем Excel файл с детализацией
            excel_path = await reports_service.save_report_to_excel(report)

            # Получаем список администраторов и диспетчеров
            recipients = await self._get_report_recipients()

            # Отправляем всем получателям
            for recipient_id in recipients:
                try:
                    await self.bot.send_message(chat_id=recipient_id, text=text, parse_mode="HTML")

                    # Отправляем Excel файл
                    document = FSInputFile(excel_path)
                    await self.bot.send_document(
                        chat_id=recipient_id,
                        document=document,
                        caption=f"📊 Еженедельный отчет за {report['period']}",
                    )

                    logger.info(f"Еженедельный отчет отправлен пользователю {recipient_id}")

                except Exception as e:
                    logger.error(
                        f"Ошибка отправки еженедельного отчета пользователю {recipient_id}: {e}"
                    )

            logger.info("Еженедельный отчет успешно отправлен всем получателям")

        except Exception as e:
            logger.error(f"Ошибка генерации еженедельного отчета: {e}")

    async def send_monthly_report(self):
        """Отправляет ежемесячный отчет"""
        try:
            from app.services.reports_service import ReportsService

            reports_service = ReportsService()
            report = await reports_service.generate_monthly_report()

            # Отправляем текстовый отчет
            text = await reports_service.format_report_to_text(report)

            # Сохраняем Excel файл с детализацией
            excel_path = await reports_service.save_report_to_excel(report)

            # Получаем список администраторов и диспетчеров
            recipients = await self._get_report_recipients()

            # Отправляем всем получателям
            for recipient_id in recipients:
                try:
                    await self.bot.send_message(chat_id=recipient_id, text=text, parse_mode="HTML")

                    # Отправляем Excel файл
                    document = FSInputFile(excel_path)
                    await self.bot.send_document(
                        chat_id=recipient_id,
                        document=document,
                        caption=f"📊 Ежемесячный отчет за {report['period']}",
                    )

                    logger.info(f"Ежемесячный отчет отправлен пользователю {recipient_id}")

                except Exception as e:
                    logger.error(
                        f"Ошибка отправки ежемесячного отчета пользователю {recipient_id}: {e}"
                    )

            logger.info("Ежемесячный отчет успешно отправлен всем получателям")

        except Exception as e:
            logger.error(f"Ошибка генерации ежемесячного отчета: {e}")

    async def _get_report_recipients(self) -> list[int]:
        """Получает список получателей отчетов (администраторы и диспетчеры)"""
        from app.database.orm_database import ORMDatabase as ORMDatabaseRuntime

        if not isinstance(self.db, ORMDatabaseRuntime):
            # В legacy-режиме используем метод базы для получения пользователей по ролям
            admins = await self.db.get_users_by_role("ADMIN")
            dispatchers = await self.db.get_users_by_role("DISPATCHER")
            recipients = [user.telegram_id for user in (admins + dispatchers) if user.telegram_id]
            logger.info("Найдено %s получателей отчетов (legacy)", len(recipients))
            return recipients

        await self.db.connect()

        try:
            if self.db.session_factory is None:
                logger.error("ORMDatabase.session_factory не инициализирован")
                return []

            async with self.db.session_factory() as session:
                from sqlalchemy import text

                result = await session.execute(
                    text(
                        """
                        SELECT telegram_id
                        FROM users
                        WHERE role LIKE '%ADMIN%' OR role LIKE '%DISPATCHER%'
                        """
                    )
                )

                rows = result.fetchall()
                recipients = [row[0] for row in rows]

                logger.info("Найдено %s получателей отчетов", len(recipients))
                return recipients

        finally:
            await self.db.disconnect()

    async def send_custom_report(
        self, start_date: str, end_date: str, recipients: list[int] | None = None
    ):
        """Отправляет кастомный отчет за указанный период"""
        try:
            from app.services.reports_service import ReportsService

            reports_service = ReportsService()

            # Генерируем отчет за период (используем дневной формат)
            report = await reports_service.generate_daily_report()
            report["period"] = f"{start_date} - {end_date}"

            # Отправляем текстовый отчет
            text = await reports_service.format_report_to_text(report)

            # Сохраняем файл отчета
            file_path = await reports_service.save_report_to_file(
                report, f"custom_report_{start_date}_{end_date}.txt"
            )

            # Используем указанных получателей или всех админов/диспетчеров
            if not recipients:
                recipients = await self._get_report_recipients()

            # Отправляем всем получателям
            for recipient_id in recipients:
                try:
                    await self.bot.send_message(chat_id=recipient_id, text=text, parse_mode="HTML")

                    # Отправляем файл
                    document = FSInputFile(file_path)
                    await self.bot.send_document(
                        chat_id=recipient_id,
                        document=document,
                        caption=f"📊 Кастомный отчет за {start_date} - {end_date}",
                    )

                    logger.info(f"Кастомный отчет отправлен пользователю {recipient_id}")

                except Exception as e:
                    logger.error(
                        f"Ошибка отправки кастомного отчета пользователю {recipient_id}: {e}"
                    )

            logger.info("Кастомный отчет успешно отправлен всем получателям")

        except Exception as e:
            logger.error(f"Ошибка генерации кастомного отчета: {e}")
