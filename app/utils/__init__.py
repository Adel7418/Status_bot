"""Утилиты и вспомогательные функции"""
from app.utils.date_parser import (
    format_datetime_for_storage,
    format_datetime_user_friendly,
    parse_natural_datetime,
    should_parse_as_date,
)
from app.utils.helpers import (
    calculate_profit_split,
    create_callback_data,
    escape_html,
    escape_markdown,
    format_date,
    format_datetime,
    format_phone,
    get_now,
    get_user_display_name,
    log_action,
    parse_callback_data,
    truncate_text,
    validate_phone,
)
from app.utils.pii_masking import (
    mask_address,
    mask_name,
    mask_phone,
    mask_username,
    safe_log_order_details,
    safe_str_order,
    safe_str_user,
    sanitize_log_message,
)
from app.utils.retry import (
    retry_on_telegram_error,
    safe_answer_callback,
    safe_delete_message,
    safe_edit_message,
    safe_send_message,
)


__all__ = [
    # Business logic
    "calculate_profit_split",
    "create_callback_data",
    "escape_html",
    "escape_markdown",  # DEPRECATED: use escape_html for HTML mode
    "format_date",
    # Format utilities
    "format_datetime",
    "format_datetime_for_storage",
    "format_datetime_user_friendly",
    "format_phone",
    # DateTime utilities
    "get_now",
    "parse_natural_datetime",
    "should_parse_as_date",
    # User utilities
    "get_user_display_name",
    # Logging
    "log_action",
    "mask_address",
    "mask_name",
    # PII Masking (GDPR compliance)
    "mask_phone",
    "mask_username",
    # Callback utilities
    "parse_callback_data",
    # Retry utilities
    "retry_on_telegram_error",
    "safe_answer_callback",
    "safe_delete_message",
    "safe_edit_message",
    "safe_log_order_details",
    "safe_send_message",
    "safe_str_order",
    "safe_str_user",
    "sanitize_log_message",
    "truncate_text",
    # Validation
    "validate_phone",
]
