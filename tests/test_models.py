"""
Тесты для моделей данных
"""
from datetime import datetime

from app.config import OrderStatus, UserRole
from app.database.models import Master, Order, User


class TestUserModel:
    """Тесты для модели User"""

    def test_user_creation(self):
        """Тест создания пользователя"""
        user = User(
            id=1,
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            role=UserRole.ADMIN,
            created_at=datetime.now()
        )

        assert user.telegram_id == 123456789
        assert user.username == "test_user"
        assert user.role == UserRole.ADMIN

    def test_get_display_name_with_username(self):
        """Тест получения имени с username"""
        user = User(
            id=1,
            telegram_id=123,
            username="test_user",
            first_name="Test",
            last_name="User",
            role=UserRole.ADMIN
        )

        assert user.get_display_name() == "@test_user"

    def test_get_display_name_without_username(self):
        """Тест получения имени без username"""
        user = User(
            id=1,
            telegram_id=123,
            username=None,
            first_name="Test",
            last_name="User",
            role=UserRole.ADMIN
        )

        assert user.get_display_name() == "Test User"

    def test_get_roles_single(self):
        """Тест получения одной роли"""
        user = User(
            id=1,
            telegram_id=123,
            role=UserRole.ADMIN
        )

        roles = user.get_roles()
        assert roles == [UserRole.ADMIN]

    def test_get_roles_multiple(self):
        """Тест получения множественных ролей"""
        user = User(
            id=1,
            telegram_id=123,
            role=f"{UserRole.ADMIN},{UserRole.DISPATCHER}"
        )

        roles = user.get_roles()
        assert UserRole.ADMIN in roles
        assert UserRole.DISPATCHER in roles

    def test_has_role(self):
        """Тест проверки наличия роли"""
        user = User(
            id=1,
            telegram_id=123,
            role=f"{UserRole.ADMIN},{UserRole.DISPATCHER}"
        )

        assert user.has_role(UserRole.ADMIN) is True
        assert user.has_role(UserRole.DISPATCHER) is True
        assert user.has_role(UserRole.MASTER) is False

    def test_add_role(self):
        """Тест добавления роли"""
        user = User(
            id=1,
            telegram_id=123,
            role=UserRole.DISPATCHER
        )

        new_roles = user.add_role(UserRole.MASTER)
        assert UserRole.DISPATCHER in new_roles
        assert UserRole.MASTER in new_roles

    def test_remove_role(self):
        """Тест удаления роли"""
        user = User(
            id=1,
            telegram_id=123,
            role=f"{UserRole.DISPATCHER},{UserRole.MASTER}"
        )

        new_roles = user.remove_role(UserRole.MASTER)
        assert UserRole.DISPATCHER in new_roles
        assert UserRole.MASTER not in new_roles

    def test_get_primary_role_single(self):
        """Тест получения основной роли (одна роль)"""
        user = User(
            id=1,
            telegram_id=123,
            role=UserRole.ADMIN
        )

        assert user.get_primary_role() == UserRole.ADMIN

    def test_get_primary_role_multiple(self):
        """Тест получения основной роли (множественные)"""
        user = User(
            id=1,
            telegram_id=123,
            role=f"{UserRole.DISPATCHER},{UserRole.MASTER}"
        )

        # Должна вернуться первая роль
        assert user.get_primary_role() == UserRole.DISPATCHER


class TestMasterModel:
    """Тесты для модели Master"""

    def test_master_creation(self):
        """Тест создания мастера"""
        master = Master(
            id=1,
            telegram_id=123456789,
            phone="+79991234567",
            specialization="Стиральные машины",
            is_active=True,
            is_approved=True,
            created_at=datetime.now()
        )

        assert master.telegram_id == 123456789
        assert master.phone == "+79991234567"
        assert master.is_active is True
        assert master.is_approved is True

    def test_get_display_name(self):
        """Тест получения имени мастера"""
        master = Master(
            id=1,
            telegram_id=123,
            phone="+79991234567",
            specialization="Стиральные машины",
            first_name="Иван",
            last_name="Иванов"
        )

        assert master.get_display_name() == "Иван Иванов"


class TestOrderModel:
    """Тесты для модели Order"""

    def test_order_creation(self):
        """Тест создания заявки"""
        order = Order(
            id=1,
            equipment_type="Стиральные машины",
            description="Не включается",
            client_name="Иван Иванов",
            client_address="ул. Ленина, 1",
            client_phone="+79991234567",
            status=OrderStatus.NEW,
            dispatcher_id=123,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        assert order.equipment_type == "Стиральные машины"
        assert order.status == OrderStatus.NEW
        assert order.dispatcher_id == 123

    def test_order_with_master(self):
        """Тест заявки с назначенным мастером"""
        order = Order(
            id=1,
            equipment_type="Стиральные машины",
            description="Не включается",
            client_name="Иван Иванов",
            client_address="ул. Ленина, 1",
            client_phone="+79991234567",
            status=OrderStatus.ASSIGNED,
            assigned_master_id=999,
            dispatcher_id=123,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        assert order.assigned_master_id == 999
        assert order.status == OrderStatus.ASSIGNED

