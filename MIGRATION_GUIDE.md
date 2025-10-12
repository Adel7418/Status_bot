# 🔄 Migration Guide

## Переход с текущей структуры на Alembic

Текущий проект использует прямое изменение схемы БД через `ALTER TABLE` в коде. Этот гайд поможет мигрировать на Alembic.

## Зачем нужен Alembic?

### Проблемы текущего подхода

В `app/database/db.py` есть код вроде:

```python
try:
    await self.connection.execute("""
        ALTER TABLE masters ADD COLUMN work_chat_id INTEGER
    """)
except Exception:
    # Поле уже существует, игнорируем ошибку
    pass
```

**Проблемы:**
- ❌ Нет версионирования изменений
- ❌ Невозможно откатить изменения
- ❌ Непонятно, какие изменения применены
- ❌ Ошибки игнорируются молча
- ❌ Сложно синхронизировать БД между окружениями

### Преимущества Alembic

- ✅ Версионирование схемы БД
- ✅ Возможность отката (rollback)
- ✅ История всех изменений
- ✅ Автоматическая генерация миграций
- ✅ Работа в команде упрощается

## Шаги миграции

### Шаг 1: Установка Alembic

```bash
pip install alembic
# или
pip install -r requirements-dev.txt
```

### Шаг 2: Инициализация (УЖЕ СДЕЛАНО)

Структура уже создана:
```
migrations/
├── env.py
├── script.py.mako
├── versions/
└── README
```

### Шаг 3: Создание базовой миграции

Эта миграция зафиксирует текущее состояние БД:

```bash
alembic revision -m "initial schema"
```

Откройте созданный файл и добавьте:

```python
def upgrade():
    # Создание таблицы users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('telegram_id', sa.Integer(), unique=True, nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('role', sa.String(), default='UNKNOWN'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now())
    )
    
    # Создание таблицы masters
    op.create_table(
        'masters',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('telegram_id', sa.Integer(), unique=True, nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('specialization', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_approved', sa.Boolean(), default=False),
        sa.Column('work_chat_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['telegram_id'], ['users.telegram_id'])
    )
    
    # Создание таблицы orders
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('equipment_type', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('client_name', sa.String(), nullable=False),
        sa.Column('client_address', sa.String(), nullable=False),
        sa.Column('client_phone', sa.String(), nullable=False),
        sa.Column('status', sa.String(), default='NEW'),
        sa.Column('assigned_master_id', sa.Integer(), nullable=True),
        sa.Column('dispatcher_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('materials_cost', sa.Float(), nullable=True),
        sa.Column('master_profit', sa.Float(), nullable=True),
        sa.Column('company_profit', sa.Float(), nullable=True),
        sa.Column('has_review', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['assigned_master_id'], ['masters.id']),
        sa.ForeignKeyConstraint(['dispatcher_id'], ['users.telegram_id'])
    )
    
    # Создание таблицы audit_log
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('details', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.telegram_id'])
    )
    
    # Создание индексов
    op.create_index('idx_users_telegram_id', 'users', ['telegram_id'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_masters_telegram_id', 'masters', ['telegram_id'])
    op.create_index('idx_masters_is_approved', 'masters', ['is_approved'])
    op.create_index('idx_orders_status', 'orders', ['status'])
    op.create_index('idx_orders_assigned_master_id', 'orders', ['assigned_master_id'])
    op.create_index('idx_orders_dispatcher_id', 'orders', ['dispatcher_id'])
    op.create_index('idx_audit_user_id', 'audit_log', ['user_id'])

def downgrade():
    op.drop_table('audit_log')
    op.drop_table('orders')
    op.drop_table('masters')
    op.drop_table('users')
```

### Шаг 4: Пометить текущую БД как migrated

Если БД уже существует, отметьте её как migrated:

```bash
# Это добавит запись в alembic_version без применения миграции
alembic stamp head
```

### Шаг 5: Рефакторинг кода БД

Удалите `ALTER TABLE` из `app/database/db.py`:

```python
# УДАЛИТЬ ЭТО:
try:
    await self.connection.execute("""
        ALTER TABLE masters ADD COLUMN work_chat_id INTEGER
    """)
except Exception:
    pass
```

Вместо этого создайте миграцию:

```bash
alembic revision -m "add work_chat_id to masters"
```

### Шаг 6: Тестирование

```bash
# Создать тестовую БД
cp bot_database.db bot_database_test.db

# Применить миграции
DATABASE_PATH=bot_database_test.db alembic upgrade head

# Проверить
sqlite3 bot_database_test.db ".schema"
```

## Workflow для новых изменений

### 1. Изменение схемы БД

Вместо добавления кода в `init_db()`:

```python
# ❌ ПЛОХО - не делайте так больше
await self.connection.execute("""
    ALTER TABLE users ADD COLUMN email TEXT
""")
```

Создайте миграцию:

```bash
# ✅ ХОРОШО
alembic revision -m "add email to users"
```

### 2. Редактирование миграции

```python
def upgrade():
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))
    op.create_index('idx_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('idx_users_email', 'users')
    op.drop_column('users', 'email')
```

### 3. Применение

```bash
alembic upgrade head
```

## Production Deployment

### Перед запуском бота

```bash
# 1. Backup БД
python backup_db.py

# 2. Применить миграции
alembic upgrade head

# 3. Запустить бота
python bot.py
```

### Автоматизация

Добавьте в `bot.py` перед `db.init_db()`:

```python
import subprocess

# Применить миграции перед запуском
try:
    subprocess.run(['alembic', 'upgrade', 'head'], check=True)
    logger.info("Миграции применены успешно")
except subprocess.CalledProcessError as e:
    logger.error(f"Ошибка применения миграций: {e}")
    sys.exit(1)
```

## Откат изменений

Если что-то пошло не так:

```bash
# 1. Остановить бота

# 2. Откатить последнюю миграцию
alembic downgrade -1

# 3. Восстановить из backup (если нужно)
cp backups/latest_backup.db bot_database.db

# 4. Запустить бота
python bot.py
```

## FAQ

### Q: Что делать с существующей БД?

A: Используйте `alembic stamp head` чтобы пометить текущую версию.

### Q: Можно ли откатить миграцию в production?

A: Да, но осторожно. Всегда делайте backup перед откатом.

### Q: Как применить миграции в Docker?

A: Добавьте в Dockerfile:
```dockerfile
RUN alembic upgrade head
```
Или в `docker-compose.yml`:
```yaml
command: sh -c "alembic upgrade head && python bot.py"
```

### Q: Нужно ли удалить `init_db()`?

A: Нет, оставьте для совместимости. Но уберите `ALTER TABLE` логику.

## Checklist миграции

- [ ] Установлен Alembic
- [ ] Создана базовая миграция (`initial schema`)
- [ ] Существующая БД помечена (`alembic stamp head`)
- [ ] Удалены `ALTER TABLE` из кода
- [ ] Протестированы миграции на тестовой БД
- [ ] Обновлён CI/CD для запуска миграций
- [ ] Обновлена документация
- [ ] Команда проинформирована о новом workflow

## Полезные ссылки

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Миграции в migrations/README](migrations/README)

