"""
Parser Config Repository

Репозиторий для работы с конфигурацией парсера заявок (ParserConfig).
"""

import logging
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.orm_models import ParserConfig


logger = logging.getLogger(__name__)


class ParserConfigRepository:
    """
    Репозиторий для управления конфигурацией парсера.

    Паттерн Single Row Config: в таблице всегда одна запись (id=1).
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализация репозитория.

        Args:
            session: Async SQLAlchemy сессия
        """
        self.session = session
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def get_config(self) -> ParserConfig | None:
        """
        Получает конфигурацию парсера.

        Returns:
            ParserConfig или None если не найдена
        """
        result = await self.session.execute(
            select(ParserConfig).where(ParserConfig.id == 1)
        )
        config = result.scalar_one_or_none()

        if config:
            self.logger.debug(
                f"Загружена конфигурация парсера: group_id={config.group_id}, enabled={config.enabled}"
            )
        else:
            self.logger.warning("Конфигурация парсера не найдена в БД")

        return cast(ParserConfig | None, config)

    async def set_group_id(self, group_id: int) -> ParserConfig:
        """
        Устанавливает ID группы для мониторинга.

        Args:
            group_id: ID Telegram-группы

        Returns:
            Обновлённая конфигурация
        """
        config = await self.get_config()

        if config:
            # Обновляем существующую запись
            config.group_id = group_id
            await self.session.commit()
            await self.session.refresh(config)
            self.logger.info(f"Группа парсера обновлена: group_id={group_id}")
        else:
            # Создаём новую запись (на случай если миграция не выполнена)
            config = ParserConfig(id=1, group_id=group_id, enabled=False)
            self.session.add(config)
            await self.session.commit()
            await self.session.refresh(config)
            self.logger.info(f"Создана конфигурация парсера: group_id={group_id}")

        return config

    async def enable_parser(self) -> ParserConfig:
        """
        Включает парсер.

        Returns:
            Обновлённая конфигурация

        Raises:
            ValueError: Если group_id не установлен
        """
        config = await self.get_config()

        if not config:
            raise ValueError("Конфигурация парсера не найдена. Сначала установите group_id.")

        if not config.group_id:
            raise ValueError("Нельзя включить парсер без установленного group_id")

        config.enabled = True
        await self.session.commit()
        await self.session.refresh(config)

        self.logger.info(f"✅ Парсер включён для группы {config.group_id}")
        return config

    async def disable_parser(self) -> ParserConfig:
        """
        Отключает парсер.

        Returns:
            Обновлённая конфигурация
        """
        config = await self.get_config()

        if not config:
            raise ValueError("Конфигурация парсера не найдена")

        config.enabled = False
        await self.session.commit()
        await self.session.refresh(config)

        self.logger.info("❌ Парсер отключён")
        return config

    async def is_enabled(self) -> bool:
        """
        Проверяет, включён ли парсер.

        Returns:
            True если парсер включён, иначе False
        """
        config = await self.get_config()
        return bool(config.enabled) if config else False

    async def get_group_id(self) -> int | None:
        """
        Получает ID группы для мониторинга.

        Returns:
            ID группы или None
        """
        config = await self.get_config()
        return int(config.group_id) if config and config.group_id is not None else None
