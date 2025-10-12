"""
Pytest fixtures и конфигурация для тестов
"""
import asyncio
import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage


# Добавляем корневую директорию в PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import Config
from app.database import Database


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Фикстура для event loop на уровне сессии
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[Database, None]:
    """
    Фикстура для тестовой базы данных (in-memory)
    """
    database = Database(":memory:")
    await database.connect()
    await database.init_db()
    yield database
    await database.disconnect()


@pytest.fixture
def bot_token() -> str:
    """
    Фикстура для тестового токена бота
    """
    return "123456789:ABCdefGHIjklMNOpqrsTUVwxyz-TEST-TOKEN"


@pytest_asyncio.fixture
async def bot(bot_token: str) -> Bot:
    """
    Фикстура для экземпляра бота
    """
    bot_instance = Bot(token=bot_token)
    yield bot_instance
    await bot_instance.session.close()


@pytest_asyncio.fixture
async def dp() -> Dispatcher:
    """
    Фикстура для диспетчера с MemoryStorage
    """
    storage = MemoryStorage()
    dispatcher = Dispatcher(storage=storage)
    yield dispatcher
    await storage.close()


@pytest.fixture
def admin_id() -> int:
    """
    Фикстура для ID администратора
    """
    return 123456789


@pytest.fixture
def dispatcher_id() -> int:
    """
    Фикстура для ID диспетчера
    """
    return 987654321


@pytest.fixture
def master_id() -> int:
    """
    Фикстура для ID мастера
    """
    return 111222333


@pytest.fixture
def mock_config(admin_id: int, dispatcher_id: int, monkeypatch) -> None:
    """
    Фикстура для замены конфигурации на тестовую
    """
    monkeypatch.setattr(Config, "ADMIN_IDS", [admin_id])
    monkeypatch.setattr(Config, "DISPATCHER_IDS", [dispatcher_id])
    monkeypatch.setattr(Config, "BOT_TOKEN", "test_token")
    monkeypatch.setattr(Config, "DATABASE_PATH", ":memory:")

