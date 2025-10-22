"""
Главный файл Telegram бота для управления заявками на ремонт техники
"""

import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, UpdateType
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from app.config import Config
from app.database import Database
from app.handlers import routers
from app.middlewares import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RoleCheckMiddleware,
    ValidationHandlerMiddleware,
    global_error_handler,
)
from app.services.scheduler import TaskScheduler
from app.utils.sentry import init_sentry


# Создаем директорию для логов если не существует
Path("logs").mkdir(exist_ok=True)

# Настройка логирования с ротацией
log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Rotating file handler (макс 10MB, хранить 5 файлов)
file_handler = RotatingFileHandler(
    "logs/bot.log",
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(log_formatter)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# Настройка root logger
# Используем LOG_LEVEL из .env (по умолчанию INFO)
log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

logging.basicConfig(
    level=log_level,
    handlers=[file_handler, console_handler],
)

logger = logging.getLogger(__name__)

# Настройка уровней логирования для различных модулей
if log_level == logging.DEBUG:
    logging.getLogger("app").setLevel(logging.DEBUG)
    logging.getLogger("aiogram").setLevel(logging.INFO)  # aiogram остается INFO чтобы не спамить
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logger.info("DEBUG режим включен (LOG_LEVEL=DEBUG)")
else:
    # Production/INFO - минимальное логирование
    logging.getLogger("app").setLevel(log_level)
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


async def on_startup(bot: Bot, db: Database, scheduler: TaskScheduler):
    """
    Действия при запуске бота

    Args:
        bot: Экземпляр бота
        db: Экземпляр базы данных
        scheduler: Планировщик задач
    """
    # БД уже инициализирована в main()

    # Запуск планировщика
    await scheduler.start()
    logger.info("Планировщик задач запущен")

    # Уведомление администраторов о запуске отключено
    # for admin_id in Config.ADMIN_IDS:
    #     try:
    #         await bot.send_message(
    #             admin_id,
    #             "✅ <b>Бот запущен!</b>\n\n"
    #             "Система управления заявками готова к работе.",
    #             parse_mode="HTML"
    #         )
    #     except Exception as e:
    #         logger.error("Failed to notify admin %s: %s", admin_id, e)

    logger.info("Бот успешно запущен!")


async def on_shutdown(bot: Bot, db: Database, scheduler: TaskScheduler):
    """
    Действия при остановке бота

    Args:
        bot: Экземпляр бота
        db: Экземпляр базы данных
        scheduler: Планировщик задач
    """
    # Остановка планировщика
    await scheduler.stop()
    logger.info("Планировщик задач остановлен")

    # Закрытие соединения с БД
    await db.disconnect()
    logger.info("Соединение с БД закрыто")

    # Уведомление администраторов об остановке
    for admin_id in Config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                "🛑 <b>Бот остановлен</b>\n\n" "Система управления заявками прекратила работу.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Failed to notify admin %s: %s", admin_id, e)

    logger.info("Бот остановлен")


async def main():
    """Основная функция запуска бота"""

    bot = None
    db = None
    scheduler = None
    dp = None

    try:
        # Инициализация Sentry (опционально)
        init_sentry()

        # Валидация конфигурации
        try:
            Config.validate()
        except ValueError as e:
            logger.error("Ошибка конфигурации: %s", e)
            sys.exit(1)

        # Инициализация бота
        bot = Bot(token=Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

        # Инициализация хранилища состояний
        # Используем Redis для production, MemoryStorage для development
        redis_url = os.getenv("REDIS_URL")

        # ОТЛАДКА: Явное логирование конфигурации storage
        logger.info("=" * 60)
        logger.info("🔧 Конфигурация FSM Storage:")
        logger.info(f"  REDIS_URL: {redis_url}")
        logger.info(f"  DEV_MODE: {Config.DEV_MODE}")
        logger.info(f"  Условие (redis_url and not DEV_MODE): {redis_url and not Config.DEV_MODE}")
        logger.info("=" * 60)

        if redis_url and not Config.DEV_MODE:
            logger.info("✅ Используется RedisStorage для FSM: %s", redis_url)
            storage = RedisStorage.from_url(redis_url)
        else:
            logger.warning("⚠️  Используется MemoryStorage (состояния потеряются при рестарте)")
            logger.warning(f"   Причина: redis_url={redis_url}, DEV_MODE={Config.DEV_MODE}")
            storage = MemoryStorage()

        # Инициализация диспетчера
        dp = Dispatcher(storage=storage)

        # Инициализация базы данных
        logger.info("=" * 60)
        logger.info("🔧 Инициализация базы данных...")
        logger.info(f"   USE_ORM: {Config.USE_ORM}")
        logger.info(f"   DATABASE_PATH: {Config.DATABASE_PATH}")
        logger.info("=" * 60)
        
        db = Database()
        await db.connect()

        # ВАЖНО: Инициализируем БД ДО подключения middleware
        logger.info("Инициализация базы данных...")
        # ORM не требует init_db - таблицы уже созданы через миграции
        if hasattr(db, "init_db"):
            await db.init_db()
        logger.info("✅ База данных инициализирована")

        # Инициализация планировщика (передаем shared DB instance)
        scheduler = TaskScheduler(bot, db)

        # Подключение middleware (после инициализации БД)
        # 1. Logging middleware (первым - логирует все входящие события)
        logging_middleware = LoggingMiddleware()
        dp.message.middleware(logging_middleware)
        dp.callback_query.middleware(logging_middleware)

        # 2. Rate Limit middleware (защита от spam и DoS атак)
        # Настройки: 2 запроса в секунду, burst до 4 запросов
        # С прогрессивным наказанием и автобаном после 30 нарушений
        rate_limit_middleware = RateLimitMiddleware(
            rate=2,  # 2 запроса/сек
            period=1,  # за 1 секунду
            burst=4,  # максимум 4 подряд
            max_violations=30,  # бан после 30 нарушений
            violation_window=60,  # в течении 60 секунд
        )
        dp.message.middleware(rate_limit_middleware)
        dp.callback_query.middleware(rate_limit_middleware)
        logger.info("Rate limiting: 2 req/sec, burst 4, auto-ban after 30 violations/min")

        # 3. Role check middleware (проверяет роли и регистрирует пользователей)
        role_middleware = RoleCheckMiddleware(db)
        dp.message.middleware(role_middleware)
        dp.callback_query.middleware(role_middleware)

        # 4. Validation handler middleware (обрабатывает ошибки State Machine)
        validation_middleware = ValidationHandlerMiddleware()
        dp.message.middleware(validation_middleware)
        dp.callback_query.middleware(validation_middleware)

        # Подключение роутеров
        for router in routers:
            dp.include_router(router)

        logger.info("Подключено %s роутеров", len(routers))

        # Регистрация глобального error handler
        dp.errors.register(global_error_handler)

        # Вызов startup функции перед запуском
        await on_startup(bot, db, scheduler)

        # Запуск бота
        logger.info("Запуск бота...")

        # Явно указываем только используемые типы updates
        allowed_updates_list = [
            UpdateType.MESSAGE,
            UpdateType.CALLBACK_QUERY,
            # Не получаем лишние update types:
            # - edited_message, channel_post и т.д. не используются
        ]

        await dp.start_polling(
            bot,
            allowed_updates=allowed_updates_list,
            drop_pending_updates=True,
        )

    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.exception("Критическая ошибка: %s", e)
    finally:
        # Гарантированная очистка ресурсов
        logger.info("Начало процедуры остановки...")

        # Остановка планировщика
        if scheduler:
            try:
                await scheduler.stop()
            except Exception as e:
                logger.error("Ошибка при остановке scheduler: %s", e)

        # Закрытие соединения с БД
        if db:
            try:
                await db.disconnect()
            except Exception as e:
                logger.error("Ошибка при отключении БД: %s", e)

        # Закрытие storage (для Redis)
        if dp and hasattr(dp.storage, "close"):
            try:
                await dp.storage.close()
                logger.info("Storage закрыт")
            except Exception as e:
                logger.error("Ошибка при закрытии storage: %s", e)

        # Закрытие bot session (критично!)
        if bot:
            try:
                await bot.session.close()
                logger.info("Bot session закрыта")
            except Exception as e:
                logger.error("Ошибка при закрытии bot session: %s", e)

        logger.info("Бот полностью остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical("Неожиданная ошибка: %s", e)
        sys.exit(1)
