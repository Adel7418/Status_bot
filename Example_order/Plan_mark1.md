 Отлично! Я изучил структуру проекта и готов создать детальный план интеграции Telethon-клиента для
       парсинга заявок из Telegram-группы.

       📋 Детальный план интеграции Telethon-клиента для парсинга заявок из Telegram-группы

       I. Обзор функции

       Краткое описание

       Интеграция Telethon-клиента, который будет мониторить указанную Telegram-группу, парсить сообщения
       диспетчеров по гибким правилам (без строгого формата) и создавать заявки с механизмом подтверждения
       через inline-кнопки.

       Бизнес-ценность

       - Автоматизация: Снижение ручного труда диспетчеров на 70-80%
       - Скорость: Мгновенное создание заявок из сообщений в группе
       - Качество: Валидация данных через Pydantic до создания заявки
       - Гибкость: Парсинг "небрежных" сообщений с разным форматом

       Затрагиваемые компоненты

       - Новый Telethon-клиент (параллельно с aiogram)
       - Модуль парсинга заявок (app/services/telegram_parser/)
       - Схемы валидации (app/schemas/parser.py)
       - База данных (новая таблица для хранения group_id)
       - Конфигурация (.env файл)

       ---
       II. Технический анализ

       Требуемые технологии и библиотеки

       1. Telethon (≥1.34.0) - для мониторинга группы
       2. re (встроенный) - для regex парсинга
       3. dateparser (уже в проекте) - для парсинга времени
       4. Pydantic 2.x (уже в проекте) - для валидации

       Архитектурные решения

       1. Два параллельных клиента

       ┌─────────────────────────────────────┐
       │         bot.py (main)               │
       ├─────────────────────────────────────┤
       │  ┌────────────┐  ┌────────────────┐ │
       │  │  Aiogram   │  │   Telethon     │ │
       │  │  (бот)     │  │   (парсер)     │ │
       │  └────────────┘  └────────────────┘ │
       │       │                  │          │
       │       └─────┬────────────┘          │
       │             │                       │
       │      ┌──────▼──────┐                │
       │      │  Database   │                │
       │      └─────────────┘                │
       └─────────────────────────────────────┘

       2. Архитектура модуля парсера

       app/services/telegram_parser/
       ├── __init__.py
       ├── client.py              # TelethonClient (мониторинг группы)
       ├── parser.py              # OrderParserService (логика парсинга)
       ├── confirmation.py        # OrderConfirmationService (обработка подтверждений)
       ├── equipment_dict.py      # EQUIPMENT_ABBREVIATIONS (словарь сокращений)
       └── patterns.py            # Regex паттерны

       Паттерны проектирования

       1. Service Layer Pattern - бизнес-логика в сервисах
       2. Repository Pattern - уже используется в проекте
       3. State Machine Pattern - для обработки подтверждений (через FSM)
       4. Singleton Pattern - для TelethonClient

       Соображения безопасности

       - API_ID/API_HASH: Хранить только в .env
       - Session файл: Добавить в .gitignore
       - Валидация: Все данные валидировать через Pydantic
       - SQL Injection: Защита уже есть в OrderCreateSchema

       Требования к производительности

       - Парсинг: < 100ms на сообщение
       - Создание заявки: < 500ms
       - Memory: +20-30MB для Telethon клиента

       ---
       III. Пошаговый план реализации

       ЭТАП 1: Подготовка инфраструктуры (Сложность: НИЗКАЯ)

       Задачи:
       1. Добавить Telethon в зависимости
       2. Обновить конфигурацию
       3. Создать миграцию для хранения group_id

       Файлы:

       1.1. requirements.txt
       - Добавить: telethon==1.34.0

       1.2. app/core/config.py
       - Добавить новые переменные:
         - TELETHON_API_ID: int
         - TELETHON_API_HASH: str
         - TELETHON_PHONE: str (для первичной авторизации)
         - TELETHON_SESSION_NAME: str (default: "parser_session")

       1.3. .env (пример)
       # Telethon Parser
       TELETHON_API_ID=12345678
       TELETHON_API_HASH=abcdef1234567890
       TELETHON_PHONE=+79001234567
       TELETHON_SESSION_NAME=parser_session

       1.4. Миграция: migrations/versions/XXX_add_parser_group_config.py
       # Создать таблицу parser_config
       # Поля: id, group_id (int), enabled (bool), created_at, updated_at

       1.5. app/database/orm_models.py
       - Добавить модель ParserConfig:
         - id: int
         - group_id: int (nullable)
         - enabled: bool (default: False)
         - created_at: datetime
         - updated_at: datetime

       Зависимости: Нет
       Оценка времени: 1-2 часа

       ---
       ЭТАП 2: Словарь сокращений и паттерны (Сложность: НИЗКАЯ)

       Задачи:
       1. Создать словарь сокращений техники
       2. Создать regex паттерны для парсинга

       Файлы:

       2.1. app/services/telegram_parser/equipment_dict.py
       """Словарь сокращений типов техники"""

       EQUIPMENT_ABBREVIATIONS: dict[str, str] = {
           # Стиральные машины
           "с/м": "Стиральная машина",
           "с//м": "Стиральная машина",
           "стиралка": "Стиральная машина",
           "стиральная": "Стиральная машина",

           # Посудомоечные машины
           "п/м": "Посудомоечная машина",
           "посудомойка": "Посудомоечная машина",

           # ТВ
           "тв": "Телевизор",
           "телевизор": "Телевизор",

           # Холодильники
           "холодильник": "Холодильник",
           "ларь": "Морозильный ларь",

           # Варочные панели
           "вп": "Варочная панель",
           "варочная": "Варочная панель",

           # Духовые шкафы
           "дш": "Духовой шкаф",
           "духовка": "Духовой шкаф",

           # Кондиционеры
           "кондиционер": "Кондиционер",

           # Кофемашины
           "кофемашина": "Кофемашина",

           # Электрика
           "электрика": "Электрика",
           "электрик": "Электрика",

           # Сантехника
           "сантехника": "Сантехника",
       }

       def normalize_equipment_type(text: str) -> str | None:
           """Нормализация типа техники из текста"""
           text_lower = text.lower().strip()
           for abbr, full_name in EQUIPMENT_ABBREVIATIONS.items():
               if abbr in text_lower:
                   return full_name
           return None

       2.2. app/services/telegram_parser/patterns.py
       """Regex паттерны для парсинга сообщений"""

       import re

       # Паттерн телефона
       PHONE_PATTERN = re.compile(
           r'(?:^|\s)(?:\+7|8|7)[\s\-\(\)]?'
           r'\d{3}[\s\-\(\)]?'
           r'\d{3}[\s\-]?'
           r'\d{2}[\s\-]?'
           r'\d{2}'
       )

       # Паттерн времени (HH:MM)
       TIME_PATTERN = re.compile(r'\b\d{1,2}:\d{2}\b')

       # Ключевые слова времени
       TIME_KEYWORDS = [
           'завтра', 'через', 'к', 'в течение', 'час',
           'обеда', 'вечера', 'утра', 'после', 'до'
       ]

       # Интервалы времени
       TIME_INTERVAL_PATTERN = re.compile(r'\d+[.,]?\d*\s*[-–—]\s*\d+[.,]?\d*')

       # Ключевые слова адреса
       ADDRESS_KEYWORDS = [
           'кв', 'дом', 'ул', 'пер', 'пр', 'корпус',
           'этаж', 'подъезд', 'д.', 'д ', 'кв.'
       ]

       def extract_phone(text: str) -> str | None:
           """Извлечение телефона из текста"""
           match = PHONE_PATTERN.search(text)
           if match:
               phone = match.group(0).strip()
               # Очистка и нормализация
               phone = re.sub(r'[^\d+]', '', phone)
               if phone.startswith('8'):
                   phone = '+7' + phone[1:]
               elif phone.startswith('7'):
                   phone = '+' + phone
               return phone
           return None

       def contains_time_indicator(line: str) -> bool:
           """Проверка наличия указания времени в строке"""
           line_lower = line.lower()

           # Проверка на формат HH:MM
           if TIME_PATTERN.search(line):
               return True

           # Проверка ключевых слов
           if any(kw in line_lower for kw in TIME_KEYWORDS):
               return True

           # Проверка интервалов
           if TIME_INTERVAL_PATTERN.search(line):
               return True

           return False

       def looks_like_address(line: str) -> bool:
           """Проверка похожа ли строка на адрес"""
           line_lower = line.lower()

           # Должны быть цифры
           if not re.search(r'\d', line):
               return False

           # Проверка ключевых слов
           if any(kw in line_lower for kw in ADDRESS_KEYWORDS):
               return True

           return False

       Зависимости: ЭТАП 1
       Оценка времени: 2-3 часа

       ---
       ЭТАП 3: Pydantic схемы для парсинга (Сложность: СРЕДНЯЯ)

       Задачи:
       1. Создать схему для результата парсинга
       2. Добавить валидацию обязательных полей

       Файлы:

       3.1. app/schemas/parser.py
       """Pydantic схемы для парсера заявок"""

       from pydantic import BaseModel, Field, field_validator, model_validator
       import re

       class OrderParsed(BaseModel):
           """Схема спарсенной заявки из сообщения"""

           equipment_type: str | None = Field(None, description="Тип техники")
           description: str = Field(..., min_length=1, description="Описание проблемы")
           client_address: str = Field(..., min_length=4, description="Адрес клиента")
           client_phone: str | None = Field(None, description="Телефон клиента")
           scheduled_time: str | None = Field(None, description="Время визита")

           # Служебное
           raw_message: str = Field(..., description="Исходное сообщение")
           message_id: int = Field(..., description="ID сообщения в Telegram")
           chat_id: int = Field(..., description="ID чата")
           sender_id: int = Field(..., description="ID отправителя")

           @field_validator("client_phone")
           @classmethod
           def validate_phone(cls, v: str | None) -> str | None:
               """Валидация телефона"""
               if v is None:
                   return None

               # Очистка
               cleaned = re.sub(r'[^\d+]', '', v.strip())

               # Проверка формата
               if not re.match(r'^\+7\d{10}$', cleaned):
                   return None  # Невалидный телефон игнорируем

               return cleaned

           @model_validator(mode='after')
           def validate_required_fields(self):
               """Проверка обязательных полей для создания заявки"""

               # Обязательно нужен адрес
               if not self.client_address or len(self.client_address.strip()) < 4:
                   raise ValueError("Адрес не указан или слишком короткий")

               # Обязательно нужно описание
               if not self.description or len(self.description.strip()) < 1:
                   raise ValueError("Описание не указано")

               return self

           def is_complete(self) -> bool:
               """Проверка что заявка достаточно заполнена для создания"""
               # Минимально нужны: адрес, описание
               # Телефон и время - опциональны
               # Тип техники - желательно, но можно создать как "Не определено"
               return bool(self.client_address and self.description)

       class ParseResult(BaseModel):
           """Результат парсинга сообщения"""

           success: bool = Field(..., description="Успешно ли распарсено")
           order: OrderParsed | None = Field(None, description="Данные заявки")
           error_message: str | None = Field(None, description="Сообщение об ошибке")
           needs_confirmation: bool = Field(default=True, description="Требует подтверждения")

       Зависимости: ЭТАП 2
       Оценка времени: 2-3 часа

       ---
       ЭТАП 4: Сервис парсинга (Сложность: ВЫСОКАЯ)

       Задачи:
       1. Реализовать логику парсинга по правилам из logic_parser.md
       2. Покрыть edge cases

       Файлы:

       4.1. app/services/telegram_parser/parser.py
       """Сервис парсинга заявок из текстовых сообщений"""

       import logging
       from typing import List

       from app.schemas.parser import OrderParsed, ParseResult
       from .equipment_dict import normalize_equipment_type
       from .patterns import (
           extract_phone,
           contains_time_indicator,
           looks_like_address
       )

       logger = logging.getLogger(__name__)

       class OrderParserService:
           """Сервис для парсинга заявок из текста"""

           def parse_message(
               self,
               text: str,
               message_id: int,
               chat_id: int,
               sender_id: int
           ) -> ParseResult:
               """
               Парсинг сообщения согласно логике из logic_parser.md

               Args:
                   text: Текст сообщения
                   message_id: ID сообщения
                   chat_id: ID чата
                   sender_id: ID отправителя

               Returns:
                   ParseResult с результатом парсинга
               """
               try:
                   # Шаг 1: Разбиение на строки
                   lines = [line.strip() for line in text.split('\n') if line.strip()]

                   if len(lines) < 2:
                       return ParseResult(
                           success=False,
                           error_message="Сообщение слишком короткое для парсинга"
                       )

                   # Шаг 2: Определение телефона (с конца)
                   phone = None
                   phone_line_idx = None
                   for i in range(len(lines) - 1, -1, -1):
                       phone = extract_phone(lines[i])
                       if phone:
                           phone_line_idx = i
                           break

                   # Убираем строку с телефоном из дальнейшего анализа
                   remaining_lines = []
                   for i, line in enumerate(lines):
                       if i != phone_line_idx:
                           remaining_lines.append(line)

                   if not remaining_lines:
                       return ParseResult(
                           success=False,
                           error_message="После извлечения телефона не осталось данных"
                       )

                   # Шаг 3: Определение времени визита (с конца оставшихся строк)
                   scheduled_time = None
                   time_line_idx = None
                   for i in range(len(remaining_lines) - 1, -1, -1):
                       if contains_time_indicator(remaining_lines[i]):
                           scheduled_time = remaining_lines[i]
                           time_line_idx = i
                           break

                   # Убираем строку со временем
                   final_lines = []
                   for i, line in enumerate(remaining_lines):
                       if i != time_line_idx:
                           final_lines.append(line)

                   if not final_lines:
                       return ParseResult(
                           success=False,
                           error_message="Недостаточно данных для определения техники и адреса"
                       )

                   # Шаг 4: Разделение на технику/проблему и адрес
                   # Если вторая строка похожа на адрес - техника в первой
                   # Иначе - техника и проблема в первых двух

                   equipment_type = None
                   description = ""
                   address_lines = []

                   if len(final_lines) >= 2 and looks_like_address(final_lines[1]):
                       # Техника в первой строке, адрес - остальное
                       equipment_type = normalize_equipment_type(final_lines[0])
                       description = final_lines[0]  # Весь текст как описание
                       address_lines = final_lines[1:]
                   else:
                       # Техника и проблема в первых двух, адрес - остальное
                       combined = " ".join(final_lines[:2])
                       equipment_type = normalize_equipment_type(combined)
                       description = combined
                       address_lines = final_lines[2:] if len(final_lines) > 2 else []

                   # Формирование адреса
                   if not address_lines:
                       # Попытка извлечь адрес из оставшегося текста
                       # Возможно адрес был в первых строках
                       for line in final_lines:
                           if looks_like_address(line):
                               address_lines.append(line)

                   client_address = " ".join(address_lines).strip()

                   # Проверка обязательных полей
                   if not client_address:
                       return ParseResult(
                           success=False,
                           error_message="Не удалось определить адрес"
                       )

                   # Если описание пустое - ставим заглушку
                   if not description.strip():
                       description = "Не указано"

                   # Создание объекта заявки
                   order = OrderParsed(
                       equipment_type=equipment_type or "Не определено",
                       description=description,
                       client_address=client_address,
                       client_phone=phone,
                       scheduled_time=scheduled_time,
                       raw_message=text,
                       message_id=message_id,
                       chat_id=chat_id,
                       sender_id=sender_id
                   )

                   return ParseResult(
                       success=True,
                       order=order,
                       needs_confirmation=True
                   )

               except Exception as e:
                   logger.error(f"Ошибка парсинга сообщения: {e}", exc_info=True)
                   return ParseResult(
                       success=False,
                       error_message=f"Ошибка парсинга: {str(e)}"
                   )

           def format_confirmation_message(self, order: OrderParsed) -> str:
               """Форматирование сообщения для подтверждения"""
               msg = "📋 Распознана заявка:\n\n"
               msg += f"🔧 Техника: {order.equipment_type}\n"
               msg += f"❗ Проблема: {order.description}\n"
               msg += f"📍 Адрес: {order.client_address}\n"

               if order.client_phone:
                   msg += f"📱 Телефон: {order.client_phone}\n"
               else:
                   msg += f"📱 Телефон: не указан\n"

               if order.scheduled_time:
                   msg += f"🕐 Время: {order.scheduled_time}\n"

               msg += "\n❓ Создать заявку?"

               return msg

       Зависимости: ЭТАП 2, ЭТАП 3
       Оценка времени: 6-8 часов

       ---
       ЭТАП 5: Telethon клиент (Сложность: ВЫСОКАЯ)

       Задачи:
       1. Создать Telethon клиент для мониторинга группы
       2. Интегрировать с парсером
       3. Обработка подтверждений через inline-кнопки

       Файлы:

       5.1. app/services/telegram_parser/client.py
       """Telethon клиент для мониторинга группы"""

       import logging
       from telethon import TelegramClient, events
       from telethon.tl.types import Message

       from app.core.config import Config
       from app.database import Database
       from app.repositories import OrderRepository
       from .parser import OrderParserService

       logger = logging.getLogger(__name__)

       class TelethonParserClient:
           """Клиент для парсинга сообщений из группы"""

           def __init__(self, db: Database):
               self.db = db
               self.client = None
               self.parser = OrderParserService()
               self.monitored_group_id: int | None = None

           async def start(self):
               """Запуск клиента"""
               try:
                   self.client = TelegramClient(
                       Config.TELETHON_SESSION_NAME,
                       Config.TELETHON_API_ID,
                       Config.TELETHON_API_HASH
                   )

                   await self.client.start(phone=Config.TELETHON_PHONE)
                   logger.info("Telethon клиент запущен")

                   # Загрузка group_id из БД
                   await self._load_group_config()

                   # Регистрация обработчиков
                   self._register_handlers()

               except Exception as e:
                   logger.error(f"Ошибка запуска Telethon клиента: {e}", exc_info=True)
                   raise

           async def stop(self):
               """Остановка клиента"""
               if self.client:
                   await self.client.disconnect()
                   logger.info("Telethon клиент остановлен")

           async def _load_group_config(self):
               """Загрузка конфигурации группы из БД"""
               # TODO: Реализовать через repository
               pass

           def _register_handlers(self):
               """Регистрация обработчиков событий"""

               @self.client.on(events.NewMessage())
               async def handle_new_message(event: events.NewMessage.Event):
                   """Обработка новых сообщений"""
                   try:
                       # Проверка что это сообщение из нужной группы
                       if self.monitored_group_id is None:
                           return

                       if event.chat_id != self.monitored_group_id:
                           return

                       message: Message = event.message

                       # Игнорируем сообщения ботов
                       if message.sender and message.sender.bot:
                           return

                       # Парсинг сообщения
                       result = self.parser.parse_message(
                           text=message.text,
                           message_id=message.id,
                           chat_id=event.chat_id,
                           sender_id=message.sender_id
                       )

                       if result.success and result.order:
                           # Отправка подтверждения
                           await self._send_confirmation(event, result)
                       else:
                           logger.debug(f"Не удалось распарсить сообщение: {result.error_message}")

                   except Exception as e:
                       logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)

           async def _send_confirmation(self, event, parse_result):
               """Отправка сообщения с подтверждением"""
               from telethon.tl.types import KeyboardButtonCallback
               from telethon.tl.types import ReplyInlineMarkup

               confirmation_text = self.parser.format_confirmation_message(parse_result.order)

               # Inline кнопки
               buttons = [
                   [
                       KeyboardButtonCallback("✅ Да", data=f"confirm_{event.message.id}"),
                       KeyboardButtonCallback("❌ Нет", data=f"cancel_{event.message.id}")
                   ]
               ]

               await event.reply(
                   confirmation_text,
                   buttons=ReplyInlineMarkup(buttons)
               )

           async def set_monitored_group(self, group_id: int):
               """Установка ID группы для мониторинга"""
               self.monitored_group_id = group_id
               # TODO: Сохранить в БД
               logger.info(f"Установлена группа для мониторинга: {group_id}")

       5.2. app/services/telegram_parser/confirmation.py
       """Сервис обработки подтверждений создания заявок"""

       import logging
       from aiogram import Bot
       from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

       from app.database import Database
       from app.repositories import OrderRepository, UserRepository
       from app.schemas.parser import OrderParsed
       from app.schemas.order import OrderCreateSchema

       logger = logging.getLogger(__name__)

       class OrderConfirmationService:
           """Обработка подтверждений создания заявок"""

           def __init__(self, db: Database, bot: Bot):
               self.db = db
               self.bot = bot
               self.order_repo = OrderRepository(db)
               self.user_repo = UserRepository(db)

               # Хранилище ожидающих подтверждения заявок
               # message_id -> OrderParsed
               self.pending_confirmations: dict[int, OrderParsed] = {}

           async def handle_confirmation(
               self,
               message_id: int,
               confirmed: bool,
               user_id: int
           ):
               """
               Обработка подтверждения/отмены

               Args:
                   message_id: ID сообщения с заявкой
                   confirmed: True - подтверждено, False - отменено
                   user_id: ID пользователя который подтвердил
               """
               order_data = self.pending_confirmations.get(message_id)

               if not order_data:
                   logger.warning(f"Подтверждение для несуществующей заявки: {message_id}")
                   return

               if confirmed:
                   await self._create_order(order_data, user_id)
               else:
                   await self._cancel_order(order_data)

               # Удаляем из ожидающих
               del self.pending_confirmations[message_id]

           async def _create_order(self, order_data: OrderParsed, dispatcher_id: int):
               """Создание заявки в БД"""
               try:
                   # Валидация через OrderCreateSchema
                   order_schema = OrderCreateSchema(
                       equipment_type=order_data.equipment_type,
                       description=order_data.description,
                       client_name="Клиент",  # По умолчанию
                       client_address=order_data.client_address,
                       client_phone=order_data.client_phone or "+70000000000",  # Заглушка
                       dispatcher_id=dispatcher_id,
                       scheduled_time=order_data.scheduled_time,
                       notes=f"Автоматически создано парсером из сообщения {order_data.message_id}"
                   )

                   # Создание заявки
                   order = await self.order_repo.create(**order_schema.model_dump())

                   logger.info(f"Заявка #{order.id} создана парсером")

                   # Отправка уведомления в группу
                   await self._send_success_notification(order_data, order.id)

               except Exception as e:
                   logger.error(f"Ошибка создания заявки: {e}", exc_info=True)
                   await self._send_error_notification(order_data, str(e))

           async def _cancel_order(self, order_data: OrderParsed):
               """Отмена создания заявки"""
               logger.info(f"Создание заявки отменено: {order_data.message_id}")
               # Можно отправить уведомление об отмене

           async def _send_success_notification(self, order_data: OrderParsed, order_id: int):
               """Уведомление об успешном создании"""
               text = f"✅ Заявка #{order_id} успешно создана!\n\n"
               text += "👨‍🔧 Назначьте мастера через бота"

               # Отправка в группу через Telethon
               # (требует доступа к telethon client)
               pass

           async def _send_error_notification(self, order_data: OrderParsed, error: str):
               """Уведомление об ошибке"""
               text = f"❌ Ошибка создания заявки:\n{error}"
               # Отправка в группу
               pass

       5.3. app/services/telegram_parser/init.py
       """Модуль парсинга заявок из Telegram"""

       from .client import TelethonParserClient
       from .parser import OrderParserService
       from .confirmation import OrderConfirmationService
       from .equipment_dict import EQUIPMENT_ABBREVIATIONS

       __all__ = [
           'TelethonParserClient',
           'OrderParserService',
           'OrderConfirmationService',
           'EQUIPMENT_ABBREVIATIONS'
       ]

       Зависимости: ЭТАП 4
       Оценка времени: 8-10 часов

       ---
       ЭТАП 6: Интеграция с основным ботом (Сложность: СРЕДНЯЯ)

       Задачи:
       1. Запуск Telethon клиента параллельно с aiogram
       2. Команда /set_group для настройки
       3. Callback handlers для подтверждений

       Файлы:

       6.1. bot.py (изменения)
       # В начале файла после импортов
       from app.services.telegram_parser import TelethonParserClient

       # В функции main(), после инициализации db
       telethon_client = None

       # После scheduler = TaskScheduler(bot, db)
       # Инициализация Telethon клиента
       if Config.TELETHON_API_ID and Config.TELETHON_API_HASH:
           telethon_client = TelethonParserClient(db)
           await telethon_client.start()
           logger.info("Telethon парсер запущен")

       # В функции on_shutdown(), после остановки scheduler
       if telethon_client:
           await telethon_client.stop()
           logger.info("Telethon клиент остановлен")

       6.2. app/handlers/parser_config.py (новый файл)
       """Обработчики для настройки парсера"""

       import logging
       from aiogram import Router, F
       from aiogram.types import Message, CallbackQuery
       from aiogram.filters import Command

       from app.config import Config
       from app.database import Database
       from app.filters import RoleFilter

       logger = logging.getLogger(__name__)
       router = Router()

       @router.message(Command("set_group"), RoleFilter(["ADMIN"]))
       async def cmd_set_group(message: Message, db: Database):
           """Установка группы для парсинга"""
           try:
               # Команда должна быть вызвана в группе
               if message.chat.type not in ['group', 'supergroup']:
                   await message.reply(
                       "❌ Эта команда должна быть вызвана в группе, "
                       "которую нужно мониторить"
                   )
                   return

               group_id = message.chat.id

               # TODO: Сохранить group_id в БД через repository
               # TODO: Обновить telethon_client.set_monitored_group(group_id)

               await message.reply(
                   f"✅ Группа установлена для парсинга!\n"
                   f"ID: {group_id}\n\n"
                   f"Теперь сообщения в этой группе будут автоматически "
                   f"распознаваться как заявки."
               )

               logger.info(f"Установлена группа для парсинга: {group_id}")

           except Exception as e:
               logger.error(f"Ошибка установки группы: {e}", exc_info=True)
               await message.reply(f"❌ Ошибка: {str(e)}")

       # Callback handlers для подтверждений будут в отдельном роутере

       6.3. app/handlers/init.py (изменения)
       # Добавить новый роутер
       from .parser_config import router as parser_config_router

       routers = [
           # ... существующие роутеры
           parser_config_router,
       ]

       Зависимости: ЭТАП 5
       Оценка времени: 4-5 часов

       ---
       ЭТАП 7: Repository для конфигурации парсера (Сложность: НИЗКАЯ)

       Задачи:
       1. Создать repository для работы с ParserConfig
       2. Методы get/set для group_id

       Файлы:

       7.1. app/repositories/parser_config_repository.py (новый файл)
       """Repository для конфигурации парсера"""

       import logging
       from datetime import datetime

       from sqlalchemy import select, update
       from sqlalchemy.ext.asyncio import AsyncSession

       from app.database.orm_models import ParserConfig
       from .base import BaseRepository

       logger = logging.getLogger(__name__)

       class ParserConfigRepository(BaseRepository[ParserConfig]):
           """Repository для ParserConfig"""

           def __init__(self, db):
               super().__init__(db, ParserConfig)

           async def get_current_config(self) -> ParserConfig | None:
               """Получение текущей конфигурации"""
               async with self._get_session() as session:
                   result = await session.execute(
                       select(ParserConfig).limit(1)
                   )
                   return result.scalar_one_or_none()

           async def set_group_id(self, group_id: int) -> ParserConfig:
               """Установка ID группы для мониторинга"""
               async with self._get_session() as session:
                   config = await self.get_current_config()

                   if config:
                       # Обновление существующей
                       config.group_id = group_id
                       config.enabled = True
                       config.updated_at = datetime.utcnow()
                   else:
                       # Создание новой
                       config = ParserConfig(
                           group_id=group_id,
                           enabled=True
                       )
                       session.add(config)

                   await session.commit()
                   await session.refresh(config)

                   return config

           async def get_group_id(self) -> int | None:
               """Получение ID группы"""
               config = await self.get_current_config()
               return config.group_id if config else None

           async def is_enabled(self) -> bool:
               """Проверка включен ли парсер"""
               config = await self.get_current_config()
               return config.enabled if config else False

       7.2. app/repositories/init.py (изменения)
       from .parser_config_repository import ParserConfigRepository

       __all__ = [
           # ... существующие
           'ParserConfigRepository',
       ]

       Зависимости: ЭТАП 1
       Оценка времени: 2-3 часа

       ---
       ЭТАП 8: Unit тесты (Сложность: СРЕДНЯЯ)

       Задачи:
       1. Тесты для парсера (≈80% coverage)
       2. Тесты для equipment_dict
       3. Тесты для patterns

       Файлы:

       8.1. tests/services/telegram_parser/test_parser.py
       """Тесты для OrderParserService"""

       import pytest
       from app.services.telegram_parser.parser import OrderParserService

       @pytest.fixture
       def parser():
           return OrderParserService()

       def test_parse_simple_message(parser):
           """Тест парсинга простого сообщения"""
           text = """С/м Bosch
       Не крутит барабан
       ул. Ленина д. 10 кв. 5
       +79001234567
       Завтра после 14:00"""

           result = parser.parse_message(text, 1, -100, 12345)

           assert result.success
           assert result.order.equipment_type == "Стиральная машина"
           assert "не крутит" in result.order.description.lower()
           assert "ленина" in result.order.client_address.lower()
           assert result.order.client_phone == "+79001234567"
           assert result.order.scheduled_time == "Завтра после 14:00"

       def test_parse_without_phone(parser):
           """Тест парсинга без телефона"""
           text = """ТВ Samsung
       Не включается
       пр. Мира 25-18"""

           result = parser.parse_message(text, 2, -100, 12345)

           assert result.success
           assert result.order.equipment_type == "Телевизор"
           assert result.order.client_phone is None

       def test_parse_incomplete_message(parser):
           """Тест парсинга неполного сообщения"""
           text = """С/м
       Барабан"""

           result = parser.parse_message(text, 3, -100, 12345)

           assert not result.success
           assert result.error_message is not None

       # ... ещё 15-20 тестов

       8.2. tests/services/telegram_parser/test_equipment_dict.py
       """Тесты для словаря сокращений"""

       import pytest
       from app.services.telegram_parser.equipment_dict import normalize_equipment_type

       def test_normalize_washing_machine():
           assert normalize_equipment_type("С/м Bosch") == "Стиральная машина"
           assert normalize_equipment_type("стиралка") == "Стиральная машина"

       def test_normalize_tv():
           assert normalize_equipment_type("ТВ Samsung") == "Телевизор"
           assert normalize_equipment_type("телевизор") == "Телевизор"

       # ... ещё тесты

       8.3. tests/services/telegram_parser/test_patterns.py
       """Тесты для regex паттернов"""

       import pytest
       from app.services.telegram_parser.patterns import (
           extract_phone,
           contains_time_indicator,
           looks_like_address
       )

       def test_extract_phone_formats():
           assert extract_phone("+79001234567") == "+79001234567"
           assert extract_phone("8 900 123-45-67") == "+79001234567"
           assert extract_phone("Телефон: 8(900)123-45-67") == "+79001234567"

       def test_time_indicator():
           assert contains_time_indicator("Завтра 14:00")
           assert contains_time_indicator("Через 2 часа")
           assert not contains_time_indicator("Позвонить клиенту")

       def test_address_detection():
           assert looks_like_address("ул. Ленина д. 10")
           assert looks_like_address("Мира 25-18")
           assert not looks_like_address("Не включается")

       # ... ещё тесты

       Зависимости: ЭТАП 4
       Оценка времени: 6-8 часов

       ---
       ЭТАП 9: Интеграционные тесты (Сложность: СРЕДНЯЯ)

       Задачи:
       1. Тест создания заявки через парсер
       2. Тест подтверждения/отмены

       Файлы:

       9.1. tests/integration/test_parser_integration.py
       """Интеграционные тесты парсера"""

       import pytest
       from app.services.telegram_parser import OrderParserService, OrderConfirmationService
       from app.database import Database

       @pytest.mark.asyncio
       async def test_full_parsing_flow(test_db: Database, test_bot):
           """Полный цикл: парсинг -> подтверждение -> создание заявки"""
           parser = OrderParserService()
           confirmation_service = OrderConfirmationService(test_db, test_bot)

           text = """С/м Bosch
       Не работает
       ул. Тестовая д. 1 кв. 1
       +79991234567"""

           # Парсинг
           result = parser.parse_message(text, 1, -100, 12345)
           assert result.success

           # Подтверждение
           confirmation_service.pending_confirmations[1] = result.order
           await confirmation_service.handle_confirmation(1, True, 12345)

           # Проверка что заявка создана в БД
           # ...

       # ... ещё 3-5 тестов

       Зависимости: ЭТАП 5, ЭТАП 8
       Оценка времени: 3-4 часа

       ---
       ЭТАП 10: Документация и финализация (Сложность: НИЗКАЯ)

       Задачи:
       1. Обновить README.md
       2. Обновить CHANGELOG.md
       3. Обновить VERSION
       4. Создать документацию по настройке

       Файлы:

       10.1. docs/PARSER_SETUP.md (новый файл)
       # Настройка Telethon парсера заявок

       ## Требования

       1. API_ID и API_HASH от Telegram
       2. Номер телефона для авторизации

       ## Шаги настройки

       ### 1. Получение API credentials

       1. Перейти на https://my.telegram.org
       2. Войти с номером телефона
       3. Перейти в API development tools
       4. Создать новое приложение
       5. Скопировать API_ID и API_HASH

       ### 2. Настройка .env

       ```env
       TELETHON_API_ID=12345678
       TELETHON_API_HASH=abcdef1234567890
       TELETHON_PHONE=+79001234567
       TELETHON_SESSION_NAME=parser_session

       3. Первый запуск

       При первом запуске Telethon запросит код подтверждения из Telegram.

       4. Настройка группы

       1. Добавить бота в группу
       2. Вызвать команду /set_group в группе
       3. Парсер начнет мониторить сообщения

       Формат сообщений

       Парсер распознает сообщения в свободной форме:

       С/м Bosch
       Не крутит барабан
       ул. Ленина д. 10 кв. 5
       +79001234567
       Завтра после 14:00

       Обязательные поля

       - Адрес (с номером дома)
       - Описание проблемы

       Опциональные поля

       - Тип техники (если не указан - "Не определено")
       - Телефон
       - Время визита

       **10.2. docs/CHANGELOG.md** (изменения)
       ```markdown
       # Changelog

       ## [v2.11.0] - 2025-01-XX

       ### Added
       - 🤖 Интеграция Telethon-клиента для парсинга заявок из Telegram-группы
       - 📝 Гибкий парсер сообщений с поддержкой свободного формата
       - ✅ Механизм подтверждения создания заявок через inline-кнопки
       - 📚 Словарь сокращений типов техники (С/м, П/м, ТВ и т.д.)
       - ⚙️ Команда /set_group для настройки группы мониторинга
       - 🗄️ Таблица parser_config для хранения настроек парсера
       - 🧪 Unit-тесты для парсера (покрытие >80%)
       - 📖 Документация по настройке парсера

       ### Changed
       - 🔧 bot.py: добавлен параллельный запуск Telethon клиента
       - 📦 requirements.txt: добавлена зависимость telethon==1.34.0

       ### Technical Details
       - Парсер работает параллельно с основным aiogram ботом
       - Поддержка парсинга телефона, адреса, времени визита
       - Автоматическое создание заявок со статусом NEW
       - Интеграция с существующей системой репозиториев

       10.3. VERSION (изменения)
       v2.11.0

       10.4. README.md (изменения)
       ## Новые возможности (v2.11.0)

       ### 🤖 Автоматический парсинг заявок из группы

       Бот теперь может автоматически распознавать заявки из сообщений в Telegram-группе!

       **Возможности:**
       - Парсинг сообщений в свободном формате
       - Распознавание типа техники по сокращениям (С/м, П/м, ТВ и т.д.)
       - Извлечение адреса, телефона, времени визита
       - Подтверждение через inline-кнопки перед созданием заявки

       **Настройка:**
       См. [docs/PARSER_SETUP.md](docs/PARSER_SETUP.md)

       Зависимости: Все предыдущие этапы
       Оценка времени: 3-4 часа

       ---
       IV. Требования к тестированию

       Unit-тесты (≈80% coverage)

       Модули для покрытия:
       1. OrderParserService - парсинг сообщений
       2. equipment_dict - нормализация типов техники
       3. patterns - regex функции
       4. ParserConfigRepository - работа с конфигурацией

       Минимум тестов: 25-30 unit-тестов

       Интеграционные тесты (≈10%)

       Сценарии:
       1. Полный цикл: парсинг → подтверждение → создание заявки
       2. Отмена создания заявки
       3. Обработка некорректных сообщений

       Минимум тестов: 5-7 интеграционных тестов

       Ручное тестирование

       Чек-лист:
       - Первичная авторизация Telethon
       - Команда /set_group в группе
       - Парсинг различных форматов сообщений
       - Подтверждение создания заявки
       - Отмена создания заявки
       - Создание заявки в БД с корректными данными
       - Параллельная работа aiogram и telethon

       ---
       V. Рекомендации по качеству

       Лучшие практики

       1. Логирование:
         - Все этапы парсинга логировать на уровне DEBUG
         - Ошибки - на уровне ERROR с exc_info=True
       2. Обработка ошибок:
         - try/except вокруг парсинга каждого сообщения
         - Graceful degradation - не падать при ошибке
       3. Валидация:
         - Всегда использовать Pydantic для валидации
         - Не доверять данным из сообщений
       4. Производительность:
         - Не блокировать event loop в обработчиках
         - Использовать asyncio для IO операций

       Потенциальные подводные камни

       1. Session файл Telethon
         - ⚠️ Обязательно добавить *.session в .gitignore
         - ⚠️ Session файл привязан к номеру телефона
       2. Конфликт двух клиентов
         - ✅ aiogram и telethon работают независимо
         - ⚠️ Но используют общую БД - нужна синхронизация
       3. Обработка callback от Telethon
         - ⚠️ Callback кнопки должны быть в Telethon, не в aiogram
         - Решение: хранить pending_confirmations в памяти
       4. Парсинг адресов
         - ⚠️ Сложность: много вариантов написания
         - Решение: гибкие правила + ручная проверка через подтверждение

       Рекомендации по оптимизации

       1. Кэширование:
         - Кэшировать group_id в памяти (не запрашивать из БД каждый раз)
       2. Батчинг:
         - Если сообщений много - батчить создание заявок
       3. Мониторинг:
         - Логировать метрики: успешных парсингов, ошибок, времени обработки

       ---
       VI. Оценка времени и приоритизация

       Общая оценка времени: 40-50 часов

       Разбивка по этапам:

       | Этап | Задача               | Часы | Приоритет |
       |------|----------------------|------|-----------|
       | 1    | Инфраструктура       | 1-2  | ВЫСОКИЙ   |
       | 2    | Словарь и паттерны   | 2-3  | ВЫСОКИЙ   |
       | 3    | Pydantic схемы       | 2-3  | ВЫСОКИЙ   |
       | 4    | Сервис парсинга      | 6-8  | ВЫСОКИЙ   |
       | 5    | Telethon клиент      | 8-10 | ВЫСОКИЙ   |
       | 6    | Интеграция с ботом   | 4-5  | ВЫСОКИЙ   |
       | 7    | Repository           | 2-3  | СРЕДНИЙ   |
       | 8    | Unit-тесты           | 6-8  | ВЫСОКИЙ   |
       | 9    | Интеграционные тесты | 3-4  | СРЕДНИЙ   |
       | 10   | Документация         | 3-4  | ВЫСОКИЙ   |

       MVC (Minimum Viable Component)

       Для быстрого прототипирования можно реализовать:

       Фаза 1 (MVP - 15-20 часов):
       - ЭТАП 1: Инфраструктура
       - ЭТАП 2: Словарь и паттерны
       - ЭТАП 3: Pydantic схемы
       - ЭТАП 4: Базовый парсер (без всех edge cases)
       - ЭТАП 5: Минимальный Telethon клиент (без подтверждений)

       Фаза 2 (Полная версия - 20-30 часов):
       - Механизм подтверждений
       - Команда /set_group
       - Тесты
       - Документация

       Опциональные улучшения (можно добавить позже)

       1. Машинное обучение:
         - Обучение модели для более точного парсинга
         - Распознавание адресов через NER
       2. Аналитика:
         - Статистика успешных/неуспешных парсингов
         - Dashboard для мониторинга
       3. Улучшенный UI:
         - Inline-редактирование распознанных данных
         - Preview перед подтверждением
       4. Мультигруппа:
         - Поддержка нескольких групп одновременно

       ---
       VII. Инструменты и ресурсы

       Необходимые инструменты

       - Python 3.11+
       - SQLite/PostgreSQL
       - Telegram API credentials
       - IDE с поддержкой async (VS Code, PyCharm)

       Внешние сервисы

       - https://my.telegram.org - для получения API credentials

       Документация

       - https://docs.telethon.dev/
       - https://docs.pydantic.dev/latest/
       - https://docs.aiogram.dev/en/latest/

       Рекомендуемые библиотеки

       - telethon==1.34.0 - Telegram MTProto клиент
       - dateparser==1.2.0 - уже в проекте
       - pytest-asyncio - для async тестов (уже должно быть)

       ---
       VIII. Чек-лист готовности к деплою

       - Все unit-тесты пройдены (coverage >80%)
       - Интеграционные тесты пройдены
       - Документация обновлена (README, CHANGELOG, PARSER_SETUP)
       - VERSION обновлен до v2.11.0
       - *.session добавлен в .gitignore
       - .env.example обновлен с новыми переменными
       - Миграция БД создана и протестирована
       - Ручное тестирование выполнено
       - Code review пройден
       - Telethon session протестирован в dev окружении

       ---
       Итоговая структура файлов

       telegram_repair_bot/
       ├── app/
       │   ├── services/
       │   │   └── telegram_parser/
       │   │       ├── __init__.py
       │   │       ├── client.py              # TelethonClient
       │   │       ├── parser.py              # OrderParserService
       │   │       ├── confirmation.py        # OrderConfirmationService
       │   │       ├── equipment_dict.py      # Словарь сокращений
       │   │       └── patterns.py            # Regex паттерны
       │   ├── schemas/
       │   │   └── parser.py                  # OrderParsed, ParseResult
       │   ├── repositories/
       │   │   └── parser_config_repository.py # ParserConfigRepository
       │   ├── database/
       │   │   └── orm_models.py              # + ParserConfig модель
       │   ├── handlers/
       │   │   └── parser_config.py           # /set_group команда
       │   └── core/
       │       └── config.py                  # + Telethon конфиг
       ├── migrations/
       │   └── versions/
       │       └── XXX_add_parser_config.py   # Миграция
       ├── tests/
       │   ├── services/
       │   │   └── telegram_parser/
       │   │       ├── test_parser.py
       │   │       ├── test_equipment_dict.py
       │   │       └── test_patterns.py
       │   └── integration/
       │       └── test_parser_integration.py
       ├── docs/
       │   ├── PARSER_SETUP.md                # Новый
       │   └── CHANGELOG.md                   # Обновлен
       ├── requirements.txt                   # + telethon
       ├── VERSION                            # v2.11.0
       ├── bot.py                             # + Telethon интеграция
       └── .gitignore                         # + *.session

       ---
       Заключение

       Этот план предоставляет полную дорожную карту для интеграции Telethon-клиента с парсером заявок.
       План разработан с учетом существующей архитектуры проекта и следует установленным практикам (чистая
       архитектура, Pydantic валидация, repository pattern).

       Ключевые преимущества плана:
       - ✅ Пошаговая реализация с четкими зависимостями
       - ✅ Высокое покрытие тестами
       - ✅ Подробная документация
       - ✅ Возможность инкрементальной реализации (MVP → Full)
       - ✅ Учет всех требований из logic_parser.md

       Следующие шаги:
       1. Получить API credentials от Telegram
       2. Начать с ЭТАП 1 (инфраструктура)
       3. Двигаться последовательно по этапам
