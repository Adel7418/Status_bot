"""
Модуль для шифрования/дешифрования персональных данных
"""

import base64
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet


logger = logging.getLogger(__name__)


class DataEncryptor:
    """Класс для шифрования/дешифрования данных"""

    def __init__(self):
        """Инициализация с ключом из переменных окружения"""
        key_str = os.getenv("ENCRYPTION_KEY")
        key: bytes

        if not key_str:
            # В production это должно вызвать ошибку!
            logger.warning("⚠️  ENCRYPTION_KEY not found in environment!")
            logger.warning("⚠️  Generating temporary key (NOT FOR PRODUCTION!)")
            key = Fernet.generate_key()
            logger.warning(f"⚠️  Add to .env: ENCRYPTION_KEY={key.decode()}")
        else:
            key = key_str.encode()

        try:
            self.cipher = Fernet(key)
            logger.info("✅ Шифрование инициализировано успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации шифрования: {e}")
            raise

    def encrypt(self, data: Optional[str]) -> Optional[str]:
        """
        Шифрование строки

        Args:
            data: Исходная строка

        Returns:
            Зашифрованная строка в base64 или None
        """
        if not data:
            return data

        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"❌ Ошибка шифрования: {e}")
            return data  # Возвращаем исходные данные в случае ошибки

    def decrypt(self, encrypted_data: Optional[str]) -> Optional[str]:
        """
        Дешифрование строки

        Args:
            encrypted_data: Зашифрованная строка

        Returns:
            Расшифрованная строка или None
        """
        if not encrypted_data:
            return encrypted_data

        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted: bytes = self.cipher.decrypt(decoded)
            result: str = decrypted.decode()
            return result
        except Exception as e:
            logger.error(f"❌ Ошибка дешифрования: {e}")
            # Возможно данные не были зашифрованы
            return encrypted_data

    def is_encrypted(self, data: str) -> bool:
        """
        Проверка, зашифрованы ли данные

        Args:
            data: Строка для проверки

        Returns:
            True если данные зашифрованы
        """
        if not data:
            return False

        try:
            # Пробуем декодировать base64
            base64.urlsafe_b64decode(data.encode())
            # Пробуем расшифровать
            self.decrypt(data)
            return True
        except Exception:
            return False


# Глобальный экземпляр
_encryptor: Optional[DataEncryptor] = None


def get_encryptor() -> DataEncryptor:
    """
    Получение глобального экземпляра шифровальщика (singleton)

    Returns:
        Экземпляр DataEncryptor
    """
    global _encryptor
    if _encryptor is None:
        _encryptor = DataEncryptor()
    return _encryptor


# Удобные функции для прямого использования
def encrypt(data: Optional[str]) -> Optional[str]:
    """Шифрование данных"""
    return get_encryptor().encrypt(data)


def decrypt(data: Optional[str]) -> Optional[str]:
    """Дешифрование данных"""
    return get_encryptor().decrypt(data)


def is_encrypted(data: str) -> bool:
    """Проверка, зашифрованы ли данные"""
    return get_encryptor().is_encrypted(data)
