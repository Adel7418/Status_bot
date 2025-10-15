# 🔧 Git команды - Шпаргалка

## 📝 Через Makefile (на Linux/Mac сервере)

### Быстрое сохранение (add + commit + push)
```bash
make git-save MSG="описание изменений"
```

### Отдельные команды
```bash
make git-status        # Посмотреть статус
make git-add           # Добавить все изменения
make git-commit MSG="описание"  # Создать коммит
make git-push          # Отправить в GitHub
make git-pull          # Получить из GitHub
make git-log           # Последние 10 коммитов
make git-diff          # Посмотреть изменения
```

## 💻 Через Git напрямую (на любой ОС)

### 1. Проверить статус
```bash
git status
```

### 2. Добавить файлы
```bash
# Добавить все изменения
git add -A

# Добавить конкретный файл
git add файл.py

# Добавить папку
git add app/
```

### 3. Создать коммит
```bash
git commit -m "описание изменений"
```

### 4. Отправить в GitHub
```bash
git push origin main
```

### 5. Получить из GitHub
```bash
git pull origin main
```

## ⚡ Быстрые команды (одной строкой)

### Windows (PowerShell)
```powershell
git add -A; git commit -m "описание"; git push origin main
```

### Linux/Mac
```bash
git add -A && git commit -m "описание" && git push origin main
```

## 📚 Дополнительные команды

### Посмотреть историю коммитов
```bash
# Последние 10 коммитов
git log --oneline -10

# Подробная история
git log

# С графом веток
git log --graph --oneline --all
```

### Посмотреть изменения
```bash
# Все изменения
git diff

# Изменения в конкретном файле
git diff файл.py

# Изменения между коммитами
git diff HEAD~1 HEAD
```

### Отменить изменения
```bash
# Отменить изменения в файле (до add)
git restore файл.py

# Убрать файл из staged (после add)
git restore --staged файл.py

# Отменить последний коммит (НЕ отправленный в GitHub!)
git reset --soft HEAD~1
```

### Работа с ветками
```bash
# Посмотреть текущую ветку
git branch

# Создать новую ветку
git branch название-ветки

# Переключиться на ветку
git checkout название-ветки

# Создать и переключиться
git checkout -b название-ветки

# Удалить ветку
git branch -d название-ветки
```

## 🔥 Типичные сценарии

### Сценарий 1: Быстрое сохранение изменений
```bash
# 1. Проверяем что изменилось
git status

# 2. Добавляем все
git add -A

# 3. Коммитим
git commit -m "fix: исправил баг с отчетами"

# 4. Отправляем
git push origin main
```

### Сценарий 2: Обновление с сервера
```bash
# Получаем изменения
git pull origin main

# Если есть конфликты - разрешаем их в редакторе
# Затем:
git add -A
git commit -m "merge: разрешил конфликты"
git push origin main
```

### Сценарий 3: Откат изменений
```bash
# Если НЕ делали git add
git restore файл.py

# Если сделали git add, но НЕ git commit
git restore --staged файл.py
git restore файл.py

# Если сделали git commit, но НЕ git push
git reset --soft HEAD~1
# (изменения останутся, но коммит отменится)
```

### Сценарий 4: Удалить файл из Git
```bash
# Удалить из Git, но оставить локально
git rm --cached файл.py

# Удалить везде
git rm файл.py

# Закоммитить
git commit -m "chore: удалил ненужный файл"
git push origin main
```

## 📖 Правила хороших коммитов

### Формат сообщения
```
тип: краткое описание (до 50 символов)

[опционально: подробное описание]

[опционально: ссылки на issues]
```

### Типы коммитов
- `feat:` - новая функциональность
- `fix:` - исправление бага
- `docs:` - изменения в документации
- `style:` - форматирование, точки с запятой и т.д.
- `refactor:` - рефакторинг кода
- `test:` - добавление тестов
- `chore:` - обновление задач сборки, зависимостей и т.д.

### Примеры
```bash
git commit -m "feat: add financial reports feature"
git commit -m "fix: resolve migration chain issue"
git commit -m "docs: update installation guide"
git commit -m "chore: cleanup old documentation files"
git commit -m "refactor: improve database query performance"
```

## ⚠️ Важные правила

### ❌ НЕ делайте:
1. **НЕ делайте** `git push --force` на `main` ветку
2. **НЕ коммитьте** секретные данные (.env файлы)
3. **НЕ коммитьте** большие бинарные файлы
4. **НЕ коммитьте** временные файлы (*.log, *.db-wal, и т.д.)

### ✅ ДЕЛАЙТЕ:
1. **Проверяйте** `.gitignore` перед коммитом
2. **Пишите понятные** сообщения коммитов
3. **Делайте** `git pull` перед `git push`
4. **Тестируйте** код перед коммитом

## 🆘 Проблемы и решения

### "Permission denied" при push
```bash
# Проверьте SSH ключ или используйте HTTPS
git remote set-url origin https://github.com/username/repo.git
```

### "Merge conflict"
```bash
# 1. Откройте файл с конфликтом
# 2. Найдите секции с <<<<<<< и >>>>>>>
# 3. Выберите нужную версию
# 4. Сохраните
git add файл.py
git commit -m "merge: resolved conflicts"
git push origin main
```

### "Cannot push because remote has changes"
```bash
# Сначала получите изменения
git pull origin main

# Разрешите конфликты если есть
# Затем отправьте
git push origin main
```

## 📌 Полезные алиасы

Добавьте в `~/.gitconfig`:
```ini
[alias]
    st = status
    co = commit
    br = branch
    pl = pull origin main
    ps = push origin main
    lg = log --graph --oneline --all
    save = !git add -A && git commit -m
```

Использование:
```bash
git st              # вместо git status
git save "fix bug"  # вместо git add -A && git commit -m "fix bug"
git ps              # вместо git push origin main
```

---

**💡 Совет:** На сервере используйте `make git-save MSG="..."` для быстрого сохранения!
