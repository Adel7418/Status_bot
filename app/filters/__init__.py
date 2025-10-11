"""
Filters package
"""
from app.filters.role_filter import RoleFilter, IsAdmin, IsDispatcher, IsMaster, IsAdminOrDispatcher

__all__ = ['RoleFilter', 'IsAdmin', 'IsDispatcher', 'IsMaster', 'IsAdminOrDispatcher']

