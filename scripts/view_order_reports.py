#!/usr/bin/env python3
"""
Скрипт для просмотра отчетов по заказам
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def view_order_reports(db_path: str, start_date: str = None, end_date: str = None):
    """Просматривает отчеты по заказам"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 100)
    print("ОТЧЕТЫ ПО ЗАКАЗАМ")
    print("=" * 100)
    print(f"База данных: {db_path}")
    print(f"Дата отчета: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print()

    # Строим запрос
    query = "SELECT * FROM order_reports WHERE 1=1"
    params = []

    if start_date:
        query += " AND DATE(closed_at) >= ?"
        params.append(start_date)

    if end_date:
        query += " AND DATE(closed_at) <= ?"
        params.append(end_date)

    query += " ORDER BY closed_at DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        print("Отчеты не найдены")
        conn.close()
        return

    print(f"Найдено отчетов: {len(rows)}")
    print()

    # Заголовки
    print(
        f"{'ID':<4} {'Заказ':<6} {'Техника':<20} {'Клиент':<20} {'Мастер':<20} {'Сумма':<10} {'Мастер':<10} {'Компания':<10} {'Выезд':<6} {'Отзыв':<6} {'Время':<8}"
    )
    print("-" * 140)

    total_amount = 0
    total_master_profit = 0
    total_company_profit = 0
    out_of_city_count = 0
    review_count = 0

    for row in rows:
        order_id = row[1]
        equipment = row[2][:18] + ".." if len(row[2]) > 20 else row[2]
        client = row[3][:18] + ".." if len(row[3]) > 20 else row[3]
        master = row[6][:18] + ".." if row[6] and len(row[6]) > 20 else (row[6] or "N/A")
        amount = row[9]
        master_profit = row[11]
        company_profit = row[12]
        out_of_city = "Да" if row[13] == 1 else "Нет"
        has_review = "Да" if row[14] == 1 else "Нет"
        completion_time = f"{row[17]:.1f}ч" if row[17] else "N/A"

        print(
            f"{row[0]:<4} #{order_id:<5} {equipment:<20} {client:<20} {master:<20} {amount:<10.2f} {master_profit:<10.2f} {company_profit:<10.2f} {out_of_city:<6} {has_review:<6} {completion_time:<8}"
        )

        # Подсчет статистики
        total_amount += amount
        total_master_profit += master_profit
        total_company_profit += company_profit
        if row[13] == 1:
            out_of_city_count += 1
        if row[14] == 1:
            review_count += 1

    print("-" * 140)
    print(
        f"{'ИТОГО:':<4} {'':<5} {'':<20} {'':<20} {'':<20} {total_amount:<10.2f} {total_master_profit:<10.2f} {total_company_profit:<10.2f} {out_of_city_count:<6} {review_count:<6} {'':<8}"
    )

    print()
    print("СТАТИСТИКА:")
    print(f"Всего заказов: {len(rows)}")
    print(f"Общая сумма: {total_amount:.2f} руб")
    print(f"Прибыль мастеров: {total_master_profit:.2f} руб")
    print(f"Прибыль компании: {total_company_profit:.2f} руб")
    print(f"Выездов за город: {out_of_city_count}")
    print(f"Отзывов: {review_count}")

    if len(rows) > 0:
        avg_amount = total_amount / len(rows)
        avg_completion = sum(row[17] for row in rows if row[17]) / len(
            [row for row in rows if row[17]]
        )
        print(f"Средний чек: {avg_amount:.2f} руб")
        print(f"Среднее время выполнения: {avg_completion:.1f} часов")

    conn.close()


def main():
    """Основная функция"""
    # По умолчанию используем продакшн БД
    if len(sys.argv) < 2:
        db_path = "bot_database.db"
        start_date = None
        end_date = None
        print("Используется продакшн БД: bot_database.db")
        print(
            "Использование: python view_order_reports.py [путь_к_базе] [начальная_дата] [конечная_дата]"
        )
        print("Пример: python view_order_reports.py bot_database_dev.db 2025-10-01 2025-10-15")
        print()
    else:
        db_path = sys.argv[1]
        start_date = sys.argv[2] if len(sys.argv) > 2 else None
        end_date = sys.argv[3] if len(sys.argv) > 3 else None

    if not Path(db_path).exists():
        print(f"ОШИБКА: База данных {db_path} не найдена!")
        return

    try:
        view_order_reports(db_path, start_date, end_date)
    except Exception as e:
        print(f"ОШИБКА при просмотре отчетов: {e}")


if __name__ == "__main__":
    main()
