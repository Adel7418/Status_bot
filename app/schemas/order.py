"""Pydantic схемы для валидации заявок (Orders)"""
import re

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import MAX_DESCRIPTION_LENGTH, MAX_NOTES_LENGTH, EquipmentType


class OrderCreateSchema(BaseModel):
    """Схема для создания заявки с полной валидацией"""

    equipment_type: str = Field(..., min_length=1, max_length=100, description="Тип техники")
    description: str = Field(
        ..., min_length=4, max_length=MAX_DESCRIPTION_LENGTH, description="Описание проблемы"
    )
    client_name: str = Field(..., min_length=2, max_length=200, description="ФИО клиента")
    client_address: str = Field(..., min_length=4, max_length=500, description="Адрес клиента")
    client_phone: str = Field(..., min_length=10, max_length=20, description="Телефон клиента")
    notes: str | None = Field(
        None, max_length=MAX_NOTES_LENGTH, description="Дополнительные заметки"
    )
    scheduled_time: str | None = Field(None, max_length=100, description="Время прибытия к клиенту")
    dispatcher_id: int = Field(..., gt=0, description="ID диспетчера создавшего заявку")

    @field_validator("equipment_type")
    @classmethod
    def validate_equipment_type(cls, v: str) -> str:
        """Валидация типа техники - должен быть из списка"""
        valid_types = EquipmentType.all_types()
        if v not in valid_types:
            raise ValueError(f"Недопустимый тип техники. Допустимые: {', '.join(valid_types)}")
        return v

    @field_validator("client_name")
    @classmethod
    def validate_client_name(cls, v: str) -> str:
        """Валидация имени клиента"""
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"[SCHEMA_DEBUG] Validating client_name: '{v}', length: {len(v)}")

        v = v.strip()
        if len(v) < 2:
            logger.error(f"[SCHEMA_DEBUG] client_name too short: '{v}', length: {len(v)}")
            raise ValueError("Имя клиента слишком короткое (минимум 2 символа)")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Валидация описания проблемы"""
        v = v.strip()
        if len(v) < 4:
            raise ValueError("Описание слишком короткое. Минимум 4 символа")

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

    @field_validator("client_address")
    @classmethod
    def validate_client_address(cls, v: str) -> str:
        """Валидация адреса клиента"""
        v = v.strip()

        if len(v) < 4:
            raise ValueError("Адрес слишком короткий. Минимум 4 символа")

        # Проверка что адрес содержит хотя бы одну цифру (номер дома)
        if not re.search(r"\d", v):
            raise ValueError("Адрес должен содержать номер дома")

        return v

    @field_validator("client_phone")
    @classmethod
    def validate_client_phone(cls, v: str) -> str:
        """Валидация и форматирование телефона"""
        # Удаляем все символы кроме цифр и +
        cleaned = re.sub(r"[^\d+]", "", v.strip())

        # Проверяем основные форматы
        patterns = [
            r"^\+7\d{10}$",  # +79001234567
            r"^8\d{10}$",  # 89001234567
            r"^7\d{10}$",  # 79001234567
        ]

        valid = any(re.match(pattern, cleaned) for pattern in patterns)
        if not valid:
            raise ValueError("Неверный формат телефона. Ожидается: +7XXXXXXXXXX или 8XXXXXXXXXX")

        # Форматируем в единый формат +7XXXXXXXXXX
        if cleaned.startswith("8") and len(cleaned) == 11:
            cleaned = "+7" + cleaned[1:]
        elif cleaned.startswith("7") and len(cleaned) == 11:
            cleaned = "+" + cleaned

        return cleaned

    @field_validator("scheduled_time")
    @classmethod
    def validate_scheduled_time(cls, v: str | None) -> str | None:
        """Валидация времени прибытия (гибкий формат)"""
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        # Проверка длины (минимум 3 символа, максимум 100)
        if len(v) < 3:
            raise ValueError("Время/инструкция слишком короткие (минимум 3 символа)")

        if len(v) > 100:
            raise ValueError("Время/инструкция слишком длинные (максимум 100 символов)")

        # Проверка на SQL injection и опасные символы
        dangerous_patterns = [
            r";\s*(drop|delete|truncate|insert|update|alter)\s+",
            r"--",
            r"/\*.*\*/",
            r"xp_",
            r"sp_",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Недопустимые символы в тексте")

        # Допускаются любые текстовые инструкции:
        # - Конкретное время: "14:30", "завтра 10:00", "15.10.2025 16:00"
        # - Инструкции: "Набрать клиенту", "После 14:00", "Уточнить у клиента"
        # - Относительное время: "Через 2 часа", "В течение дня"

        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str | None) -> str | None:
        """Валидация заметок"""
        if v is None:
            return None

        v = v.strip()
        if not v:  # Пустая строка после strip
            return None

        if len(v) > MAX_NOTES_LENGTH:
            raise ValueError(f"Заметки слишком длинные. Максимум {MAX_NOTES_LENGTH} символов")

        return v

    @model_validator(mode="after")
    def validate_full_order(self):
        """Финальная валидация всей заявки"""
        # Дополнительная проверка что все обязательные поля заполнены
        required_fields = [
            "equipment_type",
            "description",
            "client_name",
            "client_address",
            "client_phone",
            "dispatcher_id",
        ]

        for field in required_fields:
            value = getattr(self, field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Поле {field} обязательно для заполнения")

        return self

    class Config:
        """Конфигурация Pydantic схемы"""

        str_strip_whitespace = True  # Автоматически убирать пробелы
        validate_assignment = True  # Валидировать при присваивании
        from_attributes = True  # Поддержка ORM моделей


class OrderUpdateSchema(BaseModel):
    """Схема для обновления заявки (все поля опциональны)"""

    equipment_type: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=4, max_length=MAX_DESCRIPTION_LENGTH)
    client_name: str | None = Field(None, min_length=2, max_length=200)
    client_address: str | None = Field(None, min_length=4, max_length=500)
    client_phone: str | None = Field(None, min_length=10, max_length=20)
    notes: str | None = Field(None, max_length=MAX_NOTES_LENGTH)

    @field_validator("equipment_type")
    @classmethod
    def validate_equipment_type(cls, v: str | None) -> str | None:
        if v is None:
            return None
        valid_types = EquipmentType.all_types()
        if v not in valid_types:
            raise ValueError(f"Недопустимый тип техники. Допустимые: {', '.join(valid_types)}")
        return v

    @field_validator("client_phone")
    @classmethod
    def validate_client_phone(cls, v: str | None) -> str | None:
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

    total_amount: float = Field(..., ge=0, description="Общая сумма заказа")
    materials_cost: float = Field(..., ge=0, description="Стоимость материалов")
    has_review: bool = Field(default=False, description="Взят ли отзыв у клиента")

    @model_validator(mode="after")
    def validate_amounts(self):
        """Валидация финансовых данных"""
        if self.materials_cost > self.total_amount:
            raise ValueError("Стоимость материалов не может превышать общую сумму заказа")

        # Предупреждение о нереалистичных суммах (можем логировать)
        if self.total_amount > 1_000_000:
            # Просто логируем, не падаем
            pass

        return self

    class Config:
        validate_assignment = True
