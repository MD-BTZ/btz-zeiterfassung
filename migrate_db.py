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
        cursor.execute("""CREATE TABLE IF NOT EXISTS breaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attendance_id INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_minutes INTEGER,
            is_excluded_from_billing BOOLEAN DEFAULT 0,
            is_auto_detected BOOLEAN DEFAULT 0,
            description TEXT, -- Added description column
            FOREIGN KEY(attendance_id) REFERENCES attendance(id)
        )""")

        # Check and add description column to breaks table if it wasn't created by the above
        # (e.g. if table already existed without it)
        cursor.execute("PRAGMA table_info(breaks)")
        breaks_columns = [column[1] for column in cursor.fetchall()]
        if 'description' not in breaks_columns:
            print("Adding 'description' column to breaks table...")
            cursor.execute("ALTER TABLE breaks ADD COLUMN description TEXT")
        
        # Drop the old user_settings table if it exists, as we are replacing it
        # with a more flexible key-value system_settings table.
        cursor.execute("DROP TABLE IF EXISTS user_settings")
        print("Dropped old 'user_settings' table if it existed.")

        # Create system_settings table if it doesn't exist (key-value store)
        cursor.execute('''CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        print("Ensured 'system_settings' table exists.")

        # Populate system_settings with default values if they don't exist
        default_settings = {
            'auto_break_detection': '1',  # '1' for true, '0' for false
            'exclude_breaks_from_billing': '1', # '1' for true, '0' for false
            'statutory_break_6h_work_threshold': '360', # minutes (work > 6 hours)
            'statutory_break_6h_duration': '30',        # minutes
            'statutory_break_9h_work_threshold': '540', # minutes (work > 9 hours)
            'statutory_break_9h_duration': '45'         # minutes
        }

        for key, value in default_settings.items():
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)", (key, value))
        print(f"Populated 'system_settings' with default values: {default_settings}")
        
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
