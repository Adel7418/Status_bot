"""
Middleware для инжекции зависимостей (Dependency Injection)
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.database import Database


logger = logging.getLogger(__name__)


class DependencyInjectionMiddleware(BaseMiddleware):
    """
    Middleware для инжекции Database и ServiceFactory в handlers

    Это позволяет:
    - Убрать прямое создание Database() в handlers
    - Использовать единый экземпляр Database для всех запросов
    - Легко тестировать handlers с моками
    - Контролировать жизненный цикл соединений
    """

    def __init__(self, db: Database):
        """
        Инициализация

        Args:
            db: Экземпляр базы данных (singleton)
        """
        super().__init__()
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Инжектирует зависимости в data для использования в handlers

        Args:
            handler: Следующий handler
            event: Событие (Message или CallbackQuery)
            data: Данные для передачи в handler

        Returns:
            Результат выполнения handler
        """
        # Инжектируем Database в data
        # Handlers могут получить его через параметр или из data
        data["db"] = self.db

        # Инжектируем ServiceFactory через Database.services (если доступен)
        # Это позволяет использовать сервисы без прямого создания
        # Для ORMDatabase services может быть недоступен
        if hasattr(self.db, "services"):
            data["services"] = self.db.services
        else:
            # Для ORM версии services пока не реализован
            data["services"] = None

        # Вызываем следующий handler
        return await handler(event, data)
