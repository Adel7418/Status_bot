"""
State Machine для валидации переходов статусов заявок
"""

from dataclasses import dataclass

from app.core.constants import OrderStatus, UserRole


class InvalidStateTransitionError(Exception):
    """Исключение при попытке недопустимого перехода статуса"""

    def __init__(self, from_state: str, to_state: str, reason: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        message = f"Недопустимый переход из '{from_state}' в '{to_state}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


@dataclass
class OrderStateTransitionResult:
    """Результат валидации перехода статуса"""

    is_valid: bool
    error_message: str | None = None
    required_role: str | None = None
    warnings: list[str] | None = None


class OrderStateMachine:
    """
    State Machine для управления жизненным циклом заявки

    Граф переходов:

    NEW → ASSIGNED → ACCEPTED → ONSITE → CLOSED
      ↓                 ↓                    ↓
    REFUSED         REFUSED                 DR
                                             ↓
                                          CLOSED
    """

    # Допустимые переходы: из какого статуса в какие можно перейти
    TRANSITIONS: dict[str, set[str]] = {
        OrderStatus.NEW: {
            OrderStatus.ASSIGNED,  # Назначение мастера
            OrderStatus.REFUSED,  # Отмена диспетчером
        },
        OrderStatus.ASSIGNED: {
            OrderStatus.ACCEPTED,  # Мастер принял
            OrderStatus.REFUSED,  # Мастер отказался → возврат в NEW
            OrderStatus.NEW,  # Ручной возврат диспетчером
        },
        OrderStatus.ACCEPTED: {
            OrderStatus.ONSITE,  # Мастер на объекте
            OrderStatus.DR,  # Сразу в длительный ремонт
            OrderStatus.REFUSED,  # Отмена (редко)
        },
        OrderStatus.ONSITE: {
            OrderStatus.CLOSED,  # Завершение работы
            OrderStatus.DR,  # Переход в длительный ремонт
            OrderStatus.REFUSED,  # Отказ после прибытия на объект
        },
        OrderStatus.DR: {
            OrderStatus.CLOSED,  # Завершение после DR
            OrderStatus.ONSITE,  # Возврат на объект (редко)
            OrderStatus.REFUSED,  # Отказ от длительного ремонта
        },
        OrderStatus.REFUSED: {
            OrderStatus.NEW,  # Переоткрытие заявки
        },
        OrderStatus.CLOSED: set(),  # Терминальное состояние
    }

    # Роли, которые могут выполнять определённые переходы
    ROLE_PERMISSIONS: dict[tuple[str, str], set[str]] = {
        # (from_status, to_status): {allowed_roles}
        (OrderStatus.NEW, OrderStatus.ASSIGNED): {
            UserRole.ADMIN,
            UserRole.DISPATCHER,
        },
        (OrderStatus.NEW, OrderStatus.REFUSED): {
            UserRole.ADMIN,
            UserRole.DISPATCHER,
        },
        (OrderStatus.ASSIGNED, OrderStatus.ACCEPTED): {
            UserRole.MASTER,  # Мастер принимает
            UserRole.ADMIN,  # Админ может принимать за мастера
        },
        (OrderStatus.ASSIGNED, OrderStatus.REFUSED): {
            UserRole.MASTER,  # Мастер отказывается
            UserRole.ADMIN,  # Админ может отменить
        },
        (OrderStatus.ASSIGNED, OrderStatus.NEW): {
            UserRole.ADMIN,
            UserRole.DISPATCHER,
        },
        (OrderStatus.ACCEPTED, OrderStatus.ONSITE): {
            UserRole.MASTER,  # Мастер обновляет
            UserRole.ADMIN,  # Админ может обновлять за мастера
        },
        (OrderStatus.ACCEPTED, OrderStatus.DR): {
            UserRole.MASTER,
            UserRole.ADMIN,  # Админ может переводить в DR
        },
        (OrderStatus.ACCEPTED, OrderStatus.REFUSED): {
            UserRole.ADMIN,
            UserRole.DISPATCHER,
        },
        (OrderStatus.ONSITE, OrderStatus.CLOSED): {
            UserRole.MASTER,  # Мастер завершает
            UserRole.ADMIN,  # Админ может завершать за мастера
        },
        (OrderStatus.ONSITE, OrderStatus.DR): {
            UserRole.MASTER,
            UserRole.ADMIN,  # Админ может переводить в DR
        },
        (OrderStatus.ONSITE, OrderStatus.REFUSED): {
            UserRole.MASTER,  # Мастер может отказаться
            UserRole.ADMIN,  # Админ может отказаться за мастера
        },
        (OrderStatus.DR, OrderStatus.CLOSED): {
            UserRole.MASTER,
            UserRole.ADMIN,  # Админ может завершать DR
        },
        (OrderStatus.DR, OrderStatus.ONSITE): {
            UserRole.MASTER,
            UserRole.ADMIN,
        },
        (OrderStatus.DR, OrderStatus.REFUSED): {
            UserRole.MASTER,
            UserRole.ADMIN,
        },
        (OrderStatus.REFUSED, OrderStatus.NEW): {
            UserRole.ADMIN,
            UserRole.DISPATCHER,
        },
    }

    @classmethod
    def can_transition(cls, from_state: str, to_state: str) -> bool:
        """
        Проверка возможности перехода между статусами

        Args:
            from_state: Текущий статус
            to_state: Целевой статус

        Returns:
            True если переход допустим
        """
        if from_state == to_state:
            return True  # Переход в тот же статус всегда допустим (idempotent)

        allowed_transitions = cls.TRANSITIONS.get(from_state, set())
        return to_state in allowed_transitions

    @classmethod
    def validate_transition(
        cls,
        from_state: str,
        to_state: str,
        user_role: str | None = None,
        user_roles: list[str] | None = None,
        raise_exception: bool = True,
    ) -> OrderStateTransitionResult:
        """
        Валидация перехода статуса с проверкой прав

        Args:
            from_state: Текущий статус заявки
            to_state: Целевой статус
            user_role: Основная роль пользователя (deprecated, используйте user_roles)
            user_roles: Список ролей пользователя
            raise_exception: Выбрасывать ли исключение при ошибке

        Returns:
            OrderStateTransitionResult с результатом валидации

        Raises:
            InvalidStateTransitionError: Если переход недопустим и raise_exception=True
        """
        # Если статусы одинаковые - idempotent операция, всегда OK
        if from_state == to_state:
            return OrderStateTransitionResult(
                is_valid=True,
                warnings=["Переход в тот же статус (idempotent)"],
            )

        # Проверяем базовую возможность перехода
        if not cls.can_transition(from_state, to_state):
            error_msg = (
                f"Переход из '{OrderStatus.get_status_name(from_state)}' "
                f"в '{OrderStatus.get_status_name(to_state)}' недопустим"
            )

            # Подсказываем допустимые переходы
            allowed = cls.TRANSITIONS.get(from_state, set())
            if allowed:
                allowed_names = [OrderStatus.get_status_name(s) for s in allowed]
                error_msg += f". Допустимые переходы: {', '.join(allowed_names)}"
            else:
                error_msg += (
                    f". Статус '{OrderStatus.get_status_name(from_state)}' является терминальным"
                )

            if raise_exception:
                raise InvalidStateTransitionError(from_state, to_state, error_msg)

            return OrderStateTransitionResult(
                is_valid=False,
                error_message=error_msg,
            )

        # Проверяем права доступа
        transition_key = (from_state, to_state)
        required_roles = cls.ROLE_PERMISSIONS.get(transition_key, set())

        if required_roles:
            # Формируем список ролей для проверки
            roles_to_check = user_roles if user_roles else ([user_role] if user_role else [])

            # Проверяем наличие хотя бы одной подходящей роли
            has_permission = any(role in required_roles for role in roles_to_check)

            if not has_permission:
                role_names = ", ".join(required_roles)
                error_msg = (
                    f"Недостаточно прав для перехода из '{OrderStatus.get_status_name(from_state)}' "
                    f"в '{OrderStatus.get_status_name(to_state)}'. "
                    f"Требуется одна из ролей: {role_names}"
                )

                if raise_exception:
                    raise InvalidStateTransitionError(from_state, to_state, error_msg)

                return OrderStateTransitionResult(
                    is_valid=False,
                    error_message=error_msg,
                    required_role=", ".join(required_roles),
                )

        # Всё OK
        return OrderStateTransitionResult(is_valid=True)

    @classmethod
    def get_available_transitions(
        cls, from_state: str, user_roles: list[str] | None = None
    ) -> list[str]:
        """
        Получение списка доступных переходов из текущего статуса

        Args:
            from_state: Текущий статус
            user_roles: Роли пользователя для фильтрации по правам

        Returns:
            Список доступных статусов для перехода
        """
        allowed_states = cls.TRANSITIONS.get(from_state, set())

        if not user_roles:
            return list(allowed_states)

        # Фильтруем по правам доступа
        available = []
        for to_state in allowed_states:
            transition_key = (from_state, to_state)
            required_roles = cls.ROLE_PERMISSIONS.get(transition_key, set())

            # Если права не заданы - доступно всем
            if not required_roles:
                available.append(to_state)
                continue

            # Проверяем наличие подходящей роли
            if any(role in required_roles for role in user_roles):
                available.append(to_state)

        return available

    @classmethod
    def get_transition_description(cls, from_state: str, to_state: str) -> str:
        """
        Получение описания перехода на русском

        Args:
            from_state: Начальный статус
            to_state: Конечный статус

        Returns:
            Описание перехода
        """
        descriptions = {
            (OrderStatus.NEW, OrderStatus.ASSIGNED): "Назначение мастера на заявку",
            (OrderStatus.NEW, OrderStatus.REFUSED): "Отмена заявки диспетчером",
            (OrderStatus.ASSIGNED, OrderStatus.ACCEPTED): "Мастер принял заявку",
            (OrderStatus.ASSIGNED, OrderStatus.REFUSED): "Мастер отказался от заявки",
            (OrderStatus.ASSIGNED, OrderStatus.NEW): "Возврат заявки в пул",
            (OrderStatus.ACCEPTED, OrderStatus.ONSITE): "Мастер прибыл на объект",
            (OrderStatus.ACCEPTED, OrderStatus.DR): "Переход в длительный ремонт",
            (OrderStatus.ACCEPTED, OrderStatus.REFUSED): "Отмена принятой заявки",
            (OrderStatus.ONSITE, OrderStatus.CLOSED): "Завершение работы",
            (OrderStatus.ONSITE, OrderStatus.DR): "Переход в длительный ремонт",
            (OrderStatus.ONSITE, OrderStatus.REFUSED): "Отказ после прибытия на объект",
            (OrderStatus.DR, OrderStatus.CLOSED): "Завершение длительного ремонта",
            (OrderStatus.DR, OrderStatus.ONSITE): "Возврат из DR на объект",
            (OrderStatus.DR, OrderStatus.REFUSED): "Отказ от длительного ремонта",
            (OrderStatus.REFUSED, OrderStatus.NEW): "Переоткрытие отменённой заявки",
        }

        key = (from_state, to_state)
        return descriptions.get(
            key,
            f"Переход из {OrderStatus.get_status_name(from_state)} "
            f"в {OrderStatus.get_status_name(to_state)}",
        )

    @classmethod
    def is_terminal_state(cls, state: str) -> bool:
        """
        Проверка, является ли статус терминальным

        Args:
            state: Статус для проверки

        Returns:
            True если из этого статуса нельзя никуда перейти
        """
        return len(cls.TRANSITIONS.get(state, set())) == 0

    @classmethod
    def get_state_validation_rules(cls, state: str) -> dict:
        """
        Получение правил валидации для конкретного статуса

        Args:
            state: Статус заявки

        Returns:
            Словарь с правилами валидации
        """
        rules = {
            OrderStatus.NEW: {
                "required_fields": [
                    "equipment_type",
                    "description",
                    "client_name",
                    "client_address",
                    "client_phone",
                ],
                "optional_fields": ["notes", "scheduled_time"],
                "must_have": None,
                "must_not_have": ["assigned_master_id"],
            },
            OrderStatus.ASSIGNED: {
                "required_fields": ["assigned_master_id"],
                "optional_fields": [],
                "must_have": "assigned_master_id",
                "must_not_have": None,
            },
            OrderStatus.ACCEPTED: {
                "required_fields": ["assigned_master_id"],
                "optional_fields": [],
                "must_have": "assigned_master_id",
                "must_not_have": None,
            },
            OrderStatus.ONSITE: {
                "required_fields": ["assigned_master_id"],
                "optional_fields": [],
                "must_have": "assigned_master_id",
                "must_not_have": None,
            },
            OrderStatus.CLOSED: {
                "required_fields": ["total_amount"],
                "optional_fields": [
                    "materials_cost",
                    "master_profit",
                    "company_profit",
                    "has_review",
                    "out_of_city",
                ],
                "must_have": "total_amount",
                "must_not_have": None,
            },
            OrderStatus.DR: {
                "required_fields": ["estimated_completion_date"],
                "optional_fields": ["prepayment_amount"],
                "must_have": "assigned_master_id",
                "must_not_have": None,
            },
            OrderStatus.REFUSED: {
                "required_fields": [],
                "optional_fields": ["notes"],
                "must_have": None,
                "must_not_have": None,
            },
        }

        return rules.get(state, {})  # type: ignore[return-value]

    @classmethod
    def transition(
        cls,
        from_state: str,
        to_state: str,
        user_role: str | None = None,
        user_roles: list[str] | None = None,
    ) -> OrderStateTransitionResult:
        """
        Алиас для validate_transition для обратной совместимости

        Args:
            from_state: Текущий статус заявки
            to_state: Целевой статус
            user_role: Основная роль пользователя
            user_roles: Список ролей пользователя

        Returns:
            OrderStateTransitionResult с результатом валидации

        Raises:
            InvalidStateTransitionError: Если переход недопустим
        """
        return cls.validate_transition(
            from_state=from_state,
            to_state=to_state,
            user_role=user_role,
            user_roles=user_roles,
            raise_exception=True,
        )
