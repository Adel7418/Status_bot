"""
Централизованные стили для Excel-отчетов
"""

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


class ExcelStyles:
    """Централизованные стили для Excel-отчетов"""

    # ======================
    # ШРИФТЫ
    # ======================

    HEADER_FONT = Font(bold=True, size=14, color="FFFFFF")
    """Шрифт для главных заголовков (белый, жирный, 14pt)"""

    SUBHEADER_FONT = Font(bold=True, size=12)
    """Шрифт для подзаголовков (черный, жирный, 12pt)"""

    TABLE_HEADER_FONT = Font(bold=True, size=12, color="FFFFFF")
    """Шрифт для заголовков таблиц (белый, жирный, 12pt)"""

    DATA_FONT = Font(size=10)
    """Шрифт для обычных данных (черный, 10pt)"""

    BOLD_FONT = Font(bold=True, size=11)
    """Жирный шрифт для выделения (11pt)"""

    # ======================
    # ЗАЛИВКИ (ФОНЫ)
    # ======================

    HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    """Синий фон для главных заголовков (#4472C4)"""

    SUBHEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    """Светло-синий фон для подзаголовков (#D9E1F2)"""

    HIGHLIGHT_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    """Желтый фон для подсветки (#FFF2CC)"""

    SUCCESS_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    """Зеленый фон для успешных операций (#C6EFCE)"""

    WARNING_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    """Оранжевый фон для предупреждений (#FFEB9C)"""

    ERROR_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    """Красный фон для ошибок (#FFC7CE)"""

    # ======================
    # ВЫРАВНИВАНИЕ
    # ======================

    CENTER_ALIGNMENT = Alignment(horizontal="center", vertical="center")
    """Центрирование по горизонтали и вертикали"""

    LEFT_ALIGNMENT = Alignment(horizontal="left", vertical="center")
    """Выравнивание по левому краю с вертикальным центрированием"""

    RIGHT_ALIGNMENT = Alignment(horizontal="right", vertical="center")
    """Выравнивание по правому краю с вертикальным центрированием"""

    WRAP_ALIGNMENT = Alignment(horizontal="left", vertical="center", wrap_text=True)
    """Выравнивание по левому краю с переносом текста"""

    # ======================
    # ГРАНИЦЫ
    # ======================

    THIN_BORDER = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    """Тонкая граница со всех сторон"""

    THICK_BORDER = Border(
        left=Side(style="thick"),
        right=Side(style="thick"),
        top=Side(style="thick"),
        bottom=Side(style="thick"),
    )
    """Толстая граница со всех сторон"""

    NO_BORDER = Border()
    """Без границы"""

    # ======================
    # КОМБИНИРОВАННЫЕ СТИЛИ
    # ======================

    @staticmethod
    def get_header_style() -> dict:
        """
        Получить полный стиль для главного заголовка

        Returns:
            Dict со всеми свойствами стиля
        """
        return {
            "font": ExcelStyles.HEADER_FONT,
            "fill": ExcelStyles.HEADER_FILL,
            "alignment": ExcelStyles.CENTER_ALIGNMENT,
            "border": ExcelStyles.THIN_BORDER,
        }

    @staticmethod
    def get_subheader_style() -> dict:
        """
        Получить полный стиль для подзаголовка

        Returns:
            Dict со всеми свойствами стиля
        """
        return {
            "font": ExcelStyles.SUBHEADER_FONT,
            "fill": ExcelStyles.SUBHEADER_FILL,
            "alignment": ExcelStyles.CENTER_ALIGNMENT,
            "border": ExcelStyles.THIN_BORDER,
        }

    @staticmethod
    def get_table_header_style() -> dict:
        """
        Получить полный стиль для заголовка таблицы

        Returns:
            Dict со всеми свойствами стиля
        """
        return {
            "font": ExcelStyles.TABLE_HEADER_FONT,
            "fill": ExcelStyles.HEADER_FILL,
            "alignment": ExcelStyles.CENTER_ALIGNMENT,
            "border": ExcelStyles.THIN_BORDER,
        }

    @staticmethod
    def get_data_style(centered: bool = False) -> dict:
        """
        Получить полный стиль для обычных данных

        Args:
            centered: Использовать центрирование или выравнивание по левому краю

        Returns:
            Dict со всеми свойствами стиля
        """
        return {
            "font": ExcelStyles.DATA_FONT,
            "alignment": ExcelStyles.CENTER_ALIGNMENT if centered else ExcelStyles.LEFT_ALIGNMENT,
            "border": ExcelStyles.THIN_BORDER,
        }
