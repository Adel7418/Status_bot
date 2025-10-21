#!/usr/bin/env python3
"""
Парсинг экспортированного JSON из Telegram для восстановления заявок
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Database


def parse_order_confirmation(text: str) -> dict | None:
    """
    Парсинг сообщения подтверждения заявки

    Формат:
    📋 Проверьте данные заявки:

    🔧 Тип техники: Стиральные машины
    📝 Описание: Не работает

    👤 Клиент: Калинов Ильдар генадьевич
    📍 Адрес: Пр победы 27 28
    📞 Телефон: +79872242323

    📝 Заметки: К 10:00
    """
    if "Проверьте данные заявки:" not in text:
        return None

    order = {}

    # Тип техники
    match = re.search(r"🔧\s*Тип техники:\s*(.+?)(?:\n|$)", text)
    if match:
        order["equipment_type"] = match.group(1).strip()

    # Описание
    match = re.search(r"📝\s*Описание:\s*(.+?)(?:\n|$)", text)
    if match:
        order["description"] = match.group(1).strip()

    # Клиент
    match = re.search(r"👤\s*Клиент:\s*(.+?)(?:\n|$)", text)
    if match:
        order["client_name"] = match.group(1).strip()

    # Адрес
    match = re.search(r"📍\s*Адрес:\s*(.+?)(?:\n|$)", text)
    if match:
        order["client_address"] = match.group(1).strip()

    # Телефон
    match = re.search(r"📞\s*Телефон:\s*(.+?)(?:\n|$)", text)
    if match:
        phone = match.group(1).strip()
        # Очистка от лишних символов
        phone = re.sub(r'[^\d+]', '', phone)
        if not phone.startswith('+'):
            phone = '+' + phone
        order["client_phone"] = phone

    # Заметки
    match = re.search(r"📝\s*Заметки:\s*(.+?)(?:\n|$)", text)
    if match:
        order["notes"] = match.group(1).strip()
    else:
        order["notes"] = ""

    # Проверяем, что все обязательные поля есть
    required = ["equipment_type", "description", "client_name", "client_address", "client_phone"]
    if all(field in order for field in required):
        return order

    return None


def extract_order_number(text: str) -> int | None:
    """Извлечение номера заявки из текста"""
    match = re.search(r"Заявка\s*#(\d+)", text)
    if match:
        return int(match.group(1))
    return None


async def parse_and_restore(json_file: str, dispatcher_id: int, start_from: int = 1):
    """
    Парсинг JSON файла и восстановление заявок

    Args:
        json_file: Путь к result.json
        dispatcher_id: Telegram ID диспетчера (кто создавал заявки)
        start_from: Восстанавливать только заявки с номером >= этого значения
    """
    print("=" * 80)
    print("ПАРСИНГ ЭКСПОРТА TELEGRAM И ВОССТАНОВЛЕНИЕ ЗАЯВОК")
    print("=" * 80)
    print()

    # Читаем JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data.get("messages", [])
    print(f"Всего сообщений в экспорте: {len(messages)}")
    print()

    # Ищем подтверждения заявок
    orders_to_restore = []
    restored_order_numbers = set()

    for i, msg in enumerate(messages):
        # Собираем текст из всех частей
        text_parts = msg.get("text", "")
        if isinstance(text_parts, list):
            text = ""
            for part in text_parts:
                if isinstance(part, str):
                    text += part
                elif isinstance(part, dict) and "text" in part:
                    text += part["text"]
        else:
            text = str(text_parts)

        # Парсим подтверждение заявки
        order_data = parse_order_confirmation(text)
        if order_data:
            # Дата создания
            date_str = msg.get("date", "")
            try:
                created_at = datetime.fromisoformat(date_str.replace('T', ' '))
                order_data["created_at"] = created_at.strftime("%Y-%m-%d %H:%M:%S")
            except:
                order_data["created_at"] = None

            # Ищем номер заявки в следующих сообщениях
            order_number = None
            for next_msg in messages[i+1:i+5]:  # Смотрим следующие 5 сообщений
                next_text_parts = next_msg.get("text", "")
                if isinstance(next_text_parts, list):
                    next_text = ""
                    for part in next_text_parts:
                        if isinstance(part, str):
                            next_text += part
                        elif isinstance(part, dict) and "text" in part:
                            next_text += part["text"]
                else:
                    next_text = str(next_text_parts)

                num = extract_order_number(next_text)
                if num:
                    order_number = num
                    break

            if order_number and order_number not in restored_order_numbers:
                # Фильтруем по номеру заявки
                if order_number >= start_from:
                    order_data["order_number"] = order_number
                    orders_to_restore.append(order_data)
                    restored_order_numbers.add(order_number)

    print(f"Найдено заявок для восстановления (>= #{start_from}): {len(orders_to_restore)}")
    print()

    if not orders_to_restore:
        print("Не найдено заявок в экспорте.")
        return

    # Показываем найденные заявки
    print("Найденные заявки:")
    print("-" * 80)
    for order in orders_to_restore:
        print(f"\n#{order.get('order_number', '?')} - {order['equipment_type']}")
        print(f"   Клиент: {order['client_name']}")
        print(f"   Адрес: {order['client_address']}")
        print(f"   Телефон: {order['client_phone']}")
        if order.get('created_at'):
            print(f"   Дата: {order['created_at']}")
    print()

    # Спрашиваем подтверждение
    answer = input("Восстановить эти заявки в базу данных? (yes/no): ")
    if answer.lower() not in ['yes', 'y', 'да', 'д']:
        print("Отменено.")
        return

    # Восстанавливаем заявки
    db = Database()
    await db.connect()

    try:
        restored_count = 0
        for order in orders_to_restore:
            try:
                new_order = await db.create_order(
                    equipment_type=order["equipment_type"],
                    description=order["description"],
                    client_name=order["client_name"],
                    client_address=order["client_address"],
                    client_phone=order["client_phone"],
                    dispatcher_id=dispatcher_id,
                    notes=order.get("notes", ""),
                )

                # Обновляем дату создания, если она есть
                if order.get("created_at"):
                    await db.connection.execute(
                        "UPDATE orders SET created_at = ? WHERE id = ?",
                        (order["created_at"], new_order.id),
                    )
                    await db.connection.commit()

                print(f"OK: Восстановлена заявка #{new_order.id} (было #{order.get('order_number', '?')})")
                restored_count += 1

            except Exception as e:
                print(f"ERROR: Ошибка при восстановлении заявки #{order.get('order_number', '?')}: {e}")

        print()
        print(f"Восстановлено заявок: {restored_count}/{len(orders_to_restore)}")

    finally:
        await db.disconnect()

    print()
    print("=" * 80)
    print("ВОССТАНОВЛЕНИЕ ЗАВЕРШЕНО")
    print("=" * 80)


async def main():
    """Основная функция"""
    import sys

    if len(sys.argv) < 3:
        print("Использование:")
        print(f"  python {sys.argv[0]} <путь_к_result.json> <dispatcher_telegram_id> [start_from]")
        print()
        print("Примеры:")
        print(f"  # Восстановить все заявки:")
        print(f"  python {sys.argv[0]} docs/history_telegram/ChatExport_2025-10-21/result.json 5765136457")
        print()
        print(f"  # Восстановить только заявки >= #45:")
        print(f"  python {sys.argv[0]} docs/history_telegram/ChatExport_2025-10-21/result.json 5765136457 45")
        return

    json_file = sys.argv[1]
    dispatcher_id = int(sys.argv[2])
    start_from = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    if not Path(json_file).exists():
        print(f"ERROR: Файл не найден: {json_file}")
        return

    await parse_and_restore(json_file, dispatcher_id, start_from)


if __name__ == "__main__":
    asyncio.run(main())

