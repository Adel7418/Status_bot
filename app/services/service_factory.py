"""
Factory для создания сервисов и репозиториев
"""

import logging

import aiosqlite

from app.domain.order_state_machine import OrderStateMachine
from app.repositories import MasterRepository, OrderRepository, UserRepository
from app.services.master_service import MasterService
from app.services.order_service import OrderService
from app.services.user_service import UserService


logger = logging.getLogger(__name__)


class ServiceFactory:
    """
    Factory для создания сервисов с инжекцией зависимостей
    """

    def __init__(self, db_connection: aiosqlite.Connection):
        """
        Инициализация фабрики

        Args:
            db_connection: Подключение к базе данных
        """
        self.db_connection = db_connection
        self._order_repo = None
        self._user_repo = None
        self._master_repo = None
        self._order_service = None
        self._user_service = None
        self._master_service = None
        self._state_machine = None

    @property
    def order_repository(self) -> OrderRepository:
        """Ленивая инициализация OrderRepository"""
        if self._order_repo is None:
            self._order_repo = OrderRepository(self.db_connection)
        return self._order_repo

    @property
    def user_repository(self) -> UserRepository:
        """Ленивая инициализация UserRepository"""
        if self._user_repo is None:
            self._user_repo = UserRepository(self.db_connection)
        return self._user_repo

    @property
    def master_repository(self) -> MasterRepository:
        """Ленивая инициализация MasterRepository"""
        if self._master_repo is None:
            self._master_repo = MasterRepository(self.db_connection)
        return self._master_repo

    @property
    def state_machine(self) -> OrderStateMachine:
        """Ленивая инициализация OrderStateMachine"""
        if self._state_machine is None:
            self._state_machine = OrderStateMachine()
        return self._state_machine

    @property
    def order_service(self) -> OrderService:
        """Получение Order Service"""
        if self._order_service is None:
            self._order_service = OrderService(
                order_repo=self.order_repository,
                user_repo=self.user_repository,
                master_repo=self.master_repository,
                state_machine=self.state_machine,
            )
        return self._order_service

    @property
    def user_service(self) -> UserService:
        """Получение User Service"""
        if self._user_service is None:
            self._user_service = UserService(user_repo=self.user_repository)
        return self._user_service

    @property
    def master_service(self) -> MasterService:
        """Получение Master Service"""
        if self._master_service is None:
            self._master_service = MasterService(
                master_repo=self.master_repository, user_repo=self.user_repository
            )
        return self._master_service

    def reset(self):
        """Сброс кэшированных сервисов (для тестирования)"""
        self._order_repo = None
        self._user_repo = None
        self._master_repo = None
        self._order_service = None
        self._user_service = None
        self._master_service = None
        self._state_machine = None
        logger.debug("ServiceFactory: сервисы сброшены")
