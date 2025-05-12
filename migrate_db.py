#!/usr/bin/env python3
# filepath: /home/btz/btz-zeiterfassung/migrate_db.py

import sqlite3
import os
import sys

# Get the database path
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'attendance.db')

def migrate_db():
    """Migrate the database to include new break-related tables and columns."""
    print(f"Migrating database at {DATABASE}")
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Check if migration needed for attendance table
        cursor.execute("PRAGMA table_info(attendance)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add new columns to attendance table if needed
        try:
            if 'has_auto_breaks' not in columns:
                print("Adding 'has_auto_breaks' column to attendance table...")
                cursor.execute("ALTER TABLE attendance ADD COLUMN has_auto_breaks BOOLEAN DEFAULT 0")
            
            if 'billable_minutes' not in columns:
                print("Adding 'billable_minutes' column to attendance table...")
                cursor.execute("ALTER TABLE attendance ADD COLUMN billable_minutes INTEGER")
        except sqlite3.Error as e:
            print(f"Error altering table: {e}")
            # If the previous alter statement failed, try with a different approach
            print("Trying alternative approach to update attendance table...")
            
            # Create a new temporary table with all required columns
            cursor.execute('''
                CREATE TABLE attendance_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    check_in TIMESTAMP,
                    check_out TIMESTAMP,
                    has_auto_breaks BOOLEAN DEFAULT 0,
                    billable_minutes INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            
            # Copy data from old table to new table
            cursor.execute('''
                INSERT INTO attendance_new (id, user_id, check_in, check_out)
                SELECT id, user_id, check_in, check_out FROM attendance
            ''')
            
            # Drop the old table
            cursor.execute("DROP TABLE attendance")
            
            # Rename the new table to the original table name
            cursor.execute("ALTER TABLE attendance_new RENAME TO attendance")
        
        # Create breaks table if it doesn't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS breaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attendance_id INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_minutes INTEGER,
            is_excluded_from_billing BOOLEAN DEFAULT 0,
            is_auto_detected BOOLEAN DEFAULT 0,
            FOREIGN KEY(attendance_id) REFERENCES attendance(id)
        )''')
        
        # Create user settings table if it doesn't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            auto_break_detection_enabled BOOLEAN DEFAULT 0,
            auto_break_threshold_minutes INTEGER DEFAULT 30,
            exclude_breaks_from_billing BOOLEAN DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        
        # Check if system-wide settings exist (user_id = 0)
        cursor.execute("SELECT id FROM user_settings WHERE user_id = 0")
        system_settings = cursor.fetchone()
        
        if not system_settings:
            # Create default system-wide settings
            print("Creating default system-wide break settings...")
            cursor.execute('''INSERT INTO user_settings 
                           (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing)
                           VALUES (0, 1, 30, 1)''')
        
        conn.commit()
        print("Migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"Database migration error: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True

if __name__ == "__main__":
    if migrate_db():
        print("Database is now ready for automatic break detection features.")
        sys.exit(0)
    else:
        print("Database migration failed.")
        sys.exit(1)
