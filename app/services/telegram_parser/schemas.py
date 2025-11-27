"""
Pydantic схемы для валидации данных парсера

Содержит модели для валидации распарсенных заявок и результатов парсинга.
"""

from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, Field, field_validator


class OrderParsed(BaseModel):
    """
    Модель распарсенной заявки из Telegram-группы.

    Представляет структурированные данные, извлечённые из текстового сообщения.
    Используется для валидации перед созданием заявки в БД.
    """

    equipment_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Тип оборудования (нормализованный)",
    )

    problem_description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Описание проблемы",
    )

    address: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Адрес клиента (обязательное поле)",
    )

    client_name: str = Field(
        default="Клиент",
        max_length=100,
        description="Имя клиента (по умолчанию 'Клиент')",
    )

    phone: str | None = Field(
        default=None,
        max_length=20,
        description="Телефон клиента (опционально)",
    )

    scheduled_time: str | None = Field(
        default=None,
        max_length=100,
        description="Время выезда/ремонта (опционально)",
    )

    raw_message: str = Field(
        ...,
        description="Исходное сообщение из Telegram",
    )

    message_id: int = Field(
        ...,
        description="ID сообщения в Telegram",
    )

    @field_validator("equipment_type")
    @classmethod
    def validate_equipment_type(cls, v: str) -> str:
        """Валидация типа оборудования"""
        if not v or not v.strip():
            raise ValueError("Тип оборудования не может быть пустым")
        return v.strip()

    @field_validator("problem_description")
    @classmethod
    def validate_problem_description(cls, v: str) -> str:
        """Валидация описания проблемы"""
        if not v or not v.strip():
            raise ValueError("Описание проблемы не может быть пустым")
        return v.strip()

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Валидация адреса"""
        if not v or not v.strip():
            raise ValueError("Адрес не может быть пустым")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Валидация телефона (если указан)"""
        if v is None:
            return None
        # Проверяем что есть хотя бы 10 цифр
        digits = "".join(filter(str.isdigit, v))
        if len(digits) < 10:
            raise ValueError("Телефон должен содержать минимум 10 цифр")
        return v.strip()

    class Config:
        """Конфигурация Pydantic модели"""

        json_schema_extra: ClassVar[dict] = {
            "example": {
                "equipment_type": "Стиральная машина",
                "problem_description": "Не крутит барабан, шумит при отжиме",
                "address": "ул. Ленина 5, кв. 10",
                "client_name": "Клиент",
                "phone": "+79001234567",
                "scheduled_time": "завтра к 14:00",
                "raw_message": "С/м не крутит барабан. ул. Ленина 5-10. +79001234567 завтра к 14:00",
                "message_id": 12345,
            }
        }


class ParseResult(BaseModel):
    """
    Результат парсинга сообщения из Telegram-группы.

    Содержит либо успешно распарсенную заявку, либо информацию об ошибке.
    """

    success: bool = Field(
        ...,
        description="Успешность парсинга",
    )

    status: Literal["success", "missing_fields", "invalid_format", "error"] = Field(
        ...,
        description="Статус парсинга",
    )

    data: OrderParsed | None = Field(
        default=None,
        description="Распарсенные данные (если success=True)",
    )

    error_message: str | None = Field(
        default=None,
        description="Сообщение об ошибке (если success=False)",
    )

    missing_fields: list[str] = Field(
        default_factory=list,
        description="Список пропущенных обязательных полей",
    )

    parsed_at: datetime = Field(
        default_factory=datetime.now,
        description="Время парсинга",
    )

    @field_validator("data")
    @classmethod
    def validate_data_with_success(cls, v: OrderParsed | None, info) -> OrderParsed | None:
        """Проверка консистентности data и success"""
        # Получаем значение success из values
        success = info.data.get("success")

        if success and v is None:
            raise ValueError("При success=True должны быть переданы data")
        if not success and v is not None:
            raise ValueError("При success=False data должны быть None")
        return v

    class Config:
        """Конфигурация Pydantic модели"""

        json_schema_extra: ClassVar[dict] = {
            "examples": [
                {
                    "success": True,
                    "status": "success",
                    "data": {
                        "equipment_type": "Стиральная машина",
                        "problem_description": "Не крутит барабан",
                        "address": "ул. Ленина 5, кв. 10",
                        "client_name": "Клиент",
                        "phone": "+79001234567",
                        "scheduled_time": "завтра к 14:00",
                        "raw_message": "С/м не крутит. ул. Ленина 5-10. +79001234567",
                        "message_id": 12345,
                    },
                    "error_message": None,
                    "missing_fields": [],
                },
                {
                    "success": False,
                    "status": "missing_fields",
                    "data": None,
                    "error_message": "Не удалось определить адрес",
                    "missing_fields": ["address"],
                },
            ]
        }


class ConfirmationData(BaseModel):
    """
    Данные для подтверждения создания заявки.

    Используется в inline-кнопках бота после парсинга сообщения.
    """

    message_id: int = Field(
        ...,
        description="ID исходного сообщения в Telegram",
    )

    parsed_order: OrderParsed = Field(
        ...,
        description="Распарсенная заявка для подтверждения",
    )

    confirmation_message_id: int | None = Field(
        default=None,
        description="ID сообщения с кнопками подтверждения",
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Время создания запроса на подтверждение",
    )

    class Config:
        """Конфигурация Pydantic модели"""

        json_schema_extra: ClassVar[dict] = {
            "example": {
                "message_id": 12345,
                "parsed_order": {
                    "equipment_type": "Стиральная машина",
                    "problem_description": "Не крутит барабан",
                    "address": "ул. Ленина 5, кв. 10",
                    "client_name": "Клиент",
                    "phone": "+79001234567",
                    "scheduled_time": None,
                    "raw_message": "С/м не крутит. ул. Ленина 5-10. +79001234567",
                    "message_id": 12345,
                },
                "confirmation_message_id": 12346,
            }
        }
