# Парсим данные в Telegram на Python. Часть 2. Читаем и анализируем сообщения из чатов

Пишем парсер для Telegram: собираем сообщения из каналов и чатов.

Сегодня мы научимся парсить чаты из Telegram: разберёмся в том, какие модули нам пригодятся, и настроим сбор сообщений. Всё это с помощью библиотеки Telethon для Python.

Это второй урок по парсингу в Telegram. В первом мы создали парсер списка участников каналов и чатов и научились работать с инструментами разработчика API мессенджера. Если вы ещё не читали [первую часть](https://skillbox.ru/media/code/parsim-dannye-v-telegram-na-python-chast-1/), то обязательно начните с неё.

## Что у нас сейчас есть?

В первой части урока мы:
- настроили инструменты разработчика API Telegram и научились использовать их для подключения к клиенту мессенджера;
- установили и импортировали библиотеку Telethon, позволяющую работать с API Telegram, выбрав нужные нам классы, функции и типы;
- научились парсить список групп и чатов из мессенджера;
- написали код для парсинга списка пользователей в чате или мессенджере, сохраняющий их в удобном для чтения и последующего анализа виде.

У нас остаётся одна задача — спарсить сообщения из чатов. Мы сохраним только содержание чатов без дополнительной информации о времени их отправки и самом отправителе. В дальнейшем эти данные можно будет использовать для анализа переписки: например, узнать о самых часто встречающихся словах и предположить самые популярные темы для обсуждения.

## Добавляем новые импорты

Откроем в IDE [код из первой части урока](https://github.com/safronovmax/python_examples/blob/main/main.py). Мы продолжим работать с ним, а не будем писать всё с нуля. Чтобы спарсить сообщения из чатов, необходимо импортировать новый метод и функцию в начало кода:

```python
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
```

Что мы импортировали:
- `GetHistoryRequest` — метод, позволяющий получить сообщения пользователей из чата и работать с ним;
- `PeerChannel` — специальный тип, определяющий объекты типа «канал/чат», с помощью которого можно обратиться к нужному каналу для парсинга сообщений.

## Пишем код парсера сообщений

Начнём с создания пустого списка, который будет хранить сообщения, и инициализируем несколько переменных, которые пригодятся позже.

```python
all_messages = []
offset_id = 0
limit = 100
total_messages = 0
total_count_limit = 0
```

Список `all_messages` используется для хранения спарсенных сообщений. Переменная `limit` задаёт лимит на парсинг сообщений — за каждый цикл работы будет сохраняться только 100 сообщений.

Кроме того, мы используем ещё две переменные — `total_messages` и `total_count_limit`. Первая выступает счётчиком спарсенных сообщений, а вторая позволят нам задать ограничение на общее количество полученных сообщений. В примере кода `total_count_limit` равен 0, то есть парсятся все сообщения. Если история чата большая, то её парсинг может занять слишком много времени. В этом случае можно ограничить количество спарсенных сообщений вручную.

`offset_id` — важная переменная. К ней будет обращаться метод `GetHistoryRequest` для того, чтобы понять, с какого сообщения начать парсинг. Вначале присваиваем ей значение 0, чтобы парсинг шёл с самого первого сообщения в канале. То есть если бы мы указали значение, равное 100, то первые 100 сообщений парсер бы пропустил.

Добавим в код сам парсер сообщений и разберём его:

```python
while True:
    history = client(GetHistoryRequest(
        peer=target_group,
        offset_id=offset_id,
        offset_date=None,
        add_offset=0,
        limit=limit,
        max_id=0,
        min_id=0,
        hash=0
    ))
    if not history.messages:
        break
    messages = history.messages
    for message in messages:
        all_messages.append(message.to_dict())
    offset_id = messages[len(messages) - 1].id
    if total_count_limit != 0 and total_messages >= total_count_limit:
        break
```

Парсинг реализуется через цикл `while`. Код в цикле будет выполняться до тех пор, пока в чате остаются сообщения, которые мы ещё не спарсили, или пока не будет достигнут установленный лимит по числу собранных сообщений.

Для получения сообщений используем стандартный метод библиотеки Telethon — `GetHistoryRequest`, передавая его внутри запроса нашего клиента к API Telegram. Для выбора группы используется параметр `peer`, которому мы присваиваем значение выбранной группы, полученной в начале работы парсера. В нашем случае это другая переменная — `target_group`.

Параметры `offset_date` и `offset_peer` мы передаём с пустыми значениями. Обычно они используются для фильтрации полученных данных, но здесь мы хотим получить весь список сообщений. Лимит по количеству элементов в ответе задаём числом 100, передавая в параметр `limit` переменную `limit`. Также у нас есть три обязательных параметра для работы `GetHistoryRequest`: `min_id`, `max_id` и `hash`. Их передаём с нулевыми значениями, так как они не будут использоваться, но указать их обязательно — если этого не сделать, метод не будет работать.

Основной цикл работает просто:
- Проверяем, остаются ли сообщения, которые можно спарсить. Если нет, то цикл завершается. Если сообщения есть, то сохраняем их в список `messages`.
- Каждое сообщение из списка `message` мы сохраняем в список `all_messages`.
- Если количество полученных сообщений больше их количества в чате или мы достигли лимита парсинга, то цикл завершается.

`GetHistoryRequest` получает `offset_id`, который показывает, с какого сообщения `GetHistoryRequest` должен начать получать историю чата. Важно правильно установить смещение для `offset_id`, чтобы все сообщения были уникальными. Поэтому стартовое значение `offset_id` для следующего прохождения цикла устанавливается со смещением на одно сообщение.

## Сохраняем полученные сообщения в файл

Полученные сообщения сохраняем в формате CSV по аналогии с парсингом пользователей:

```python
print("Сохраняем данные в файл...") #Cообщение для пользователя о том, что начался парсинг сообщений.
with open("chats.csv", "w", encoding="UTF-8") as f:
    writer = csv.writer(f, delimiter=",", lineterminator="\n")
    writer.writerow(["message"])
    for message in all_messages:
        writer.writerow([message])
print("Парсинг сообщений группы успешно выполнен.") #Сообщение об удачном парсинге чата.
```

После этого переходим к сохранению данных в файл формата CSV с помощью стандартного модуля `csv`. Открываем файл в режиме записи, указывая кодировку UTF-8.

Если файл отсутствует в директории, то будет в ней создан. После этого создаём объект CSV writer и записываем в него сообщение из нашего списка `all_messages`.

Запустим парсер и выберем группу из списка:
Всё получилось. Откроем нашу директорию. Теперь в ней два файла в формате CSV: `members.csv` и `chats.csv`. Откроем последний:
Мы видим, что сохранились не только сами сообщения, но и техническая информация про их id, id запроса и так далее. Такой результат нам не подходит. Вернёмся к циклу `while` и добавим к методу `message` параметр `message.message`. Он позволяет сохранять только само сообщение.

```python
if not history.messages:
    break
messages = history.messages
for message in messages:
    all_messages.append(message.message) #Добавим параметр message к методу message.
offset_id = messages[len(messages) - 1].id
if total_count_limit != 0 and total_messages >= total_count_limit:
    break
```

Повторно запустим код и посмотрим на результат:
Теперь всё работает как надо. Сохранились только сообщения без служебной информации о запросах.

## Код парсера для Telegram на Python полностью

В двух частях урока по парсингу информации из Telegram мы написали много кода. Посмотрим на него полностью:

```python
from xmlrpc.client import DateTime
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
import csv

api_id = 18377495
api_hash = "a0c785ad0fd3e92e7c131f0a70987987"
phone = "+79991669331"

client = TelegramClient(phone, api_id, api_hash)

client.start()
chats = []
last_date = None
chunk_size = 200
groups=[]

result = client(GetDialogsRequest(
             offset_date=last_date,
             offset_id=0,
             offset_peer=InputPeerEmpty(),
             limit=chunk_size,
             hash = 0
         ))
chats.extend(result.chats)

for chat in chats:
    try:
        if chat.megagroup== True:
            groups.append(chat)
    except:
        continue

print("Выберите группу для парсинга сообщений и членов группы:")
i=0
for g in groups:
    print(str(i) + "- " + g.title)
    i+=1

g_index = input("Введите нужную цифру: ")
target_group=groups[int(g_index)]

print("Узнаём пользователей...")
all_participants = []
all_participants = client.get_participants(target_group)

print("Сохраняем данные в файл...")
with open("members.csv", "w", encoding="UTF-8") as f:
    writer = csv.writer(f,delimiter=",",lineterminator="\n")
    writer.writerow(["username", "name","group"])
    for user in all_participants:
        if user.username:
            username= user.username
        else:
            username= ""
        if user.first_name:
            first_name= user.first_name
        else:
            first_name= ""
        if user.last_name:
            last_name= user.last_name
        else:
            last_name= ""
        name= (first_name + ' ' + last_name).strip()
        writer.writerow([username,name,target_group.title])      
print("Парсинг участников группы успешно выполнен.")

offset_id = 0
limit = 100
all_messages = []
total_messages = 0
total_count_limit = 0

while True:
    history = client(GetHistoryRequest(
        peer=target_group,
        offset_id=offset_id,
        offset_date=None,
        add_offset=0,
        limit=limit,
        max_id=0,
        min_id=0,
        hash=0
    ))
    if not history.messages:
        break
    messages = history.messages
    for message in messages:
        all_messages.append(message.message)
    offset_id = messages[len(messages) - 1].id
    if total_count_limit != 0 and total_messages >= total_count_limit:
        break

print("Сохраняем данные в файл...")
with open("chats.csv", "w", encoding="UTF-8") as f:
    writer = csv.writer(f, delimiter=",", lineterminator="\n")
    for message in all_messages:
        writer.writerow([message])
print('Парсинг сообщений группы успешно выполнен.')
```

## Что дальше?

Библиотека Telethon используется не только для парсинга информации о пользователях и сообщений в каналах и чатах, но и для автоматизации работы с Telegram. Например, администраторы каналов могут создать бота, позволяющего писать сообщения, отправлять стикеры и управлять списком участников. Эти примеры разобраны в [документации библиотеки](https://telethonn.readthedocs.io/en/latest/).
