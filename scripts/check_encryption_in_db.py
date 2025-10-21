"""
Скрипт для проверки шифрования данных в базе данных
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from app.database import Database
from app.utils.encryption import is_encrypted, decrypt


def print_section(title: str):
    """Печать заголовка секции"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def check_orders_encryption():
    """Проверка шифрования данных в таблице orders"""
    print_section("ПРОВЕРКА ШИФРОВАНИЯ В ТАБЛИЦЕ ORDERS")

    db = Database()
    await db.connect()

    try:
        cursor = await db.connection.execute(
            "SELECT id, phone, client_name, address FROM orders LIMIT 20"
        )
        rows = await cursor.fetchall()

        if not rows:
            print("⚠️  В таблице orders нет данных")
            return

        stats = {
            'total': 0,
            'phone_encrypted': 0,
            'name_encrypted': 0,
            'address_encrypted': 0,
            'phone_total': 0,
            'name_total': 0,
            'address_total': 0,
        }

        print(f"\nНайдено заявок: {len(rows)}")
        print("-" * 70)

        for row in rows:
            order_id = row['id']
            phone = row['phone']
            client_name = row['client_name']
            address = row['address']

            stats['total'] += 1

            print(f"\n📋 Заявка #{order_id}:")

            # Проверка телефона
            if phone:
                stats['phone_total'] += 1
                phone_enc = is_encrypted(phone)
                stats['phone_encrypted'] += 1 if phone_enc else 0

                if phone_enc:
                    decrypted = decrypt(phone)
                    print(f"  📱 Телефон: 🔐 Зашифрован (расшифровано: {decrypted})")
                else:
                    print(f"  📱 Телефон: ⚠️  Не зашифрован ({phone})")
            else:
                print(f"  📱 Телефон: (отсутствует)")

            # Проверка имени
            if client_name:
                stats['name_total'] += 1
                name_enc = is_encrypted(client_name)
                stats['name_encrypted'] += 1 if name_enc else 0

                if name_enc:
                    decrypted = decrypt(client_name)
                    print(f"  👤 Имя: 🔐 Зашифровано (расшифровано: {decrypted})")
                else:
                    print(f"  👤 Имя: ⚠️  Не зашифровано ({client_name})")
            else:
                print(f"  👤 Имя: (отсутствует)")

            # Проверка адреса
            if address:
                stats['address_total'] += 1
                addr_enc = is_encrypted(address)
                stats['address_encrypted'] += 1 if addr_enc else 0

                if addr_enc:
                    decrypted = decrypt(address)
                    print(f"  📍 Адрес: 🔐 Зашифрован (расшифровано: {decrypted[:30]}...)")
                else:
                    print(f"  📍 Адрес: ⚠️  Не зашифрован ({address[:30]}...)")
            else:
                print(f"  📍 Адрес: (отсутствует)")

        # Статистика
        print_section("СТАТИСТИКА ШИФРОВАНИЯ")

        print(f"\n📊 Всего заявок: {stats['total']}")

        if stats['phone_total'] > 0:
            phone_percent = (stats['phone_encrypted'] / stats['phone_total']) * 100
            print(f"\n📱 Телефоны:")
            print(f"   Всего: {stats['phone_total']}")
            print(f"   Зашифровано: {stats['phone_encrypted']} ({phone_percent:.1f}%)")
            print(f"   Не зашифровано: {stats['phone_total'] - stats['phone_encrypted']}")

        if stats['name_total'] > 0:
            name_percent = (stats['name_encrypted'] / stats['name_total']) * 100
            print(f"\n👤 Имена:")
            print(f"   Всего: {stats['name_total']}")
            print(f"   Зашифровано: {stats['name_encrypted']} ({name_percent:.1f}%)")
            print(f"   Не зашифровано: {stats['name_total'] - stats['name_encrypted']}")

        if stats['address_total'] > 0:
            addr_percent = (stats['address_encrypted'] / stats['address_total']) * 100
            print(f"\n📍 Адреса:")
            print(f"   Всего: {stats['address_total']}")
            print(f"   Зашифровано: {stats['address_encrypted']} ({addr_percent:.1f}%)")
            print(f"   Не зашифровано: {stats['address_total'] - stats['address_encrypted']}")

        # Рекомендации
        total_fields = stats['phone_total'] + stats['name_total'] + stats['address_total']
        total_encrypted = stats['phone_encrypted'] + stats['name_encrypted'] + stats['address_encrypted']

        if total_fields > 0:
            overall_percent = (total_encrypted / total_fields) * 100
            print(f"\n📈 Общий процент шифрования: {overall_percent:.1f}%")

            if overall_percent < 100:
                print("\n⚠️  РЕКОМЕНДАЦИИ:")
                print("   Не все данные зашифрованы!")
                print("   Запустите миграцию для шифрования существующих данных.")
                print("   См. docs/ENCRYPTION_GUIDE.md раздел 'Миграция существующих данных'")
            else:
                print("\n✅ Все персональные данные зашифрованы!")

    finally:
        await db.disconnect()


async def check_users_encryption():
    """Проверка шифрования данных в таблице users"""
    print_section("ПРОВЕРКА ШИФРОВАНИЯ В ТАБЛИЦЕ USERS")

    db = Database()
    await db.connect()

    try:
        cursor = await db.connection.execute(
            "SELECT id, username, first_name, last_name FROM users LIMIT 10"
        )
        rows = await cursor.fetchall()

        if not rows:
            print("⚠️  В таблице users нет данных")
            return

        print(f"\nНайдено пользователей: {len(rows)}")
        print("-" * 70)

        for row in rows:
            user_id = row['id']
            username = row['username']
            first_name = row['first_name']
            last_name = row['last_name']

            print(f"\n👤 Пользователь #{user_id}:")
            print(f"   Username: {username if username else '(нет)'}")

            # Имя обычно не шифруется, т.к. это публичная информация из Telegram
            print(f"   Имя: {first_name if first_name else '(нет)'}")
            print(f"   Фамилия: {last_name if last_name else '(нет)'}")

        print("\nℹ️  Примечание: Данные пользователей из Telegram обычно не шифруются,")
        print("   т.к. это публичная информация. Шифруются только чувствительные данные")
        print("   клиентов в заявках (телефоны, адреса).")

    finally:
        await db.disconnect()


async def test_encryption_roundtrip():
    """Тест полного цикла шифрования/дешифрования с БД"""
    print_section("ТЕСТ ПОЛНОГО ЦИКЛА ШИФРОВАНИЯ С БД")

    from app.utils.encryption import encrypt, decrypt

    # Тестовые данные
    test_phone = "+79991234567"
    test_name = "Тестов Тест Тестович"
    test_address = "г. Москва, ул. Тестовая, д. 123"

    print("\n📝 Тестовые данные:")
    print(f"   Телефон: {test_phone}")
    print(f"   Имя: {test_name}")
    print(f"   Адрес: {test_address}")

    # Шифруем
    encrypted_phone = encrypt(test_phone)
    encrypted_name = encrypt(test_name)
    encrypted_address = encrypt(test_address)

    print("\n🔐 Зашифрованные данные:")
    print(f"   Телефон: {encrypted_phone[:50]}...")
    print(f"   Имя: {encrypted_name[:50]}...")
    print(f"   Адрес: {encrypted_address[:50]}...")

    # Сохраняем в БД
    db = Database()
    await db.connect()

    try:
        # Используем транзакцию для безопасности
        cursor = await db.connection.execute(
            """
            INSERT INTO orders (
                phone, client_name, address,
                description, equipment_type, status,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                encrypted_phone,
                encrypted_name,
                encrypted_address,
                "Тестовая заявка для проверки шифрования",
                "Тестовое оборудование",
                "new",
            )
        )
        await db.connection.commit()
        order_id = cursor.lastrowid

        print(f"\n💾 Данные сохранены в БД (заявка #{order_id})")

        # Читаем из БД
        cursor = await db.connection.execute(
            "SELECT phone, client_name, address FROM orders WHERE id = ?",
            (order_id,)
        )
        row = await cursor.fetchone()

        # Дешифруем
        decrypted_phone = decrypt(row['phone'])
        decrypted_name = decrypt(row['client_name'])
        decrypted_address = decrypt(row['address'])

        print(f"\n🔓 Расшифрованные данные из БД:")
        print(f"   Телефон: {decrypted_phone}")
        print(f"   Имя: {decrypted_name}")
        print(f"   Адрес: {decrypted_address}")

        # Проверяем совпадение
        success = (
            test_phone == decrypted_phone
            and test_name == decrypted_name
            and test_address == decrypted_address
        )

        if success:
            print("\n✅ ТЕСТ ПРОЙДЕН: Все данные корректно зашифрованы и расшифрованы!")
        else:
            print("\n❌ ТЕСТ НЕ ПРОЙДЕН: Данные не совпадают!")

        # Удаляем тестовую заявку
        await db.connection.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        await db.connection.commit()
        print(f"\n🗑️  Тестовая заявка #{order_id} удалена")

        return success

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        return False

    finally:
        await db.disconnect()


async def main():
    """Главная функция"""
    print("\n" + "🔐" * 35)
    print("  ПРОВЕРКА ШИФРОВАНИЯ ДАННЫХ В БАЗЕ ДАННЫХ")
    print("🔐" * 35)

    # Загрузка переменных окружения
    load_dotenv()

    try:
        # Проверка существующих данных
        await check_orders_encryption()
        await check_users_encryption()

        # Тест полного цикла
        test_result = await test_encryption_roundtrip()

        # Итоги
        print_section("ИТОГИ")

        if test_result:
            print("\n✅ Шифрование работает корректно!")
            print("✅ Полный цикл шифрования/дешифрования с БД работает!")
        else:
            print("\n⚠️  Обнаружены проблемы с шифрованием!")
            print("   Проверьте логи выше для деталей.")

        print("\n📚 Для получения дополнительной информации см.:")
        print("   docs/ENCRYPTION_GUIDE.md")

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
