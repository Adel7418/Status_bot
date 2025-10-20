"""
Domain layer для бизнес-логики
"""

from app.domain.order_state_machine import (
    InvalidStateTransitionError,
    OrderStateMachine,
    OrderStateTransitionResult,
)


__all__ = [
    "InvalidStateTransitionError",
    "OrderStateMachine",
    "OrderStateTransitionResult",
]
