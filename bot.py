"""
Главный файл Telegram бота для управления заявками на ремонт техники
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import Config
from app.database import Database
from app.handlers import routers
from app.middlewares import RoleCheckMiddleware
from app.services.scheduler import TaskScheduler


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


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
                "🛑 <b>Бот остановлен</b>\n\n"
                "Система управления заявками прекратила работу.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error("Failed to notify admin %s: %s", admin_id, e)

    logger.info("Бот остановлен")


async def main():
    """Основная функция запуска бота"""

    # Валидация конфигурации
    try:
        Config.validate()
    except ValueError as e:
        logger.error("Ошибка конфигурации: %s", e)
        sys.exit(1)

    # Инициализация бота
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    # Инициализация хранилища состояний
    storage = MemoryStorage()

    # Инициализация диспетчера
    dp = Dispatcher(storage=storage)

    # Инициализация базы данных
    db = Database()
    await db.connect()

    # ВАЖНО: Инициализируем БД ДО подключения middleware
    logger.info("Инициализация базы данных...")
    await db.init_db()
    logger.info("База данных инициализирована")

    # Инициализация планировщика
    scheduler = TaskScheduler(bot)

    # Подключение middleware (после инициализации БД)
    role_middleware = RoleCheckMiddleware(db)
    dp.message.middleware(role_middleware)
    dp.callback_query.middleware(role_middleware)

    # Подключение роутеров
    for router in routers:
        dp.include_router(router)

    logger.info("Подключено %s роутеров", len(routers))

    # Вызов startup функции перед запуском
    await on_startup(bot, db, scheduler)

    # Запуск бота
    try:
        logger.info("Запуск бота...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
    except Exception as e:
        logger.error("Критическая ошибка: %s", e)
    finally:
        # Вызов shutdown функции при завершении
        await on_shutdown(bot, db, scheduler)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical("Неожиданная ошибка: %s", e)
        sys.exit(1)

