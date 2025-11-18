"""
Фильтры для работы с группами
"""

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.database import get_database


class IsGroupChat(BaseFilter):
    """Фильтр для проверки, что сообщение из группы"""

    async def __call__(self, message: Message) -> bool:
        return message.chat.type in ["group", "supergroup"]


class IsPrivateChat(BaseFilter):
    """Фильтр для проверки, что сообщение из личного чата"""

    async def __call__(self, message: Message) -> bool:
        return bool(message.chat.type == "private")


class IsMasterWorkGroup(BaseFilter):
    """Фильтр для проверки, что сообщение из рабочей группы мастера"""

    async def __call__(self, message: Message) -> bool:
        if message.chat.type not in ["group", "supergroup"]:
            return False

        # Проверяем, является ли эта группа рабочей группой какого-либо мастера
        db = get_database()
        await db.connect()

        try:
            # Получаем всех мастеров с этой рабочей группой
            masters = await db.get_all_masters(only_approved=True, only_active=True)
            work_chat_ids = [master.work_chat_id for master in masters if master.work_chat_id]

            return message.chat.id in work_chat_ids
        finally:
            await db.disconnect()


class IsOrderRelatedMessage(BaseFilter):
    """Фильтр для проверки, что сообщение связано с заказом"""

    async def __call__(self, message: Message) -> bool:
        # Проверяем, содержит ли сообщение упоминание заказа
        text = message.text or ""

        # Команды для работы с заказами
        order_commands = ["/order", "/заказ", "/заявка"]
        if any(cmd in text.lower() for cmd in order_commands):
            return True

        # Проверяем, содержит ли сообщение номер заказа
        import re

        order_pattern = r"#?\d+"
        return bool(re.search(order_pattern, text))


class IsMasterInGroup(BaseFilter):
    """Фильтр для проверки, что отправитель - мастер в этой группе"""

    async def __call__(self, message: Message) -> bool:
        if message.chat.type not in ["group", "supergroup"]:
            return False

        user = message.from_user
        if not user:
            return False

        db = get_database()
        await db.connect()

        try:
            # Получаем мастера по telegram_id
            master = await db.get_master_by_telegram_id(user.id)

            if not master:
                return False

            # Проверяем, что эта группа - рабочая группа мастера
            return bool(master.work_chat_id == message.chat.id)
        finally:
            await db.disconnect()


class IsGroupOrderCallback(BaseFilter):
    """Фильтр для проверки, что callback связан с групповым взаимодействием с заказом"""

    async def __call__(self, callback: CallbackQuery) -> bool:
        message = callback.message
        if not isinstance(message, Message):
            return False

        if message.chat.type not in ["group", "supergroup"]:
            return False

        # Проверяем, что callback связан с групповыми действиями
        group_actions = [
            "group_accept_order",
            "group_refuse_order",
            "group_onsite_order",
            "group_complete_order",
            "group_dr_order",
        ]

        data = callback.data or ""
        return any(action in data for action in group_actions)
