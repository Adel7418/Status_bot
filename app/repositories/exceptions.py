"""
Исключения для работы с репозиториями
"""


class RepositoryError(Exception):
    """Базовое исключение для репозиториев"""


class ConcurrentModificationError(RepositoryError):
    """
    Исключение при конфликте версий (optimistic locking)

    Возникает когда запись была изменена другим процессом между
    чтением и попыткой обновления.
    """

    def __init__(self, entity_type: str, entity_id: int, expected_version: int):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.expected_version = expected_version
        super().__init__(
            f"{entity_type} #{entity_id} was modified by another process "
            f"(expected version {expected_version}). "
            "Please reload and try again."
        )


class EntityNotFoundError(RepositoryError):
    """
    Исключение при отсутствии записи
    """

    def __init__(self, entity_type: str, entity_id: int):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} #{entity_id} not found")


class IntegrityError(RepositoryError):
    """
    Исключение при нарушении целостности данных
    """


