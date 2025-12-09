# Seg

Сервис сегментации пользователей.

## Цель, задачи, и т.д.

**Цель**: Реализовать сервис сегментации пользователей, реализующим CRUD на сегменты, получение пользователей в сегменте и сегменты пользователя, возможность добавления сегмента проценту пользователей сервиса.

**Задачи**:

1. Настроить проект FastAPI с базой данной PostgreSQL и кэшом в Redis, подготовить настройки линтеров.
2. Реализовать CRUD для сегментов и пользователей.
3. Реализовать интерфейс просмотра, добавления и удаления связей между сегментами и пользователями.
4. Добавить методы фильтрации в CRUD, получения сегмента по пользователю и пользователей по сегментам.
5. Добавить метод для раздачи сегментов всей базе пользователей.

**Образ результата**:

Готовый сервис должен содержать полноценные CRUD для управления сегментами, пользователями и связями `сегмент-пользователь`, дополнительные методы фильтрации и массовой раздачи сегментов.

### Оптимальный способ достижения результата
Для уменьшения нагрузки на базу данных:
1. Дадим каждому сегменту UUID-индекс, который будем использовать как главный ключ, вместо использования названия сегмента в качестве главного ключа. Поиск по строкам в базе данных недостаточно эффективен.
2. Пользователей будем хранить в базе, но лишь их индексы - целые числа, согласно условию.
3. Для уменьшения времени выполнения Read запросов установим кэш, воспользуемся базой Redis для этого.

Для в целом оптимальной работы сервиса:
1. Используем фреймворк FastAPI - автоматически генерирует документацию и схему OpenAPI.
2. Будем использовать самодельные решения для миграций и чистый SQL вместо всяких там слабых ORM.

Для общего упрощения работы:
1. Ставить компоненты сервиса (базы данных) через докер
2. Заодно и ориентировать сервис под докерный деплой.
3. Для организации проекта будем использовать пакетный менеджер uv.
4. Для поддержки стиля и читаемости добавим кучу всяких линтеров:
    - Ruff
    - Wemake-Python-Styleguide
    - Mypy

### Разработайте сервис

разработал.

## Протестируйте сервис

Проведем пару запусков, проверочных вызовов ручек.

### Всякие запуски
**Проверим локальный запуск.**

Установим зависимости:

```bash
uv sync
```

Сначала запустим необходимые сервисы в докере. Если в корне проекта нету файла `.env`, его следует создать:

```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

Запустим докер:
```bash
docker compose up --build
```

Проведем миграции:
```bash
uv run seg/main.py --verbose
```

Собсна запуск:
```bash
uv run seg/app.py
```

Пройдем на http://localhost:8000/docs чтобы увидеть замечательную Swagger документацию.

**Проверим запуск в продовом контейнере.**

Заменим содержимое файла `.env` на что-то более приемлимое:
```ini
REDIS_URL="redis://cache:6379"
POSTGRES_URL="postgres://secret:bassford@db:5432/seg?target_session_attrs=read-write"
DEBUG=0
API_URL="http://backend:8000"

POSTGRES_USER=secret
POSTGRES_PASSWORD=bassford
```

Запустим докер (вы же почистили контейнер с предыдущего запуска да):
```bash
docker compose --file compose-prod.yml up --build
```

Пройдем на http://localhost/docs чтобы увидеть замечательную Swagger документацию.

### Собсна тесты

1. Проверим что выдаст поиск сегментов с дефолтными параметрами по пустой базе:
```bash
curl -X 'GET' \
  'http://localhost/api/v1/s/?pgi=0&pgl=10' \
  -H 'accept: application/json'
```
```json
[]
```
Весьма успешно на мой счет.

2. Добавим сегмент `MAIL_VOICE_MESSAGES`:
```bash
curl -X 'POST' \
  'http://localhost/api/v1/s/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '[
  {
    "name": "MAIL_VOICE_MESSAGES"
  }
]'
```
Проверим что по сегментам получилось:
```bash
curl -X 'GET' \
  'http://localhost/api/v1/s/?pgi=0&pgl=10' \
  -H 'accept: application/json'
```
```json
[
  {
    "id": "adc217ab-47c1-4071-8997-8e2fa0937b66",
    "name": "MAIL_VOICE_MESSAGES"
  }
]
```
Любопытно...

3. Добавим сразу еще два сегмента `CLOUD_DISCOUNT_30` и `MAIL_GPT`:
```bash
curl -X 'POST' \
  'http://localhost/api/v1/s/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '[
  {
    "name": "CLOUD_DISCOUNT_30"
  },
  {
    "name": "MAIL_GPT"
  }
]'
```
О, он кстати при добавлении вывел какие ID получили новые сегменты:
```json
[
  {
    "id": "c39848ba-05b2-42e0-a63f-541cbc0e3646",
    "name": "CLOUD_DISCOUNT_30"
  },
  {
    "id": "f5869100-d94b-4082-9572-86b6b75277d9",
    "name": "MAIL_GPT"
  }
]
```
прикольно...

Проверим что по всем сегментам:
```bash
curl -X 'GET' \
  'http://localhost/api/v1/s/?pgi=0&pgl=10' \
  -H 'accept: application/json'
```
```json
[
  {
    "id": "adc217ab-47c1-4071-8997-8e2fa0937b66",
    "name": "MAIL_VOICE_MESSAGES"
  },
  {
    "id": "c39848ba-05b2-42e0-a63f-541cbc0e3646",
    "name": "CLOUD_DISCOUNT_30"
  },
  {
    "id": "f5869100-d94b-4082-9572-86b6b75277d9",
    "name": "MAIL_GPT"
  }
]
```
Все 3, как и положено.

Проверим, что паджинация работает как надо:
```bash
curl -X 'GET' \
  'http://localhost/api/v1/s/?pgi=1&pgl=2' \
  -H 'accept: application/json'
```
```json
[
  {
    "id": "f5869100-d94b-4082-9572-86b6b75277d9",
    "name": "MAIL_GPT"
  }
]
```
Похоже на правду.

Проверим поиск по названию:
```bash
curl -X 'GET' \
  'http://localhost/api/v1/s/?pgi=0&pgl=10&name=CLOUD_DISCOUNT_30' \
  -H 'accept: application/json'
```
```json
[
  {
    "id": "c39848ba-05b2-42e0-a63f-541cbc0e3646",
    "name": "CLOUD_DISCOUNT_30"
  }
]
```
4. Изменим-ка один сегмент

Хочу повысить скидку. Вспоминаем индекс сегмента `CLOUD_DISCOUNT_30` и вставляем его в запрос:
```bash
curl -X 'PUT' \
  'http://localhost/api/v1/s/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '[
  {
    "id": "c39848ba-05b2-42e0-a63f-541cbc0e3646",
    "new_name": "CLOUD_DISCOUNT_40"
  }
]'
```
Посмотрим как выглядит полный список:
```bash
curl -X 'GET' \
  'http://localhost/api/v1/s/?pgi=0&pgl=10&name=CLOUD_DISCOUNT_30' \
  -H 'accept: application/json'
```
```json
[]
```
Упс, запустил снова поиск с прошлого раза. Зато мы точно видим, что старое название исчезло...
```bash
curl -X 'GET' \
  'http://localhost/api/v1/s/?pgi=0&pgl=10' \
  -H 'accept: application/json'
```
```json
[
  {
    "id": "adc217ab-47c1-4071-8997-8e2fa0937b66",
    "name": "MAIL_VOICE_MESSAGES"
  },
  {
    "id": "c39848ba-05b2-42e0-a63f-541cbc0e3646",
    "name": "CLOUD_DISCOUNT_40"
  },
  {
    "id": "f5869100-d94b-4082-9572-86b6b75277d9",
    "name": "MAIL_GPT"
  }
]
```
... а новое появилось.

Несмотря на простоту и очевидность вышесделанного, неправильная инвалидация кеша могла спокойно выдать нам неверные ответы.

5. Добавим пользователей

Мне слишком лень все расписывать подробно.

```bash
curl -X 'POST' \
  'http://localhost/api/v1/u/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '[
  15230, 19241, 18321
]'
```
Проверим результат:
```bash
curl -X 'GET' \
  'http://localhost/api/v1/u/?pgi=0&pgl=10' \
  -H 'accept: application/json'
```
```json
[
  {
    "id": 15230
  },
  {
    "id": 18321
  },
  {
    "id": 19241
  }
]
```

6. Назначение сегментов конкретным пользователям

```bash
curl -X 'POST' \
  'http://localhost/api/v1/su/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '[
  {
    "user_id": 15230,
    "segment_id": "adc217ab-47c1-4071-8997-8e2fa0937b66"
  },
{
    "user_id": 19241,
    "segment_id": "f5869100-d94b-4082-9572-86b6b75277d9"
  },
{
    "user_id": 15230,
    "segment_id": "f5869100-d94b-4082-9572-86b6b75277d9"
  }
]'
```
Проверим
```bash
curl -X 'GET' \
  'http://localhost/api/v1/su/?pgi=0&pgl=10' \
  -H 'accept: application/json'
```
```json
[
  {
    "user_id": 15230,
    "segment_id": "adc217ab-47c1-4071-8997-8e2fa0937b66"
  },
  {
    "user_id": 15230,
    "segment_id": "f5869100-d94b-4082-9572-86b6b75277d9"
  },
  {
    "user_id": 19241,
    "segment_id": "f5869100-d94b-4082-9572-86b6b75277d9"
  }
]
```

7. Назначение сегмента проценту пользователей

```bash
curl -X 'POST' \
  'http://localhost/api/v1/su/mass' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "ratio": 0.5,
  "segment_ids": [
    "c39848ba-05b2-42e0-a63f-541cbc0e3646"
  ]
}'
```
Проверим
```bash
curl -X 'GET' \
  'http://localhost/api/v1/su/?pgi=0&pgl=10' \
  -H 'accept: application/json'
```
```json
[
  {
    "user_id": 15230,
    "segment_id": "adc217ab-47c1-4071-8997-8e2fa0937b66"
  },
  {
    "user_id": 15230,
    "segment_id": "f5869100-d94b-4082-9572-86b6b75277d9"
  },
  {
    "user_id": 19241,
    "segment_id": "f5869100-d94b-4082-9572-86b6b75277d9"
  },
  {
    "user_id": 19241,
    "segment_id": "c39848ba-05b2-42e0-a63f-541cbc0e3646"
  }
]
```
Досталось лишь одному :^(

8. Вывод сегментов указанного пользователя

```bash
curl -X 'GET' \
  'http://localhost/api/v1/s/?pgi=0&pgl=10&user_id=15230' \
  -H 'accept: application/json'
```
```json
[
  {
    "id": "adc217ab-47c1-4071-8997-8e2fa0937b66",
    "name": "MAIL_VOICE_MESSAGES"
  },
  {
    "id": "f5869100-d94b-4082-9572-86b6b75277d9",
    "name": "MAIL_GPT"
  }
]
```

9. Вывод пользователей, входящих в сегмент (а это было обязательно???)

```bash
curl -X 'GET' \
  'http://localhost/api/v1/u/?pgi=0&pgl=10&segment_id=c39848ba-05b2-42e0-a63f-541cbc0e3646' \
  -H 'accept: application/json'
```
```json
[
  {
    "id": 19241
  }
]
```

