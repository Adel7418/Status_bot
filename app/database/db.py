"""
Работа с базой данных
"""
import aiosqlite
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.config import Config, UserRole, OrderStatus
from app.database.models import User, Master, Order, AuditLog

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = None):
        """
        Инициализация
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path or Config.DATABASE_PATH
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Подключение к базе данных"""
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row
        logger.info(f"Подключено к базе данных: {self.db_path}")
    
    async def disconnect(self):
        """Отключение от базы данных"""
        if self.connection:
            await self.connection.close()
            logger.info("Отключено от базы данных")
    
    async def init_db(self):
        """Инициализация базы данных"""
        if not self.connection:
            await self.connect()
        
        # Создание таблицы users
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                role TEXT DEFAULT 'UNKNOWN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создание таблицы masters
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                specialization TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                is_approved BOOLEAN DEFAULT 0,
                work_chat_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)
        
        # Добавление поля work_chat_id в существующую таблицу (если его нет)
        try:
            await self.connection.execute("""
                ALTER TABLE masters ADD COLUMN work_chat_id INTEGER
            """)
            await self.connection.commit()
            logger.info("Добавлено поле work_chat_id в таблицу masters")
        except Exception:
            # Поле уже существует, игнорируем ошибку
            pass
        
        # Создание таблицы orders
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_type TEXT NOT NULL,
                description TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_address TEXT NOT NULL,
                client_phone TEXT NOT NULL,
                status TEXT DEFAULT 'NEW',
                assigned_master_id INTEGER,
                dispatcher_id INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assigned_master_id) REFERENCES masters(id),
                FOREIGN KEY (dispatcher_id) REFERENCES users(telegram_id)
            )
        """)
        
        # Создание таблицы audit_log
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
        """)
        
        await self.connection.commit()
        logger.info("База данных инициализирована")
        
        # Создание индексов для оптимизации запросов
        await self._create_indexes()
    
    async def _create_indexes(self):
        """Создание индексов для оптимизации"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS idx_masters_telegram_id ON masters(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_masters_is_approved ON masters(is_approved)",
            "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
            "CREATE INDEX IF NOT EXISTS idx_orders_assigned_master_id ON orders(assigned_master_id)",
            "CREATE INDEX IF NOT EXISTS idx_orders_dispatcher_id ON orders(dispatcher_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_log(user_id)"
        ]
        
        for index_sql in indexes:
            await self.connection.execute(index_sql)
        
        await self.connection.commit()
    
    # ==================== USERS ====================
    
    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """
        Получение или создание пользователя
        
        Args:
            telegram_id: Telegram ID
            username: Username
            first_name: Имя
            last_name: Фамилия
            
        Returns:
            Объект User
        """
        # Проверяем существование пользователя
        user = await self.get_user_by_telegram_id(telegram_id)
        
        if user:
            # Обновляем информацию если изменилась
            if user.username != username or user.first_name != first_name or user.last_name != last_name:
                await self.connection.execute(
                    """
                    UPDATE users 
                    SET username = ?, first_name = ?, last_name = ?
                    WHERE telegram_id = ?
                    """,
                    (username, first_name, last_name, telegram_id)
                )
                await self.connection.commit()
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
            return user
        
        # Определяем роль
        role = UserRole.UNKNOWN
        if telegram_id in Config.ADMIN_IDS:
            role = UserRole.ADMIN
        elif telegram_id in Config.DISPATCHER_IDS:
            role = UserRole.DISPATCHER
        
        # Создаем нового пользователя
        cursor = await self.connection.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_id, username, first_name, last_name, role)
        )
        await self.connection.commit()
        
        user = User(
            id=cursor.lastrowid,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
            created_at=datetime.now()
        )
        
        logger.info(f"Создан новый пользователь: {telegram_id} с ролью {role}")
        return user
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Получение пользователя по Telegram ID
        
        Args:
            telegram_id: Telegram ID
            
        Returns:
            Объект User или None
        """
        cursor = await self.connection.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return User(
                id=row['id'],
                telegram_id=row['telegram_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                role=row['role'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
            )
        return None
    
    async def update_user_role(self, telegram_id: int, role: str) -> bool:
        """
        Обновление роли пользователя
        
        Args:
            telegram_id: Telegram ID
            role: Новая роль
            
        Returns:
            True если успешно
        """
        await self.connection.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?",
            (role, telegram_id)
        )
        await self.connection.commit()
        logger.info(f"Роль пользователя {telegram_id} изменена на {role}")
        return True
    
    async def get_all_users(self) -> List[User]:
        """
        Получение всех пользователей
        
        Returns:
            Список пользователей
        """
        cursor = await self.connection.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        
        users = []
        for row in rows:
            users.append(User(
                id=row['id'],
                telegram_id=row['telegram_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                role=row['role'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
            ))
        return users
    
    # ==================== MASTERS ====================
    
    async def create_master(
        self,
        telegram_id: int,
        phone: str,
        specialization: str,
        is_approved: bool = False
    ) -> Master:
        """
        Создание мастера
        
        Args:
            telegram_id: Telegram ID
            phone: Телефон
            specialization: Специализация
            is_approved: Одобрен ли
            
        Returns:
            Объект Master
        """
        cursor = await self.connection.execute(
            """
            INSERT INTO masters (telegram_id, phone, specialization, is_approved)
            VALUES (?, ?, ?, ?)
            """,
            (telegram_id, phone, specialization, is_approved)
        )
        await self.connection.commit()
        
        master = Master(
            id=cursor.lastrowid,
            telegram_id=telegram_id,
            phone=phone,
            specialization=specialization,
            is_approved=is_approved,
            created_at=datetime.now()
        )
        
        logger.info(f"Создан мастер: {telegram_id}")
        return master
    
    async def get_master_by_telegram_id(self, telegram_id: int) -> Optional[Master]:
        """
        Получение мастера по Telegram ID
        
        Args:
            telegram_id: Telegram ID
            
        Returns:
            Объект Master или None
        """
        cursor = await self.connection.execute(
            """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE m.telegram_id = ?
            """,
            (telegram_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return Master(
                id=row['id'],
                telegram_id=row['telegram_id'],
                phone=row['phone'],
                specialization=row['specialization'],
                is_active=bool(row['is_active']),
                is_approved=bool(row['is_approved']),
                work_chat_id=row['work_chat_id'] if 'work_chat_id' in row.keys() else None,
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name']
            )
        return None
    
    async def get_master_by_id(self, master_id: int) -> Optional[Master]:
        """
        Получение мастера по ID
        
        Args:
            master_id: ID мастера
            
        Returns:
            Объект Master или None
        """
        cursor = await self.connection.execute(
            """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE m.id = ?
            """,
            (master_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return Master(
                id=row['id'],
                telegram_id=row['telegram_id'],
                phone=row['phone'],
                specialization=row['specialization'],
                is_active=bool(row['is_active']),
                is_approved=bool(row['is_approved']),
                work_chat_id=row['work_chat_id'] if 'work_chat_id' in row.keys() else None,
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name']
            )
        return None
    
    async def get_all_masters(self, only_approved: bool = False, only_active: bool = False) -> List[Master]:
        """
        Получение всех мастеров
        
        Args:
            only_approved: Только одобренные
            only_active: Только активные
            
        Returns:
            Список мастеров
        """
        query = """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE 1=1
        """
        params = []
        
        if only_approved:
            query += " AND m.is_approved = 1"
        if only_active:
            query += " AND m.is_active = 1"
        
        query += " ORDER BY m.created_at DESC"
        
        cursor = await self.connection.execute(query, params)
        rows = await cursor.fetchall()
        
        masters = []
        for row in rows:
            masters.append(Master(
                id=row['id'],
                telegram_id=row['telegram_id'],
                phone=row['phone'],
                specialization=row['specialization'],
                is_active=bool(row['is_active']),
                is_approved=bool(row['is_approved']),
                work_chat_id=row['work_chat_id'] if 'work_chat_id' in row.keys() else None,
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name']
            ))
        return masters
    
    async def get_pending_masters(self) -> List[Master]:
        """
        Получение мастеров, ожидающих одобрения
        
        Returns:
            Список мастеров
        """
        cursor = await self.connection.execute(
            """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE m.is_approved = 0
            ORDER BY m.created_at ASC
            """
        )
        rows = await cursor.fetchall()
        
        masters = []
        for row in rows:
            masters.append(Master(
                id=row['id'],
                telegram_id=row['telegram_id'],
                phone=row['phone'],
                specialization=row['specialization'],
                is_active=bool(row['is_active']),
                is_approved=bool(row['is_approved']),
                work_chat_id=row['work_chat_id'] if 'work_chat_id' in row.keys() else None,
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name']
            ))
        return masters
    
    async def approve_master(self, telegram_id: int) -> bool:
        """
        Одобрение мастера
        
        Args:
            telegram_id: Telegram ID мастера
            
        Returns:
            True если успешно
        """
        await self.connection.execute(
            "UPDATE masters SET is_approved = 1 WHERE telegram_id = ?",
            (telegram_id,)
        )
        await self.connection.commit()
        
        # Обновляем роль пользователя
        await self.update_user_role(telegram_id, UserRole.MASTER)
        
        logger.info(f"Мастер {telegram_id} одобрен")
        return True
    
    async def reject_master(self, telegram_id: int) -> bool:
        """
        Отклонение мастера (удаление из базы)
        
        Args:
            telegram_id: Telegram ID мастера
            
        Returns:
            True если успешно
        """
        await self.connection.execute(
            "DELETE FROM masters WHERE telegram_id = ?",
            (telegram_id,)
        )
        await self.connection.commit()
        
        logger.info(f"Мастер {telegram_id} отклонен и удален")
        return True
    
    async def update_master_status(self, telegram_id: int, is_active: bool) -> bool:
        """
        Обновление статуса активности мастера
        
        Args:
            telegram_id: Telegram ID мастера
            is_active: Статус активности
            
        Returns:
            True если успешно
        """
        await self.connection.execute(
            "UPDATE masters SET is_active = ? WHERE telegram_id = ?",
            (is_active, telegram_id)
        )
        await self.connection.commit()
        
        logger.info(f"Статус мастера {telegram_id} изменен на {'активный' if is_active else 'неактивный'}")
        return True
    
    async def update_master_work_chat(self, telegram_id: int, work_chat_id: Optional[int]) -> bool:
        """
        Обновление ID рабочей группы мастера
        
        Args:
            telegram_id: Telegram ID мастера
            work_chat_id: ID рабочей группы (None для сброса)
            
        Returns:
            True если успешно
        """
        await self.connection.execute(
            "UPDATE masters SET work_chat_id = ? WHERE telegram_id = ?",
            (work_chat_id, telegram_id)
        )
        await self.connection.commit()
        
        logger.info(f"Work chat для мастера {telegram_id} установлен: {work_chat_id}")
        return True
    
    # ==================== ORDERS ====================
    
    async def create_order(
        self,
        equipment_type: str,
        description: str,
        client_name: str,
        client_address: str,
        client_phone: str,
        dispatcher_id: int,
        notes: Optional[str] = None
    ) -> Order:
        """
        Создание заявки
        
        Args:
            equipment_type: Тип техники
            description: Описание проблемы
            client_name: Имя клиента
            client_address: Адрес клиента
            client_phone: Телефон клиента
            dispatcher_id: ID диспетчера
            notes: Заметки
            
        Returns:
            Объект Order
        """
        cursor = await self.connection.execute(
            """
            INSERT INTO orders (equipment_type, description, client_name, client_address, 
                              client_phone, dispatcher_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (equipment_type, description, client_name, client_address, client_phone, 
             dispatcher_id, notes)
        )
        await self.connection.commit()
        
        order = Order(
            id=cursor.lastrowid,
            equipment_type=equipment_type,
            description=description,
            client_name=client_name,
            client_address=client_address,
            client_phone=client_phone,
            dispatcher_id=dispatcher_id,
            notes=notes,
            status=OrderStatus.NEW,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        logger.info(f"Создана заявка #{order.id}")
        return order
    
    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """
        Получение заявки по ID
        
        Args:
            order_id: ID заявки
            
        Returns:
            Объект Order или None
        """
        cursor = await self.connection.execute(
            """
            SELECT o.*, 
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE o.id = ?
            """,
            (order_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return Order(
                id=row['id'],
                equipment_type=row['equipment_type'],
                description=row['description'],
                client_name=row['client_name'],
                client_address=row['client_address'],
                client_phone=row['client_phone'],
                status=row['status'],
                assigned_master_id=row['assigned_master_id'],
                dispatcher_id=row['dispatcher_id'],
                notes=row['notes'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
                dispatcher_name=row['dispatcher_name'],
                master_name=row['master_name']
            )
        return None
    
    async def get_all_orders(
        self,
        status: Optional[str] = None,
        master_id: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Order]:
        """
        Получение всех заявок с фильтрацией
        
        Args:
            status: Фильтр по статусу
            master_id: Фильтр по ID мастера
            limit: Лимит количества
            
        Returns:
            Список заявок
        """
        query = """
            SELECT o.*, 
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND o.status = ?"
            params.append(status)
        
        if master_id:
            query += " AND o.assigned_master_id = ?"
            params.append(master_id)
        
        query += " ORDER BY o.created_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = await self.connection.execute(query, params)
        rows = await cursor.fetchall()
        
        orders = []
        for row in rows:
            orders.append(Order(
                id=row['id'],
                equipment_type=row['equipment_type'],
                description=row['description'],
                client_name=row['client_name'],
                client_address=row['client_address'],
                client_phone=row['client_phone'],
                status=row['status'],
                assigned_master_id=row['assigned_master_id'],
                dispatcher_id=row['dispatcher_id'],
                notes=row['notes'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
                dispatcher_name=row['dispatcher_name'],
                master_name=row['master_name']
            ))
        return orders
    
    async def update_order_status(self, order_id: int, status: str) -> bool:
        """
        Обновление статуса заявки
        
        Args:
            order_id: ID заявки
            status: Новый статус
            
        Returns:
            True если успешно
        """
        await self.connection.execute(
            "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, order_id)
        )
        await self.connection.commit()
        
        logger.info(f"Статус заявки #{order_id} изменен на {status}")
        return True
    
    async def assign_master_to_order(self, order_id: int, master_id: int) -> bool:
        """
        Назначение мастера на заявку
        
        Args:
            order_id: ID заявки
            master_id: ID мастера
            
        Returns:
            True если успешно
        """
        await self.connection.execute(
            """
            UPDATE orders 
            SET assigned_master_id = ?, status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
            """,
            (master_id, OrderStatus.ASSIGNED, order_id)
        )
        await self.connection.commit()
        
        logger.info(f"Мастер {master_id} назначен на заявку #{order_id}")
        return True
    
    async def update_order(
        self,
        order_id: int,
        equipment_type: Optional[str] = None,
        description: Optional[str] = None,
        client_name: Optional[str] = None,
        client_address: Optional[str] = None,
        client_phone: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Обновление информации о заявке
        
        Args:
            order_id: ID заявки
            equipment_type: Тип техники
            description: Описание
            client_name: Имя клиента
            client_address: Адрес клиента
            client_phone: Телефон клиента
            notes: Заметки
            
        Returns:
            True если успешно
        """
        updates = []
        params = []
        
        if equipment_type:
            updates.append("equipment_type = ?")
            params.append(equipment_type)
        if description:
            updates.append("description = ?")
            params.append(description)
        if client_name:
            updates.append("client_name = ?")
            params.append(client_name)
        if client_address:
            updates.append("client_address = ?")
            params.append(client_address)
        if client_phone:
            updates.append("client_phone = ?")
            params.append(client_phone)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        
        if not updates:
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(order_id)
        
        query = f"UPDATE orders SET {', '.join(updates)} WHERE id = ?"
        await self.connection.execute(query, params)
        await self.connection.commit()
        
        logger.info(f"Заявка #{order_id} обновлена")
        return True
    
    async def get_orders_by_master(self, master_id: int, exclude_closed: bool = True) -> List[Order]:
        """
        Получение заявок мастера
        
        Args:
            master_id: ID мастера
            exclude_closed: Исключить закрытые заявки
            
        Returns:
            Список заявок
        """
        query = """
            SELECT o.*, 
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE o.assigned_master_id = ?
        """
        params = [master_id]
        
        if exclude_closed:
            query += " AND o.status NOT IN (?, ?)"
            params.extend([OrderStatus.CLOSED, OrderStatus.REFUSED])
        
        query += " ORDER BY o.created_at DESC"
        
        cursor = await self.connection.execute(query, params)
        rows = await cursor.fetchall()
        
        orders = []
        for row in rows:
            orders.append(Order(
                id=row['id'],
                equipment_type=row['equipment_type'],
                description=row['description'],
                client_name=row['client_name'],
                client_address=row['client_address'],
                client_phone=row['client_phone'],
                status=row['status'],
                assigned_master_id=row['assigned_master_id'],
                dispatcher_id=row['dispatcher_id'],
                notes=row['notes'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
                dispatcher_name=row['dispatcher_name'],
                master_name=row['master_name']
            ))
        return orders
    
    # ==================== AUDIT LOG ====================
    
    async def add_audit_log(
        self,
        user_id: int,
        action: str,
        details: Optional[str] = None
    ):
        """
        Добавление записи в лог аудита
        
        Args:
            user_id: ID пользователя
            action: Действие
            details: Детали
        """
        await self.connection.execute(
            "INSERT INTO audit_log (user_id, action, details) VALUES (?, ?, ?)",
            (user_id, action, details)
        )
        await self.connection.commit()
    
    async def get_audit_logs(self, limit: int = 100) -> List[AuditLog]:
        """
        Получение логов аудита
        
        Args:
            limit: Лимит записей
            
        Returns:
            Список логов
        """
        cursor = await self.connection.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        
        logs = []
        for row in rows:
            logs.append(AuditLog(
                id=row['id'],
                user_id=row['user_id'],
                action=row['action'],
                details=row['details'],
                timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None
            ))
        return logs
    
    # ==================== STATISTICS ====================
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики
        
        Returns:
            Словарь со статистикой
        """
        stats = {}
        
        # Количество пользователей по ролям
        cursor = await self.connection.execute(
            "SELECT role, COUNT(*) as count FROM users GROUP BY role"
        )
        roles_stats = await cursor.fetchall()
        stats['users_by_role'] = {row['role']: row['count'] for row in roles_stats}
        
        # Количество заявок по статусам
        cursor = await self.connection.execute(
            "SELECT status, COUNT(*) as count FROM orders GROUP BY status"
        )
        orders_stats = await cursor.fetchall()
        stats['orders_by_status'] = {row['status']: row['count'] for row in orders_stats}
        
        # Количество активных мастеров
        cursor = await self.connection.execute(
            "SELECT COUNT(*) as count FROM masters WHERE is_active = 1 AND is_approved = 1"
        )
        row = await cursor.fetchone()
        stats['active_masters'] = row['count']
        
        # Общее количество заявок
        cursor = await self.connection.execute("SELECT COUNT(*) as count FROM orders")
        row = await cursor.fetchone()
        stats['total_orders'] = row['count']
        
        return stats

