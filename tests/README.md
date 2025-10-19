# Тесты для Telegram Bot

## Структура тестов

```
tests/
├── __init__.py           # Инициализация пакета тестов
├── conftest.py           # Общие фикстуры для всех тестов
├── test_config.py        # Тесты для конфигурации
├── test_database.py      # Тесты для базы данных
├── test_models.py        # Тесты для моделей данных
├── test_utils.py         # Тесты для утилит
└── README.md            # Этот файл
```

## Установка зависимостей

```bash
pip install -r requirements-dev.txt
```

## Запуск тестов

### Запуск всех тестов

```bash
pytest
```

### Запуск с coverage

```bash
pytest --cov=app --cov-report=html --cov-report=term
```

### Запуск конкретного файла

```bash
pytest tests/test_database.py
```

### Запуск конкретного теста

```bash
pytest tests/test_database.py::TestDatabase::test_create_and_get_user
```

### Запуск с verbose режимом

```bash
pytest -v
```

### Запуск с отображением print

```bash
pytest -s
```

## Типы тестов

### Unit тесты
Тестируют отдельные функции и методы в изоляции.

```bash
pytest -m unit
```

### Integration тесты
Тестируют взаимодействие между компонентами.

```bash
pytest -m integration
```

### Медленные тесты
Пропуск медленных тестов:

```bash
pytest -m "not slow"
```

## Фикстуры

### Фикстуры базы данных

- `db` - in-memory база данных SQLite для тестов
- `admin_id` - ID администратора
- `dispatcher_id` - ID диспетчера
- `master_id` - ID мастера

### Фикстуры aiogram

- `bot` - экземпляр бота для тестов
- `dp` - диспетчер с MemoryStorage
- `bot_token` - тестовый токен

### Фикстуры конфигурации

- `mock_config` - замена реальной конфигурации на тестовую

## Coverage отчёт

После запуска с `--cov-report=html` откройте:

```bash
# Windows
start htmlcov/index.html

# Linux/macOS
open htmlcov/index.html
```

## Continuous Integration

Тесты автоматически запускаются при push в репозиторий через GitHub Actions.

См. `.github/workflows/test.yml` для настройки CI/CD.

## Написание новых тестов

### Пример unit теста

```python
def test_example():
    """Описание теста"""
    result = my_function(42)
    assert result == expected_value
```

### Пример async теста

```python
@pytest.mark.asyncio
async def test_async_example(db: Database):
    """Описание async теста"""
    user = await db.get_user_by_telegram_id(123)
    assert user is not None
```

### Пример теста с mock

```python
def test_with_mock(mocker):
    """Тест с использованием mock"""
    mock_function = mocker.patch('app.module.function')
    mock_function.return_value = "mocked"

    result = call_function_that_uses_mock()
    assert result == "expected"
    mock_function.assert_called_once()
```

## Полезные команды

```bash
# Запуск тестов с автоматической перезагрузкой
pytest-watch

# Запуск только упавших тестов
pytest --lf

# Запуск последних упавших тестов в первую очередь
pytest --ff

# Остановка после первого упавшего теста
pytest -x

# Параллельный запуск тестов
pytest -n auto
```

## Troubleshooting

### Проблема: тесты не находят модули

```bash
# Убедитесь, что PYTHONPATH настроен правильно
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Проблема: async тесты не работают

```bash
# Установите pytest-asyncio
pip install pytest-asyncio
```

### Проблема: Coverage показывает 0%

```bash
# Укажите правильный путь к исходникам
pytest --cov=app --cov-report=term
```
