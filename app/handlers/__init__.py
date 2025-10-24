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


# Список всех роутеров
# ВАЖНО: common_router должен быть последним, чтобы не перехватывать сообщения других роутеров
# developer_router первым для команд разработчика (только для админов)
# financial_reports_router ПЕРЕД dispatcher_router, чтобы перехватывать кнопку "📊 Отчеты"
# admin_history_router для работы с историей заявок
# order_edit_router для редактирования заявок
routers = [
    developer_router,
    admin_router,
    admin_history_router,
    financial_reports_router,
    dispatcher_router,
    order_search_router,  # Поиск заказов
    master_router,
    order_edit_router,  # Редактирование заявок
    group_router,
    common_router,
]

__all__ = ["routers"]
