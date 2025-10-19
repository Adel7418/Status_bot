# 🚀 Ваш простой workflow

## ⚡ Быстрая шпаргалка

### Локально (Cursor):
```bash
# Разработка, тестирование
make test
make lint

# Коммит и отправка
git add -A
git commit -m "описание изменений"
git push origin main
```

### На сервере:
```bash
# SSH
ssh root@ваш-IP

# Обновление (одна команда)
cd ~/telegram_repair_bot && git pull && cd docker && docker compose -f docker-compose.prod.yml restart

# Проверка
docker compose -f docker-compose.prod.yml logs --tail=50 bot
```

---

## 📖 Детальная документация

См. **[МИНИМАЛЬНЫЙ_WORKFLOW.md](МИНИМАЛЬНЫЙ_WORKFLOW.md)** для подробных инструкций.

---

## ❓ FAQ

**В: Git pull удаляет файлы?**
О: ДА! Если вы удалили файл локально, закоммитили и запушили, то при `git pull` на сервере файл тоже удалится. Это нормально!

**В: Нужен ли staging?**
О: НЕТ! Тестируете локально - этого достаточно.

**В: Как откатить изменения?**
О: На сервере: `git log --oneline -10`, потом `git reset --hard <commit>` и `docker compose restart`

---

## 🎯 Главное

**Два шага:**
1. Локально: `git push`
2. На сервере: `git pull` + `docker restart`

**Готово!** ✅
