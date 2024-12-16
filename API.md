# API Документация

## Общая информация

Базовый URL: `http://your-domain.com/api/v1`

Все запросы к API должны содержать заголовок Basic Auth авторизации:
```
Authorization: Basic <base64(username:password)>
```

Пример:
```
username: admin
password: secret123
Authorization: Basic YWRtaW46c2VjcmV0MTIz
```

Ответы API возвращаются в формате JSON.

## Аутентификация

### Получение токена

```http
POST /auth/token
```

**Тело запроса:**
```json
{
    "username": "string",
    "password": "string"
}
```

**Ответ:**
```json
{
    "access_token": "string",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

## Приложения

### Получение списка приложений

```http
GET /applications
```

**Заголовки:**
```
Authorization: Basic <base64(username:password)>
```

**Параметры запроса:**
- `category_id` (опционально) - ID категории для фильтрации
- `page` (опционально) - номер страницы
- `per_page` (опционально) - количество элементов на странице

**Ответ:**
```json
{
    "items": [
        {
            "id": 1,
            "package_name": "com.example.app",
            "name": "Example App",
            "description": "string",
            "category_id": 1,
            "category_name": "string",
            "latest_version": {
                "version_number": "1.0.0",
                "branch": "release",
                "is_stable": true
            }
        }
    ],
    "total": 100,
    "page": 1,
    "pages": 10
}
```

### Получение информации о приложении

```http
GET /applications/{id}
```

**Заголовки:**
```
Authorization: Basic <base64(username:password)>
```

**Ответ:**
```json
{
    "id": 1,
    "package_name": "com.example.app",
    "name": "Example App",
    "description": "string",
    "category_id": 1,
    "category_name": "string",
    "versions": [
        {
            "id": 1,
            "version_number": "1.0.0",
            "branch": "release",
            "upload_date": "2024-01-16T14:30:00Z",
            "file_size": 1048576,
            "downloads": 100,
            "is_stable": true,
            "changelog": "string"
        }
    ]
}
```

### Создание нового приложения

```http
POST /applications
```

**Заголовки:**
```
Authorization: Basic <base64(username:password)>
Content-Type: application/json
```

**Тело запроса:**
```json
{
    "package_name": "string",
    "name": "string",
    "description": "string",
    "category_id": 1
}
```

**Ответ:**
```json
{
    "id": 1,
    "package_name": "string",
    "name": "string",
    "description": "string",
    "category_id": 1
}
```

## Версии

### Получение списка версий приложения

```http
GET /applications/{id}/versions
```

**Заголовки:**
```
Authorization: Basic <base64(username:password)>
```

**Параметры запроса:**
- `branch` (опционально) - фильтр по ветке (release, debug, beta, alpha)
- `is_stable` (опционально) - фильтр по стабильным версиям
- `page` (опционально) - номер страницы
- `per_page` (опционально) - количество элементов на странице

**Ответ:**
```json
{
    "items": [
        {
            "id": 1,
            "version_number": "1.0.0",
            "branch": "release",
            "upload_date": "2024-01-16T14:30:00Z",
            "file_size": 1048576,
            "downloads": 100,
            "is_stable": true,
            "changelog": "string"
        }
    ],
    "total": 100,
    "page": 1,
    "pages": 10
}
```

### Загрузка новой версии

```http
POST /applications/{id}/versions
```

**Заголовки:**
```
Authorization: Basic <base64(username:password)>
Content-Type: multipart/form-data
```

**Тело запроса (multipart/form-data):**
- `apk_file`: файл (обязательно)
- `changelog`: string (опционально)
- `is_stable`: boolean (опционально)

**Ответ:**
```json
{
    "id": 1,
    "version_number": "1.0.0",
    "branch": "release",
    "upload_date": "2024-01-16T14:30:00Z",
    "file_size": 1048576,
    "downloads": 0,
    "is_stable": false,
    "changelog": "string"
}
```

### Пакетная загрузка версий

```http
POST /applications/{id}/versions/batch
```

**Заголовки:**
```
Authorization: Basic <base64(username:password)>
Content-Type: multipart/form-data
```

**Тело запроса (multipart/form-data):**
- `apk_files[]`: массив файлов (обязательно)

**Ответ:**
```json
{
    "uploaded": [
        {
            "id": 1,
            "version_number": "1.0.0",
            "branch": "release",
            "filename": "string"
        }
    ],
    "failed": [
        {
            "filename": "string",
            "error": "string"
        }
    ]
}
```

### Обновление информации о версии

```http
PATCH /versions/{id}
```

**Заголовки:**
```
Authorization: Basic <base64(username:password)>
Content-Type: application/json
```

**Тело запроса:**
```json
{
    "changelog": "string",
    "is_stable": true,
    "branch": "string"
}
```

**Ответ:**
```json
{
    "id": 1,
    "version_number": "1.0.0",
    "branch": "release",
    "changelog": "string",
    "is_stable": true
}
```

### Скачивание версии

```http
GET /versions/{id}/download
```

**Заголовки:**
```
Authorization: Basic <base64(username:password)>
```

**Ответ:** Файл APK

### Создание одноразовой ссылки для скачивания

```http
POST /versions/{id}/generate-link
```

**Заголовки:**
```
Authorization: Basic <base64(username:password)>
```

**Ответ:**
```json
{
    "download_url": "string",
    "expires_at": "2024-01-17T14:30:00Z"
}
```

### Скачивание по одноразовой ссылке

```http
GET /download/{token}
```

**Примечание:** Для этого эндпоинта авторизация не требуется, так как используется одноразовый токен.

**Ответ:** Файл APK

## Категории

### Получение списка категорий

```http
GET /categories
```

**Заголовки:**
```
Authorization: Basic <base64(username:password)>
```

**Ответ:**
```json
{
    "items": [
        {
            "id": 1,
            "name": "string",
            "description": "string",
            "applications_count": 10
        }
    ]
}
```

## Флаги версий

### Добавление флага к версии

```http
POST /versions/{id}/flags
```

**Заголовки:**
```
Authorization: Basic <base64(username:password)>
Content-Type: application/json
```

**Тело запроса:**
```json
{
    "flag_type": "bug|feature|warning",
    "description": "string"
}
```

**Ответ:**
```json
{
    "id": 1,
    "flag_type": "string",
    "description": "string",
    "created_date": "2024-01-16T14:30:00Z",
    "created_by": "string"
}
```

## Коды ошибок

- `400 Bad Request` - Неверный запрос
- `401 Unauthorized` - Неверные учетные данные
- `403 Forbidden` - Недостаточно прав
- `404 Not Found` - Ресурс не найден
- `409 Conflict` - Конфликт (например, версия уже существует)
- `413 Payload Too Large` - Превышен размер загружаемого файла
- `429 Too Many Requests` - Превышен лимит запросов
- `500 Internal Server Error` - Внутренняя ошибка сервера

## Ограничения

- Максимальный размер APK файла: 500 MB
- Максимальное количество файлов для пакетной загрузки: 50
- Максимальный общий размер пакетной загрузки: 1 GB
- Срок действия одноразовой ссылки: 24 часа
- Формат имени APK файла: `package_name-vX.X.X-branch.apk`

## Примечания по безопасности

1. Все запросы должны выполняться через HTTPS
2. Пароль в Basic Auth передается в base64, поэтому важно использовать HTTPS
3. Рекомендуется использовать сложные пароли
4. При неверных учетных данных API всегда возвращает код 401
5. После нескольких неудачных попыток авторизации возможна временная блокировка IP-адреса