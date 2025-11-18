"""
Database package: фабрика выбора реализации (legacy SQL vs ORM).

Задачи модуля:
- выбрать реализацию БД в рантайме в зависимости от конфигурации;
- предоставить тип для аннотаций (объединяющий legacy и ORM реализации);
- дать фабрику `get_database()` для единообразного создания экземпляров.
"""

from typing import TYPE_CHECKING, Union


if TYPE_CHECKING:
    # Типы только для аннотаций
    from .db import Database as LegacyDatabase
    from .orm_database import ORMDatabase

    DatabaseType = ORMDatabase | LegacyDatabase
    Database = DatabaseType  # псевдоним для использования в type hints
else:
    # Runtime: выбираем конкретный класс БД по конфигурации
    from app.core.config import Config

    if Config.USE_ORM:
        from .orm_database import ORMDatabase as Database
    else:
        from .db import Database

    # В рантайме достаточно знать, что это тот же тип, что и выбранный Database
    DatabaseType = Database


if TYPE_CHECKING:

    def get_database() -> DatabaseType:
        """
        Фабрика для получения экземпляра БД (типовая сигнатура для mypy).
        Реальная логика выбора реализации скрыта от type checker.
        """
        ...
else:

    def get_database() -> "DatabaseType":
        """
        Фабрика для получения экземпляра БД.

        Используйте эту функцию вместо прямого вызова `Database()`
        в хэндлерах и сервисах.
        """

        return Database()


__all__ = ["Database", "DatabaseType", "get_database"]
