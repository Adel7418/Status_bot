"""
FSM States для различных процессов
"""

from aiogram.fsm.state import State, StatesGroup


class CreateOrderStates(StatesGroup):
    """Состояния для создания заявки"""

    equipment_type = State()  # Выбор типа техники
    description = State()  # Ввод описания проблемы
    client_name = State()  # Ввод имени клиента
    client_address = State()  # Ввод адреса клиента
    client_phone = State()  # Ввод телефона клиента
    notes = State()  # Ввод дополнительных заметок
    scheduled_time = State()  # Ввод времени прибытия к клиенту
    confirm = State()  # Подтверждение создания


class EditOrderStates(StatesGroup):
    """Состояния для редактирования заявки"""

    select_field = State()  # Выбор поля для редактирования
    enter_value = State()  # Ввод нового значения


class AddMasterStates(StatesGroup):
    """Состояния для добавления мастера администратором"""

    enter_telegram_id = State()  # Ввод Telegram ID мастера
    enter_phone = State()  # Ввод телефона
    enter_specialization = State()  # Ввод специализации
    confirm = State()  # Подтверждение


class AssignMasterStates(StatesGroup):
    """Состояния для назначения мастера на заявку"""

    select_master = State()  # Выбор мастера


class ReportStates(StatesGroup):
    """Состояния для генерации отчетов"""

    select_type = State()  # Выбор типа отчета
    select_period = State()  # Выбор периода (если нужно)
    enter_dates = State()  # Ввод дат (для custom периода)


class NotesStates(StatesGroup):
    """Состояния для добавления заметок к заявке"""

    enter_notes = State()  # Ввод заметок


class SetWorkChatStates(StatesGroup):
    """Состояния для установки рабочей группы мастера"""

    enter_chat_id = State()  # Ввод ID группы или пересылка сообщения


class CompleteOrderStates(StatesGroup):
    """Состояния для завершения заказа"""

    enter_total_amount = State()  # Ввод общей суммы заказа
    enter_materials_cost = State()  # Ввод суммы расходного материала
    confirm_review = State()  # Подтверждение наличия отзыва
    confirm_out_of_city = State()  # Подтверждение выезда за город


class AdminCloseOrderStates(StatesGroup):
    """Состояния для закрытия заказа админом/диспетчером"""

    enter_total_amount = State()  # Ввод общей суммы заказа
    enter_materials_cost = State()  # Ввод суммы расходного материала
    confirm_review = State()  # Подтверждение наличия отзыва
    confirm_out_of_city = State()  # Подтверждение выезда за город


class LongRepairStates(StatesGroup):
    """Состояния для перевода заявки в длительный ремонт"""

    enter_completion_date_and_prepayment = (
        State()
    )  # Ввод срока окончания + предоплаты (опционально)


class RescheduleOrderStates(StatesGroup):
    """Состояния для переноса заявки"""

    enter_new_time = State()  # Ввод нового времени прибытия
    enter_reason = State()  # Ввод причины переноса (опционально)
