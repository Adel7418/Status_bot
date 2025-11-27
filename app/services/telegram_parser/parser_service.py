"""
Order Parser Service

Сервис для парсинга текстовых сообщений из Telegram-группы в структурированные заявки.
Использует regex паттерны, словарь сокращений и эвристики для извлечения данных.
"""

import logging

from pydantic import ValidationError

from .equipment_dict import normalize_equipment_type
from .patterns import (
    contains_time_indicator,
    extract_phone,
    looks_like_address,
    normalize_phone,
)
from .schemas import OrderParsed, ParseResult


logger = logging.getLogger(__name__)


class OrderParserService:
    """
    Сервис парсинга заявок из неформализованных текстовых сообщений.

    Основная логика парсинга:
    1. Разбить текст на строки
    2. Извлечь телефон (если есть)
    3. Извлечь временной индикатор (если есть)
    4. Разделить оставшееся на: оборудование/проблема и адрес
    5. Нормализовать тип оборудования через словарь
    6. Валидировать результат через Pydantic
    """

    def __init__(self) -> None:
        """Инициализация сервиса парсинга"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse_message(self, text: str, message_id: int) -> ParseResult:  # noqa: PLR0911
        """
        Парсит текстовое сообщение в структурированную заявку.

        Args:
            text: Текст сообщения из Telegram
            message_id: ID сообщения в Telegram

        Returns:
            ParseResult с результатом парсинга (success/failure)

        Example:
            >>> service = OrderParserService()
            >>> result = service.parse_message(
            ...     "С/м не крутит барабан. ул. Ленина 5-10. +79001234567",
            ...     message_id=12345
            ... )
            >>> result.success
            True
            >>> result.data.equipment_type
            "Стиральная машина"
        """
        try:
            # Шаг 1: Предобработка текста
            lines = self._split_into_lines(text)
            if not lines:
                return self._create_error_result(
                    "Пустое сообщение",
                    "invalid_format",
                    [],
                )

            # Шаг 2: Извлечь телефон
            phone = self._extract_phone_from_lines(lines)
            if phone:
                phone = normalize_phone(phone)
                # Удаляем строку с телефоном из lines
                lines = [line for line in lines if phone.replace("+", "") not in line.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")]

            # Шаг 3: Извлечь временной индикатор
            scheduled_time = self._extract_time_from_lines(lines)
            if scheduled_time:
                # Удаляем строки с временным индикатором
                lines = [line for line in lines if not contains_time_indicator(line)]

            # Шаг 4: Разделить на оборудование/проблема и адрес
            equipment_problem, address = self._split_equipment_and_address(lines)

            if not equipment_problem:
                return self._create_error_result(
                    "Не удалось определить тип оборудования или проблему",
                    "missing_fields",
                    ["equipment_type", "problem_description"],
                )

            if not address:
                return self._create_error_result(
                    "Не удалось определить адрес",
                    "missing_fields",
                    ["address"],
                )

            # Шаг 5: Извлечь тип оборудования из equipment_problem
            equipment_type = self._extract_equipment_type(equipment_problem)
            if not equipment_type:
                return self._create_error_result(
                    "Не удалось определить тип оборудования",
                    "missing_fields",
                    ["equipment_type"],
                )

            # Шаг 6: Остаток от equipment_problem — это описание проблемы
            problem_description = self._extract_problem_description(equipment_problem, equipment_type)
            if not problem_description:
                return self._create_error_result(
                    "Не удалось определить описание проблемы",
                    "missing_fields",
                    ["problem_description"],
                )

            # Шаг 7: Создаём OrderParsed и валидируем через Pydantic
            try:
                order_data = OrderParsed(
                    equipment_type=equipment_type,
                    problem_description=problem_description,
                    address=address,
                    client_name="Клиент",  # По умолчанию
                    phone=phone,
                    scheduled_time=scheduled_time,
                    raw_message=text,
                    message_id=message_id,
                )

                return ParseResult(
                    success=True,
                    status="success",
                    data=order_data,
                    error_message=None,
                    missing_fields=[],
                )

            except ValidationError as e:
                self.logger.warning(f"Ошибка валидации Pydantic: {e}")
                return self._create_error_result(
                    f"Ошибка валидации данных: {e!s}",
                    "invalid_format",
                    [],
                )

        except Exception as e:
            self.logger.exception(f"Неожиданная ошибка парсинга: {e}")
            return self._create_error_result(
                f"Внутренняя ошибка парсинга: {e!s}",
                "error",
                [],
            )

    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================

    def _split_into_lines(self, text: str) -> list[str]:
        """
        Разбивает текст на строки и очищает их.

        Args:
            text: Исходный текст

        Returns:
            Список непустых строк
        """
        lines = [line.strip() for line in text.split("\n")]
        # Убираем пустые строки
        lines = [line for line in lines if line]

        # Если только одна строка - попробуем разбить по точкам
        if len(lines) == 1:
            # Разбиваем по точкам, но только если точка не в середине числа (вроде 14.00)
            parts = []
            for part in lines[0].split("."):
                part = part.strip()
                if part:
                    parts.append(part)
            # Используем разбиение по точкам, если получилось > 1 части
            if len(parts) > 1:
                return parts

        return lines

    def _extract_phone_from_lines(self, lines: list[str]) -> str | None:
        """
        Извлекает телефон из списка строк.

        Args:
            lines: Список строк сообщения

        Returns:
            Телефонный номер или None
        """
        # Проверяем каждую строку
        for line in lines:
            phone = extract_phone(line)
            if phone:
                return phone

        # Если не нашли — пробуем весь текст целиком
        full_text = " ".join(lines)
        return extract_phone(full_text)

    def _extract_time_from_lines(self, lines: list[str]) -> str | None:
        """
        Извлекает временной индикатор из списка строк.

        Args:
            lines: Список строк сообщения

        Returns:
            Временной индикатор или None
        """
        time_indicators: list[str] = []

        for line in lines:
            if contains_time_indicator(line):
                time_indicators.append(line)

        if time_indicators:
            # Объединяем все временные индикаторы в одну строку
            return " ".join(time_indicators)

        return None

    def _split_equipment_and_address(self, lines: list[str]) -> tuple[str, str]:
        """
        Разделяет строки на оборудование/проблема и адрес.

        Эвристика:
        - Строки, похожие на адрес (содержат адресные ключевые слова или цифры) — это адрес
        - Остальные строки — оборудование и проблема

        Args:
            lines: Список строк сообщения (без телефона и времени)

        Returns:
            Кортеж (оборудование_проблема, адрес)
        """
        equipment_lines: list[str] = []
        address_lines: list[str] = []

        for line in lines:
            if looks_like_address(line):
                address_lines.append(line)
            else:
                equipment_lines.append(line)

        equipment_problem = " ".join(equipment_lines).strip()
        address = " ".join(address_lines).strip()

        return equipment_problem, address

    def _extract_equipment_type(self, equipment_problem: str) -> str:
        """
        Извлекает и нормализует тип оборудования из текста.

        Args:
            equipment_problem: Текст с оборудованием и проблемой

        Returns:
            Нормализованный тип оборудования
        """
        # Берём первое слово/фразу (обычно 1-2 слова или аббревиатуру)
        words = equipment_problem.split()
        if not words:
            return ""

        # Пробуем взять первое слово
        first_word = words[0]
        equipment_type = normalize_equipment_type(first_word)

        # Если первое слово дало результат - возвращаем
        if equipment_type != first_word.capitalize():
            return equipment_type

        # Если нет - пробуем первые два слова
        if len(words) >= 2:
            first_two = " ".join(words[:2])
            equipment_type = normalize_equipment_type(first_two)
            if equipment_type != first_two.capitalize():
                return equipment_type

        # Возвращаем результат нормализации первого слова
        return normalize_equipment_type(first_word)

    def _extract_problem_description(self, equipment_problem: str, equipment_type: str) -> str:
        """
        Извлекает описание проблемы из текста.

        Args:
            equipment_problem: Полный текст с оборудованием и проблемой
            equipment_type: Уже извлечённый тип оборудования

        Returns:
            Описание проблемы
        """
        # Убираем первое слово или первые два слова (оборудование) из начала
        words = equipment_problem.split()

        # Пытаемся найти, где заканчивается equipment type
        # Проверяем первое слово
        first_word = words[0] if words else ""
        normalized_first = normalize_equipment_type(first_word)

        if normalized_first == equipment_type:
            # Первое слово - это equipment, убираем его
            problem = " ".join(words[1:]).strip()
        elif len(words) >= 2:
            # Проверяем первые два слова
            first_two = " ".join(words[:2])
            normalized_two = normalize_equipment_type(first_two)
            if normalized_two == equipment_type:
                # Первые два слова - это equipment, убираем их
                problem = " ".join(words[2:]).strip()
            else:
                # Убираем только первое слово
                problem = " ".join(words[1:]).strip()
        else:
            problem = equipment_problem

        # Если после всех манипуляций пусто — возвращаем исходный текст
        if not problem or len(problem) < 3:
            problem = equipment_problem

        return problem

    def _create_error_result(
        self,
        error_message: str,
        status: str,
        missing_fields: list[str],
    ) -> ParseResult:
        """
        Создаёт ParseResult с ошибкой.

        Args:
            error_message: Сообщение об ошибке
            status: Статус ошибки
            missing_fields: Список пропущенных полей

        Returns:
            ParseResult с success=False
        """
        return ParseResult(
            success=False,
            status=status,
            data=None,
            error_message=error_message,
            missing_fields=missing_fields,
        )
