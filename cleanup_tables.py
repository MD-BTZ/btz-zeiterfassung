#!/usr/bin/env python3
# cleanup_tables.py
# Removes the old temp_passwords_old table after successful migration and testing

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
        logging.FileHandler('cleanup.log')
    ]
)
logger = logging.getLogger('cleanup')

# Database path
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'attendance.db')

def cleanup_old_tables():
    """Remove old temp_passwords_old table from the database."""
    logger.info("Starting cleanup of old password tables")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check if the old table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='temp_passwords_old'")
        old_table_exists = cursor.fetchone() is not None
        
        if old_table_exists:
            logger.info("Found temp_passwords_old table, removing...")
            cursor.execute("DROP TABLE temp_passwords_old")
            conn.commit()
            logger.info("Successfully removed temp_passwords_old table")
        else:
            logger.info("No temp_passwords_old table found, nothing to do")
        
        # Check if the original temp_passwords table still exists (it shouldn't)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='temp_passwords'")
        if cursor.fetchone() is not None:
            logger.warning("Found original temp_passwords table, this should have been renamed. Removing...")
            cursor.execute("DROP TABLE temp_passwords")
            conn.commit()
            logger.info("Successfully removed original temp_passwords table")
        
        return True
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("WARNING: This script will permanently remove the old password tables.")
    print("Make sure the application is working correctly with the new structure before proceeding.")
    confirmation = input("Type 'YES' to confirm cleanup: ")
    
    if confirmation == "YES":
        if cleanup_old_tables():
            print("Cleanup completed successfully!")
            sys.exit(0)
        else:
            print("Cleanup failed. Check the logs for details.")
            sys.exit(1)
    else:
        print("Cleanup cancelled.")
        sys.exit(0)
