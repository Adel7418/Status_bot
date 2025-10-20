"""
Опциональная интеграция Sentry для error tracking
"""

import logging
import os


logger = logging.getLogger(__name__)


def init_sentry() -> str | None:
    """
    Инициализация Sentry для error tracking (опционально)

    Returns:
        Sentry DSN если успешно, None если Sentry не настроен
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")

    if not sentry_dsn:
        logger.info("Sentry DSN не настроен, error tracking отключен")
        return None

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration

        # Интеграция с logging
        logging_integration = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors as events
        )

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            traces_sample_rate=0.1,  # 10% транзакций для performance monitoring
            profiles_sample_rate=0.1,  # 10% профилирования
            integrations=[logging_integration],
            # Опции для production
            send_default_pii=False,  # Не отправляем PII данные
            attach_stacktrace=True,  # Включаем stacktrace
            # Максимальный размер breadcrumbs
            max_breadcrumbs=50,
        )

        logger.info(f"Sentry инициализирован (environment: {environment})")
        return sentry_dsn

    except ImportError:
        logger.warning(
            "Sentry SDK не установлен. "
            "Установите: pip install sentry-sdk или pip install -e .[monitoring]"
        )
        return None
    except Exception as e:
        logger.error(f"Ошибка инициализации Sentry: {e}")
        return None
