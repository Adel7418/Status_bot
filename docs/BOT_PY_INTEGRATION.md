# Интеграция парсера в bot.py

## Инструкции по добавлению ParserIntegration в основной бот

### 1. Импорт

Добавьте импорт в начало `bot.py` (после других импортов services):

```python
from app.services.parser_integration import ParserIntegration
```

### 2. Переменная в main()

В функции `main()` добавьте переменную для парсера:

```python
async def main():
    """Основная функция запуска бота"""

    bot = None
    db = None
    scheduler = None
    dp = None
    parser_integration = None  # <-- ДОБАВИТЬ
```

### 3. Инициализация в on_startup()

В функции `on_startup()` добавьте инициализацию парсера после запуска scheduler:

```python
async def on_startup(bot: Bot, db: Database, scheduler: TaskScheduler):
    """
    Действия при запуске бота
    """
    # ... существующий код ...

    # Запуск планировщика
    await scheduler.start()
    logger.info("Планировщик задач запущен")

    # Инициализация парсера заявок (ДОБАВИТЬ)
    parser_integration = ParserIntegration(bot, db)
    try:
        await parser_integration.start()
    except Exception as e:
        logger.error(f"Не удалось запустить парсер: {e}", exc_info=True)
        # Продолжаем работу бота даже если парсер не запустился

    logger.info("Бот успешно запущен!")

    return parser_integration  # <-- ВАЖНО: вернуть для использования в finally
```

### 4. Изменение сигнатуры on_startup()

Измените сигнатуру чтобы возвращать parser_integration:

```python
async def on_startup(bot: Bot, db: Database, scheduler: TaskScheduler) -> ParserIntegration | None:
```

### 5. Сохранение ссылки в main()

В функции `main()` сохраните ссылку на parser_integration:

```python
# Вызов startup функции перед запуском
parser_integration = await on_startup(bot, db, scheduler)
```

### 6. Остановка в on_shutdown()

В функции `on_shutdown()` добавьте остановку парсера:

```python
async def on_shutdown(bot: Bot, db: Database, scheduler: TaskScheduler, parser_integration: ParserIntegration | None = None):
    """
    Действия при остановке бота
    """
    # Остановка парсера (ДОБАВИТЬ в начало)
    if parser_integration:
        try:
            await parser_integration.stop()
            logger.info("Парсер заявок остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке парсера: {e}")

    # Остановка планировщика
    await scheduler.stop()
    logger.info("Планировщик задач остановлен")

    # ... остальной код ...
```

### 7. Остановка в finally блоке

В блоке `finally` функции `main()` добавьте остановку парсера:

```python
finally:
    # Гарантированная очистка ресурсов
    logger.info("Начало процедуры остановки...")

    # Остановка парсера (ДОБАВИТЬ)
    if parser_integration:
        try:
            await parser_integration.stop()
        except Exception as e:
            logger.error("Ошибка при остановке парсера: %s", e)

    # Остановка планировщика
    if scheduler:
        try:
            await scheduler.stop()
        except Exception as e:
            logger.error("Ошибка при остановке scheduler: %s", e)

    # ... остальной код ...
```

## Полный diff для bot.py

```diff
+ from app.services.parser_integration import ParserIntegration

- async def on_startup(bot: Bot, db: Database, scheduler: TaskScheduler):
+ async def on_startup(bot: Bot, db: Database, scheduler: TaskScheduler) -> ParserIntegration | None:
      """
      Действия при запуске бота
      """
      # Запуск планировщика
      await scheduler.start()
      logger.info("Планировщик задач запущен")

+     # Инициализация парсера заявок
+     parser_integration = ParserIntegration(bot, db)
+     try:
+         await parser_integration.start()
+     except Exception as e:
+         logger.error(f"Не удалось запустить парсер: {e}", exc_info=True)
+         parser_integration = None

      logger.info("Бот успешно запущен!")
+     return parser_integration

- async def on_shutdown(bot: Bot, db: Database, scheduler: TaskScheduler):
+ async def on_shutdown(bot: Bot, db: Database, scheduler: TaskScheduler, parser_integration: ParserIntegration | None = None):
      """
      Действия при остановке бота
      """
+     # Остановка парсера
+     if parser_integration:
+         try:
+             await parser_integration.stop()
+         except Exception as e:
+             logger.error(f"Ошибка при остановке парсера: {e}")
+
      # Остановка планировщика
      await scheduler.stop()
      logger.info("Планировщик задач остановлен")

  async def main():
      """Основная функция запуска бота"""

      bot = None
      db = None
      scheduler = None
      dp = None
+     parser_integration = None

      try:
          # ... инициализация ...

          # Вызов startup функции перед запуском
-         await on_startup(bot, db, scheduler)
+         parser_integration = await on_startup(bot, db, scheduler)

          # ... запуск бота ...

      finally:
          logger.info("Начало процедуры остановки...")

+         # Остановка парсера
+         if parser_integration:
+             try:
+                 await parser_integration.stop()
+             except Exception as e:
+                 logger.error("Ошибка при остановке парсера: %s", e)
+
          # Остановка планировщика
          if scheduler:
              try:
                  await scheduler.stop()
              except Exception as e:
                  logger.error("Ошибка при остановке scheduler: %s", e)
```

## После интеграции

1. Запустите бота
2. Проверьте логи на наличие сообщения:
   ```
   🟢 Парсер заявок успешно запущен!
   ```
   или
   ```
   Парсер отключён (PARSER_ENABLED=false), пропускаем запуск
   ```

3. Если парсер включён — используйте `/parser_status` для проверки

4. Настройте group_id через `/set_group`

5. Парсер начнёт мониторинг автоматически

---

**Примечание:** Интеграция спроектирована так, чтобы не ломать основной бот.
Если парсер не запускается — бот продолжает работу в обычном режиме.
