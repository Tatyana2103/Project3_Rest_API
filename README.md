
Сервис для сокращения длинных ссылок с возможностью аналитики, кастомными алиасами и управлением временем жизни ссылок.

##  Содержание

- [Описание API](#описание-api)
- [Примеры запросов](#примеры-запросов)
- [Инструкция по запуску](#инструкция-по-запуску)
- [База данных](#база-данных)
- [Тестирование](#тестирование)


##  Описание API

### Аутентификация

| Метод | Эндпоинт | Описание | Доступ |
|-------|----------|----------|--------|
| POST | `/auth/register` | Регистрация нового пользователя | Все |
| POST | `/auth/token` | Получение JWT токена | Все |

### Работа с ссылками

| Метод | Эндпоинт | Описание | Доступ |
|-------|----------|----------|--------|
| POST | `/links/shorten` | Создание короткой ссылки | Все |
| GET | `/links/{short_code}` | Редирект на оригинальный URL | Все |
| GET | `/links/{short_code}/stats` | Статистика по ссылке | Все (публичная) |
| PUT | `/links/{short_code}` | Обновление оригинального URL | Только владелец |
| DELETE | `/links/{short_code}` | Удаление ссылки | Только владелец |
| GET | `/links/search?original_url={url}` | Поиск по оригинальному URL | Все |
| GET | `/links/user/me` | Список ссылок пользователя | Только владелец |

##  Примеры запросов

### 1. Регистрация пользователя

**Запрос:**
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepassword123"
  }'

Ответ:
```
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "created_at": "2024-01-15T10:30:00Z",
  "is_active": true
}
```
### 2. Создание короткой ссылки
Обычная ссылка:

```bash
curl -X POST "http://localhost:8000/links/shorten" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://example.com/very/long/url/that/needs/shortening"
  }'
```

С кастомным алиасом и временем жизни:
```bash
curl -X POST "http://localhost:8000/links/shorten" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "original_url": "https://example.com/very/long/url",
    "custom_alias": "mycustomlink",
    "expires_at": "2024-12-31T23:59:59Z"
  }'
Ответ:
```

```
json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "short_code": "mycustomlink",
  "short_url": "http://localhost:8000/mycustomlink",
  "original_url": "https://example.com/very/long/url",
  "custom_alias": "mycustomlink",
  "created_at": "2024-01-15T10:35:00Z",
  "expires_at": "2024-12-31T23:59:59Z",
  "clicks": 0,
  "last_accessed": null,
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```


## Инструкция по запуску
#### 1. Создание виртуального окружения

```bash
# Linux/Mac
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```
#### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```
Если будет возникать ошибка с установкой greenlet, то запустить также:
```bash
pip install --only-binary :all: greenlet
```

#### 3. Настройка переменных окружения
Создайте файл .env в корне проекта:


#### 4. Запуск PostgreSQL и Redis

```bash
# PostgreSQL (пароль должен совпадать с .env)
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_USER=user \
  -e POSTGRES_DB=urlshortener \
  -p 5432:5432 \
  postgres:15

# Redis
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7
```

### 5. Запуск приложения

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

##  База данных

##  Таблица `users`

Хранит информацию о зарегистрированных пользователях сервиса.

### Структура таблицы

| Колонка | Тип данных | Ограничения | Описание |
|---------|------------|-------------|----------|
| `id` | `VARCHAR` | `PRIMARY KEY` | UUID идентификатор пользователя (генерируется автоматически) |
| `username` | `VARCHAR` | `UNIQUE`, `NOT NULL` | Уникальное имя пользователя для входа |
| `email` | `VARCHAR` | `UNIQUE`, `NOT NULL` | Email пользователя |
| `hashed_password` | `VARCHAR` | `NOT NULL` | Хеш пароля (bcrypt) |
| `created_at` | `TIMESTAMP` | `DEFAULT now()` | Дата и время регистрации |
| `is_active` | `BOOLEAN` | `DEFAULT true` | Флаг активности пользователя |

---


##  Таблица `links`

Таблица `links` хранит все сокращенные ссылки, созданные пользователями сервиса. Каждая запись представляет собой связь между коротким кодом и оригинальным URL, а также содержит статистику переходов и метаданные.

---

##  Структура таблицы


| Колонка | Тип данных | Ограничения | По умолчанию | Описание |
|---------|------------|-------------|--------------|----------|
| `id` | `VARCHAR` | `PRIMARY KEY` | `gen_random_uuid()::VARCHAR` | Уникальный идентификатор ссылки |
| `short_code` | `VARCHAR(50)` | `UNIQUE`, `NOT NULL` | - | Уникальный короткий код для редиректа |
| `original_url` | `TEXT` | `NOT NULL` | - | Оригинальный длинный URL |
| `custom_alias` | `VARCHAR(50)` | `UNIQUE` | `NULL` | Пользовательский алиас (если задан) |
| `created_at` | `TIMESTAMP` | - | `CURRENT_TIMESTAMP` | Дата создания ссылки |
| `expires_at` | `TIMESTAMP` | - | `NULL` | Дата истечения срока действия |
| `clicks` | `INTEGER` | - | `0` | Количество переходов по ссылке |
| `last_accessed` | `TIMESTAMP` | - | `NULL` | Дата и время последнего перехода |
| `user_id` | `VARCHAR` | `FOREIGN KEY REFERENCES users(id) ON DELETE SET NULL` | `NULL` | ID пользователя-владельца |
| `is_active` | `BOOLEAN` | - | `true` | Флаг активности ссылки |

---
## Тестирование

#### Запуск тестов с измерением покрытия
```bash
coverage run -m pytest tests/
```

#### Запуск конкретных тестов
```bash
coverage run -m pytest tests/unit/
coverage run -m pytest tests/functional/test_auth.py
```

#### Показать отчет в терминале
```bash
coverage report
```

#### Создание HTML отчета
```bash
coverage html
```

#### Указать директорию для отчета
```bash
coverage html -d tests/coverage_html
```

#### Открыть отчет в браузере
```bash
open tests/coverage_html/index.html  # macOS
start tests/coverage_html/index.html # Windows
xdg-open tests/coverage_html/index.html # Linux
```

#### Нагрузочное тестирование

#### Запуск Locust

Запуск с веб-интерфейсом
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

#### Покрытие кода (HTML отчет)
В репозитории HTML отчет о покрытии доступен по пути: tests/Coverage report.html
