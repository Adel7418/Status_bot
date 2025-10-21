"""
Скрипт для проверки работы шифрования данных
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from app.utils.encryption import DataEncryptor, encrypt, decrypt, is_encrypted


def print_section(title: str):
    """Печать заголовка секции"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_encryption_basic():
    """Базовый тест шифрования"""
    print_section("БАЗОВЫЙ ТЕСТ ШИФРОВАНИЯ")

    # Тестовые данные
    test_data = [
        ("Тестовый текст", "Обычная строка"),
        ("+79991234567", "Номер телефона"),
        ("Иванов Иван Иванович", "ФИО"),
        ("test@example.com", "Email"),
        ("Москва, ул. Ленина, д. 1", "Адрес"),
    ]

    for original, description in test_data:
        print(f"\n[TEST] {description}")
        print(f"   Исходные данные: {original}")

        # Шифруем
        encrypted = encrypt(original)
        print(f"   Зашифровано: {encrypted[:50]}..." if encrypted and len(encrypted) > 50 else f"   Зашифровано: {encrypted}")

        # Дешифруем
        decrypted = decrypt(encrypted)
        print(f"   Расшифровано: {decrypted}")

        # Проверяем
        if original == decrypted:
            print("   [OK] УСПЕШНО: Данные совпадают")
        else:
            print("   [FAIL] ОШИБКА: Данные не совпадают!")
            return False

    return True


def test_encryption_edge_cases():
    """Тест граничных случаев"""
    print_section("ТЕСТ ГРАНИЧНЫХ СЛУЧАЕВ")

    test_cases = [
        (None, "None"),
        ("", "Пустая строка"),
        ("   ", "Пробелы"),
        ("Спецсимволы: !@#$%^&*()", "Спецсимволы"),
    ]

    for data, description in test_cases:
        print(f"\n[TEST] {description}")
        print(f"   Данные: {repr(data)}")

        encrypted = encrypt(data)
        decrypted = decrypt(encrypted)

        print(f"   Зашифровано: {repr(encrypted)}")
        print(f"   Расшифровано: {repr(decrypted)}")

        if data == decrypted:
            print("   [OK] УСПЕШНО")
        else:
            print("   [FAIL] ОШИБКА")
            return False

    return True


def test_encryption_detection():
    """Тест определения зашифрованных данных"""
    print_section("ТЕСТ ОПРЕДЕЛЕНИЯ ЗАШИФРОВАННЫХ ДАННЫХ")

    # Обычный текст
    plain_text = "Обычный текст"
    print(f"\n[TEST] Проверка обычного текста: '{plain_text}'")
    print(f"   is_encrypted: {is_encrypted(plain_text)}")
    print(f"   [OK] УСПЕШНО" if not is_encrypted(plain_text) else "   [FAIL] ОШИБКА")

    # Зашифрованный текст
    encrypted_text = encrypt("Зашифрованный текст")
    print(f"\n[TEST] Проверка зашифрованного текста")
    print(f"   Зашифровано: {encrypted_text[:50]}..." if encrypted_text and len(encrypted_text) > 50 else f"   Зашифровано: {encrypted_text}")
    print(f"   is_encrypted: {is_encrypted(encrypted_text)}")
    print(f"   [OK] УСПЕШНО" if is_encrypted(encrypted_text) else "   [FAIL] ОШИБКА")


def test_encryption_key():
    """Проверка наличия ключа шифрования"""
    print_section("ПРОВЕРКА КЛЮЧА ШИФРОВАНИЯ")

    encryption_key = os.getenv("ENCRYPTION_KEY")

    if encryption_key:
        print(f"[OK] ENCRYPTION_KEY найден в переменных окружения")
        print(f"   Длина ключа: {len(encryption_key)} символов")
        print(f"   Первые 10 символов: {encryption_key[:10]}...")
    else:
        print("[WARNING] ENCRYPTION_KEY НЕ НАЙДЕН в переменных окружения!")
        print("   Будет сгенерирован временный ключ")
        print("   [WARNING] ДЛЯ PRODUCTION НЕОБХОДИМО ДОБАВИТЬ ENCRYPTION_KEY!")

    return True


def test_multiple_instances():
    """Тест множественных экземпляров (singleton)"""
    print_section("ТЕСТ SINGLETON ПАТТЕРНА")

    encryptor1 = DataEncryptor()
    encryptor2 = DataEncryptor()

    test_text = "Тестовое сообщение"

    # Шифруем первым экземпляром
    encrypted1 = encryptor1.encrypt(test_text)
    print(f"[TEST] Зашифровано первым экземпляром: {encrypted1[:50]}...")

    # Дешифруем вторым экземпляром
    decrypted2 = encryptor2.decrypt(encrypted1)
    print(f"[TEST] Расшифровано вторым экземпляром: {decrypted2}")

    if test_text == decrypted2:
        print("[OK] УСПЕШНО: Экземпляры используют один ключ")
        return True
    else:
        print("[FAIL] ОШИБКА: Разные ключи у экземпляров!")
        return False


def generate_encryption_key():
    """Генерация нового ключа шифрования"""
    print_section("ГЕНЕРАЦИЯ НОВОГО КЛЮЧА")

    from cryptography.fernet import Fernet

    new_key = Fernet.generate_key()
    print("\n>>> Новый ключ шифрования:")
    print(f"   {new_key.decode()}")
    print("\n>>> Добавьте в .env файл:")
    print(f"   ENCRYPTION_KEY={new_key.decode()}")


def main():
    """Главная функция"""
    print("\n" + "=" * 60)
    print("  ТЕСТИРОВАНИЕ ШИФРОВАНИЯ ДАННЫХ")
    print("=" * 60)

    # Загрузка переменных окружения
    load_dotenv()

    results = []

    # Проверка ключа
    results.append(("Проверка ключа", test_encryption_key()))

    # Базовый тест
    results.append(("Базовое шифрование", test_encryption_basic()))

    # Граничные случаи
    results.append(("Граничные случаи", test_encryption_edge_cases()))

    # Определение зашифрованных данных
    test_encryption_detection()

    # Тест множественных экземпляров
    results.append(("Singleton паттерн", test_multiple_instances()))

    # Генерация ключа если нужно
    if not os.getenv("ENCRYPTION_KEY"):
        generate_encryption_key()

    # Итоги
    print_section("ИТОГИ ТЕСТИРОВАНИЯ")

    for test_name, result in results:
        status = "[PASSED]" if result else "[FAILED]"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n*** ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО! ***")
    else:
        print("\n*** НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ! ***")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
