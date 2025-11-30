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
    confirm_client_data = State()  # Подтверждение найденных данных клиента
    master_lead_name = State()  # Ввод имени мастера-источника лида
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
    confirm_low_amount_refusal = State()  # Подтверждение отказа для сумм <1000р
    enter_refuse_reason_on_complete = State()  # Ввод причины отказа при завершении
    enter_materials_cost = State()  # Ввод суммы расходного материала
    confirm_materials = State()  # Подтверждение суммы материалов
    confirm_review = State()  # Подтверждение наличия отзыва
    confirm_out_of_city = State()  # Подтверждение выезда за город


class AdminCloseOrderStates(StatesGroup):
    """Состояния для закрытия заказа админом/диспетчером"""

    enter_total_amount = State()  # Ввод общей суммы заказа
    enter_materials_cost = State()  # Ввод суммы расходного материала
    confirm_materials = State()  # Подтверждение суммы материалов
    confirm_review = State()  # Подтверждение наличия отзыва
    confirm_out_of_city = State()  # Подтверждение выезда за город
    enter_value = State()  # Ввод значения при точечном редактировании


class EditClosedOrderStates(StatesGroup):
    """Состояния для редактирования закрытой заявки (только ADMIN)"""

    waiting_order_id = State()  # Ввод ID заявки или выбор
    select_field = State()  # Выбор редактируемого поля
    enter_total_amount = State()  # Ввод общей суммы
    enter_materials_cost = State()  # Ввод суммы расхода
    confirm_review = State()  # Подтверждение наличия отзыва
    confirm_out_of_city = State()  # Подтверждение выезда за город
    confirm = State()  # Подтверждение изменений


class LongRepairStates(StatesGroup):
    """Состояния для перевода заявки в длительный ремонт"""

    enter_completion_date = State()  # Ввод срока окончания ремонта
    enter_parts_info = State()  # Ввод информации о запчастях
    enter_estimated_cost = State()  # Ввод предварительной суммы согласования с клиентом
    confirm_dr = State()  # Подтверждение перевода в длительный ремонт
    change_date = State()  # Изменение даты завершения  # Изменение даты завершения


class RescheduleOrderStates(StatesGroup):
    """Состояния для переноса заявки"""

    enter_new_time = State()  # Ввод нового времени прибытия
    enter_reason = State()  # Ввод причины переноса (опционально)
    confirm = State()  # Подтверждение переноса


class RefuseOrderStates(StatesGroup):
    """Состояния для отказа от заявки"""

    enter_refuse_reason = State()  # Ввод причины отказа
    confirm_refusal = State()  # Подтверждение отказа


class SearchOrderStates(StatesGroup):
    """Состояния для поиска заказов"""

    enter_query = State()  # Единый ввод запроса для умного поиска (адрес/телефон/ID)


class EditMasterSpecializationStates(StatesGroup):
    """Состояния для редактирования специализации мастера (только ADMIN)"""

    enter_specialization = State()  # Ввод новой специализации


class ParserAuthState(StatesGroup):
    """Состояния для аутентификации парсера"""
    waiting_for_code = State()
    waiting_for_password = State()  # Ожидание кода подтверждения от Telegram
    waiting_for_password = State()  # Ожидание пароля 2FA (если есть)


class EditParsedOrderStates(StatesGroup):
    """Состояния для редактирования распарсенной заявки перед созданием"""

    select_field = State()  # Выбор поля для редактирования
    enter_value = State()  # Ввод нового значения
