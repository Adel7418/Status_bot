"""
MasterPresenter - форматирование информации о мастерах
"""

from typing import Optional


class MasterPresenter:
    """Presenter для форматирования информации о мастерах"""

    @staticmethod
    def format_master_details(master, include_stats: bool = False) -> str:
        """
        Форматирование детальной информации о мастере

        Args:
            master: Объект мастера
            include_stats: Включать ли статистику

        Returns:
            Отформатированный текст с деталями мастера
        """
        status_emoji = "✅" if master.is_approved else "⏳"
        status_text = "Одобрен" if master.is_approved else "Ожидает одобрения"

        active_emoji = "🟢" if master.is_active else "🔴"
        active_text = "Активен" if master.is_active else "Неактивен"

        text = (
            f"👨‍🔧 <b>Мастер: {master.get_display_name()}</b>\n\n"
            f"📞 <b>Телефон:</b> {master.phone}\n"
            f"🔧 <b>Специализация:</b> {master.specialization}\n"
            f"📊 <b>Статус:</b> {status_emoji} {status_text}\n"
            f"🔄 <b>Активность:</b> {active_emoji} {active_text}\n"
        )

        if master.work_chat_id:
            text += "💬 <b>Рабочая группа:</b> настроена\n"

        if include_stats and hasattr(master, "stats"):
            stats = master.stats
            text += (
                f"\n📈 <b>Статистика:</b>\n"
                f"├ Всего заявок: {stats.get('total', 0)}\n"
                f"├ Завершено: {stats.get('completed', 0)}\n"
                f"└ В работе: {stats.get('in_progress', 0)}\n"
            )

        return text

    @staticmethod
    def format_master_short(master) -> str:
        """
        Краткое форматирование мастера для списков

        Args:
            master: Объект мастера

        Returns:
            Краткий текст мастера
        """
        active_emoji = "🟢" if master.is_active else "🔴"
        return f"{active_emoji} {master.get_display_name()} - {master.specialization}"

    @staticmethod
    def format_master_list(masters: list, title: str = "Мастера") -> str:
        """
        Форматирование списка мастеров

        Args:
            masters: Список мастеров
            title: Заголовок списка

        Returns:
            Отформатированный список мастеров
        """
        if not masters:
            return f"📭 {title}: нет мастеров"

        text = f"👥 <b>{title}:</b> ({len(masters)})\n\n"

        for master in masters:
            text += f"• {MasterPresenter.format_master_short(master)}\n"

        return text

    @staticmethod
    def format_master_stats(
        master,
        total_orders: int,
        completed_orders: int,
        in_progress_orders: int,
        total_revenue: Optional[float] = None,
    ) -> str:
        """
        Форматирование статистики мастера

        Args:
            master: Объект мастера
            total_orders: Всего заявок
            completed_orders: Завершено заявок
            in_progress_orders: В работе
            total_revenue: Общая выручка

        Returns:
            Отформатированная статистика
        """
        completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0

        text = (
            f"📊 <b>Статистика мастера {master.get_display_name()}</b>\n\n"
            f"📋 <b>Заявки:</b>\n"
            f"├ Всего: {total_orders}\n"
            f"├ Завершено: {completed_orders}\n"
            f"├ В работе: {in_progress_orders}\n"
            f"└ Процент завершения: {completion_rate:.1f}%\n"
        )

        if total_revenue is not None:
            text += f"\n💰 <b>Выручка:</b> {total_revenue:.2f} ₽\n"

        return text

    @staticmethod
    def format_master_notification(
        master, action: str, additional_info: Optional[str] = None
    ) -> str:
        """
        Форматирование уведомления о мастере

        Args:
            master: Объект мастера
            action: Действие (зарегистрирован, одобрен, деактивирован и т.д.)
            additional_info: Дополнительная информация

        Returns:
            Отформатированное уведомление
        """
        text = (
            f"👨‍🔧 <b>Мастер {action}</b>\n\n"
            f"👤 {master.get_display_name()}\n"
            f"📞 {master.phone}\n"
            f"🔧 {master.specialization}\n"
        )

        if additional_info:
            text += f"\n{additional_info}"

        return text
