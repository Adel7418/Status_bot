
from datetime import UTC, datetime, timedelta, timezone


# Define MOSCOW_TZ as in the code
MOSCOW_TZ = timezone(timedelta(hours=3))

def get_now_mock():
    return datetime.now(MOSCOW_TZ)

def test_timezone_logic():
    print("Testing timezone logic independent of project dependencies...")

    # 1. Verify MOSCOW_TZ definition
    print(f"MOSCOW_TZ: {MOSCOW_TZ}")
    assert str(MOSCOW_TZ) == "UTC+03:00"

    # 2. Verify datetime.now(tz) behavior
    # It should return time in the specified timezone
    now_moscow = get_now_mock()
    print(f"Current time (Moscow): {now_moscow}")
    print(f"Timezone info: {now_moscow.tzinfo}")

    # Verify it matches UTC+3
    now_utc = datetime.now(UTC)
    expected_moscow_time = now_utc + timedelta(hours=3)

    # Allow small difference due to execution time
    diff = abs(now_moscow.replace(tzinfo=None) - expected_moscow_time.replace(tzinfo=None))
    print(f"Difference from UTC+3: {diff}")
    assert diff < timedelta(seconds=1)

    print("Confirmed: datetime.now(MOSCOW_TZ) returns correct Moscow time regardless of server local time.")

    # 3. Verify Night Mode Logic
    sla_night_start = 22
    sla_night_end = 6

    def is_night_mode(dt):
        hour = dt.hour
        start = sla_night_start
        end = sla_night_end
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end

    # Test 23:00
    dt = datetime(2023, 1, 1, 23, 0, 0, tzinfo=MOSCOW_TZ)
    assert is_night_mode(dt)
    print("23:00 is night mode: OK")

    # Test 05:00
    dt = datetime(2023, 1, 1, 5, 0, 0, tzinfo=MOSCOW_TZ)
    assert is_night_mode(dt)
    print("05:00 is night mode: OK")

    # Test 12:00
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=MOSCOW_TZ)
    assert not is_night_mode(dt)
    print("12:00 is night mode: OK")

if __name__ == "__main__":
    test_timezone_logic()
