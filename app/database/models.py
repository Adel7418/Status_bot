"""
Модели данных
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Модель пользователя"""
    id: Optional[int] = None
    telegram_id: int = 0
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "UNKNOWN"
    created_at: Optional[datetime] = None
    
    def get_full_name(self) -> str:
        """Получение полного имени"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or f"ID: {self.telegram_id}"


@dataclass
class Master:
    """Модель мастера"""
    id: Optional[int] = None
    telegram_id: int = 0
    phone: str = ""
    specialization: str = ""
    is_active: bool = True
    is_approved: bool = False
    work_chat_id: Optional[int] = None  # ID рабочей группы с мастером
    created_at: Optional[datetime] = None
    
    # Дополнительные поля из join с users
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    def get_display_name(self) -> str:
        """Получение отображаемого имени мастера"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or f"ID: {self.telegram_id}"


@dataclass
class Order:
    """Модель заявки"""
    id: Optional[int] = None
    equipment_type: str = ""
    description: str = ""
    client_name: str = ""
    client_address: str = ""
    client_phone: str = ""
    status: str = "NEW"
    assigned_master_id: Optional[int] = None
    dispatcher_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Дополнительные поля из join
    master_name: Optional[str] = None
    dispatcher_name: Optional[str] = None


@dataclass
class AuditLog:
    """Модель лога аудита"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    action: str = ""
    details: Optional[str] = None
    timestamp: Optional[datetime] = None

