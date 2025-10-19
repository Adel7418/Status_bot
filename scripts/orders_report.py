#!/usr/bin/env python3
"""
Полный отчет по заказам и мастерам
Включает информацию о выездах, отзывах, финансовых данных
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def get_orders_report(db_path: str):
    """Генерирует полный отчет по заказам"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 80)
    print("ПОЛНЫЙ ОТЧЕТ ПО ЗАКАЗАМ И МАСТЕРАМ")
    print("=" * 80)
    print(f"База данных: {db_path}")
    print(f"Дата отчета: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print()

    # Общая статистика
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'CLOSED'")
    closed_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM masters")
    total_masters = cursor.fetchone()[0]

    print("ОБЩАЯ СТАТИСТИКА:")
    print(f"Всего заказов: {total_orders}")
    print(f"Завершенных заказов: {closed_orders}")
    print(f"Всего мастеров: {total_masters}")
    print()

    # Заказы с выездами за город
    cursor.execute(
        """
        SELECT o.id, o.equipment_type, o.client_name, o.client_address,
               o.status, o.out_of_city, o.has_review, o.total_amount,
               o.materials_cost, o.master_profit, o.company_profit,
               o.created_at, o.updated_at,
               u_master.first_name || ' ' || u_master.last_name as master_name,
               u_dispatcher.first_name || ' ' || u_dispatcher.last_name as dispatcher_name
        FROM orders o
        LEFT JOIN masters m ON o.assigned_master_id = m.id
        LEFT JOIN users u_master ON m.telegram_id = u_master.telegram_id
        LEFT JOIN users u_dispatcher ON o.dispatcher_id = u_dispatcher.telegram_id
        WHERE o.out_of_city = 1 OR o.out_of_city IS NOT NULL
        ORDER BY o.id DESC
    """
    )

    out_of_city_orders = cursor.fetchall()

    print("ЗАКАЗЫ С ВЫЕЗДАМИ ЗА ГОРОД:")
    print("-" * 80)
    if out_of_city_orders:
        for order in out_of_city_orders:
            print(f"Заказ #{order[0]}: {order[1]} | Клиент: {order[2]}")
            print(f"  Адрес: {order[3]}")
            print(f"  Статус: {order[4]}")
            print(
                f"  Выезд за город: {'Да' if order[5] == 1 else 'Нет' if order[5] == 0 else 'Не указано'}"
            )
            print(
                f"  Отзыв: {'Есть' if order[6] == 1 else 'Нет' if order[6] == 0 else 'Не указано'}"
            )
            print(f"  Сумма: {order[7]:.2f} руб | Материалы: {order[8]:.2f} руб")
            print(f"  Прибыль мастера: {order[9]:.2f} руб | Прибыль компании: {order[10]:.2f} руб")
            print(f"  Мастер: {order[13] or 'Не назначен'}")
            print(f"  Диспетчер: {order[14] or 'Не указан'}")
            print(f"  Создан: {order[11]}")
            print(f"  Обновлен: {order[12]}")
            print()
    else:
        print("Заказы с выездами не найдены")
    print()

    # Все завершенные заказы
    cursor.execute(
        """
        SELECT o.id, o.equipment_type, o.client_name, o.client_address,
               o.status, o.out_of_city, o.has_review, o.total_amount,
               o.materials_cost, o.master_profit, o.company_profit,
               o.created_at, o.updated_at,
               u_master.first_name || ' ' || u_master.last_name as master_name,
               u_dispatcher.first_name || ' ' || u_dispatcher.last_name as dispatcher_name
        FROM orders o
        LEFT JOIN masters m ON o.assigned_master_id = m.id
        LEFT JOIN users u_master ON m.telegram_id = u_master.telegram_id
        LEFT JOIN users u_dispatcher ON o.dispatcher_id = u_dispatcher.telegram_id
        WHERE o.status = 'CLOSED'
        ORDER BY o.id DESC
    """
    )

    closed_orders_data = cursor.fetchall()

    print("ВСЕ ЗАВЕРШЕННЫЕ ЗАКАЗЫ:")
    print("-" * 80)
    if closed_orders_data:
        for order in closed_orders_data:
            print(f"Заказ #{order[0]}: {order[1]} | Клиент: {order[2]}")
            print(f"  Адрес: {order[3]}")
            print(
                f"  Выезд за город: {'Да' if order[5] == 1 else 'Нет' if order[5] == 0 else 'Не указано'}"
            )
            print(
                f"  Отзыв: {'Есть' if order[6] == 1 else 'Нет' if order[6] == 0 else 'Не указано'}"
            )
            print(f"  Сумма: {order[7]:.2f} руб | Материалы: {order[8]:.2f} руб")
            print(f"  Прибыль мастера: {order[9]:.2f} руб | Прибыль компании: {order[10]:.2f} руб")
            print(f"  Мастер: {order[13] or 'Не назначен'}")
            print(f"  Диспетчер: {order[14] or 'Не указан'}")
            print(f"  Создан: {order[11]}")
            print()
    else:
        print("Завершенные заказы не найдены")
    print()

    # Статистика по мастерам
    cursor.execute(
        """
        SELECT m.id, u.first_name || ' ' || u.last_name as master_name,
               COUNT(o.id) as orders_count,
               SUM(CASE WHEN o.status = 'CLOSED' THEN 1 ELSE 0 END) as closed_orders,
               SUM(CASE WHEN o.out_of_city = 1 THEN 1 ELSE 0 END) as out_of_city_count,
               SUM(CASE WHEN o.has_review = 1 THEN 1 ELSE 0 END) as reviews_count,
               SUM(CASE WHEN o.status = 'CLOSED' THEN o.master_profit ELSE 0 END) as total_profit,
               AVG(CASE WHEN o.status = 'CLOSED' THEN o.total_amount ELSE NULL END) as avg_order_amount
        FROM masters m
        LEFT JOIN users u ON m.telegram_id = u.telegram_id
        LEFT JOIN orders o ON m.id = o.assigned_master_id
        GROUP BY m.id, u.first_name, u.last_name
        ORDER BY total_profit DESC
    """
    )

    masters_stats = cursor.fetchall()

    print("СТАТИСТИКА ПО МАСТЕРАМ:")
    print("-" * 80)
    if masters_stats:
        for master in masters_stats:
            print(f"Мастер: {master[1]} (ID: {master[0]})")
            print(f"  Всего заказов: {master[2]}")
            print(f"  Завершенных: {master[3]}")
            print(f"  Выездов за город: {master[4]}")
            print(f"  Отзывов: {master[5]}")
            print(f"  Общая прибыль: {master[6]:.2f} руб")
            print(f"  Средний чек: {master[7]:.2f} руб" if master[7] else "  Средний чек: N/A")
            print()
    else:
        print("Мастера не найдены")
    print()

    # Проблемные заказы (с некорректными данными)
    cursor.execute(
        """
        SELECT id, equipment_type, client_name, status, out_of_city, has_review,
               total_amount, materials_cost, master_profit, company_profit
        FROM orders
        WHERE (out_of_city IS NOT NULL AND out_of_city != 0 AND out_of_city != 1)
           OR (has_review IS NOT NULL AND has_review != 0 AND has_review != 1)
        ORDER BY id DESC
    """
    )

    problematic_orders = cursor.fetchall()

    if problematic_orders:
        print("ПРОБЛЕМНЫЕ ЗАКАЗЫ (с некорректными данными):")
        print("-" * 80)
        for order in problematic_orders:
            print(f"Заказ #{order[0]}: {order[1]} | Клиент: {order[2]}")
            print(f"  Статус: {order[3]}")
            print(f"  out_of_city: {order[4]} (тип: {type(order[4])})")
            print(f"  has_review: {order[5]} (тип: {type(order[5])})")
            print(f"  Суммы: {order[6]}, {order[7]}, {order[8]}, {order[9]}")
            print()

    conn.close()


def main():
    """Основная функция"""
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # По умолчанию используем dev базу
        db_path = "bot_database_dev.db"

    if not Path(db_path).exists():
        print(f"ОШИБКА: База данных {db_path} не найдена!")
        return

    try:
        get_orders_report(db_path)
    except Exception as e:
        print(f"ОШИБКА при генерации отчета: {e}")


if __name__ == "__main__":
    main()
