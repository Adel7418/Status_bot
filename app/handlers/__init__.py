"""
Handlers package
"""
from app.handlers.admin import router as admin_router
from app.handlers.common import router as common_router
from app.handlers.dispatcher import router as dispatcher_router
from app.handlers.group_interaction import router as group_router
from app.handlers.master import router as master_router


# Список всех роутеров
# ВАЖНО: common_router должен быть последним, чтобы не перехватывать сообщения других роутеров
routers = [
    admin_router,
    dispatcher_router,
    master_router,
    group_router,
    common_router
]

__all__ = ["routers"]

