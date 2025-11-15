"""
Database package: фабрика выбора реализации (legacy SQL vs ORM)
"""

from typing import TYPE_CHECKING

from app.core.config import Config

if TYPE_CHECKING:
    from .orm_database import ORMDatabase as Database
else:
    if Config.USE_ORM:
        from .orm_database import ORMDatabase as Database
    else:
        from .db import Database

__all__ = ["Database"]
