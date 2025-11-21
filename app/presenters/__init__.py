"""
Presenters - модуль для форматирования текста и данных для отображения

Presenters отвечают за преобразование данных из моделей в текст для пользователя.
Это разделяет логику бизнеса (handlers) и логику представления (presenters).
"""

from app.presenters.master_presenter import MasterPresenter
from app.presenters.order_presenter import OrderPresenter


__all__ = ["MasterPresenter", "OrderPresenter"]


