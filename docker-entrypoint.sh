#!/bin/bash

# Создание необходимых директорий
mkdir -p /app/instance /app/uploads

# Установка правильных прав для директорий
chown -R app:app /app/instance /app/uploads
chmod -R 755 /app/instance /app/uploads

# Инициализация базы данных, если она еще не существует
if [ ! -f "/app/instance/app.db" ]; then
    echo "Initializing database..."
    python init_db.py
fi

# Запуск gunicorn
exec gunicorn --bind 0.0.0.0:5000 \
    --workers 4 \
    --threads 2 \
    --timeout 600 \
    --access-logfile - \
    --error-logfile - \
    "main:app" 