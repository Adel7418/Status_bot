"""Utils package"""
# Retry механизм
from app.utils.retry import (
    retry_on_telegram_error,
    safe_answer_callback,
    safe_delete_message,
    safe_edit_message,
    safe_send_message,
)

# Вспомогательные функции
from app.utils.helpers import (
    calculate_profit_split,
    create_callback_data,
    escape_markdown,
    format_date,
    format_datetime,
    format_phone,
    get_user_display_name,
    log_action,
    parse_callback_data,
    truncate_text,
    validate_phone,
)

__all__ = [
    # Retry
    "retry_on_telegram_error",
    "safe_send_message",
    "safe_answer_callback",
    "safe_edit_message",
    "safe_delete_message",
    # Helpers
    "validate_phone",
    "format_phone",
    "format_datetime",
    "format_date",
    "truncate_text",
    "escape_markdown",
    "get_user_display_name",
    "parse_callback_data",
    "create_callback_data",
    "log_action",
    "calculate_profit_split",
]

