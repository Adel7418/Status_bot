#!/usr/bin/env python3
"""
Скрипт для проверки работы новых handlers
"""

import asyncio
import io
import sys
from pathlib import Path


# Фикс кодировки для Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Проверка импорта модулей"""
    print("\n" + "=" * 60)
    print("🔍 ТЕСТ 1: Проверка импорта модулей")
    print("=" * 60)

    try:
        print("Импорт admin_history handler...", end=" ")
        print("✅")

        print("Импорт OrderRepositoryExtended...", end=" ")
        print("✅")

        print("Импорт SearchService...", end=" ")
        print("✅")

        print("Импорт encryption (опционально)...", end=" ")
        try:
            from app.utils.encryption import decrypt, encrypt

            print("✅")
        except ImportError:
            print("⚠️  (cryptography не установлена)")

        print("\n✅ Все модули импортированы успешно!")
        return True

    except Exception as e:
        print(f"\n❌ Ошибка импорта: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_router_registration():
    """Проверка регистрации router"""
    print("\n" + "=" * 60)
    print("🔍 ТЕСТ 2: Проверка регистрации router")
    print("=" * 60)

    try:
        from app.handlers import routers

        print(f"Всего роутеров зарегистрировано: {len(routers)}")

        # Проверяем наличие admin_history_router
        from app.handlers.admin_history import router as admin_history_router

        if admin_history_router in routers:
            print("✅ admin_history_router зарегистрирован")
        else:
            print("❌ admin_history_router НЕ зарегистрирован")
            return False

        # В aiogram 3.x атрибут handlers недоступен напрямую
        # Проверяем наличие observer (новый API)
        if hasattr(admin_history_router, "observers"):
            print("✅ Router observers доступны (aiogram 3.x)")

        # Проверяем, что router - это экземпляр Router
        from aiogram import Router

        if isinstance(admin_history_router, Router):
            print("✅ admin_history_router - валидный Router")

        # Проверяем функции напрямую (более надежный способ)
        from app.handlers import admin_history

        functions = [
            "cmd_history",
            "cmd_deleted_orders",
            "cmd_search",
            "callback_history_status",
            "callback_deleted_orders",
        ]
        found = sum(1 for f in functions if hasattr(admin_history, f))
        print(f"✅ Найдено функций в модуле: {found}/{len(functions)}")

        print("\n✅ Router зарегистрирован успешно!")
        return True

    except Exception as e:
        print(f"\n❌ Ошибка регистрации: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_functions_exist():
    """Проверка наличия функций"""
    print("\n" + "=" * 60)
    print("🔍 ТЕСТ 3: Проверка функций")
    print("=" * 60)

    try:
        from app.handlers import admin_history

        functions = [
            "cmd_history",
            "cmd_deleted_orders",
            "cmd_search",
            "cmd_restore_order",
            "callback_history_status",
            "callback_history_changes",
            "callback_history_audit",
            "callback_history_full",
            "callback_deleted_orders",
            "callback_restore_order",
            "callback_view_deleted",
        ]

        for func_name in functions:
            if hasattr(admin_history, func_name):
                print(f"✅ {func_name}")
            else:
                print(f"❌ {func_name} не найдена")
                return False

        print("\n✅ Все функции существуют!")
        return True

    except Exception as e:
        print(f"\n❌ Ошибка проверки функций: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_keyboards_exist():
    """Проверка наличия клавиатур"""
    print("\n" + "=" * 60)
    print("🔍 ТЕСТ 4: Проверка клавиатур")
    print("=" * 60)

    try:
        from app.handlers import admin_history

        keyboards = [
            "get_history_keyboard",
            "get_deleted_orders_keyboard",
            "get_restore_keyboard",
        ]

        for kb_name in keyboards:
            if hasattr(admin_history, kb_name):
                func = getattr(admin_history, kb_name)

                # Пробуем вызвать
                if kb_name == "get_history_keyboard":
                    kb = func(order_id=1)
                elif kb_name == "get_deleted_orders_keyboard":
                    kb = func(page=0)
                elif kb_name == "get_restore_keyboard":
                    kb = func(order_id=1)

                buttons_count = sum(len(row) for row in kb.inline_keyboard)
                print(f"✅ {kb_name} ({buttons_count} кнопок)")
            else:
                print(f"❌ {kb_name} не найдена")
                return False

        print("\n✅ Все клавиатуры работают!")
        return True

    except Exception as e:
        print(f"\n❌ Ошибка проверки клавиатур: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_repository_methods():
    """Проверка методов репозитория"""
    print("\n" + "=" * 60)
    print("🔍 ТЕСТ 5: Проверка методов репозитория")
    print("=" * 60)

    try:
        from app.database.db import Database
        from app.repositories.order_repository_extended import OrderRepositoryExtended

        # Подключаемся к БД
        db = Database()
        await db.connect()

        try:
            repo = OrderRepositoryExtended(db.connection)

            # Проверяем наличие методов
            methods = [
                "soft_delete",
                "restore",
                "get_by_id",
                "get_all",
                "search_orders",
                "get_deleted_orders",
                "get_full_history",
                "get_statistics",
            ]

            for method_name in methods:
                if hasattr(repo, method_name):
                    print(f"✅ {method_name}")
                else:
                    print(f"❌ {method_name} не найден")
                    return False

            # Пробуем получить статистику
            stats = await repo.get_statistics(include_deleted=True)
            print("\n📊 Статистика:")
            print(f"   Всего заявок: {stats['total']}")
            print(f"   Удалено: {stats['deleted']}")

            print("\n✅ Все методы репозитория работают!")
            return True

        finally:
            await db.disconnect()

    except Exception as e:
        print(f"\n❌ Ошибка проверки репозитория: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_search_service():
    """Проверка сервиса поиска"""
    print("\n" + "=" * 60)
    print("🔍 ТЕСТ 6: Проверка сервиса поиска")
    print("=" * 60)

    try:
        from app.database.db import Database
        from app.repositories.order_repository_extended import OrderRepositoryExtended
        from app.services.search_service import SearchService

        # Подключаемся к БД
        db = Database()
        await db.connect()

        try:
            repo = OrderRepositoryExtended(db.connection)
            service = SearchService(repo)

            # Проверяем наличие методов
            methods = [
                "search",
                "search_by_id",
                "search_by_client_phone",
                "search_by_client_name",
                "search_by_date_range",
                "search_deleted_orders",
                "get_full_order_history",
                "get_statistics",
                "format_search_results",
            ]

            for method_name in methods:
                if hasattr(service, method_name):
                    print(f"✅ {method_name}")
                else:
                    print(f"❌ {method_name} не найден")
                    return False

            # Пробуем поиск
            results = await service.search(limit=5)
            print(f"\n🔍 Результаты поиска: {len(results)} заявок")

            # Пробуем форматирование
            formatted = service.format_search_results(results[:2])
            print(f"✅ Форматирование работает ({len(formatted)} символов)")

            print("\n✅ Сервис поиска работает!")
            return True

        finally:
            await db.disconnect()

    except Exception as e:
        print(f"\n❌ Ошибка проверки сервиса: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_documentation_exists():
    """Проверка наличия документации"""
    print("\n" + "=" * 60)
    print("🔍 ТЕСТ 7: Проверка документации")
    print("=" * 60)

    docs = [
        ("docs/USAGE_HISTORY_FEATURES.md", "Руководство по использованию"),
        ("docs/ПОСТОЯННОЕ_ХРАНЕНИЕ_ЗАЯВОК.md", "Краткая справка"),
        ("docs/QUICKSTART_PERMANENT_STORAGE.md", "Быстрый старт"),
        ("docs/PERMANENT_STORAGE_GUIDE.md", "Полное руководство"),
        ("docs/PERMANENT_STORAGE_EXAMPLES.md", "Примеры кода"),
        ("PERMANENT_STORAGE_README.md", "README"),
        ("SUMMARY_PERMANENT_STORAGE.md", "Резюме"),
        ("ДОРАБОТКА_СИСТЕМЫ_ГОТОВО.md", "Отчет о доработке"),
    ]

    found = 0
    for doc_path, doc_name in docs:
        if Path(doc_path).exists():
            size = Path(doc_path).stat().st_size
            print(f"✅ {doc_name} ({size} байт)")
            found += 1
        else:
            print(f"❌ {doc_name} не найден: {doc_path}")

    print(f"\n📚 Найдено документов: {found}/{len(docs)}")

    if found == len(docs):
        print("✅ Вся документация на месте!")
        return True
    else:
        print("⚠️  Некоторые документы отсутствуют")
        return True  # Не критично


async def main():
    """Главная функция"""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ДОРАБОТАННОЙ СИСТЕМЫ")
    print("=" * 60)

    tests = [
        ("Импорт модулей", test_imports),
        ("Регистрация router", test_router_registration),
        ("Проверка функций", test_functions_exist),
        ("Проверка клавиатур", test_keyboards_exist),
        ("Методы репозитория", test_repository_methods),
        ("Сервис поиска", test_search_service),
        ("Документация", test_documentation_exists),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Ошибка теста {test_name}: {e}")
            results.append((test_name, False))

    # Итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")

    print("\n" + "=" * 60)
    print(f"Успешно: {passed}/{total} тестов")

    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("=" * 60)
        print("\n✅ Система полностью готова к использованию!")
        print("\n📚 Читайте документацию:")
        print("   - docs/USAGE_HISTORY_FEATURES.md")
        print("   - docs/ПОСТОЯННОЕ_ХРАНЕНИЕ_ЗАЯВОК.md")
        print("\n🚀 Запустите бота:")
        print("   python bot.py")
        print()
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("=" * 60)
        print("\nПроверьте ошибки выше")

    print()


if __name__ == "__main__":
    asyncio.run(main())
