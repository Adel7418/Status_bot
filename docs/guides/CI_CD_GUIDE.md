# CI/CD Guide - Telegram Repair Bot

**Дата создания:** 19 октября 2025
**Статус:** ✅ Готово к использованию

---

## 📋 Содержание

1. [Обзор](#обзор)
2. [GitHub Actions Workflows](#github-actions-workflows)
3. [Pre-commit Hooks](#pre-commit-hooks)
4. [Dependabot](#dependabot)
5. [Настройка](#настройка)
6. [Использование](#использование)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Обзор

### Что настроено:

✅ **Автоматическое тестирование** при каждом push/PR
✅ **Линтинг и форматирование** кода
✅ **Проверка безопасности** (Bandit, Safety, CodeQL)
✅ **Проверка защиты PII**
✅ **Docker build тесты**
✅ **Автоматический деплой** (при создании тега)
✅ **Pre-commit hooks** для локальной проверки
✅ **Dependabot** для обновления зависимостей
✅ **Автоматическая маркировка PR**

---

## 🔄 GitHub Actions Workflows

### 1. CI - Tests and Quality Checks (`ci.yml`)

**Триггеры:**
- Push в `main` или `develop`
- Pull Request в `main` или `develop`

**Jobs:**

#### 1.1 Tests
- Запуск на Python 3.11, 3.12, 3.13
- Pytest с coverage
- Загрузка coverage в Codecov
- Сохранение HTML отчета

#### 1.2 Lint
- Ruff linter
- Ruff formatter
- MyPy type checking

#### 1.3 Security
- Bandit (security linter)
- Safety check (vulnerability scan)
- Сохранение отчетов

#### 1.4 PII Protection Check
- Запуск тестов PII маскирования
- Проверка кода на прямое логирование PII

#### 1.5 Docker Build
- Build Docker image
- Кэширование для ускорения

---

### 2. Deploy to Production (`deploy.yml`)

**Триггеры:**
- Push тега `v*.*.*` (например, `v1.2.0`)
- Ручной запуск (workflow_dispatch)

**Процесс:**
1. Запуск тестов перед деплоем
2. Создание deployment package
3. Загрузка артефакта
4. Deploy на сервер (настраивается)
5. Создание GitHub Release с changelog

**Как создать релиз:**
```bash
# 1. Обновить VERSION файл
echo "1.2.0" > VERSION

# 2. Commit и push
git add VERSION
git commit -m "release: v1.2.0"
git push

# 3. Создать и push тег
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0

# 4. GitHub Actions автоматически:
#    - Запустит тесты
#    - Создаст deployment package
#    - Создаст GitHub Release
#    - Задеплоит (если настроено)
```

---

### 3. Pull Request Checks (`pr-checks.yml`)

**Проверки:**

#### 3.1 PR Validation
- Формат заголовка PR: `type(scope): description`
  - Примеры: `feat(auth): add login`, `fix(bot): resolve crash`
- Проверка merge conflicts
- Проверка измененных файлов
- Поиск новых TODO/FIXME

#### 3.2 PR Size Check
- Предупреждение при большом количестве изменений (>50 файлов)

#### 3.3 Dependency Review
- Проверка новых зависимостей на уязвимости
- Блокировка нежелательных лицензий (GPL-3.0, AGPL-3.0)

#### 3.4 Auto Label
- Автоматическая маркировка по измененным файлам

#### 3.5 Coverage Comment
- Комментарий с процентом покрытия кода

**Правильный формат PR:**
```
✅ feat(orders): add Excel export
✅ fix(database): resolve connection leak
✅ docs: update installation guide
✅ refactor(handlers): simplify error handling
✅ test: add PII masking tests
✅ chore(deps): update aiogram to 3.16.0

❌ Added new feature
❌ Fixed bug
❌ Updated docs
```

---

### 4. CodeQL Security Scan (`codeql.yml`)

**Триггеры:**
- Push в `main` или `develop`
- Pull Request в `main`
- Расписание: каждый понедельник в 6:00 UTC

**Функции:**
- Статический анализ кода на уязвимости
- Проверка security-extended queries
- Автоматические alerts в GitHub Security

---

## 🪝 Pre-commit Hooks

### Установка:

```bash
# 1. Установить pre-commit
pip install pre-commit

# 2. Установить hooks
pre-commit install

# 3. (Опционально) Установить для commit-msg
pre-commit install --hook-type commit-msg
```

### Что проверяется локально:

✅ **Общие проверки:**
- Trailing whitespace
- End of file fixer
- YAML/JSON/TOML validation
- Большие файлы (>1MB)
- Merge conflicts
- Debug statements

✅ **Python:**
- Ruff linter + formatter
- MyPy type checking
- Bandit security scan

✅ **Кастомные проверки:**
- PII в логировании
- Hardcoded secrets
- Pytest (только при push)

### Использование:

```bash
# Автоматически при commit
git commit -m "feat: add new feature"
# → pre-commit запустится автоматически

# Вручную на всех файлах
pre-commit run --all-files

# Вручную на конкретном hook
pre-commit run ruff --all-files

# Пропустить pre-commit (не рекомендуется!)
git commit -m "fix: urgent hotfix" --no-verify
```

### Обновление hooks:

```bash
# Обновить до последних версий
pre-commit autoupdate

# Очистить кэш
pre-commit clean
```

---

## 🤖 Dependabot

### Что делает:

- **Python dependencies** - проверка каждый понедельник в 9:00
- **GitHub Actions** - проверка каждый понедельник в 10:00
- **Docker** - проверка каждый вторник в 9:00

### Группировка обновлений:

- `aiogram*` - все пакеты aiogram вместе
- `pytest*` - все пакеты pytest вместе
- Development dependencies - minor и patch вместе

### Настройка:

1. Откройте `.github/dependabot.yml`
2. Замените `your-github-username` на свой username:
   ```yaml
   reviewers:
     - "your-github-username"
   assignees:
     - "your-github-username"
   ```

### Игнорирование зависимостей:

```yaml
# В конце .github/dependabot.yml
ignore:
  - dependency-name: "aiogram"
    versions: ["4.x"]  # Не обновлять до версии 4.x
```

---

## ⚙️ Настройка

### 1. Secrets для GitHub Actions

Добавьте secrets в настройках репозитория:

```
Settings → Secrets and variables → Actions → New repository secret
```

**Необходимые secrets:**

| Secret | Описание | Обязательно |
|--------|----------|-------------|
| `CODECOV_TOKEN` | Токен Codecov для coverage | Нет |
| `SERVER_HOST` | IP/hostname сервера | Для деплоя |
| `SERVER_USER` | SSH user | Для деплоя |
| `SERVER_SSH_KEY` | SSH приватный ключ | Для деплоя |
| `SERVER_PORT` | SSH порт (default: 22) | Для деплоя |

### 2. Environments

Создайте environments для деплоя:

```
Settings → Environments → New environment
```

**Environments:**
- `production` - production сервер
- `staging` - staging/test сервер

**Настройка environment:**
- Required reviewers (опционально)
- Wait timer (опционально)
- Deployment branches: только `main` для production

### 3. Branch Protection Rules

Рекомендуемые правила для `main`:

```
Settings → Branches → Add rule
```

**Правила:**
- ✅ Require pull request before merging
- ✅ Require status checks to pass before merging
  - CI - Tests
  - CI - PII Protection Check
  - CI - Docker Build
- ✅ Require conversation resolution before merging
- ✅ Do not allow bypassing the above settings

### 4. Codecov (опционально)

```bash
# 1. Зарегистрироваться на codecov.io
# 2. Добавить репозиторий
# 3. Получить CODECOV_TOKEN
# 4. Добавить в GitHub Secrets
```

---

## 🚀 Использование

### Workflow для разработки:

```bash
# 1. Создать feature branch
git checkout -b feat/new-feature

# 2. Сделать изменения
# ... edit files ...

# 3. Pre-commit автоматически проверит при commit
git add .
git commit -m "feat(orders): add Excel export"

# 4. Push в GitHub
git push origin feat/new-feature

# 5. Создать Pull Request
# → GitHub Actions автоматически запустит все проверки

# 6. После прохождения проверок и review - merge
# 7. В main автоматически запустятся тесты
```

### Создание релиза:

```bash
# 1. Убедитесь, что все изменения в main
git checkout main
git pull

# 2. Обновите VERSION
echo "1.2.0" > VERSION

# 3. Commit версии
git add VERSION CHANGELOG.md
git commit -m "release: v1.2.0"
git push

# 4. Создайте тег
git tag -a v1.2.0 -m "Release v1.2.0

Features:
- Added Excel export
- Improved PII protection

Fixes:
- Fixed memory leak in handlers
- Resolved database connection issues"

# 5. Push тег
git push origin v1.2.0

# 6. GitHub Actions:
#    - Запустит тесты
#    - Создаст deployment package
#    - Создаст GitHub Release
#    - Задеплоит (если настроено)
```

### Ручной деплой:

```bash
# Через GitHub UI
Actions → Deploy to Production → Run workflow
→ Выбрать environment (production/staging)
→ Run workflow
```

---

## 🔍 Мониторинг CI/CD

### GitHub Actions Dashboard:

```
Repository → Actions
```

**Что смотреть:**
- ✅ Зеленые галочки - все прошло
- ❌ Красные крестики - что-то сломалось
- 🟡 Желтые точки - в процессе

### Badges для README:

Добавьте в `README.md`:

```markdown
![CI](https://github.com/your-username/telegram-repair-bot/workflows/CI%20-%20Tests%20and%20Quality%20Checks/badge.svg)
![codecov](https://codecov.io/gh/your-username/telegram-repair-bot/branch/main/graph/badge.svg)
![CodeQL](https://github.com/your-username/telegram-repair-bot/workflows/CodeQL%20Security%20Scan/badge.svg)
```

### Уведомления:

GitHub отправляет email уведомления при:
- ❌ Провале workflow
- ✅ Успешном деплое
- 🔒 Security alerts

---

## 🐛 Troubleshooting

### Проблема: Pre-commit слишком медленный

**Решение:**
```bash
# Пропустить некоторые hooks
SKIP=mypy,pytest-check git commit -m "fix: quick fix"

# Или отключить pytest для локальных коммитов
# Отредактировать .pre-commit-config.yaml:
- id: pytest-check
  stages: [push]  # Только при push, не при commit
```

### Проблема: CI падает на тестах, но локально работает

**Проверьте:**
1. Версия Python совпадает?
   ```bash
   python --version  # Локально
   # vs
   # python-version: '3.11'  # В ci.yml
   ```

2. Все зависимости установлены?
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. База данных в правильном состоянии?
   ```bash
   alembic upgrade head
   ```

### Проблема: Dependabot создает слишком много PR

**Решение:**
```yaml
# .github/dependabot.yml
open-pull-requests-limit: 3  # Уменьшить лимит

# Или группировать обновления
groups:
  all-dependencies:
    patterns:
      - "*"
    update-types:
      - "minor"
      - "patch"
```

### Проблема: CodeQL слишком долго работает

**Решение:**
```yaml
# .github/workflows/codeql.yml
# Запускать только по расписанию
on:
  schedule:
    - cron: '0 6 * * 1'  # Только понедельник
  # Убрать push и pull_request
```

### Проблема: Деплой падает

**Проверьте:**
1. SSH ключ правильный?
2. Сервер доступен?
3. Docker установлен на сервере?
4. Порты открыты?

**Debug деплоя:**
```yaml
# В deploy.yml добавить:
- name: Debug SSH connection
  run: |
    ssh -vvv ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_HOST }}
```

---

## 📊 Метрики качества

### Цели:

| Метрика | Цель | Текущее |
|---------|------|---------|
| Test Coverage | > 80% | ~6% ⚠️ |
| CI Success Rate | > 95% | - |
| Deploy Success Rate | > 99% | - |
| Pre-commit Pass Rate | > 90% | - |

### Как улучшить coverage:

```bash
# 1. Найти непокрытый код
pytest --cov=app --cov-report=html
open htmlcov/index.html

# 2. Написать тесты для непокрытых файлов
# 3. Цель: handlers > 60%, services > 80%, utils > 90%
```

---

## 🎓 Best Practices

### 1. Commit Messages

```bash
# Хорошо
feat(orders): add Excel export functionality
fix(database): resolve connection leak in pooling
docs: update CI/CD setup guide
test(pii): add tests for address masking
refactor(handlers): simplify error handling logic

# Плохо
added feature
fixed bug
updated docs
```

### 2. Pull Requests

- Маленькие PR (<300 строк)
- Один PR = одна feature/fix
- Заполнить описание
- Добавить скриншоты (если UI)
- Линковать issues (#123)

### 3. Reviews

- Проверить тесты
- Проверить coverage не упал
- Проверить безопасность
- Проверить PII защиту

### 4. Releases

- Semantic versioning (1.2.3)
- Подробный CHANGELOG
- Testing перед релизом
- Rollback plan

---

## ✅ Checklist для Production

Перед первым production deploy:

- [ ] Все тесты проходят
- [ ] Coverage > 80%
- [ ] Нет critical security issues
- [ ] PII protection тесты зеленые
- [ ] Docker image собирается
- [ ] Secrets настроены в GitHub
- [ ] Branch protection включен
- [ ] Environments настроены
- [ ] Rollback plan подготовлен
- [ ] Monitoring настроен (опционально)

---

## 📚 Дополнительные ресурсы

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [CodeQL Documentation](https://codeql.github.com/docs/)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## 🎉 Итог

✅ **Полноценный CI/CD pipeline настроен!**

**Что работает автоматически:**
- Тестирование при каждом push
- Проверка качества кода
- Проверка безопасности
- Защита PII
- Автоматический деплой
- Обновление зависимостей

**Следующие шаги:**
1. Настроить secrets
2. Создать первый PR
3. Убедиться, что все checks проходят
4. Настроить деплой (опционально)
5. Добавить badges в README

---

**Вопросы?** Смотрите [Troubleshooting](#troubleshooting) или создайте issue.
