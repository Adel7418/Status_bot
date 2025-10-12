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
    role: str = "UNKNOWN"  # Роли хранятся через запятую, например: "DISPATCHER,MASTER"
    created_at: Optional[datetime] = None
    
    def get_full_name(self) -> str:
        """Получение полного имени"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or f"ID: {self.telegram_id}"
    
    def get_roles(self) -> list[str]:
        """
        Получение списка ролей пользователя
        
        Returns:
            Список ролей
        """
        if not self.role or self.role == "UNKNOWN":
            return ["UNKNOWN"]
        return [r.strip() for r in self.role.split(",") if r.strip()]
    
    def has_role(self, role: str) -> bool:
        """
        Проверка наличия роли у пользователя
        
        Args:
            role: Роль для проверки
            
        Returns:
            True если роль есть
        """
        return role in self.get_roles()
    
    def add_role(self, role: str) -> str:
        """
        Добавление роли пользователю
        
        Args:
            role: Роль для добавления
            
        Returns:
            Обновленная строка ролей
        """
        roles = self.get_roles()
        if "UNKNOWN" in roles:
            roles.remove("UNKNOWN")
        if role not in roles:
            roles.append(role)
        self.role = ",".join(sorted(roles))
        return self.role
    
    def remove_role(self, role: str) -> str:
        """
        Удаление роли у пользователя
        
        Args:
            role: Роль для удаления
            
        Returns:
            Обновленная строка ролей
        """
        roles = self.get_roles()
        if role in roles:
            roles.remove(role)
        if not roles:
            roles = ["UNKNOWN"]
        self.role = ",".join(sorted(roles))
        return self.role
    
    def get_primary_role(self) -> str:
        """
        Получение основной роли (для обратной совместимости)
        Приоритет: ADMIN > DISPATCHER > MASTER > UNKNOWN
        
        Returns:
            Основная роль
        """
        roles = self.get_roles()
        priority = ["ADMIN", "DISPATCHER", "MASTER", "UNKNOWN"]
        for p_role in priority:
            if p_role in roles:
                return p_role
        return "UNKNOWN"


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
    total_amount: Optional[float] = None  # Общая сумма заказа
    materials_cost: Optional[float] = None  # Сумма расходного материала
    master_profit: Optional[float] = None  # Прибыль мастера
    company_profit: Optional[float] = None  # Прибыль компании
    has_review: Optional[bool] = None  # Взял ли мастер отзыв у клиента
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

