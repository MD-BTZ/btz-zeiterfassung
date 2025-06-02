#!/usr/bin/env python3
"""
Database schema checker and fixer for btz-zeiterfassung.
This script will check for missing columns and tables, and add them if needed.
"""

import sqlite3
import os
import sys

# Path to the database
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'attendance.db')

def check_and_fix_db():
    """Check and fix database schema issues."""
    print(f"Checking database schema in {DATABASE}...")
    
    conn = None
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Step 1: Check and add the arbzg_breaks_enabled column
        print("Step 1: Checking for arbzg_breaks_enabled column...")
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Found columns in user_settings table: {columns}")
        
        if 'arbzg_breaks_enabled' not in columns:
            print("Column arbzg_breaks_enabled not found, adding it...")
            try:
                cursor.execute("ALTER TABLE user_settings ADD COLUMN arbzg_breaks_enabled BOOLEAN DEFAULT 1")
                print("Added arbzg_breaks_enabled column to user_settings table")
                
                # Update existing records
                cursor.execute("UPDATE user_settings SET arbzg_breaks_enabled = 1")
                print("Set default value for arbzg_breaks_enabled in existing records")
                
                # Make sure system-wide settings exist
                cursor.execute("SELECT id FROM user_settings WHERE user_id = 0")
                system_settings = cursor.fetchone()
                
                if system_settings:
                    print("System-wide settings found, updating with ArbZG flag...")
                    cursor.execute("UPDATE user_settings SET arbzg_breaks_enabled = 1 WHERE user_id = 0")
                else:
                    print("No system-wide settings found, creating them...")
                    cursor.execute('''INSERT INTO user_settings 
                                  (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, 
                                   exclude_breaks_from_billing, arbzg_breaks_enabled)
                                  VALUES (0, 1, 30, 1, 1)''')
                
                conn.commit()
                print("Database schema updated successfully!")
            except sqlite3.Error as e:
                print(f"Error updating schema: {e}")
                conn.rollback()
        else:
            print("Column arbzg_breaks_enabled already exists, no action needed")
        
        # Step 2: Check if description column exists in breaks table
        print("\nStep 2: Checking for description column in breaks table...")
        cursor.execute("PRAGMA table_info(breaks)")
        break_columns = [column[1] for column in cursor.fetchall()]
        print(f"Found columns in breaks table: {break_columns}")
        
        if 'description' not in break_columns:
            print("Column description not found, adding it...")
            try:
                cursor.execute("ALTER TABLE breaks ADD COLUMN description TEXT")
                print("Added description column to breaks table")
                conn.commit()
            except sqlite3.Error as e:
                print(f"Error adding column: {e}")
                conn.rollback()
        else:
            print("Column description already exists in breaks table")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"Unexpected error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            
    print("\nDatabase check and fix completed.")

if __name__ == "__main__":
    print("=== BTZ-Zeiterfassung Database Schema Checker ===")
    check_and_fix_db()
    sys.exit(0)
