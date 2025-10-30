# Множество ботов на одном сервере (Docker)

## Что делает конфигурация
- Два сервиса: `bot_city1` и `bot_city2`
- У каждого свой `.env` и свои каталоги данных/логов/бэкапов
- Общий Redis, но разные БД индексы (`/0` и `/1`)

## Файлы
- `docker/docker-compose.multibot.yml` — основной compose для двух ботов
- `env.city1.example` / `env.city2.example` — примеры env для каждого бота
- `START_city1.bat` / `START_city2.bat` — запуск конкретного бота под Windows

## Подготовка
1. Скопируйте примеры env:
   ```bash
   cp env.city1.example env.city1
   cp env.city2.example env.city2
   ```
2. Заполните `BOT_TOKEN`, `ADMIN_IDS` и другие переменные.
3. Создайте каталоги для данных (если нужно):
   ```bash
   mkdir -p data/city1 logs/city1 backups/city1
   mkdir -p data/city2 logs/city2 backups/city2
   ```

## Запуск
- Оба бота:
  ```bash
  docker-compose -f docker/docker-compose.multibot.yml up -d --build
  ```
- Только city1:
  ```bash
  docker-compose -f docker/docker-compose.multibot.yml up -d --build bot_city1
  ```
- Только city2:
  ```bash
  docker-compose -f docker/docker-compose.multibot.yml up -d --build bot_city2
  ```

## Логи
```bash
docker-compose -f docker/docker-compose.multibot.yml logs -f bot_city1
docker-compose -f docker/docker-compose.multibot.yml logs -f bot_city2
```

## Обновление
```bash
docker-compose -f docker/docker-compose.multibot.yml pull
docker-compose -f docker/docker-compose.multibot.yml up -d --build
```

## Примечания
- Путь к БД внутри контейнера фиксирован (`/app/data/bot_database.db`), для разделения используются разные bind-монты.
- Если хотите отдельный Redis на бота — продублируйте сервис `redis` и замените `REDIS_URL`.
