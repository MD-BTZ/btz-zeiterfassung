# BTZ Zeiterfassung Database Management

This document describes the comprehensive database management system for the BTZ Zeiterfassung application.

## Overview

The BTZ Zeiterfassung application uses SQLite as its database backend. We provide several scripts and tools to automatically create, update, and manage the database schema and data.

## Database Management Scripts

### 1. `setup_database.py` - Main Database Management Script

The primary database management script that provides comprehensive functionality:

```bash
python setup_database.py [options]
```

**Options:**
- `--create` - Create a fresh database (backs up existing)
- `--update` - Update existing database schema
- `--verify` - Verify database structure and integrity
- `--info` - Show detailed database information
- `--backup` - Create a backup of the current database

**Auto-detection:** If run without options, it automatically detects whether to create or update the database.

### 2. `db.sh` - User-Friendly Wrapper Script

A simple wrapper script with colored output and easy commands:

```bash
./db.sh [command]
```

**Commands:**
- `create` - Create a fresh database (backs up existing)
- `update` - Update existing database schema
- `verify` - Verify database structure and integrity
- `info` - Show detailed database information
- `backup` - Create a backup of the current database
- `migrate` - Run the old migration script (legacy)
- `help` - Show help message

### 3. `run_migrations.sh` - Legacy Migration Script

The original migration script (still available for compatibility):

```bash
bash run_migrations.sh
```

### 4. `migrate_user_data.py` - Standalone Migration Script

Standalone script for migrating user data:

```bash
python migrate_user_data.py
```

## Database Schema

The application uses the following tables:

### Core Tables

1. **users** - User accounts and profiles
   - Basic auth: `id`, `username`, `password`, `is_admin`
   - Profile: `first_name`, `last_name`, `employee_id`
   - Role management: `user_role`, `department`, `account_status`
   - Timestamps: `last_login`, `created_at`, `updated_at`

2. **attendance** - Time tracking records
   - `id`, `user_id`, `check_in`, `check_out`
   - `has_auto_breaks`, `billable_minutes`

3. **breaks** - Break periods within attendance records
   - `id`, `attendance_id`, `start_time`, `end_time`
   - `duration_minutes`, `is_excluded_from_billing`
   - `is_auto_detected`, `description`

### Configuration Tables

4. **user_settings** - User preferences and settings
   - Break detection: `auto_break_detection_enabled`, `auto_break_threshold_minutes`
   - Billing: `exclude_breaks_from_billing`, `arbzg_breaks_enabled`
   - Lunch periods: `lunch_period_start_hour`, `lunch_period_start_minute`, etc.

5. **user_consents** - GDPR compliance and privacy consents
   - `id`, `user_id`, `consent_status`, `consent_date`

### Administrative Tables

6. **data_deletion_log** - Log of data deletions
   - `id`, `user_id`, `deletion_date`, `record_count`

7. **deletion_requests** - User data deletion requests
   - `id`, `user_id`, `request_date`, `reason`, `status`
   - `admin_notes`, `processed_by`, `processed_date`, `original_username`

8. **temp_passwords** - Temporary password storage for user datasheets
   - `id`, `user_id`, `temp_password`, `created_at`

## Usage Examples

### Initial Setup (New Installation)

```bash
# Create a fresh database
./db.sh create

# Or using Python directly
python setup_database.py --create
```

### Updating Existing Installation

```bash
# Update database schema
./db.sh update

# Or using Python directly
python setup_database.py --update
```

### Maintenance Operations

```bash
# Verify database integrity
./db.sh verify

# Show database information
./db.sh info

# Create backup
./db.sh backup
```

### Auto-Detection

```bash
# Automatically detect what to do
./db.sh auto
# or
python setup_database.py
```

## Features

### ✅ **Automatic Schema Updates**
- Detects missing columns and adds them automatically
- Updates existing data with default values
- Maintains backward compatibility

### ✅ **Data Safety**
- Automatic backups before any destructive operations
- Rollback capability on errors
- Verification of database integrity

### ✅ **User Management**
- Creates default admin user (username: `admin`, password: `admin`)
- Ensures all users have required settings and consent records
- Supports enhanced user profiles with roles and departments

### ✅ **GDPR Compliance**
- Automatic consent record creation
- Data deletion logging
- Privacy-compliant user management

### ✅ **Comprehensive Validation**
- Verifies all required tables exist
- Checks column structure and data types
- Validates data integrity and relationships

## Database File Management

### Location
- Database file: `attendance.db`
- Backups: `attendance_backup_YYYYMMDD_HHMMSS.db`

### Backup Strategy
- Automatic backups before schema changes
- Manual backup command available
- Timestamped backup files for easy identification

## Integration with Application

### Application Startup
The application automatically runs schema checks on startup via:
- `init_db()` function in `app.py`
- `check_and_fix_db_schema()` function
- `migrate_existing_user_data()` function

### Development Workflow
1. Make schema changes in the management scripts
2. Test with `./db.sh verify`
3. Apply updates with `./db.sh update`
4. Verify with `./db.sh verify`

## Troubleshooting

### Common Issues

**Database locked error:**
```bash
# Stop the application first, then run:
./db.sh verify
```

**Missing columns:**
```bash
# Update the schema:
./db.sh update
```

**Corrupted database:**
```bash
# Create fresh database (backs up existing):
./db.sh create
```

### Error Recovery

1. **Check database integrity:**
   ```bash
   ./db.sh verify
   ```

2. **Create backup:**
   ```bash
   ./db.sh backup
   ```

3. **Update schema:**
   ```bash
   ./db.sh update
   ```

4. **If all else fails, recreate:**
   ```bash
   ./db.sh create
   ```

## Advanced Usage

### Custom Admin User
To create a custom admin user after database creation:

```python
# Connect to database and run:
import bcrypt
hashed_password = bcrypt.generate_password_hash("your_password").decode('utf-8')
cursor.execute('''INSERT INTO users 
              (username, password, is_admin, user_role, account_status) 
              VALUES (?, ?, 1, 'admin', 'active')''', 
              ("your_username", hashed_password))
```

### Schema Customization
To add custom columns, modify the `setup_database.py` script:

```python
# Add to user_columns_to_add dictionary
user_columns_to_add = {
    'custom_field': 'TEXT DEFAULT "default_value"',
    # ... existing columns
}
```

## Security Considerations

- Default admin password should be changed immediately after setup
- Database file should have appropriate file permissions
- Backups should be stored securely
- Regular verification of database integrity recommended

## Performance

- SQLite is suitable for small to medium installations
- For large installations, consider migration to PostgreSQL
- Regular VACUUM operations recommended for optimal performance

## Support

For issues with database management:
1. Check this documentation
2. Run `./db.sh verify` to diagnose issues
3. Check application logs in `app.log`
4. Create backup before attempting fixes 