"""
SQLAlchemy ORM модели для базы данных
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


# Базовый класс для всех моделей
Base = declarative_base()


class User(Base):
    """Модель пользователя в SQLAlchemy"""

    __tablename__ = "users"

    # Основные поля
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="UNKNOWN")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    # Связи
    masters: Mapped[list["Master"]] = relationship("Master", back_populates="user")
    created_orders: Mapped[list["Order"]] = relationship(
        "Order", foreign_keys="Order.dispatcher_id", back_populates="dispatcher"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")
    status_changes: Mapped[list["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory", back_populates="changed_by_user"
    )

    # Индексы
    __table_args__ = (
        Index("idx_users_telegram_id", "telegram_id"),
        Index("idx_users_role", "role"),
        Index("idx_users_deleted_at", "deleted_at"),
        CheckConstraint("telegram_id > 0", name="chk_users_telegram_id"),
        CheckConstraint(
            "role IN ('ADMIN', 'DISPATCHER', 'MASTER', 'UNKNOWN') OR role LIKE '%,%'",
            name="chk_users_role",
        ),
    )

    def get_roles(self) -> list[str]:
        """Получение списка ролей пользователя"""
        if not self.role or self.role == "UNKNOWN":
            return ["UNKNOWN"]
        return [r.strip() for r in self.role.split(",") if r.strip()]

    def has_role(self, role: str) -> bool:
        """Проверка наличия роли у пользователя"""
        return role in self.get_roles()

    def add_role(self, role: str) -> str:
        """Добавление роли пользователю"""
        roles = self.get_roles()
        if "UNKNOWN" in roles:
            roles.remove("UNKNOWN")
        if role not in roles:
            roles.append(role)
        self.role = ",".join(sorted(roles))
        return self.role

    def remove_role(self, role: str) -> str:
        """Удаление роли у пользователя"""
        roles = self.get_roles()
        if role in roles:
            roles.remove(role)
        if not roles:
            roles = ["UNKNOWN"]
        self.role = ",".join(sorted(roles))
        return self.role

    def get_primary_role(self) -> str:
        """Получение основной роли"""
        roles = self.get_roles()
        priority = ["ADMIN", "DISPATCHER", "MASTER", "UNKNOWN"]
        for p_role in priority:
            if p_role in roles:
                return p_role
        return "UNKNOWN"

    def get_display_name(self) -> str:
        """Получение отображаемого имени"""
        if self.username:
            return f"@{self.username}"

        full_name = ""
        if self.first_name:
            full_name += self.first_name
        if self.last_name:
            if full_name:
                full_name += " "
            full_name += self.last_name

        return full_name or f"User #{self.telegram_id}"


class Master(Base):
    """Модель мастера в SQLAlchemy"""

    __tablename__ = "masters"

    # Основные поля
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.telegram_id"), unique=True, nullable=False
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    specialization: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    work_chat_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="masters")
    assigned_orders: Mapped[list["Order"]] = relationship("Order", back_populates="assigned_master")

    # Индексы и ограничения
    __table_args__ = (
        Index("idx_masters_telegram_id", "telegram_id"),
        Index("idx_masters_is_approved", "is_approved"),
        Index("idx_masters_deleted_at", "deleted_at"),
        Index("idx_masters_active_approved", "is_active", "is_approved"),
        Index("idx_masters_work_chat", "work_chat_id"),
        CheckConstraint("telegram_id > 0", name="chk_masters_telegram_id"),
        CheckConstraint("is_active IN (0, 1)", name="chk_masters_is_active"),
        CheckConstraint("is_approved IN (0, 1)", name="chk_masters_is_approved"),
        CheckConstraint(
            "phone LIKE '+%' OR phone LIKE '8%' OR phone LIKE '7%'", name="chk_masters_phone"
        ),
    )

    def get_display_name(self) -> str:
        """Получение отображаемого имени мастера"""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.first_name or self.user.username or f"ID: {self.telegram_id}"


class Order(Base):
    """Модель заявки в SQLAlchemy"""

    __tablename__ = "orders"

    # Основные поля
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipment_type: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_address: Mapped[str] = mapped_column(Text, nullable=False)
    client_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="NEW")

    # Связи с пользователями
    assigned_master_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("masters.id"), nullable=True
    )
    dispatcher_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.telegram_id"), nullable=True
    )

    # Дополнительные поля
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scheduled_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Финансовые поля
    total_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    materials_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    master_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    company_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    has_review: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    out_of_city: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    estimated_completion_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prepayment_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Поля для переноса
    rescheduled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_rescheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reschedule_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Системные поля
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    # Связи
    assigned_master: Mapped[Optional["Master"]] = relationship(
        "Master", back_populates="assigned_orders"
    )
    dispatcher: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[dispatcher_id], back_populates="created_orders"
    )
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory", back_populates="order"
    )

    # Индексы и ограничения
    __table_args__ = (
        Index("idx_orders_status", "status"),
        Index("idx_orders_assigned_master_id", "assigned_master_id"),
        Index("idx_orders_dispatcher_id", "dispatcher_id"),
        Index("idx_orders_deleted_at", "deleted_at"),
        Index("idx_orders_status_created", "status", "created_at"),
        Index("idx_orders_master_status", "assigned_master_id", "status"),
        Index("idx_orders_period", "updated_at", "status"),
        Index("idx_orders_financial", "status", "total_amount"),
        Index("idx_orders_review", "has_review", "status"),
        CheckConstraint(
            "status IN ('NEW', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED', 'REFUSED')",
            name="chk_orders_status",
        ),
        CheckConstraint(
            "total_amount IS NULL OR total_amount >= 0", name="chk_orders_total_amount"
        ),
        CheckConstraint(
            "materials_cost IS NULL OR materials_cost >= 0", name="chk_orders_materials_cost"
        ),
        CheckConstraint(
            "master_profit IS NULL OR master_profit >= 0", name="chk_orders_master_profit"
        ),
        CheckConstraint(
            "company_profit IS NULL OR company_profit >= 0", name="chk_orders_company_profit"
        ),
        CheckConstraint("has_review IN (0, 1) OR has_review IS NULL", name="chk_orders_has_review"),
        CheckConstraint("rescheduled_count >= 0", name="chk_orders_rescheduled_count"),
    )


class OrderStatusHistory(Base):
    """Модель истории изменений статусов заявок"""

    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    old_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.telegram_id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Связи
    order: Mapped["Order"] = relationship("Order", back_populates="status_history")
    changed_by_user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="status_changes"
    )

    # Индексы
    __table_args__ = (
        Index("idx_status_history_order", "order_id", "changed_at"),
        Index("idx_status_history_changed_at", "changed_at"),
        Index("idx_status_history_changed_by", "changed_by"),
    )


class AuditLog(Base):
    """Модель лога аудита"""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.telegram_id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Связи
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    # Индексы
    __table_args__ = (
        Index("idx_audit_user_id", "user_id"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_log_deleted_at", "deleted_at"),
    )


class FinancialReport(Base):
    """Модель финансового отчета"""

    __tablename__ = "financial_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # DAILY, WEEKLY, MONTHLY
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_materials_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_net_profit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_company_profit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_master_profit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_check: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Связи
    master_reports: Mapped[list["MasterFinancialReport"]] = relationship(
        "MasterFinancialReport", back_populates="report"
    )


class MasterFinancialReport(Base):
    """Модель отчета по мастеру"""

    __tablename__ = "master_financial_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("financial_reports.id"), nullable=False
    )
    master_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("masters.id"), nullable=True
    )
    master_name: Mapped[str] = mapped_column(String(255), nullable=False)
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_materials_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_net_profit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_master_profit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_company_profit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_check: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reviews_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_of_city_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Связи
    report: Mapped["FinancialReport"] = relationship(
        "FinancialReport", back_populates="master_reports"
    )
    master: Mapped[Optional["Master"]] = relationship("Master")


class EntityHistory(Base):
    """Модель истории изменений сущностей"""

    __tablename__ = "entity_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(50), nullable=False)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.telegram_id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Связи
    changed_by_user: Mapped[Optional["User"]] = relationship("User")

    # Индексы
    __table_args__ = (
        Index("idx_entity_history_table_record", "table_name", "record_id"),
        Index("idx_entity_history_changed_at", "changed_at"),
        Index("idx_entity_history_changed_by", "changed_by"),
    )
