# 🧹 План очистки проекта

## 📊 Анализ проблем

### 1. База данных (6 файлов вместо 1!)
❌ **Проблема:**
- `bot_database.db` + `.db-shm` + `.db-wal` (3 файла)
- `bot_database_dev.db` + `.db-shm` + `.db-wal` (еще 3 файла)

✅ **Решение:**
- Оставить только `bot_database.db` (остальные создаются автоматически)
- Удалить `bot_database_dev.db` и его файлы
- Добавить `*.db-shm` и `*.db-wal` в `.gitignore`

### 2. Дублирующиеся документы (50+ файлов!)
❌ **Проблемы:**
- Множество SESSION_SUMMARY файлов
- Дублирующиеся гайды (DEPLOYMENT, MIGRATION)
- Устаревшие отчеты (AUDIT_REPORT, FIX_REPORT)

✅ **Решение:** Объединить в структурированную документацию

### 3. Дублирующиеся скрипты деплоя
❌ **Проблема:**
- `deploy_prod.sh`
- `deploy_to_vps.sh`
- `deploy_with_migrations.sh`
- `update_bot.sh`

✅ **Решение:** Оставить только `deploy_with_migrations.sh`

### 4. Makefile не используется
❌ **Проблема:** Хороший Makefile, но не используется в продакшн

✅ **Решение:** Интегрировать с текущими скриптами

## 🗑️ Файлы к удалению

### База данных
- [x] bot_database_dev.db*
- [x] bot_database.db-shm
- [x] bot_database.db-wal
- [x] bot_database_dev.db-shm
- [x] bot_database_dev.db-wal

### Устаревшие документы (docs/)
- [ ] AUDIT_REPORT_2025-10-15.md (устарел)
- [ ] BUTTON_FIX_REPORT.md (устарел)
- [ ] BUTTONS_SETUP_REPORT.md (устарел)
- [ ] CANCEL_BUTTON_FIX.md (устарел)
- [ ] CLIENT_NAME_VALIDATION_UPDATE.md (устарел)
- [ ] CREATE_ORDER_SETUP_REPORT.md (устарел)
- [ ] DUAL_ROLE_FIX.md (устарел)
- [ ] FINAL_AUDIT_REPORT.md (устарел)
- [ ] NOTIFICATION_FIX_REPORT.md (устарел)
- [ ] NOTIFICATION_TIME_FIX.md (устарел)
- [ ] PHONE_PRIVACY_UPDATE.md (устарел)
- [ ] PYDANTIC_IMPLEMENTATION_SUMMARY.md (устарел)
- [ ] REFACTORING_REPORT.md (устарел)
- [ ] REMINDER_SETTINGS_UPDATE.md (устарел)
- [ ] RETRY_MECHANISM_IMPLEMENTATION.md (устарел)
- [ ] SCHEDULED_TIME_FIX_REPORT.md (устарел)
- [ ] SESSION_SUMMARY_2025-10-12_DUAL_ROLE_FIX.md (устарел)
- [ ] SESSION_SUMMARY_2025-10-12.md (устарел)
- [ ] BOT_NOT_RESPONDING_FIX.md (устарел)

### Дублирующиеся гайды
- [ ] docs/MIGRATION_GUIDE.md (есть MIGRATIONS_GUIDE.md)
- [ ] docs/UPDATE_DOCKER_GUIDE.md (дублирует DOCKER_USAGE.md)

### Устаревшие скрипты
- [ ] scripts/deploy_prod.sh (заменен deploy_with_migrations.sh)
- [ ] scripts/deploy_to_vps.sh (заменен deploy_with_migrations.sh)
- [ ] scripts/update_bot.sh (заменен deploy_with_migrations.sh)
- [ ] scripts/migrate.sh (есть в Makefile)

### Временные файлы
- [ ] data/db_export_20251013_192724.json
- [ ] data/coverage.xml
- [ ] htmlcov/ (coverage отчет)
- [ ] ОТВЕТ_НА_ВОПРОС.md (корневой)

## 📁 Новая структура документации

```
docs/
├── README.md                       # Главная страница документации
├── QUICKSTART.md                   # Быстрый старт
├── INSTALLATION.md                 # Установка
├── MIGRATIONS_GUIDE.md             # Миграции (уже есть)
├── TROUBLESHOOTING.md              # Решение проблем
│
├── deployment/                     # Развертывание
│   ├── PRODUCTION_DEPLOY.md
│   ├── DOCKER_USAGE.md
│   └── SERVER_DEPLOYMENT.md
│
├── development/                    # Разработка
│   ├── CONTRIBUTING.md
│   ├── DEV_MODE_GUIDE.md
│   └── TESTING.md
│
├── features/                       # Функции
│   ├── FINANCIAL_REPORTS_GUIDE.md
│   ├── MULTIPLE_ROLES_GUIDE.md
│   └── GROUP_INTERACTION_GUIDE.md
│
└── user-guides/                    # Пользовательские гайды
    ├── admin_guide.md
    ├── dispatcher_guide.md
    └── master_guide.md
```

## ✅ Что оставляем

### Документация (важная)
- README.md
- QUICKSTART.md
- INSTALLATION.md
- MIGRATIONS_GUIDE.md
- TROUBLESHOOTING.md
- CONTRIBUTING.md
- CHANGELOG.md
- SERVER_DEPLOYMENT.md
- БЫСТРОЕ_ОБНОВЛЕНИЕ.md

### Скрипты (актуальные)
- backup_db.py
- check_database.py
- deploy_with_migrations.sh  ⭐ ОСНОВНОЙ
- diagnose_update.sh
- export_db.py / import_db.py
- fix_migrations_prod.py
- orders_report.py
- sync_roles_from_env.py
- view_order_reports.py

## 🔧 Обновление Makefile

Интегрируем с нашими скриптами:

```makefile
prod-deploy:  ## Полный деплой с миграциями (ГЛАВНАЯ КОМАНДА)
	./scripts/deploy_with_migrations.sh

prod-diagnose:  ## Диагностика проблем обновления
	./scripts/diagnose_update.sh

prod-backup:  ## Создать backup БД
	cd docker && docker-compose -f docker-compose.prod.yml exec bot python scripts/backup_db.py
```

## 📋 Порядок действий

1. ✅ Обновить .gitignore
2. ✅ Удалить dev БД файлы
3. ✅ Удалить устаревшие документы
4. ✅ Удалить дублирующиеся скрипты
5. ✅ Создать docs/README.md с навигацией
6. ✅ Обновить Makefile
7. ✅ Обновить корневой README.md
8. ✅ Коммит и пуш
