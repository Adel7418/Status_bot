"""Pydantic схемы для валидации пользователей"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.config import UserRole


class UserCreateSchema(BaseModel):
    """Схема для создания пользователя"""
    
    telegram_id: int = Field(
        ...,
        gt=0,
        description="Telegram ID пользователя"
    )
    username: Optional[str] = Field(
        None,
        min_length=5,
        max_length=32,
        description="Telegram username без @"
    )
    first_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Имя пользователя"
    )
    last_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Фамилия пользователя"
    )
    role: str = Field(
        default=UserRole.UNKNOWN,
        description="Роль пользователя"
    )
    
    @field_validator('telegram_id')
    @classmethod
    def validate_telegram_id(cls, v: int) -> int:
        """Валидация Telegram ID"""
        if v <= 0:
            raise ValueError("Telegram ID должен быть положительным числом")
        
        if v > 10_000_000_000:
            raise ValueError("Telegram ID слишком большой")
        
        return v
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Валидация username"""
        if v is None:
            return None
        
        v = v.strip()
        
        # Убираем @ если он есть
        if v.startswith("@"):
            v = v[1:]
        
        # Проверка формата username (буквы, цифры, подчеркивания)
        import re
        if not re.match(r"^[a-zA-Z0-9_]{5,32}$", v):
            raise ValueError(
                "Username должен содержать только буквы, цифры и подчеркивания (5-32 символа)"
            )
        
        return v
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Валидация роли пользователя"""
        # Роль может быть одна или несколько через запятую
        roles = [r.strip() for r in v.split(",")]
        valid_roles = UserRole.all_roles()
        
        for role in roles:
            if role not in valid_roles:
                raise ValueError(
                    f"Недопустимая роль: {role}. Допустимые: {', '.join(valid_roles)}"
                )
        
        return v
    
    class Config:
        str_strip_whitespace = True
        validate_assignment = True
        from_attributes = True

