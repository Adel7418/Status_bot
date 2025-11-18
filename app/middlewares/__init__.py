"""Middlewares package"""

from app.middlewares.dependency_injection import DependencyInjectionMiddleware
from app.middlewares.error_handler import global_error_handler
from app.middlewares.logging import LoggingMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.role_check import RoleCheckMiddleware
from app.middlewares.validation_handler import ValidationHandlerMiddleware


__all__ = [
    "DependencyInjectionMiddleware",
    "LoggingMiddleware",
    "RateLimitMiddleware",
    "RoleCheckMiddleware",
    "ValidationHandlerMiddleware",
    "global_error_handler",
]
