"""
Domain layer для бизнес-логики
"""

from app.domain.order_state_machine import (
    OrderStateMachine,
    InvalidStateTransitionError,
    OrderStateTransitionResult,
)

__all__ = [
    "OrderStateMachine",
    "InvalidStateTransitionError",
    "OrderStateTransitionResult",
]

