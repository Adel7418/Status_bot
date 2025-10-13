"""Утилиты и вспомогательные функции"""
from app.utils.helpers import (
    calculate_profit_split,
    create_callback_data,
    escape_html,
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
from app.utils.retry import (
    retry_on_telegram_error,
    safe_answer_callback,
    safe_delete_message,
    safe_edit_message,
    safe_send_message,
)

__all__ = [
    # Format utilities
    "format_datetime",
    "format_date",
    "format_phone",
    "truncate_text",
    "escape_html",
    "escape_markdown",  # DEPRECATED: use escape_html for HTML mode
    # User utilities
    "get_user_display_name",
    # Callback utilities
    "parse_callback_data",
    "create_callback_data",
    # Validation
    "validate_phone",
    # Logging
    "log_action",
    # Business logic
    "calculate_profit_split",
    # Retry utilities
    "retry_on_telegram_error",
    "safe_send_message",
    "safe_answer_callback",
    "safe_edit_message",
    "safe_delete_message",
]
