# Badges для README.md

Скопируйте эти badges в ваш `README.md`:

## Основные badges:

```markdown
# В начало README.md после заголовка

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen)

## CI/CD

![CI Tests](https://github.com/YOUR-USERNAME/telegram-repair-bot/workflows/CI%20-%20Tests%20and%20Quality%20Checks/badge.svg)
![CodeQL](https://github.com/YOUR-USERNAME/telegram-repair-bot/workflows/CodeQL%20Security%20Scan/badge.svg)
![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)

## Code Quality

![Coverage](https://codecov.io/gh/YOUR-USERNAME/telegram-repair-bot/branch/main/graph/badge.svg)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![MyPy](https://img.shields.io/badge/mypy-checked-blue)

## Security

![Security Rating](https://img.shields.io/badge/security-A-brightgreen)
![PII Protection](https://img.shields.io/badge/PII-protected-success)
![GDPR](https://img.shields.io/badge/GDPR-compliant-success)

## Tech Stack

![Aiogram](https://img.shields.io/badge/aiogram-3.16-blue)
![SQLite](https://img.shields.io/badge/sqlite-3-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![Redis](https://img.shields.io/badge/redis-optional-yellow)
```

## Замените в badges:

1. `YOUR-USERNAME` → ваш GitHub username
2. `telegram-repair-bot` → название вашего репозитория

## Пример готового раздела для README:

```markdown
# Telegram Repair Bot

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen)
![CI Tests](https://github.com/YOUR-USERNAME/telegram-repair-bot/workflows/CI%20-%20Tests%20and%20Quality%20Checks/badge.svg)
![Coverage](https://codecov.io/gh/YOUR-USERNAME/telegram-repair-bot/branch/main/graph/badge.svg)
![Security](https://img.shields.io/badge/security-A-brightgreen)
![PII Protection](https://img.shields.io/badge/PII-protected-success)

Telegram-бот для управления заявками на ремонт техники с автоматизацией бизнес-процессов.

## ✨ Features

- ✅ Автоматическое тестирование (CI/CD)
- ✅ Защита персональных данных (GDPR compliant)
- ✅ State Machine для валидации переходов
- ✅ Rate limiting против спама
- ✅ Финансовая отчетность
- ✅ Docker deployment ready

## 🚀 Quick Start

...ваша документация...
```

## Дополнительные badges (опционально):

```markdown
## Для deployment
![Docker Hub](https://img.shields.io/docker/v/YOUR-USERNAME/telegram-repair-bot?label=docker)
![Docker Size](https://img.shields.io/docker/image-size/YOUR-USERNAME/telegram-repair-bot)

## Для версионирования
![Version](https://img.shields.io/github/v/release/YOUR-USERNAME/telegram-repair-bot)
![Latest Commit](https://img.shields.io/github/last-commit/YOUR-USERNAME/telegram-repair-bot)

## Для community
![Stars](https://img.shields.io/github/stars/YOUR-USERNAME/telegram-repair-bot?style=social)
![Forks](https://img.shields.io/github/forks/YOUR-USERNAME/telegram-repair-bot?style=social)
![Issues](https://img.shields.io/github/issues/YOUR-USERNAME/telegram-repair-bot)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

## Для мониторинга
![Uptime](https://img.shields.io/uptimerobot/ratio/7/m123456789-abcdef1234567890)
![Response Time](https://img.shields.io/uptimerobot/response/7/m123456789-abcdef1234567890)
```

## Рекомендуемый набор (минимум):

```markdown
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![CI](https://github.com/YOUR-USERNAME/telegram-repair-bot/workflows/CI%20-%20Tests%20and%20Quality%20Checks/badge.svg)
![Security](https://img.shields.io/badge/security-A-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)
```

---

**Совет:** Не используйте слишком много badges. 4-6 достаточно для начала.

**Генераторы badges:**
- https://shields.io/
- https://badgen.net/
- https://img.shields.io/

**После настройки Codecov:**
1. Зарегистрируйтесь на codecov.io
2. Добавьте репозиторий
3. Badge появится автоматически
