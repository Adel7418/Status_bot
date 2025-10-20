"""Тест финансовых отчетов"""
import asyncio
from datetime import datetime

from app.services.financial_reports import FinancialReportsService
from app.utils.helpers import MOSCOW_TZ


async def test_daily_report():
    service = FinancialReportsService()
    today = datetime.now(MOSCOW_TZ)

    print(f"Testing daily report for {today.strftime('%Y-%m-%d')}")

    try:
        report = await service.generate_daily_report(today)
        print("✅ Report generated successfully!")
        print(f"   Total orders: {report.total_orders}")
        print(f"   Total amount: {report.total_amount}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_daily_report())
