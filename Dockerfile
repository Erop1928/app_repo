FROM python:3.11-slim

# Установка необходимых системных пакетов
RUN apt-get update && apt-get install -y \
    build-essential \
    gosu \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя для запуска приложения
RUN useradd -m -U app && \
    mkdir -p /app && \
    chown -R app:app /app

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY --chown=app:app requirements.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir flask-migrate

# Копирование исходного кода приложения
COPY --chown=app:app . .

# Создание директорий для данных
RUN mkdir -p uploads migrations && \
    chown -R app:app uploads migrations

# Установка переменных окружения
ENV FLASK_APP=main.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Сделать entrypoint-скрипт исполняемым
RUN chmod +x docker-entrypoint.sh

# Открытие порта
EXPOSE 5000

# Установка entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"] 