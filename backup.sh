#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Определяем пути к директориям
DATA_DIR="./pgdata"
UPLOADS_DIR="./uploads"
BACKUPS_DIR="./backups"
LOGS_DIR="./logs"

# Создаем необходимые директории
mkdir -p "$BACKUPS_DIR" "$LOGS_DIR"

# Определяем текущий лог файл
CURRENT_LOG="$LOGS_DIR/$(date +%Y%m%d_%H).log"

# Функция для логирования
write_log() {
    local level=$1
    local message=$2
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    local log_message="[$timestamp] $level: $message"
    
    # Проверяем, нужно ли создать новый лог файл
    local new_log="$LOGS_DIR/$(date +%Y%m%d_%H).log"
    if [ "$new_log" != "$CURRENT_LOG" ]; then
        CURRENT_LOG="$new_log"
    fi
    
    # Записываем в лог файл
    echo "$log_message" >> "$CURRENT_LOG"
    
    # Выводим в консоль с цветом
    case $level in
        "INFO")
            echo -e "${GREEN}$log_message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}$log_message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}$log_message${NC}"
            ;;
        *)
            echo "$log_message"
            ;;
    esac
}

# Функции для разных уровней логирования
log() {
    write_log "INFO" "$1"
}

error() {
    write_log "ERROR" "$1"
}

warning() {
    write_log "WARNING" "$1"
}

# Текущая дата для имени файла
DATE=$(date +%Y%m%d_%H%M%S)

# Бэкап базы данных
log "Creating database backup..."
if docker-compose exec -T db pg_dump -U postgres app_db > "$BACKUPS_DIR/db_backup_$DATE.sql"; then
    log "Database backup created: $BACKUPS_DIR/db_backup_$DATE.sql"
else
    error "Failed to create database backup"
    exit 1
fi

# Бэкап загруженных файлов
log "Creating uploads backup..."
if tar -czf "$BACKUPS_DIR/uploads_backup_$DATE.tar.gz" -C "$UPLOADS_DIR" .; then
    log "Uploads backup created: $BACKUPS_DIR/uploads_backup_$DATE.tar.gz"
else
    error "Failed to create uploads backup"
    exit 1
fi

log "Backup completed successfully" 