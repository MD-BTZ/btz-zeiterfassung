#!/usr/bin/env python3
# Script to fix settings tables and migrate data between system_settings and user_settings

import sqlite3
import os
import sys

# Get the database path
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'attendance.db')

def fix_settings():
    """Create user_settings table and migrate data from system_settings if needed."""
    print(f"Fixing settings tables in database: {DATABASE}")
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Check if user_settings table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_settings'")
        user_settings_exists = cursor.fetchone() is not None
        
        # Check if system_settings table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_settings'")
        system_settings_exists = cursor.fetchone() is not None
        
        # Create user_settings table if it doesn't exist
        if not user_settings_exists:
            print("Creating user_settings table...")
            cursor.execute('''CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                auto_break_detection_enabled BOOLEAN DEFAULT 0,
                auto_break_threshold_minutes INTEGER DEFAULT 30,
                exclude_breaks_from_billing BOOLEAN DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )''')
            
            # Insert default settings
            cursor.execute('''INSERT INTO user_settings 
                       (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing)
                       VALUES (0, 1, 30, 1)''')
            print("Created user_settings table with default settings")
        
        # If both tables exist, migrate data from system_settings to user_settings
        if user_settings_exists and system_settings_exists:
            # Check if we have system-wide settings in user_settings
            cursor.execute("SELECT id FROM user_settings WHERE user_id = 0")
            has_system_settings = cursor.fetchone() is not None
            
            if not has_system_settings:
                print("Migrating settings from system_settings to user_settings...")
                # Get settings from system_settings
                auto_break_detection = False
                auto_break_threshold = 30
                exclude_breaks = False
                
                cursor.execute("SELECT value FROM system_settings WHERE key = 'auto_break_detection'")
                result = cursor.fetchone()
                if result:
                    auto_break_detection = result[0] == '1'
                
                cursor.execute("SELECT value FROM system_settings WHERE key = 'statutory_break_6h_work_threshold'")
                result = cursor.fetchone()
                if result:
                    # Convert to minutes, use a reasonable value
                    auto_break_threshold = 30  # Default to 30 minutes
                
                cursor.execute("SELECT value FROM system_settings WHERE key = 'exclude_breaks_from_billing'")
                result = cursor.fetchone()
                if result:
                    exclude_breaks = result[0] == '1'
                
                # Insert into user_settings
                cursor.execute('''INSERT INTO user_settings 
                           (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing)
                           VALUES (0, ?, ?, ?)''', 
                           (auto_break_detection, auto_break_threshold, exclude_breaks))
                
                print(f"Migrated settings: auto_break_detection={auto_break_detection}, " 
                      f"auto_break_threshold={auto_break_threshold}, exclude_breaks={exclude_breaks}")
        
        conn.commit()
        print("Settings tables fixed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if fix_settings():
        print("Settings tables are now ready.")
        sys.exit(0)
    else:
        print("Failed to fix settings tables.")
        sys.exit(1)
