#!/bin/bash

# Database Backup Script for Expense Tracker
# This script provides simplified backup operations

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Default values
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_DATABASE="${MYSQL_DATABASE:-expense_tracker}"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_dependencies() {
    local missing_deps=()
    
    if ! command -v mysqldump &> /dev/null; then
        missing_deps+=("mysqldump")
    fi
    
    if ! command -v mysql &> /dev/null; then
        missing_deps+=("mysql")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_error "Please install MySQL client tools"
        exit 1
    fi
}

create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    fi
}

backup_database() {
    local backup_name="$1"
    local compress="$2"
    
    if [ -z "$backup_name" ]; then
        backup_name="expense_tracker_backup_$(date +%Y%m%d_%H%M%S)"
    fi
    
    create_backup_dir
    
    local backup_file="$BACKUP_DIR/${backup_name}.sql"
    if [ "$compress" = "true" ]; then
        backup_file="${backup_file}.gz"
    fi
    
    log_info "Creating database backup: $backup_file"
    
    # Build mysqldump command
    local cmd="mysqldump"
    cmd="$cmd --host=$MYSQL_HOST"
    cmd="$cmd --port=$MYSQL_PORT" 
    cmd="$cmd --user=$MYSQL_USER"
    cmd="$cmd --single-transaction"
    cmd="$cmd --routines"
    cmd="$cmd --triggers"
    cmd="$cmd --complete-insert"
    cmd="$cmd --extended-insert"
    cmd="$cmd --add-drop-table"
    cmd="$cmd --create-options"
    cmd="$cmd --disable-keys"
    cmd="$cmd --set-charset"
    
    if [ -n "$MYSQL_PASSWORD" ]; then
        cmd="$cmd --password=$MYSQL_PASSWORD"
    fi
    
    cmd="$cmd $MYSQL_DATABASE"
    
    # Execute backup
    if [ "$compress" = "true" ]; then
        eval "$cmd" | gzip > "$backup_file"
    else
        eval "$cmd" > "$backup_file"
    fi
    
    if [ $? -eq 0 ]; then
        local file_size=$(du -h "$backup_file" | cut -f1)
        log_success "Backup created successfully!"
        log_info "File: $backup_file"
        log_info "Size: $file_size"
    else
        log_error "Backup failed!"
        rm -f "$backup_file"
        exit 1
    fi
}

restore_database() {
    local backup_file="$1"
    local force="$2"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    if [ "$force" != "true" ]; then
        log_warning "This will replace the current database '$MYSQL_DATABASE'"
        log_info "Backup file: $backup_file"
        echo -n "Are you sure you want to proceed? (yes/no): "
        read -r confirm
        if [ "$confirm" != "yes" ]; then
            log_info "Restore cancelled."
            exit 0
        fi
    fi
    
    log_info "Restoring database from: $backup_file"
    
    # Build mysql command
    local cmd="mysql"
    cmd="$cmd --host=$MYSQL_HOST"
    cmd="$cmd --port=$MYSQL_PORT"
    cmd="$cmd --user=$MYSQL_USER"
    
    if [ -n "$MYSQL_PASSWORD" ]; then
        cmd="$cmd --password=$MYSQL_PASSWORD"
    fi
    
    cmd="$cmd $MYSQL_DATABASE"
    
    # Execute restore
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" | eval "$cmd"
    else
        eval "$cmd" < "$backup_file"
    fi
    
    if [ $? -eq 0 ]; then
        log_success "Database restored successfully!"
    else
        log_error "Restore failed!"
        exit 1
    fi
}

list_backups() {
    if [ ! -d "$BACKUP_DIR" ]; then
        log_info "No backup directory found: $BACKUP_DIR"
        return
    fi
    
    local backups=$(find "$BACKUP_DIR" -name "*.sql" -o -name "*.sql.gz" | sort -r)
    
    if [ -z "$backups" ]; then
        log_info "No backups found in: $BACKUP_DIR"
        return
    fi
    
    echo -e "${BLUE}📋 Available backups:${NC}"
    echo "----------------------------------------"
    
    while IFS= read -r backup; do
        local filename=$(basename "$backup")
        local size=$(du -h "$backup" | cut -f1)
        local date=$(date -r "$backup" "+%Y-%m-%d %H:%M:%S")
        
        echo "📁 $filename"
        echo "   📅 $date"
        echo "   💾 $size"
        echo "   📂 $backup"
        echo
    done <<< "$backups"
}

cleanup_backups() {
    local retention_days="${BACKUP_RETENTION_DAYS:-30}"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_info "No backup directory found: $BACKUP_DIR"
        return
    fi
    
    log_info "Cleaning up backups older than $retention_days days..."
    
    local removed=0
    while IFS= read -r backup; do
        if [ -f "$backup" ]; then
            rm -f "$backup"
            log_info "Removed: $(basename "$backup")"
            ((removed++))
        fi
    done < <(find "$BACKUP_DIR" -name "*.sql*" -mtime +$retention_days)
    
    log_success "Cleaned up $removed old backups"
}

show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  backup [NAME] [--compress]  Create database backup"
    echo "  restore FILE [--force]     Restore database from backup"
    echo "  list                       List available backups"
    echo "  cleanup                    Remove old backups"
    echo
    echo "Examples:"
    echo "  $0 backup                           # Create timestamped backup"
    echo "  $0 backup my_backup --compress      # Create compressed backup"
    echo "  $0 restore backups/backup.sql       # Restore from backup"
    echo "  $0 list                             # List all backups"
    echo "  $0 cleanup                          # Clean old backups"
    echo
    echo "Environment Variables:"
    echo "  MYSQL_HOST         Database host (default: localhost)"
    echo "  MYSQL_PORT         Database port (default: 3306)"
    echo "  MYSQL_USER         Database user (default: root)"
    echo "  MYSQL_PASSWORD     Database password"
    echo "  MYSQL_DATABASE     Database name (default: expense_tracker)"
    echo "  BACKUP_DIR         Backup directory (default: ./backups)"
    echo "  BACKUP_RETENTION_DAYS  Backup retention in days (default: 30)"
}

# Main script logic
main() {
    check_dependencies
    
    case "${1:-}" in
        backup)
            local backup_name="$2"
            local compress="false"
            
            # Check for compress flag
            for arg in "$@"; do
                if [ "$arg" = "--compress" ]; then
                    compress="true"
                    break
                fi
            done
            
            backup_database "$backup_name" "$compress"
            ;;
        restore)
            local backup_file="$2"
            local force="false"
            
            if [ -z "$backup_file" ]; then
                log_error "Backup file required for restore"
                show_usage
                exit 1
            fi
            
            # Check for force flag
            for arg in "$@"; do
                if [ "$arg" = "--force" ]; then
                    force="true"
                    break
                fi
            done
            
            restore_database "$backup_file" "$force"
            ;;
        list)
            list_backups
            ;;
        cleanup)
            cleanup_backups
            ;;
        help|--help|-h)
            show_usage
            ;;
        "")
            log_error "No command specified"
            show_usage
            exit 1
            ;;
        *)
            log_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
