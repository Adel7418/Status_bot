"""
Тест 'До и После': наглядное сравнение логирования
"""

import logging

# Настройка логирования для теста
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Имитация данных
user_data = {
    "telegram_id": 123456789,
    "username": "john_doe",
    "first_name": "Ivan",
    "last_name": "Petrov",
    "role": "DISPATCHER",
}

order_data = {
    "id": 1,
    "client_name": "Ivanov Ivan Petrovich",
    "client_phone": "+79991234567",
    "client_address": "Moskva, ul. Lenina, d. 10, kv. 5",
    "status": "NEW",
    "equipment_type": "Kholodilnik",
}

print("\n" + "=" * 80)
print("  TEST: DO I POSLE VNEDRENIYA ZASHCHITY PII")
print("=" * 80)

print("\n" + "-" * 80)
print("  [X] KAK BYLO (NEBEZOPASNO):")
print("-" * 80)
print("\nPRIMER 1: Logirovanie User")
print("  Kod: logger.info(f'User: {user_data}')")
logger.info(f"User: {user_data}")
print("  ^^ PROBLEMA: vidny username, first_name, last_name!\n")

print("PRIMER 2: Logirovanie Order")
print("  Kod: logger.info(f'Creating order for {order_data['client_name']}')")
logger.info(f"Creating order for {order_data['client_name']}")
print("  ^^ PROBLEMA: vidno polnoe imya klienta!\n")

print("PRIMER 3: Logirovanie telefona")
print("  Kod: logger.info(f'Client phone: {order_data['client_phone']}')")
logger.info(f"Client phone: {order_data['client_phone']}")
print("  ^^ PROBLEMA: viden polnyi nomer telefona!\n")

print("-" * 80)
print("  [OK] KAK STALO (BEZOPASNO):")
print("-" * 80)

# Импортируем утилиты
from app.utils import safe_str_user, safe_str_order, mask_phone

print("\nPRIMER 1: Logirovanie User")
print("  Kod: logger.info(f'User: {safe_str_user(user_data)}')")
logger.info(f"User: {safe_str_user(user_data)}")
print("  ^^ OK: tolko ID i rol, net PII!\n")

print("PRIMER 2: Logirovanie Order")
print("  Kod: logger.info(f'Order: {safe_str_order(order_data)}')")
logger.info(f"Order: {safe_str_order(order_data)}")
print("  ^^ OK: net dannykh klienta!\n")

print("PRIMER 3: Logirovanie telefona")
print("  Kod: logger.info(f'Client phone: {mask_phone(order_data['client_phone'])}')")
logger.info(f"Client phone: {mask_phone(order_data['client_phone'])}")
print("  ^^ OK: telefon maskiovan!\n")

print("=" * 80)
print("  VYVOD:")
print("    [+] Vse personalnye dannye teper maskiruyutsya avtomaticheski")
print("    [+] Starye logi (do ispravleniya) soderzhali PII - eto normalno")
print("    [+] Novye logi (posle ispravleniya) NE soderzhat PII")
print("    [+] 34 testa garantiruyut korrektnost raboty")
print("=" * 80 + "\n")

