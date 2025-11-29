# Contributing Guide

Спасибо за интерес к проекту! Этот документ описывает процесс контрибуции.

## 📋 Содержание

- [Code of Conduct](#code-of-conduct)
- [Как начать](#как-начать)
- [Процесс разработки](#процесс-разработки)
- [Pull Request Process](#pull-request-process)
- [Стиль кода](#стиль-кода)
- [Тестирование](#тестирование)
- [Документация](#документация)

## Code of Conduct

Участвуя в проекте, вы соглашаетесь соблюдать наш Code of Conduct:

- Будьте уважительны к другим участникам
- Конструктивная критика приветствуется
- Фокусируйтесь на том, что лучше для проекта
- Проявляйте эмпатию к другим участникам

## Как начать

### 1. Fork и Clone

```bash
# Fork через GitHub UI
# Затем clone your fork
git clone https://github.com/YOUR_USERNAME/telegram-repair-bot.git
cd telegram-repair-bot
```

### 2. Настройка окружения

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
make install-dev
# или
pip install -r requirements-dev.txt

# Установить pre-commit hooks
pre-commit install
```

### 3. Создать ветку

```bash
git checkout -b feature/my-new-feature
# или
git checkout -b fix/bug-description
```

## Процесс разработки

### Типы изменений

Используйте префиксы для веток:

- `feature/` - новая функциональность
- `fix/` - исправление бага
- `docs/` - изменения в документации
- `refactor/` - рефакторинг без изменения функциональности
- `test/` - добавление тестов
- `chore/` - технические изменения (dependencies, CI, etc.)

### Workflow

1. **Сделать изменения**
   ```bash
   # Редактировать файлы
   # Тестировать локально
   ```

2. **Запустить проверки**
   ```bash
   make lint      # Проверка линтерами
   make format    # Форматирование кода
   make test      # Запуск тестов
   ```

3. **Commit**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   Используйте [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - новая функциональность
   - `fix:` - исправление бага
   - `docs:` - изменения в документации
   - `style:` - форматирование, пробелы, etc.
   - `refactor:` - рефакторинг кода
   - `test:` - добавление тестов
   - `chore:` - обновление зависимостей, CI

4. **Push**
   ```bash
   git push origin feature/my-new-feature
   ```

5. **Создать Pull Request**
   - Откройте PR на GitHub
   - Заполните описание по шаблону
   - Дождитесь проверки CI
   - Ответьте на комментарии reviewers

## Pull Request Process

### Требования к PR

1. **Описание**
   - Что изменено и почему
   - Ссылка на issue (если есть)
   - Screenshots (для UI изменений)

2. **Тесты**
   - Добавить тесты для новой функциональности
   - Все тесты должны проходить
   - Coverage не должен падать

3. **Документация**
   - Обновить README если нужно
   - Добавить docstrings
   - Обновить CHANGELOG.md

4. **Code Review**
   - Минимум 1 approve от maintainer
   - Все комментарии должны быть resolved
   - CI checks должны быть зелёными

### Шаблон PR

```markdown
## Описание
Краткое описание изменений

## Тип изменения
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Как протестировано
Опишите как вы тестировали изменения

## Checklist
- [ ] Мой код следует code style проекта
- [ ] Я провёл self-review кода
- [ ] Я добавил комментарии в сложных местах
- [ ] Я обновил документацию
- [ ] Мои изменения не создают новых warnings
- [ ] Я добавил тесты
- [ ] Все тесты проходят локально
- [ ] Я обновил CHANGELOG.md
```

## Стиль кода

### Python

Следуем PEP 8 с некоторыми дополнениями:

#### Форматирование

```python
# Black настроен на line-length=100
# Используйте
make format

# Или вручную
black .
isort .
```

#### Naming Conventions

```python
# Классы: PascalCase
class UserManager:
    pass

# Функции и переменные: snake_case
def get_user_by_id(user_id: int) -> User:
    current_user = ...
    return current_user

# Константы: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Приватные: _leading_underscore
def _internal_helper():
    pass
```

#### Type Hints

```python
# Всегда используйте type hints
from typing import Optional, List, Dict

def process_data(
    data: List[Dict[str, Any]],
    timeout: int = 30,
) -> Optional[Result]:
    """
    Process data with timeout.

    Args:
        data: List of dictionaries to process
        timeout: Timeout in seconds

    Returns:
        Result object or None if failed
    """
    pass
```

#### Docstrings

```python
def complex_function(arg1: str, arg2: int) -> bool:
    """
    One-line summary.

    Longer description if needed.
    Multiple paragraphs are OK.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: When arg2 is negative

    Example:
        >>> complex_function("test", 42)
        True
    """
    pass
```

### Imports

```python
# Порядок импортов (isort настроен автоматически):
# 1. Стандартная библиотека
import os
import sys
from typing import Optional

# 2. Сторонние библиотеки
from aiogram import Bot, Dispatcher
from aiogram.types import Message

# 3. Локальные импорты
from app.config import Config
from app.database import Database
```

## Тестирование

### Написание тестов

```python
# tests/test_feature.py
import pytest
from app.feature import my_function

class TestFeature:
    """Tests for Feature functionality."""

    @pytest.mark.asyncio
    async def test_my_function(self):
        """Test my_function with valid input."""
        result = await my_function("test")
        assert result == expected_value

    @pytest.mark.asyncio
    async def test_my_function_invalid_input(self):
        """Test my_function raises error on invalid input."""
        with pytest.raises(ValueError):
            await my_function("")
```

### Запуск тестов

```bash
# Все тесты
make test

# С coverage
make test-cov

# Конкретный файл
pytest tests/test_feature.py

# Конкретный тест
pytest tests/test_feature.py::TestFeature::test_my_function

# С verbose
pytest -v

# С output
pytest -s
```

### Coverage

Минимальный coverage: **80%**

```bash
# Генерация coverage report
pytest --cov=app --cov-report=html

# Открыть в браузере
open htmlcov/index.html
```

## Документация

### README Updates

Обновляйте README.md если:
- Добавлена новая команда
- Изменён процесс установки
- Добавлена новая функциональность
- Изменены требования

### Docstrings

- Все public функции должны иметь docstrings
- Используйте Google style docstrings
- Включайте примеры для сложных функций

### CHANGELOG

Всегда обновляйте CHANGELOG.md:

```markdown
## [Unreleased]

### Added
- Новая функциональность (#123)

### Fixed
- Исправлен баг с X (#124)
```

## Вопросы?

- Создайте [Issue](https://github.com/Adel7418/telegram-repair-bot/issues)
- Напишите в [Discussions](https://github.com/Adel7418/telegram-repair-bot/discussions)

## Лицензия

Контрибутя в проект, вы соглашаетесь что ваш код будет лицензирован под MIT License.

---

**Спасибо за вклад в проект! 🎉**
