"""
Тесты для вспомогательных функций
"""
import pytest

from app.utils.helpers import calculate_profit_split


@pytest.mark.parametrize(
    ("total_amount", "materials_cost", "expected_master_profit", "expected_company_profit"),
    [
        (6000, 1000, 2000, 3000),  # Net profit < 7000, 40/60 split
        (10000, 2000, 4000, 4000),  # Net profit >= 7000, 50/50 split
    ],
)
def test_calculate_profit_split_regular(
    total_amount, materials_cost, expected_master_profit, expected_company_profit
):
    """Тест расчета прибыли для обычного мастера."""
    master_profit, company_profit = calculate_profit_split(
        total_amount=total_amount, materials_cost=materials_cost
    )
    assert master_profit == expected_master_profit
    assert company_profit == expected_company_profit


def test_calculate_profit_split_senior_master():
    """Тест расчета прибыли для старшего мастера (гарантированные 50%)."""
    # Net profit < 7000, но для SENIOR_MASTER должно быть 50/50
    master_profit, company_profit = calculate_profit_split(
        total_amount=6000, materials_cost=1000, master_roles=["SENIOR_MASTER"]
    )
    assert master_profit == 2500  # 50% of 5000
    assert company_profit == 2500


def test_calculate_profit_split_admin():
    """Тест расчета прибыли для админа (гарантированные 50%)."""
    # Net profit < 7000, но для ADMIN должно быть 50/50
    master_profit, company_profit = calculate_profit_split(
        total_amount=6000, materials_cost=1000, master_roles=["ADMIN"]
    )
    assert master_profit == 2500  # 50% of 5000
    assert company_profit == 2500


def test_calculate_profit_split_out_of_city():
    """Тест расчета прибыли с бонусом за выезд за город."""
    # Net profit < 7000 (40/60) + 10% bonus
    master_profit, company_profit = calculate_profit_split(
        total_amount=6000, materials_cost=1000, out_of_city=True
    )
    net_profit = 5000
    base_master_profit = net_profit * 0.4  # 2000
    bonus = net_profit * 0.1  # 500
    expected_master_profit = base_master_profit + bonus  # 2500
    expected_company_profit = net_profit - expected_master_profit  # 2500
    assert master_profit == expected_master_profit
    assert company_profit == expected_company_profit


def test_calculate_profit_split_senior_master_out_of_city():
    """Тест расчета прибыли для старшего мастера с выездом за город."""
    # Net profit < 7000 (50/50 for senior) + 10% bonus
    master_profit, company_profit = calculate_profit_split(
        total_amount=6000,
        materials_cost=1000,
        master_roles=["SENIOR_MASTER"],
        out_of_city=True,
    )
    net_profit = 5000
    base_master_profit = net_profit * 0.5  # 2500
    bonus = net_profit * 0.1  # 500
    expected_master_profit = base_master_profit + bonus  # 3000
    expected_company_profit = net_profit - expected_master_profit  # 2000
    assert master_profit == expected_master_profit
    assert company_profit == expected_company_profit

def test_calculate_profit_split_admin_out_of_city():
    """Тест расчета прибыли для админа с выездом за город."""
    # Net profit < 7000 (50/50 for admin) + 10% bonus
    master_profit, company_profit = calculate_profit_split(
        total_amount=6000,
        materials_cost=1000,
        master_roles=["ADMIN"],
        out_of_city=True,
    )
    net_profit = 5000
    base_master_profit = net_profit * 0.5  # 2500
    bonus = net_profit * 0.1  # 500
    expected_master_profit = base_master_profit + bonus  # 3000
    expected_company_profit = net_profit - expected_master_profit # 2000
    assert master_profit == expected_master_profit
    assert company_profit == expected_company_profit

def test_calculate_profit_split_specialization_rate():
    """Тест расчета с фиксированной ставкой для специальности."""
    # Ставка 60/40 для специальности
    master_profit, company_profit = calculate_profit_split(
        total_amount=10000,
        materials_cost=2000,
        specialization_rate=(60.0, 40.0)
    )
    net_profit = 8000
    assert master_profit == net_profit * 0.6  # 4800
    assert company_profit == net_profit * 0.4  # 3200

def test_calculate_profit_split_equipment_type():
    """Тест расчета для типа техники 'электрика'."""
    # Для электрики всегда 50/50, даже если чистая прибыль < 7000
    master_profit, company_profit = calculate_profit_split(
        total_amount=6000,
        materials_cost=1000,
        equipment_type="Электрика"
    )
    net_profit = 5000
    assert master_profit == net_profit * 0.5 # 2500
    assert company_profit == net_profit * 0.5 # 2500
