# 🛡️ Безопасность БЕЗ шифрования БД

## Решение: Шифрование БД отключено

Для небольшого проекта с доверенной командой шифрование каждого поля избыточно.
Вместо этого фокусируемся на других аспектах безопасности.

## ✅ Что делать ВМЕСТО шифрования БД:

### 1. Защита на уровне сервера

#### Права доступа к файлам:

```bash
# На сервере
cd /path/to/telegram_repair_bot

# База данных - только владелец может читать/писать
chmod 600 data/bot_database.db
chmod 600 env.production

# Директория данных
chmod 700 data/

# Проверка
ls -la data/bot_database.db
# Должно быть: -rw------- (600)
```

#### Владелец файлов:

```bash
# Убедитесь что файлы принадлежат правильному пользователю
chown -R appuser:appuser /path/to/telegram_repair_bot

# Проверка
ls -la
```

### 2. Защита backup'ов

#### Вариант A: Зашифрованное хранилище

```bash
# Создайте зашифрованный том для backup'ов
sudo cryptsetup luksFormat /dev/sdb1
sudo cryptsetup open /dev/sdb1 encrypted_backups
sudo mkfs.ext4 /dev/mapper/encrypted_backups
sudo mount /dev/mapper/encrypted_backups /mnt/backups

# Backup'ы туда
cp data/bot_database.db /mnt/backups/
```

#### Вариант B: GPG шифрование backup'ов

```bash
# Скрипт автоматического шифрования backup'ов
# scripts/encrypted_backup.sh

#!/bin/bash
BACKUP_FILE="bot_database_$(date +%Y%m%d_%H%M%S).db"
GPG_RECIPIENT="admin@example.com"

# Создать backup
cp data/bot_database.db "backups/$BACKUP_FILE"

# Зашифровать
gpg --encrypt --recipient "$GPG_RECIPIENT" "backups/$BACKUP_FILE"

# Удалить незашифрованный
rm "backups/$BACKUP_FILE"

echo "✅ Backup создан: backups/${BACKUP_FILE}.gpg"
```

#### Вариант C: Облачное хранилище с E2E шифрованием

```bash
# Использовать Restic для encrypted backups
restic -r s3:s3.amazonaws.com/my-backups init
restic -r s3:s3.amazonaws.com/my-backups backup data/bot_database.db
```

### 3. Защита сетевого доступа

#### Firewall:

```bash
# Разрешить только SSH и внутренние соединения
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp  # SSH
sudo ufw enable

# Проверка
sudo ufw status
```

#### SSH ключи (отключить пароли):

```bash
# /etc/ssh/sshd_config
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no

# Перезапуск SSH
sudo systemctl restart sshd
```

#### VPN для удаленного доступа:

```bash
# Установить WireGuard
sudo apt install wireguard

# Настроить VPN
# Доступ к серверу ТОЛЬКО через VPN
```

### 4. Мониторинг и аудит

#### Логирование доступа:

```bash
# /etc/rsyslog.d/custom.conf
# Логировать все обращения к БД

# Мониторинг логов
tail -f /var/log/auth.log
tail -f /var/log/syslog
```

#### Автоматические уведомления:

```bash
# scripts/security_monitor.sh
#!/bin/bash

# Проверка изменений БД
DB_HASH=$(md5sum data/bot_database.db | awk '{print $1}')
LAST_HASH=$(cat /tmp/db_hash 2>/dev/null || echo "")

if [ "$DB_HASH" != "$LAST_HASH" ]; then
    echo "⚠️ БД изменена: $(date)" | mail -s "DB Changed" admin@example.com
    echo "$DB_HASH" > /tmp/db_hash
fi
```

### 5. Регулярные обновления

```bash
# Автообновление системы
sudo apt update && sudo apt upgrade -y

# Обновление Docker образов
docker compose -f docker/docker-compose.prod.yml pull
docker compose -f docker/docker-compose.prod.yml up -d

# Обновление зависимостей Python
pip install --upgrade -r requirements.txt
```

### 6. Ограничение данных

#### Удаление старых данных:

```python
# scripts/cleanup_old_data.py
"""
Автоматическое удаление старых завершенных заказов
"""

import asyncio
from datetime import timedelta
from app.database import Database
from app.utils import get_now

async def cleanup_old_orders():
    """Удаление заказов старше 6 месяцев"""
    db = Database()
    await db.connect()

    cutoff_date = get_now() - timedelta(days=180)

    cursor = await db.connection.execute(
        """
        DELETE FROM orders
        WHERE status = 'completed'
        AND completed_at < ?
        """,
        (cutoff_date,)
    )

    deleted = cursor.rowcount
    await db.connection.commit()
    await db.disconnect()

    print(f"✅ Удалено старых заказов: {deleted}")

if __name__ == "__main__":
    asyncio.run(cleanup_old_orders())
```

Запуск через cron:

```bash
# crontab -e
# Каждый месяц 1-го числа в 3:00
0 3 1 * * cd /path/to/bot && python scripts/cleanup_old_data.py
```

### 7. Минимизация логирования ПД

```python
# app/core/logging_config.py

import logging

class SensitiveDataFilter(logging.Filter):
    """Фильтр для скрытия чувствительных данных в логах"""

    def filter(self, record):
        # Скрыть телефоны
        if hasattr(record, 'msg'):
            record.msg = self.mask_phones(str(record.msg))
        return True

    def mask_phones(self, text):
        import re
        # +7999123456 -> +7999***456
        return re.sub(
            r'(\+7\d{3})\d{5}(\d{2})',
            r'\1***\2',
            text
        )

# Применить
logger = logging.getLogger('app')
logger.addFilter(SensitiveDataFilter())
```

### 8. Защита Docker контейнера

```bash
# docker-compose.prod.yml
services:
  bot:
    # Запуск от непривилегированного пользователя
    user: "1000:1000"

    # Ограничение ресурсов
    mem_limit: 512m
    cpus: 0.5

    # Read-only файловая система (кроме data/)
    read_only: true
    tmpfs:
      - /tmp

    volumes:
      - ./data:/app/data:rw  # Только data/ доступна для записи
      - ./:/app:ro           # Остальное read-only

    # Запрет повышения привилегий
    security_opt:
      - no-new-privileges:true

    # AppArmor/SELinux профиль
    security_opt:
      - apparmor:docker-default
```

### 9. Двухфакторная аутентификация для админов

```python
# app/middlewares/admin_2fa.py
"""
2FA для административных команд
"""

class Admin2FAMiddleware(BaseMiddleware):
    """Требовать 2FA код для критичных операций"""

    async def __call__(self, handler, event, data):
        if data.get('user_role') == UserRole.ADMIN:
            # Проверить 2FA код
            if not await self.verify_2fa(event.from_user.id):
                await event.answer("⚠️ Требуется 2FA код")
                return

        return await handler(event, data)
```

### 10. Регулярные аудиты

```bash
# Еженедельно проверяйте:
- Кто имеет доступ к серверу
- Список активных пользователей бота
- Размер БД (нет ли аномального роста)
- Логи на предмет подозрительной активности
- Backup'ы (можно ли восстановить)
```

## 📋 Чеклист безопасности БЕЗ шифрования:

### Сервер:
- [ ] Права доступа 600 на bot_database.db
- [ ] Права доступа 600 на env.production
- [ ] Firewall настроен (ufw/iptables)
- [ ] SSH только по ключам
- [ ] Fail2ban установлен
- [ ] Автообновления включены

### Backup'ы:
- [ ] Backup'ы зашифрованы (GPG/LUKS)
- [ ] Хранятся в безопасном месте
- [ ] Регулярно тестируется восстановление
- [ ] Offsite backup (не на том же сервере)

### Доступ:
- [ ] VPN для удаленного доступа
- [ ] Только доверенные пользователи
- [ ] Сильные пароли (20+ символов)
- [ ] 2FA для критичных операций

### Мониторинг:
- [ ] Логирование включено
- [ ] Уведомления о важных событиях
- [ ] Регулярный аудит логов
- [ ] Мониторинг доступа к БД

### Данные:
- [ ] Минимальное хранение ПД
- [ ] Автоудаление старых данных (6+ месяцев)
- [ ] Маскирование ПД в логах
- [ ] Ограничение доступа к отчетам

## 🎯 Рекомендуемая конфигурация:

```bash
# 1. Зашифрованный диск для данных
sudo cryptsetup luksFormat /dev/sdb1

# 2. Строгие права
chmod 600 data/bot_database.db
chmod 600 env.production

# 3. Firewall
sudo ufw enable
sudo ufw default deny

# 4. SSH ключи
PasswordAuthentication no

# 5. VPN (WireGuard)
sudo apt install wireguard

# 6. Backup с шифрованием
restic backup --encrypt

# 7. Fail2ban
sudo apt install fail2ban

# 8. Автоудаление старых данных
# cron: 0 3 1 * * cleanup_old_data.py
```

## 💰 Стоимость безопасности:

| Метод | Сложность | Эффективность | Стоимость |
|-------|-----------|---------------|-----------|
| Шифрование БД | Средняя | Средняя | Средняя |
| Зашифрованный диск | Низкая | **Высокая** | **Низкая** |
| Строгие права | **Низкая** | **Высокая** | **Бесплатно** |
| VPN | Средняя | **Высокая** | Низкая |
| Backup GPG | **Низкая** | **Высокая** | **Бесплатно** |
| Firewall | **Низкая** | **Высокая** | **Бесплатно** |

**Рекомендация:** Фокус на простые и эффективные методы!

## 📚 Дополнительно:

### Если ПОТОМ понадобится шифрование:

Код уже готов! Просто:

1. Раскомментировать ENCRYPTION_KEY
2. Запустить миграцию
3. Готово!

Все скрипты остаются в проекте:
- `scripts/test_encryption.py`
- `scripts/check_encryption_in_db.py`
- `app/utils/encryption.py`
- `docs/ENCRYPTION_GUIDE.md`

### Когда стоит ВКЛЮЧИТЬ шифрование:

- Рост команды (>10 человек)
- Требования клиентов/партнеров
- Юридические требования
- Выход на крупный рынок

---

**Итог:** Для маленького проекта защита сервера, backup'ов и доступа важнее чем шифрование каждого поля в БД. Фокус на простые и надежные методы! 🛡️
