"""Pydantic схемы для валидации мастеров"""
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MasterCreateSchema(BaseModel):
    """Схема для создания/регистрации мастера"""
    
    telegram_id: int = Field(
        ...,
        gt=0,
        description="Telegram ID мастера"
    )
    phone: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="Телефон мастера"
    )
    specialization: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Специализация мастера"
    )
    is_approved: bool = Field(
        default=False,
        description="Одобрен ли мастер администратором"
    )
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Валидация телефона мастера"""
        cleaned = re.sub(r"[^\d+]", "", v.strip())
        
        patterns = [
            r"^\+7\d{10}$",
            r"^8\d{10}$",
            r"^7\d{10}$",
        ]
        
        if not any(re.match(pattern, cleaned) for pattern in patterns):
            raise ValueError("Неверный формат телефона")
        
        # Форматируем
        if cleaned.startswith("8") and len(cleaned) == 11:
            cleaned = "+7" + cleaned[1:]
        elif cleaned.startswith("7") and len(cleaned) == 11:
            cleaned = "+" + cleaned
        
        return cleaned
    
    @field_validator('specialization')
    @classmethod
    def validate_specialization(cls, v: str) -> str:
        """Валидация специализации"""
        v = v.strip()
        
        if len(v) < 3:
            raise ValueError("Специализация слишком короткая (минимум 3 символа)")
        
        # Проверка что содержит хотя бы одну букву
        if not re.search(r"[А-Яа-яA-Za-z]", v):
            raise ValueError("Специализация должна содержать буквы")
        
        return v
    
    @field_validator('telegram_id')
    @classmethod
    def validate_telegram_id(cls, v: int) -> int:
        """Валидация Telegram ID"""
        # Telegram ID всегда положительные числа
        if v <= 0:
            raise ValueError("Telegram ID должен быть положительным числом")
        
        # Проверка разумного диапазона (Telegram IDs обычно 9-10 цифр)
        if v > 10_000_000_000:  # 10 миллиардов
            raise ValueError("Telegram ID слишком большой")
        
        return v
    
    class Config:
        str_strip_whitespace = True
        validate_assignment = True
        from_attributes = True


class MasterUpdateSchema(BaseModel):
    """Схема для обновления данных мастера"""
    
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    specialization: Optional[str] = Field(None, min_length=3, max_length=200)
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None
    work_chat_id: Optional[int] = None
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        
        cleaned = re.sub(r"[^\d+]", "", v.strip())
        patterns = [r"^\+7\d{10}$", r"^8\d{10}$", r"^7\d{10}$"]
        
        if not any(re.match(pattern, cleaned) for pattern in patterns):
            raise ValueError("Неверный формат телефона")
        
        if cleaned.startswith("8") and len(cleaned) == 11:
            cleaned = "+7" + cleaned[1:]
        elif cleaned.startswith("7") and len(cleaned) == 11:
            cleaned = "+" + cleaned
        
        return cleaned
    
    @field_validator('specialization')
    @classmethod
    def validate_specialization(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Специализация слишком короткая")
        
        return v
    
    @field_validator('work_chat_id')
    @classmethod
    def validate_work_chat_id(cls, v: Optional[int]) -> Optional[int]:
        """Валидация ID рабочего чата"""
        if v is None:
            return None
        
        # Групповые чаты в Telegram имеют отрицательные ID
        # Обычно начинаются с -100
        if v >= 0:
            raise ValueError("ID группового чата должен быть отрицательным")
        
        return v
    
    class Config:
        str_strip_whitespace = True
        validate_assignment = True
        from_attributes = True

