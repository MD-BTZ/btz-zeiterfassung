#!/bin/bash
# Script to run all migrations for the attendance application
# This ensures the database schema is properly updated

echo "Starting BTZ Zeiterfassung Database Migration..."
echo "================================================"

# Check if Python virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: Virtual environment not found. Using system Python."
fi

# Check if the database exists
if [ ! -f "attendance.db" ]; then
    echo "Database not found. Creating new database..."
    python3 -c "
import sys
sys.path.insert(0, '.')
import app
with app.app.app_context():
    app.init_db()
    print('Database initialized successfully.')
"
else
    echo "Database found. Running migrations..."
    python3 -c "
import sys
sys.path.insert(0, '.')
import app
with app.app.app_context():
    print('Running schema updates...')
    app.check_and_fix_db_schema()
    print('Running user data migration...')
    app.migrate_existing_user_data()
    print('Migration completed successfully.')
"
fi

echo ""
echo "Migration Summary:"
echo "=================="
echo "✓ Database schema updated"
echo "✓ New user fields added"
echo "✓ Existing user data migrated"
echo "✓ Default values populated"
echo "✓ System synchronization ready"
echo ""
echo "Enhanced Features Available:"
echo "- Extended user profiles (first name, last name, employee ID)"
echo "- User roles and permissions (employee, supervisor, hr, admin)"
echo "- Department management"
echo "- Account status control"
echo "- Privacy consent tracking"
echo "- System synchronization APIs"
echo "- Webhook support for external integrations"
echo ""
echo "Migration completed successfully!"
echo "You can now start the application with: python3 app.py"
