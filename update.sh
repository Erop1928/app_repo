#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Начинаем обновление приложения...${NC}"

# Проверяем наличие docker и docker-compose
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker не установлен!${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose не установлен!${NC}"
    exit 1
fi

# Получаем последние изменения из репозитория
echo -e "${YELLOW}Получаем последние изменения из репозитория...${NC}"
git pull

if [ $? -ne 0 ]; then
    echo -e "${RED}Ошибка при получении изменений из репозитория!${NC}"
    exit 1
fi

# Останавливаем текущие контейнеры
echo -e "${YELLOW}Останавливаем текущие контейнеры...${NC}"
docker-compose down

# Удаляем старые образы
echo -e "${YELLOW}Удаляем старые образы...${NC}"
docker image prune -f

# Собираем новые образы
echo -e "${YELLOW}Собираем новые образы...${NC}"
docker-compose build --no-cache

if [ $? -ne 0 ]; then
    echo -e "${RED}Ошибка при сборке образов!${NC}"
    exit 1
fi

# Запускаем контейнеры
echo -e "${YELLOW}Запускаем контейнеры...${NC}"
docker-compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}Ошибка при запуске контейнеров!${NC}"
    exit 1
fi

# Проверяем статус контейнеров
echo -e "${YELLOW}Проверяем статус контейнеров...${NC}"
docker-compose ps

# Выводим логи для проверки
echo -e "${YELLOW}Последние логи:${NC}"
docker-compose logs --tail=50

echo -e "${GREEN}Обновление завершено успешно!${NC}" 

docker ps
