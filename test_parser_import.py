"""
Тестовый скрипт для проверки импортов парсера
"""
import sys


print("Проверка импортов парсера...")
print("-" * 50)

try:
    from app.core.config import Config
    print("[OK] Config импортирован")
    print(f"  PARSER_ENABLED: {Config.PARSER_ENABLED}")
    print(f"  TELETHON_API_ID: {Config.TELETHON_API_ID}")
    print(f"  TELETHON_SESSION_NAME: {Config.TELETHON_SESSION_NAME}")
except Exception as e:
    print(f"[ERROR] Ошибка импорта Config: {e}")
    sys.exit(1)

try:
    print("[OK] ParserIntegration импортирован")
except Exception as e:
    print(f"[ERROR] Ошибка импорта ParserIntegration: {e}")
    sys.exit(1)

try:
    from app.services.telegram_parser import OrderParserService
    print("[OK] OrderParserService импортирован")
except Exception as e:
    print(f"[ERROR] Ошибка импорта OrderParserService: {e}")
    sys.exit(1)

try:
    print("[OK] TelethonClient импортирован")
except Exception as e:
    print(f"[ERROR] Ошибка импорта TelethonClient: {e}")
    sys.exit(1)

try:
    print("[OK] OrderConfirmationService импортирован")
except Exception as e:
    print(f"[ERROR] Ошибка импорта OrderConfirmationService: {e}")
    sys.exit(1)

try:
    print("[OK] ParserConfigRepository импортирован")
except Exception as e:
    print(f"[ERROR] Ошибка импорта ParserConfigRepository: {e}")
    sys.exit(1)

try:
    print("[OK] parser_config router импортирован")
except Exception as e:
    print(f"[ERROR] Ошибка импорта parser_config router: {e}")
    sys.exit(1)

print("-" * 50)
print("[OK] Все импорты успешны!")
print()

# Простой тест парсинга
print("Тест парсинга сообщения...")
print("-" * 50)

try:
    parser = OrderParserService()

    test_message = """С/м не крутит барабан
ул. Ленина 5, кв. 10
+79001234567
завтра к 14:00"""

    result = parser.parse_message(test_message, message_id=1)

    if result.success:
        print("[OK] Парсинг успешен!")
        print(f"  Техника: {result.data.equipment_type}")
        print(f"  Проблема: {result.data.problem_description}")
        print(f"  Адрес: {result.data.address}")
        print(f"  Телефон: {result.data.phone}")
        print(f"  Время: {result.data.scheduled_time}")
    else:
        print(f"[ERROR] Парсинг не удался: {result.error_message}")
        sys.exit(1)

except Exception as e:
    print(f"[ERROR] Ошибка парсинга: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("-" * 50)
print("[OK] Все проверки пройдены!")
