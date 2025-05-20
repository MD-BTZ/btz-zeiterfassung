#!/usr/bin/env python3
# migrate_temp_passwords.py
# Migration script to add verification_hash column to temp_passwords table

import sqlite3
import os
import sys
import logging
import bcrypt
import hashlib

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
    """Add verification_hash column to temp_passwords table and update existing records"""
    logger.info("Starting temporary passwords migration")
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check if column already exists to avoid errors
        cursor.execute("PRAGMA table_info(temp_passwords)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add verification_hash column if it doesn't exist
        if 'verification_hash' not in columns:
            logger.info("Adding verification_hash column to temp_passwords table")
            cursor.execute("ALTER TABLE temp_passwords ADD COLUMN verification_hash TEXT")
            
            # Get all existing records
            cursor.execute("SELECT user_id, temp_password FROM temp_passwords")
            temp_passwords = cursor.fetchall()
            
            logger.info(f"Migrating {len(temp_passwords)} existing temporary password records")
            
            # Update each record with a verification hash
            for record in temp_passwords:
                user_id = record['user_id']
                temp_password = record['temp_password']
                
                # Check if the password is already hashed (starts with $2b$)
                if temp_password.startswith('$2b$'):
                    logger.info(f"Password for user {user_id} is already hashed")
                    # We can't derive a verification hash from a hashed password
                    # We'll need to set this to NULL and it will be handled during the next password retrieval
                    cursor.execute(
                        "UPDATE temp_passwords SET verification_hash = NULL WHERE user_id = ?", 
                        (user_id,)
                    )
                else:
                    # Create a verification hash for plaintext password
                    verification_hash = hashlib.sha256(temp_password.encode()).hexdigest()
                    
                    # Hash the password
                    hashed_password = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    # Update the record
                    cursor.execute(
                        "UPDATE temp_passwords SET temp_password = ?, verification_hash = ? WHERE user_id = ?", 
                        (hashed_password, verification_hash, user_id)
                    )
                    
                    logger.info(f"Updated temporary password for user {user_id} with hash and verification hash")
            
            # Commit the changes
            conn.commit()
            logger.info("Migration of temporary passwords completed successfully")
            
        else:
            logger.info("Column verification_hash already exists in temp_passwords table")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
    print("Migration completed successfully. Temporary passwords are now securely stored.")
