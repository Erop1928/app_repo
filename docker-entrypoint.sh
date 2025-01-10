#!/bin/bash

# Создание директории для загрузок
mkdir -p /app/uploads
chown -R app:app /app/uploads

# Ожидание готовности базы данных
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

# Запуск приложения от имени пользователя app
exec gosu app bash -c '
# Инициализация базы данных
echo "Initializing database..."
python init_db.py

# Запуск gunicorn
exec gunicorn --bind 0.0.0.0:5000 \
    --workers 4 \
    --threads 2 \
    --timeout 600 \
    --access-logfile - \
    --error-logfile - \
    "main:app"
' 