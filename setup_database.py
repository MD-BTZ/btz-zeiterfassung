#!/usr/bin/env python3
"""
BTZ Zeiterfassung Database Setup and Management Script
This script provides comprehensive database management functionality.
"""

import sqlite3
import os
import sys
import logging
import argparse
from datetime import datetime
import pytz
import bcrypt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE = 'attendance.db'
TIMEZONE = 'Europe/Berlin'

def get_local_time():
    """Get the current time in CEST (Central European Summer/Winter Time)"""
    return datetime.now(pytz.timezone(TIMEZONE))

def database_exists():
    """Check if database file exists"""
    return os.path.exists(DATABASE)

def backup_database():
    """Create a backup of the existing database"""
    if database_exists():
        timestamp = get_local_time().strftime('%Y%m%d_%H%M%S')
        backup_name = f"attendance_backup_{timestamp}.db"
        
        try:
            import shutil
            shutil.copy2(DATABASE, backup_name)
            print(f"✓ Database backed up to: {backup_name}")
            return backup_name
        except Exception as e:
            print(f"✗ Failed to create backup: {e}")
            return None
    return None

def create_fresh_database():
    """Create a completely new database with all tables"""
    print("Creating fresh database...")
    
    if database_exists():
        backup_database()
        os.remove(DATABASE)
        print("✓ Removed existing database")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Users table with all enhanced fields
        cursor.execute('''CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            first_name TEXT,
            last_name TEXT,
            employee_id TEXT,
            user_role TEXT DEFAULT 'employee',
            department TEXT,
            account_status TEXT DEFAULT 'active',
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Attendance table
        cursor.execute('''CREATE TABLE attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            check_in TIMESTAMP,
            check_out TIMESTAMP,
            has_auto_breaks BOOLEAN DEFAULT 0,
            billable_minutes INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        
        # Breaks table
        cursor.execute('''CREATE TABLE breaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attendance_id INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_minutes INTEGER,
            is_excluded_from_billing BOOLEAN DEFAULT 0,
            is_auto_detected BOOLEAN DEFAULT 0,
            description TEXT,
            FOREIGN KEY(attendance_id) REFERENCES attendance(id)
        )''')
        
        # User settings table
        cursor.execute('''CREATE TABLE user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            auto_break_detection_enabled BOOLEAN DEFAULT 0,
            auto_break_threshold_minutes INTEGER DEFAULT 30,
            exclude_breaks_from_billing BOOLEAN DEFAULT 0,
            arbzg_breaks_enabled BOOLEAN DEFAULT 1,
            lunch_period_start_hour INTEGER DEFAULT 11,
            lunch_period_start_minute INTEGER DEFAULT 30,
            lunch_period_end_hour INTEGER DEFAULT 14,
            lunch_period_end_minute INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        
        # User consents table
        cursor.execute('''CREATE TABLE user_consents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            consent_status TEXT,
            consent_date TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        
        # Data deletion log table
        cursor.execute('''CREATE TABLE data_deletion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            deletion_date TIMESTAMP,
            record_count INTEGER
        )''')
        
        # Deletion requests table
        cursor.execute('''CREATE TABLE deletion_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            request_date TIMESTAMP,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            admin_notes TEXT,
            processed_by INTEGER,
            processed_date TIMESTAMP,
            original_username TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(processed_by) REFERENCES users(id)
        )''')
        
        # Temporary passwords table
        cursor.execute('''CREATE TABLE temp_passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            temp_password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        
        # Create default admin user
        create_default_admin(cursor)
        
        # Create system-wide settings
        cursor.execute('''INSERT INTO user_settings 
                      (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing, arbzg_breaks_enabled)
                      VALUES (0, 1, 30, 1, 1)''')
        
        conn.commit()
        print("✓ Fresh database created successfully")
        
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
    
    return True

def create_default_admin(cursor):
    """Create default admin user"""
    try:
        # Check if admin already exists
        cursor.execute('SELECT * FROM users WHERE username=?', ("admin",))
        if cursor.fetchone() is None:
            hashed_password = bcrypt.generate_password_hash("admin").decode('utf-8')
            current_time = get_local_time().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''INSERT INTO users 
                          (username, password, is_admin, user_role, account_status, created_at, updated_at) 
                          VALUES (?, ?, 1, 'admin', 'active', ?, ?)''', 
                          ("admin", hashed_password, current_time, current_time))
            
            print("✓ Default admin user created (username: admin, password: admin)")
        else:
            print("✓ Admin user already exists")
    except Exception as e:
        print(f"✗ Error creating admin user: {e}")

def update_existing_database():
    """Update existing database with new schema"""
    print("Updating existing database schema...")
    
    if not database_exists():
        print("✗ Database does not exist. Use --create to create a new one.")
        return False
    
    # Create backup first
    backup_database()
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check and add missing columns to users table
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        user_columns_to_add = {
            'is_admin': 'BOOLEAN DEFAULT 0',
            'first_name': 'TEXT',
            'last_name': 'TEXT',
            'employee_id': 'TEXT',
            'user_role': 'TEXT DEFAULT "employee"',
            'department': 'TEXT',
            'account_status': 'TEXT DEFAULT "active"',
            'last_login': 'TIMESTAMP',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for column_name, column_def in user_columns_to_add.items():
            if column_name not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE users ADD COLUMN {column_name} {column_def}')
                    print(f"✓ Added column: users.{column_name}")
                except sqlite3.Error as e:
                    print(f"✗ Error adding column {column_name}: {e}")
        
        # Update existing users with default values
        current_time = get_local_time().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("UPDATE users SET user_role = 'employee' WHERE user_role IS NULL OR user_role = ''")
        cursor.execute("UPDATE users SET user_role = 'admin' WHERE is_admin = 1")
        cursor.execute("UPDATE users SET account_status = 'active' WHERE account_status IS NULL OR account_status = ''")
        cursor.execute("UPDATE users SET created_at = ? WHERE created_at IS NULL OR created_at = ''", (current_time,))
        cursor.execute("UPDATE users SET updated_at = ? WHERE updated_at IS NULL OR updated_at = ''", (current_time,))
        
        # Ensure admin user exists
        create_default_admin(cursor)
        
        # Check and update other tables
        update_user_settings_table(cursor)
        update_breaks_table(cursor)
        update_deletion_requests_table(cursor)
        create_missing_tables(cursor)
        
        # Ensure all users have settings and consent records
        ensure_user_records(cursor)
        
        conn.commit()
        print("✓ Database schema updated successfully")
        
    except Exception as e:
        print(f"✗ Error updating database: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
    
    return True

def update_user_settings_table(cursor):
    """Update user_settings table with missing columns"""
    cursor.execute("PRAGMA table_info(user_settings)")
    columns = [column[1] for column in cursor.fetchall()]
    
    settings_columns_to_add = {
        'arbzg_breaks_enabled': 'BOOLEAN DEFAULT 1',
        'lunch_period_start_hour': 'INTEGER DEFAULT 11',
        'lunch_period_start_minute': 'INTEGER DEFAULT 30',
        'lunch_period_end_hour': 'INTEGER DEFAULT 14',
        'lunch_period_end_minute': 'INTEGER DEFAULT 0'
    }
    
    for column_name, column_def in settings_columns_to_add.items():
        if column_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE user_settings ADD COLUMN {column_name} {column_def}")
                print(f"✓ Added column: user_settings.{column_name}")
            except sqlite3.Error as e:
                print(f"✗ Error adding column {column_name}: {e}")

def update_breaks_table(cursor):
    """Update breaks table with missing columns"""
    cursor.execute("PRAGMA table_info(breaks)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'description' not in columns:
        try:
            cursor.execute("ALTER TABLE breaks ADD COLUMN description TEXT")
            print("✓ Added column: breaks.description")
        except sqlite3.Error as e:
            print(f"✗ Error adding description column: {e}")

def update_deletion_requests_table(cursor):
    """Update deletion_requests table with missing columns"""
    cursor.execute("PRAGMA table_info(deletion_requests)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'original_username' not in columns:
        try:
            cursor.execute("ALTER TABLE deletion_requests ADD COLUMN original_username TEXT")
            print("✓ Added column: deletion_requests.original_username")
        except sqlite3.Error as e:
            print(f"✗ Error adding original_username column: {e}")

def create_missing_tables(cursor):
    """Create any missing tables"""
    # Check if temp_passwords table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='temp_passwords'")
    if not cursor.fetchone():
        try:
            cursor.execute('''CREATE TABLE temp_passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                temp_password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )''')
            print("✓ Created table: temp_passwords")
        except sqlite3.Error as e:
            print(f"✗ Error creating temp_passwords table: {e}")

def ensure_user_records(cursor):
    """Ensure all users have settings and consent records"""
    try:
        # Create missing user_settings records
        cursor.execute('''
            INSERT INTO user_settings (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing, arbzg_breaks_enabled)
            SELECT u.id, 1, 30, 1, 1
            FROM users u
            WHERE u.id NOT IN (SELECT user_id FROM user_settings WHERE user_id IS NOT NULL)
        ''')
        settings_created = cursor.rowcount
        if settings_created > 0:
            print(f"✓ Created {settings_created} missing user_settings records")
        
        # Create missing consent records
        current_time = get_local_time().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO user_consents (user_id, consent_status, consent_date)
            SELECT u.id, 'pending', ?
            FROM users u
            WHERE u.id NOT IN (SELECT user_id FROM user_consents WHERE user_id IS NOT NULL)
        ''', (current_time,))
        consents_created = cursor.rowcount
        if consents_created > 0:
            print(f"✓ Created {consents_created} missing consent records")
        
    except sqlite3.Error as e:
        print(f"✗ Error ensuring user records: {e}")

def verify_database():
    """Verify database integrity and structure"""
    print("Verifying database structure...")
    
    if not database_exists():
        print("✗ Database does not exist")
        return False
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check all required tables exist
        required_tables = [
            'users', 'attendance', 'breaks', 'user_settings', 
            'user_consents', 'data_deletion_log', 'deletion_requests', 'temp_passwords'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        if missing_tables:
            print(f"✗ Missing tables: {missing_tables}")
            return False
        else:
            print("✓ All required tables present")
        
        # Check users table structure
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [column[1] for column in cursor.fetchall()]
        
        required_user_columns = [
            'id', 'username', 'password', 'is_admin', 'first_name', 'last_name',
            'employee_id', 'user_role', 'department', 'account_status', 'last_login',
            'created_at', 'updated_at'
        ]
        
        missing_user_columns = [col for col in required_user_columns if col not in user_columns]
        if missing_user_columns:
            print(f"✗ Missing user columns: {missing_user_columns}")
            return False
        else:
            print("✓ Users table structure complete")
        
        # Check data integrity
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_settings WHERE user_id > 0")
        settings_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_consents")
        consents_count = cursor.fetchone()[0]
        
        print(f"✓ Database statistics:")
        print(f"  - Users: {user_count}")
        print(f"  - User settings: {settings_count}")
        print(f"  - User consents: {consents_count}")
        
        # Check admin user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            print("⚠️  No admin users found")
        else:
            print(f"✓ Admin users: {admin_count}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error verifying database: {e}")
        return False
    finally:
        conn.close()

def show_database_info():
    """Show detailed database information"""
    if not database_exists():
        print("Database does not exist")
        return
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        print("Database Information:")
        print("=" * 50)
        
        # File info
        file_size = os.path.getsize(DATABASE)
        print(f"File: {DATABASE}")
        print(f"Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        # Tables info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables: {len(tables)}")
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count} records")
        
        # Users info
        print("\nUsers:")
        cursor.execute("SELECT username, user_role, account_status, is_admin FROM users")
        users = cursor.fetchall()
        for user in users:
            username, role, status, is_admin = user
            admin_flag = " (ADMIN)" if is_admin else ""
            print(f"  - {username}: {role} - {status}{admin_flag}")
        
    except Exception as e:
        print(f"Error getting database info: {e}")
    finally:
        conn.close()

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='BTZ Zeiterfassung Database Management')
    parser.add_argument('--create', action='store_true', help='Create a fresh database')
    parser.add_argument('--update', action='store_true', help='Update existing database schema')
    parser.add_argument('--verify', action='store_true', help='Verify database structure')
    parser.add_argument('--info', action='store_true', help='Show database information')
    parser.add_argument('--backup', action='store_true', help='Create database backup')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BTZ Zeiterfassung Database Management")
    print("=" * 60)
    
    if args.create:
        success = create_fresh_database()
        if success:
            verify_database()
        return 0 if success else 1
    
    elif args.update:
        success = update_existing_database()
        if success:
            verify_database()
        return 0 if success else 1
    
    elif args.verify:
        success = verify_database()
        return 0 if success else 1
    
    elif args.info:
        show_database_info()
        return 0
    
    elif args.backup:
        backup_file = backup_database()
        return 0 if backup_file else 1
    
    else:
        # Auto-detect what to do
        if not database_exists():
            print("No database found. Creating fresh database...")
            success = create_fresh_database()
        else:
            print("Database found. Updating schema...")
            success = update_existing_database()
        
        if success:
            verify_database()
        
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 