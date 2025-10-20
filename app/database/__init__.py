"""
Database package: фабрика выбора реализации (legacy SQL vs ORM)
"""

from app.core.config import Config


if Config.USE_ORM:
    from .orm_database import ORMDatabase as Database  # type: ignore
else:
    from .db import Database  # type: ignore

__all__ = ["Database"]
