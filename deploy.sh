#!/bin/bash

# Проверка наличия Docker и Docker Compose
if ! command -v docker &> /dev/null; then
    echo "Docker не установлен. Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose не установлен. Установка Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Проверка наличия .env файла
if [ ! -f ".env" ]; then
    echo "Создание .env файла..."
    cp .env.example .env
    
    # Генерация случайного ключа
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/your-super-secret-key-change-it/$SECRET_KEY/" .env
    
    # Запрос URL сервера
    read -p "Введите URL сервера (например, http://example.com): " HOST_URL
    sed -i "s|http://localhost|$HOST_URL|" .env
fi

# Остановка и удаление старых контейнеров и томов
echo "Очистка старых контейнеров и томов..."
docker-compose down -v

# Создание и запуск новых контейнеров
echo "Сборка и запуск контейнеров..."
docker-compose build --no-cache
docker-compose up -d

echo "Развертывание завершено!"
echo "Приложение доступно по адресу: $(grep HOST_URL .env | cut -d '=' -f2)" 