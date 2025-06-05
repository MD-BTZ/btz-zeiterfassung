#!/usr/bin/env python3
"""
BTZ Zeiterfassung User Data Migration Script
This script migrates the database to support enhanced user management features.
"""

import sqlite3
import os
import logging
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE = 'attendance.db'
TIMEZONE = 'Europe/Berlin'

def get_local_time():
    """Get the current time in CEST (Central European Summer/Winter Time)"""
    return datetime.now(pytz.timezone(TIMEZONE))

def migrate_user_schema():
    """Add new columns to users table"""
    print("Migrating user schema...")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        # Add new columns if they don't exist
        new_columns = {
            'first_name': 'TEXT',
            'last_name': 'TEXT', 
            'employee_id': 'TEXT',
            'user_role': 'TEXT',
            'department': 'TEXT',
            'account_status': 'TEXT',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP'
        }
        
        for column_name, column_def in new_columns.items():
            if column_name not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE users ADD COLUMN {column_name} {column_def}')
                    print(f"✓ Added column: {column_name}")
                except sqlite3.Error as e:
                    print(f"✗ Error adding column {column_name}: {e}")
        
        conn.commit()
        print("Schema migration completed successfully")
        
    except Exception as e:
        print(f"Error during schema migration: {e}")
        conn.rollback()
    finally:
        conn.close()

def migrate_user_data():
    """Update existing users with default values"""
    print("Migrating existing user data...")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Get all users
        cursor.execute("SELECT id, username, is_admin FROM users")
        users = cursor.fetchall()
        
        current_time = get_local_time().strftime('%Y-%m-%d %H:%M:%S')
        
        for user_id, username, is_admin in users:
            # Determine user role
            if is_admin:
                user_role = 'admin'
            elif username == 'admin':
                user_role = 'admin'
            else:
                user_role = 'employee'
            
            # Update user with default values
            cursor.execute('''
                UPDATE users 
                SET user_role = ?, 
                    account_status = 'active',
                    created_at = ?,
                    updated_at = ?
                WHERE id = ?
            ''', (user_role, current_time, current_time, user_id))
            
            print(f"✓ Migrated user: {username} (ID: {user_id}) -> Role: {user_role}")
        
        conn.commit()
        print("User data migration completed successfully")
        
    except Exception as e:
        print(f"Error during user data migration: {e}")
        conn.rollback()
    finally:
        conn.close()

def ensure_user_settings():
    """Ensure all users have user_settings records"""
    print("Ensuring user settings records...")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO user_settings (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing, arbzg_breaks_enabled)
            SELECT u.id, 1, 30, 1, 1
            FROM users u
            WHERE u.id NOT IN (SELECT user_id FROM user_settings WHERE user_id IS NOT NULL)
        ''')
        
        rows_affected = cursor.rowcount
        conn.commit()
        print(f"✓ Created {rows_affected} missing user_settings records")
        
    except Exception as e:
        print(f"Error creating user_settings: {e}")
        conn.rollback()
    finally:
        conn.close()

def ensure_user_consents():
    """Ensure all users have consent records"""
    print("Ensuring user consent records...")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        current_time = get_local_time().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO user_consents (user_id, consent_status, consent_date)
            SELECT u.id, 'pending', ?
            FROM users u
            WHERE u.id NOT IN (SELECT user_id FROM user_consents WHERE user_id IS NOT NULL)
        ''', (current_time,))
        
        rows_affected = cursor.rowcount
        conn.commit()
        print(f"✓ Created {rows_affected} missing consent records")
        
    except Exception as e:
        print(f"Error creating consent records: {e}")
        conn.rollback()
    finally:
        conn.close()

def verify_migration():
    """Verify the migration was successful"""
    print("Verifying migration...")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check users table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        required_columns = ['first_name', 'last_name', 'employee_id', 'user_role', 'department', 'account_status', 'created_at', 'updated_at']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"✗ Missing columns: {missing_columns}")
            return False
        else:
            print("✓ All required columns present")
        
        # Check user data
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_role IS NOT NULL AND user_role != ''")
        users_with_roles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        print(f"✓ Users with roles: {users_with_roles}/{total_users}")
        
        # Check settings and consents
        cursor.execute("SELECT COUNT(*) FROM user_settings")
        settings_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_consents")
        consents_count = cursor.fetchone()[0]
        
        print(f"✓ User settings records: {settings_count}")
        print(f"✓ User consent records: {consents_count}")
        
        return True
        
    except Exception as e:
        print(f"Error during verification: {e}")
        return False
    finally:
        conn.close()

def main():
    """Run the complete migration"""
    print("=" * 60)
    print("BTZ Zeiterfassung User Data Migration")
    print("=" * 60)
    
    if not os.path.exists(DATABASE):
        print(f"Error: Database file '{DATABASE}' not found!")
        return False
    
    try:
        # Run migration steps
        migrate_user_schema()
        migrate_user_data()
        ensure_user_settings()
        ensure_user_consents()
        
        # Verify migration
        if verify_migration():
            print("\n" + "=" * 60)
            print("✓ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("\nEnhanced Features Now Available:")
            print("- Extended user profiles (first name, last name, employee ID)")
            print("- User roles and permissions (employee, supervisor, hr, admin)")
            print("- Department management")
            print("- Account status control")
            print("- Privacy consent tracking")
            print("- System synchronization ready")
            print("\nYou can now use the enhanced user creation form!")
            return True
        else:
            print("\n✗ Migration verification failed!")
            return False
            
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 