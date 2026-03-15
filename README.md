
Сервис для сокращения длинных ссылок с возможностью аналитики, кастомными алиасами и управлением временем жизни ссылок.

##  Содержание

- [Описание API](#описание-api)
- [Примеры запросов](#примеры-запросов)
- [Инструкция по запуску](#инструкция-по-запуску)
- [База данных](#база-данных)


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
2. Создание короткой ссылки
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
