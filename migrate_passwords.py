#!/usr/bin/env python3
# migrate_passwords.py
# Migrates passwords from temp_passwords table to users table

import sqlite3
import os
import sys
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('migration.log')
    ]
)
logger = logging.getLogger('password_migration')

# Database path
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'attendance.db')

def migrate_passwords():
    """Merge the temp_passwords table into the users table."""
    logger.info("Starting password migration from temp_passwords to users table")
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Backup the database before making changes
    backup_file = f"attendance_backup_{int(time.time())}.db"
    backup_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), backup_file)
    
    try:
        # Create a backup
        with open(backup_path, 'wb') as backup_file:
            for data in conn.iterdump():
                backup_file.write(f"{data}\n".encode('utf-8'))
        logger.info(f"Database backup created at {backup_path}")
        
        # Check if the users table has the required columns
        cursor.execute("PRAGMA table_info(users)")
        columns = [column['name'] for column in cursor.fetchall()]
        
        # Add plain_password column if it doesn't exist
        if 'plain_password' not in columns:
            logger.info("Adding plain_password column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN plain_password TEXT")
        
        # Add verification_hash column if it doesn't exist
        if 'verification_hash' not in columns:
            logger.info("Adding verification_hash column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN verification_hash TEXT")
        
        # Add last_password_change column if it doesn't exist
        if 'last_password_change' not in columns:
            logger.info("Adding last_password_change column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN last_password_change TIMESTAMP")
        
        # Get all entries from temp_passwords
        cursor.execute("""
            SELECT user_id, temp_password, verification_hash, created_at
            FROM temp_passwords
        """)
        temp_passwords = cursor.fetchall()
        
        logger.info(f"Found {len(temp_passwords)} temporary password entries to migrate")
        
        # Update users table with data from temp_passwords
        for entry in temp_passwords:
            user_id = entry['user_id']
            temp_password = entry['temp_password']
            verification_hash = entry['verification_hash'] if 'verification_hash' in entry.keys() else None
            created_at = entry['created_at'] if 'created_at' in entry.keys() else None
            
            # Update the users table
            cursor.execute("""
                UPDATE users 
                SET plain_password = ?,
                    verification_hash = ?,
                    last_password_change = ?
                WHERE id = ?
            """, (temp_password, verification_hash, created_at or 'CURRENT_TIMESTAMP', user_id))
            
            if cursor.rowcount > 0:
                logger.info(f"Updated user {user_id} with password data")
            else:
                logger.warning(f"Failed to update user {user_id} - user may not exist")
        
        # Commit the changes
        conn.commit()
        logger.info("Password data migration completed successfully")
        
        # Now that we've migrated the data, we don't immediately drop the temp_passwords table
        # Instead, we rename it to keep it as a backup for a while
        cursor.execute("ALTER TABLE temp_passwords RENAME TO temp_passwords_old")
        logger.info("Renamed temp_passwords table to temp_passwords_old for backup")
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if migrate_passwords():
        print("Password migration completed successfully!")
        sys.exit(0)
    else:
        print("Password migration failed. Check the logs for details.")
        sys.exit(1)
