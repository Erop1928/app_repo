#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Функция для вывода справки
show_help() {
    echo "Использование: $0 [опции]"
    echo "Опции:"
    echo "  -h, --help          Показать эту справку"
    echo "  -c, --clean         Полная очистка с удалением томов"
    echo "  -r, --rebuild       Пересобрать образы"
}

# Парсим аргументы
CLEAN=false
REBUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -r|--rebuild)
            REBUILD=true
            shift
            ;;
        *)
            echo -e "${RED}Неизвестный параметр: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

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

# Если указан флаг clean, удаляем тома
if [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}Удаляем тома...${NC}"
    docker volume rm $(docker volume ls -q | grep app_repo) || true
fi

# Если указан флаг rebuild или clean, удаляем старые образы
if [ "$REBUILD" = true ] || [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}Удаляем старые образы...${NC}"
    docker image prune -f
    BUILD_ARG="--no-cache"
else
    BUILD_ARG=""
fi

# Собираем новые образы
echo -e "${YELLOW}Собираем новые образы...${NC}"
docker-compose build $BUILD_ARG

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
