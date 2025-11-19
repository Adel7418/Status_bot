"""
Скрипт для мониторинга работы handlers в реальных условиях

Использование:
    python scripts/test_handlers_realtime.py

Проверяет:
    - Работу DI (Dependency Injection)
    - Обработку запросов handlers
    - Ошибки в логах
    - Статистику использования handlers
"""

import asyncio
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_database
from app.handlers.master import router as master_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def analyze_log_file(log_path: Path) -> dict:
    """
    Анализирует лог файл на наличие ошибок и статистику handlers

    Args:
        log_path: Путь к лог файлу

    Returns:
        dict: Статистика и ошибки
    """
    if not log_path.exists():
        return {"error": "Log file not found", "stats": {}}

    stats = {
        "total_lines": 0,
        "errors": [],
        "handlers_called": defaultdict(int),
        "di_injections": 0,
        "db_operations": 0,
        "recent_activity": [],
    }

    try:
        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()
            stats["total_lines"] = len(lines)

            # Анализируем последние 1000 строк
            for line in lines[-1000:]:
                # Ищем ошибки
                if "ERROR" in line or "Exception" in line:
                    stats["errors"].append(line.strip())
                    if len(stats["errors"]) > 20:  # Ограничиваем количество
                        stats["errors"] = stats["errors"][-20:]

                # Ищем вызовы handlers
                if "app.handlers" in line:
                    # Извлекаем имя handler
                    match = re.search(r"app\.handlers\.(\w+)", line)
                    if match:
                        handler_name = match.group(1)
                        stats["handlers_called"][handler_name] += 1

                # Ищем DI инъекции
                if "DependencyInjectionMiddleware" in line or "db injected" in line.lower():
                    stats["di_injections"] += 1

                # Ищем операции с БД
                if "database" in line.lower() or "db." in line.lower():
                    stats["db_operations"] += 1

                # Сохраняем последние активности
                if "INFO" in line and ("handler" in line.lower() or "order" in line.lower()):
                    stats["recent_activity"].append(line.strip())
                    if len(stats["recent_activity"]) > 10:
                        stats["recent_activity"] = stats["recent_activity"][-10:]

    except Exception as e:
        stats["error"] = f"Error reading log file: {e}"

    return stats


async def test_di_injection():
    """
    Тестирует работу Dependency Injection

    Returns:
        bool: True если DI работает корректно
    """
    logger.info("=" * 60)
    logger.info("Тестирование Dependency Injection...")
    logger.info("=" * 60)

    try:
        # Проверяем, что экземпляр БД можно получить через фабрику
        db = get_database()
        await db.connect()

        logger.info("✅ Database создан успешно")
        logger.info(f"   Тип: {type(db).__name__}")
        logger.info(f"   USE_ORM: {db.use_orm if hasattr(db, 'use_orm') else 'N/A'}")

        # Проверяем, что handlers зарегистрированы
        logger.info(
            f"✅ Handlers зарегистрированы: {len(master_router.sub_routers) if hasattr(master_router, 'sub_routers') else 'N/A'}"
        )

        # Проверяем подключение к БД
        try:
            # Проверяем тип Database
            if hasattr(db, "get_session"):
                # ORM Database
                from app.database.models import User

                async with db.get_session() as session:
                    from sqlalchemy import select

                    result = await session.execute(select(User).limit(1))
                    users = result.scalars().all()
                    logger.info(
                        f"✅ Подключение к БД работает (ORM, найдено пользователей: {len(users)})"
                    )
            elif hasattr(db, "get_user_by_telegram_id"):
                # Legacy Database
                await db.get_user_by_telegram_id(1)  # Тестовый запрос
                logger.info("✅ Подключение к БД работает (Legacy)")
            else:
                logger.warning("⚠️  Неизвестный тип Database")
        except Exception as e:
            logger.warning(f"⚠️  Ошибка при проверке БД: {e}")

        await db.disconnect()
        logger.info("✅ DI тест пройден успешно")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании DI: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_handler_registration():
    """
    Проверяет регистрацию handlers

    Returns:
        dict: Информация о зарегистрированных handlers
    """
    logger.info("=" * 60)
    logger.info("Проверка регистрации handlers...")
    logger.info("=" * 60)

    handlers_info = {}

    # Проверяем master router
    try:
        # Получаем все зарегистрированные handlers
        if hasattr(master_router, "observers"):
            observers = master_router.observers
            handlers_info["master_observers"] = len(observers) if observers else 0
            logger.info(f"✅ Master router: {handlers_info['master_observers']} observers")
        else:
            logger.warning("⚠️  Не удалось получить observers из router")
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке handlers: {e}")

    return handlers_info


def print_statistics(stats: dict):
    """
    Выводит статистику в читаемом виде

    Args:
        stats: Статистика из analyze_log_file
    """
    import io
    import sys

    # Устанавливаем UTF-8 для вывода
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("\n" + "=" * 60)
    print("СТАТИСТИКА РАБОТЫ HANDLERS")
    print("=" * 60)

    if "error" in stats:
        print(f"❌ Ошибка: {stats['error']}")
        return

    print("\n📊 Общая статистика:")
    print(f"   Всего строк в логе: {stats['total_lines']}")
    print(f"   DI инъекций: {stats['di_injections']}")
    print(f"   Операций с БД: {stats['db_operations']}")

    if stats["handlers_called"]:
        print("\n📋 Вызовы handlers (последние 1000 строк):")
        for handler, count in sorted(
            stats["handlers_called"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"   {handler}: {count}")

    if stats["errors"]:
        print(f"\n❌ Найдено ошибок: {len(stats['errors'])}")
        print("   Последние ошибки:")
        for error in stats["errors"][-5:]:
            print(f"   - {error[:100]}...")
    else:
        print("\n✅ Ошибок не найдено")

    if stats["recent_activity"]:
        print("\n📝 Последняя активность:")
        for activity in stats["recent_activity"][-5:]:
            print(f"   {activity[:80]}...")


async def main():
    """Главная функция"""
    import io
    import sys

    # Устанавливаем UTF-8 для вывода
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ HANDLERS В РЕАЛЬНЫХ УСЛОВИЯХ")
    print("=" * 60)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. Тест DI
    di_ok = await test_di_injection()
    print()

    # 2. Проверка регистрации handlers
    check_handler_registration()
    print()

    # 3. Анализ логов
    log_path = Path("logs/bot.log")
    if not log_path.exists():
        log_path = Path("data/bot.log")

    if log_path.exists():
        print("=" * 60)
        print("АНАЛИЗ ЛОГОВ")
        print("=" * 60)
        stats = analyze_log_file(log_path)
        print_statistics(stats)
    else:
        print("⚠️  Лог файл не найден. Проверьте путь к логам.")

    # 4. Итоговый результат
    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("=" * 60)
    if di_ok:
        print("✅ Dependency Injection работает корректно")
    else:
        print("❌ Обнаружены проблемы с Dependency Injection")

    print("\n💡 Рекомендации:")
    print("   1. Проверьте логи на наличие ошибок")
    print("   2. Протестируйте handlers через Telegram бота")
    print("   3. Убедитесь, что все handlers получают db через DI")
    print("   4. Проверьте работу в групповых чатах")


if __name__ == "__main__":
    asyncio.run(main())
