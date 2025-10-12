"""Pydantic схемы для валидации заявок (Orders)"""
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import MAX_DESCRIPTION_LENGTH, MAX_NOTES_LENGTH, EquipmentType


class OrderCreateSchema(BaseModel):
    """Схема для создания заявки с полной валидацией"""
    
    equipment_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Тип техники"
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=MAX_DESCRIPTION_LENGTH,
        description="Описание проблемы"
    )
    client_name: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="ФИО клиента"
    )
    client_address: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Адрес клиента"
    )
    client_phone: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="Телефон клиента"
    )
    notes: Optional[str] = Field(
        None,
        max_length=MAX_NOTES_LENGTH,
        description="Дополнительные заметки"
    )
    scheduled_time: Optional[str] = Field(
        None,
        max_length=100,
        description="Время прибытия к клиенту"
    )
    dispatcher_id: int = Field(
        ...,
        gt=0,
        description="ID диспетчера создавшего заявку"
    )
    
    @field_validator('equipment_type')
    @classmethod
    def validate_equipment_type(cls, v: str) -> str:
        """Валидация типа техники - должен быть из списка"""
        valid_types = EquipmentType.all_types()
        if v not in valid_types:
            raise ValueError(
                f"Недопустимый тип техники. Допустимые: {', '.join(valid_types)}"
            )
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Валидация описания проблемы"""
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Описание слишком короткое. Минимум 10 символов")
        
        # Проверка на подозрительные паттерны (базовая защита от SQL injection)
        suspicious_patterns = [
            r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER)\s+",
            r"--",
            r"/\*.*\*/",
            r"UNION\s+SELECT",
        ]
        for pattern in suspicious_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Описание содержит недопустимые символы")
        
        return v
    
    @field_validator('client_name')
    @classmethod
    def validate_client_name(cls, v: str) -> str:
        """Валидация имени клиента"""
        v = v.strip()
        
        # Минимум 5 символов
        if len(v) < 5:
            raise ValueError("Имя клиента слишком короткое (минимум 5 символов)")
        
        # Проверяем что содержит хотя бы одну букву
        if not re.search(r"[А-Яа-яЁёA-Za-z]", v):
            raise ValueError("Имя должно содержать буквы")
        
        return v
    
    @field_validator('client_address')
    @classmethod
    def validate_client_address(cls, v: str) -> str:
        """Валидация адреса клиента"""
        v = v.strip()
        
        if len(v) < 10:
            raise ValueError("Адрес слишком короткий. Минимум 10 символов")
        
        # Проверка что адрес содержит хотя бы одну цифру (номер дома)
        if not re.search(r"\d", v):
            raise ValueError("Адрес должен содержать номер дома")
        
        return v
    
    @field_validator('client_phone')
    @classmethod
    def validate_client_phone(cls, v: str) -> str:
        """Валидация и форматирование телефона"""
        # Удаляем все символы кроме цифр и +
        cleaned = re.sub(r"[^\d+]", "", v.strip())
        
        # Проверяем основные форматы
        patterns = [
            r"^\+7\d{10}$",  # +79001234567
            r"^8\d{10}$",    # 89001234567
            r"^7\d{10}$",    # 79001234567
        ]
        
        valid = any(re.match(pattern, cleaned) for pattern in patterns)
        if not valid:
            raise ValueError(
                "Неверный формат телефона. Ожидается: +7XXXXXXXXXX или 8XXXXXXXXXX"
            )
        
        # Форматируем в единый формат +7XXXXXXXXXX
        if cleaned.startswith("8") and len(cleaned) == 11:
            cleaned = "+7" + cleaned[1:]
        elif cleaned.startswith("7") and len(cleaned) == 11:
            cleaned = "+" + cleaned
        
        return cleaned
    
    @field_validator('scheduled_time')
    @classmethod
    def validate_scheduled_time(cls, v: Optional[str]) -> Optional[str]:
        """Валидация времени прибытия"""
        if v is None:
            return None
            
        v = v.strip()
        if not v:
            return None
            
        # Проверяем основные форматы времени
        patterns = [
            r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",  # 14:30, 9:00
            r"^завтра\s+([01]?[0-9]|2[0-3]):[0-5][0-9]$",  # завтра 14:30
            r"^послезавтра\s+([01]?[0-9]|2[0-3]):[0-5][0-9]$",  # послезавтра 14:30
            r"^сегодня\s+([01]?[0-9]|2[0-3]):[0-5][0-9]$",  # сегодня 14:30
            r"^\d{1,2}\.\d{1,2}\.\d{4}\s+([01]?[0-9]|2[0-3]):[0-5][0-9]$",  # 15.10.2025 14:30
        ]
        
        valid = any(re.match(pattern, v, re.IGNORECASE) for pattern in patterns)
        if not valid:
            raise ValueError(
                "Неверный формат времени. Ожидается: 14:30, завтра 10:00, 15.10.2025 14:30"
            )
        
        return v
    
    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Валидация заметок"""
        if v is None:
            return None
        
        v = v.strip()
        if not v:  # Пустая строка после strip
            return None
        
        if len(v) > MAX_NOTES_LENGTH:
            raise ValueError(f"Заметки слишком длинные. Максимум {MAX_NOTES_LENGTH} символов")
        
        return v
    
    @model_validator(mode='after')
    def validate_full_order(self):
        """Финальная валидация всей заявки"""
        # Дополнительная проверка что все обязательные поля заполнены
        required_fields = [
            'equipment_type',
            'description',
            'client_name',
            'client_address',
            'client_phone',
            'dispatcher_id'
        ]
        
        for field in required_fields:
            value = getattr(self, field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Поле {field} обязательно для заполнения")
        
        return self
    
    class Config:
        """Конфигурация Pydantic схемы"""
        str_strip_whitespace = True  # Автоматически убирать пробелы
        validate_assignment = True   # Валидировать при присваивании
        from_attributes = True       # Поддержка ORM моделей


class OrderUpdateSchema(BaseModel):
    """Схема для обновления заявки (все поля опциональны)"""
    
    equipment_type: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=MAX_DESCRIPTION_LENGTH)
    client_name: Optional[str] = Field(None, min_length=5, max_length=200)
    client_address: Optional[str] = Field(None, min_length=10, max_length=500)
    client_phone: Optional[str] = Field(None, min_length=10, max_length=20)
    notes: Optional[str] = Field(None, max_length=MAX_NOTES_LENGTH)
    
    @field_validator('equipment_type')
    @classmethod
    def validate_equipment_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        valid_types = EquipmentType.all_types()
        if v not in valid_types:
            raise ValueError(f"Недопустимый тип техники. Допустимые: {', '.join(valid_types)}")
        return v
    
    @field_validator('client_phone')
    @classmethod
    def validate_client_phone(cls, v: Optional[str]) -> Optional[str]:
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
    
    class Config:
        str_strip_whitespace = True
        validate_assignment = True
        from_attributes = True


class OrderAmountsSchema(BaseModel):
    """Схема для обновления финансовой информации заявки"""
    
    total_amount: float = Field(
        ...,
        ge=0,
        description="Общая сумма заказа"
    )
    materials_cost: float = Field(
        ...,
        ge=0,
        description="Стоимость материалов"
    )
    has_review: bool = Field(
        default=False,
        description="Взят ли отзыв у клиента"
    )
    
    @model_validator(mode='after')
    def validate_amounts(self):
        """Валидация финансовых данных"""
        if self.materials_cost > self.total_amount:
            raise ValueError(
                "Стоимость материалов не может превышать общую сумму заказа"
            )
        
        # Предупреждение о нереалистичных суммах (можем логировать)
        if self.total_amount > 1_000_000:
            # Просто логируем, не падаем
            pass
        
        return self
    
    class Config:
        validate_assignment = True

