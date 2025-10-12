"""
Filters package
"""

from app.filters.group_filter import (
    IsGroupChat,
    IsGroupOrderCallback,
    IsMasterInGroup,
    IsMasterWorkGroup,
    IsOrderRelatedMessage,
    IsPrivateChat,
)
from app.filters.role_filter import IsAdmin, IsAdminOrDispatcher, IsDispatcher, IsMaster, RoleFilter


__all__ = [
    "IsAdmin",
    "IsAdminOrDispatcher",
    "IsDispatcher",
    "IsGroupChat",
    "IsGroupOrderCallback",
    "IsMaster",
    "IsMasterInGroup",
    "IsMasterWorkGroup",
    "IsOrderRelatedMessage",
    "IsPrivateChat",
    "RoleFilter",
]
