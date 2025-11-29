
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

# Mock dotenv
mock_dotenv = MagicMock()
sys.modules["dotenv"] = mock_dotenv

# Mock aiogram
mock_aiogram = MagicMock()
sys.modules["aiogram"] = mock_aiogram
sys.modules["aiogram.types"] = MagicMock()
sys.modules["aiogram.fsm"] = MagicMock()
sys.modules["aiogram.fsm.context"] = MagicMock()
sys.modules["aiogram.fsm.state"] = MagicMock()
sys.modules["aiogram.utils"] = MagicMock()

sys.modules["aiogram.utils.keyboard"] = MagicMock()
sys.modules["aiogram.filters"] = MagicMock()
sys.modules["aiogram.exceptions"] = MagicMock()

# Mock database dependencies
sys.modules["aiosqlite"] = MagicMock()
sys.modules["sqlalchemy"] = MagicMock()
sys.modules["sqlalchemy.ext"] = MagicMock()
sys.modules["sqlalchemy.ext.asyncio"] = MagicMock()
sys.modules["sqlalchemy.ext.declarative"] = MagicMock()
sys.modules["sqlalchemy.orm"] = MagicMock()
sys.modules["sqlalchemy.sql"] = MagicMock()
sys.modules["sqlalchemy.schema"] = MagicMock()
sys.modules["sqlalchemy.types"] = MagicMock()



# Mock other dependencies
sys.modules["dateparser"] = MagicMock()
sys.modules["pytz"] = MagicMock()
sys.modules["pydantic"] = MagicMock()
sys.modules["openpyxl"] = MagicMock()
sys.modules["openpyxl.styles"] = MagicMock()






# Setup Router mock to handle decorators
mock_router = MagicMock()
def decorator_mock(*args, **kwargs):
    def wrapper(func):
        return func
    return wrapper
mock_router.message = MagicMock(side_effect=decorator_mock)
mock_router.callback_query = MagicMock(side_effect=decorator_mock)
mock_aiogram.Router = MagicMock(return_value=mock_router)
mock_aiogram.F = MagicMock()

# Mock app.states
sys.modules["app.states"] = MagicMock()
sys.modules["app.filters"] = MagicMock()
sys.modules["app.filters.role_filter"] = MagicMock()

from app.config import UserRole
from app.handlers.master import process_out_of_city_confirmation_callback

async def test_notification_broadcast():
    print("Starting test_notification_broadcast...")

    # Mock dependencies
    mock_callback = AsyncMock()
    mock_callback.data = "confirm_out_of_city:yes:123"
    mock_callback.from_user.id = 111  # Master ID
    mock_callback.message = AsyncMock()
    mock_callback.bot = AsyncMock()

    mock_state = AsyncMock()
    mock_state.get_data.return_value = {
        "total_amount": 5000.0,
        "materials_cost": 1000.0,
        "has_review": True,
        "order_id": 123
    }

    # Mock Database
    mock_db = AsyncMock()
    
    # Mock Order
    mock_order = MagicMock()
    mock_order.id = 123
    mock_order.dispatcher_id = 999
    mock_order.assigned_master_id = 1
    mock_order.equipment_type = "Fridge"
    mock_db.get_order_by_id.return_value = mock_order

    # Mock Master
    mock_master = MagicMock()
    mock_master.id = 1
    mock_master.telegram_id = 111
    mock_master.get_display_name.return_value = "Master John"
    mock_db.get_master_by_telegram_id.return_value = mock_master

    # Mock User (Master)
    mock_user = MagicMock()
    mock_user.get_roles.return_value = [UserRole.MASTER]
    mock_db.get_user_by_telegram_id.return_value = mock_user

    # Mock Admins and Dispatchers
    admin1 = MagicMock()
    admin1.telegram_id = 101
    admin2 = MagicMock()
    admin2.telegram_id = 102
    dispatcher1 = MagicMock()
    dispatcher1.telegram_id = 999 # Same as assigned dispatcher

    mock_db.get_admins_and_dispatchers.return_value = [admin1, admin2, dispatcher1]

    # Mock get_database
    with patch("app.handlers.master.get_database", return_value=mock_db):
        # Mock safe_send_message
        with patch("app.utils.safe_send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            # Mock parse_callback_data
            with patch("app.utils.parse_callback_data") as mock_parse:
                mock_parse.return_value = {"action": "confirm_out_of_city", "params": ["yes", "123"]}
                
                # Mock calculate_profit_split
                with patch("app.utils.helpers.calculate_profit_split", return_value=(2000, 2000)):
                    
                    # Run the handler
                    await process_out_of_city_confirmation_callback(mock_callback, mock_state, [UserRole.MASTER])

            # Verify calls
            print(f"safe_send_message call count: {mock_send.call_count}")
            
            called_recipients = {call.args[1] for call in mock_send.call_args_list}
            print(f"Recipients: {called_recipients}")

            expected_recipients = {101, 102, 999}
            
            if expected_recipients.issubset(called_recipients):
                print("SUCCESS: All expected recipients were notified.")
            else:
                print(f"FAILURE: Missing recipients. Expected {expected_recipients}, got {called_recipients}")

if __name__ == "__main__":
    asyncio.run(test_notification_broadcast())
