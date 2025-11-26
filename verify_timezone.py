
import os
import sys
from datetime import datetime


# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import Config
from app.utils.helpers import MOSCOW_TZ, get_now


def test_timezone_handling():
    print("Testing timezone handling...")

    # 1. Verify MOSCOW_TZ
    print(f"MOSCOW_TZ: {MOSCOW_TZ}")
    assert str(MOSCOW_TZ) == "UTC+03:00"

    # 2. Verify get_now() returns aware datetime with correct timezone
    now = get_now()
    print(f"Current time (Moscow): {now}")
    print(f"Timezone info: {now.tzinfo}")

    assert now.tzinfo is not None
    assert now.tzinfo == MOSCOW_TZ

    # 3. Verify night mode logic with mocked time
    # Mock Config values just in case
    Config.SLA_NIGHT_START = 22
    Config.SLA_NIGHT_END = 6

    def is_night_mode(dt):
        hour = dt.hour
        start = Config.SLA_NIGHT_START
        end = Config.SLA_NIGHT_END
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end

    # Test cases
    # 23:00 Moscow time -> Should be Night Mode
    dt_night = datetime(2023, 1, 1, 23, 0, 0, tzinfo=MOSCOW_TZ)
    assert is_night_mode(dt_night)
    print(f"23:00 Moscow is night mode: {is_night_mode(dt_night)}")

    # 03:00 Moscow time -> Should be Night Mode
    dt_early_morning = datetime(2023, 1, 1, 3, 0, 0, tzinfo=MOSCOW_TZ)
    assert is_night_mode(dt_early_morning)
    print(f"03:00 Moscow is night mode: {is_night_mode(dt_early_morning)}")

    # 14:00 Moscow time -> Should NOT be Night Mode
    dt_day = datetime(2023, 1, 1, 14, 0, 0, tzinfo=MOSCOW_TZ)
    assert not is_night_mode(dt_day)
    print(f"14:00 Moscow is night mode: {is_night_mode(dt_day)}")

    print("All timezone tests passed!")

if __name__ == "__main__":
    test_timezone_handling()
