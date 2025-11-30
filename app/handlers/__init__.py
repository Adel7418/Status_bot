"""
Handlers package
"""

from app.handlers.admin import router as admin_router
from app.handlers.admin_history import router as admin_history_router
from app.handlers.common import router as common_router
from app.handlers.developer import router as developer_router
from app.handlers.dispatcher import router as dispatcher_router
from app.handlers.financial_reports import router as financial_reports_router
from app.handlers.group_interaction import router as group_router
from app.handlers.master import router as master_router
from app.handlers.order_edit import router as order_edit_router
from app.handlers.order_search import router as order_search_router
from app.handlers.parser_config import router as parser_config_router
from app.handlers.parser_stats import router as parser_stats_router
from app.handlers.template import router as template_router


# Список всех роутеров
# ВАЖНО: common_router должен быть последним, чтобы не перехватывать сообщения других роутеров
# developer_router первым для команд разработчика (только для админов)
# financial_reports_router ПЕРЕД dispatcher_router, чтобы перехватывать кнопку "📊 Отчеты"
# admin_history_router для работы с историей заявок
# order_edit_router для редактирования заявок
# parser_config_router для настройки парсера (только админы)
routers = [
    developer_router,
    admin_router,
    parser_config_router,  # Настройка парсера
    parser_stats_router,  # Статистика парсера
    admin_history_router,
    financial_reports_router,
    dispatcher_router,
    order_search_router,  # Поиск заказов
    master_router,
    order_edit_router,  # Редактирование заявок
    group_router,
    template_router,  # Шаблон заявки
    common_router,
]

__all__ = ["routers"]
