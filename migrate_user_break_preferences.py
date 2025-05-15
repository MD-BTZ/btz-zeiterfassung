#!/usr/bin/env python3
# migrate_user_break_preferences.py
# Migration script to add enhanced user break preferences

import sqlite3
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('migration.log')
    ]
)
logger = logging.getLogger('migration')

# Database path
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'attendance.db')

def migrate_db():
    """Add enhanced user break preferences to the database schema"""
    logger.info("Starting user break preferences migration")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist to avoid errors
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # New columns to add for user-specific break preferences
        new_columns = [
            # Preference for break consolidation
            ('prefer_consolidated_breaks', 'BOOLEAN DEFAULT 0'),
            # Preference for break timing strategy
            ('break_timing_strategy', 'TEXT DEFAULT "lunch_priority"'),
            # Minimum break duration (in minutes)
            ('min_break_duration', 'INTEGER DEFAULT 15'),
            # Maximum number of breaks to add per day
            ('max_breaks_per_day', 'INTEGER DEFAULT 3'),
            # Preferred break spacing (in minutes)
            ('preferred_break_spacing', 'INTEGER DEFAULT 120')
        ]
        
        # Add each column if it doesn't exist
        for column_name, column_definition in new_columns:
            if column_name not in columns:
                logger.info(f"Adding column {column_name} to user_settings")
                cursor.execute(f"ALTER TABLE user_settings ADD COLUMN {column_name} {column_definition}")
            else:
                logger.info(f"Column {column_name} already exists in user_settings")
        
        # Commit the changes
        conn.commit()
        logger.info("User break preferences migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
    print("Migration completed successfully. New user break preference fields added to the database.")
