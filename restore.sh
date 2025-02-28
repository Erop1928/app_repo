#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Определяем пути к директориям
DATA_DIR="./pgdata"
UPLOADS_DIR="./uploads"
LOGS_DIR="./logs"

# Создаем директорию для логов
mkdir -p "$LOGS_DIR"

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

if [ "$#" -ne 2 ]; then
    error "Usage: $0 <database_backup.sql> <uploads_backup.tar.gz>"
    exit 1
fi

DB_BACKUP=$1
UPLOADS_BACKUP=$2

if [ ! -f "$DB_BACKUP" ]; then
    error "Database backup file not found: $DB_BACKUP"
    exit 1
fi

if [ ! -f "$UPLOADS_BACKUP" ]; then
    error "Uploads backup file not found: $UPLOADS_BACKUP"
    exit 1
fi

# Восстановление базы данных
log "Restoring database..."
if docker-compose exec -T db psql -U postgres -d app_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" && \
   docker-compose exec -T db psql -U postgres app_db < "$DB_BACKUP"; then
    log "Database restored successfully"
else
    error "Failed to restore database"
    exit 1
fi

# Восстановление файлов
log "Restoring uploads..."
if rm -rf "$UPLOADS_DIR"/* && tar -xzf "$UPLOADS_BACKUP" -C "$UPLOADS_DIR"; then
    log "Files restored successfully"
else
    error "Failed to restore files"
    exit 1
fi

log "Restore completed successfully!" 