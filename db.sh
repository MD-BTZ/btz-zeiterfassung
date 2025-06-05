#!/bin/bash
# BTZ Zeiterfassung Database Management Wrapper
# Simple wrapper script for database operations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_SCRIPT="$SCRIPT_DIR/setup_database.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}BTZ Zeiterfassung Database Tool${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Check if Python script exists
if [ ! -f "$DB_SCRIPT" ]; then
    print_error "Database script not found: $DB_SCRIPT"
    exit 1
fi

# Check if virtual environment exists and activate it
if [ -d "$SCRIPT_DIR/venv" ]; then
    print_status "Activating virtual environment..."
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Function to show usage
show_usage() {
    print_header
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  create    - Create a fresh database (backs up existing)"
    echo "  update    - Update existing database schema"
    echo "  verify    - Verify database structure and integrity"
    echo "  info      - Show detailed database information"
    echo "  backup    - Create a backup of the current database"
    echo "  migrate   - Run the old migration script (legacy)"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 create     # Create new database"
    echo "  $0 update     # Update existing database"
    echo "  $0 info       # Show database info"
    echo ""
}

# Main command handling
case "${1:-help}" in
    "create")
        print_header
        print_status "Creating fresh database..."
        python "$DB_SCRIPT" --create
        ;;
    "update")
        print_header
        print_status "Updating database schema..."
        python "$DB_SCRIPT" --update
        ;;
    "verify")
        print_header
        print_status "Verifying database..."
        python "$DB_SCRIPT" --verify
        ;;
    "info")
        print_header
        python "$DB_SCRIPT" --info
        ;;
    "backup")
        print_header
        print_status "Creating database backup..."
        python "$DB_SCRIPT" --backup
        ;;
    "migrate")
        print_header
        print_status "Running legacy migration script..."
        if [ -f "$SCRIPT_DIR/run_migrations.sh" ]; then
            bash "$SCRIPT_DIR/run_migrations.sh"
        else
            print_error "Legacy migration script not found"
            exit 1
        fi
        ;;
    "auto")
        print_header
        print_status "Auto-detecting database operation..."
        python "$DB_SCRIPT"
        ;;
    "help"|"-h"|"--help"|"")
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac 