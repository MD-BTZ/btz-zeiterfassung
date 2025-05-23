#!/usr/bin/env python3
# update_password_code.py
# Updates app.py to use the users table for passwords instead of temp_passwords

import os
import re
import sys
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('code_migration.log')
    ]
)
logger = logging.getLogger('code_migration')

# Path to app.py
APP_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.py')

def backup_file(file_path):
    """Create a backup of the given file."""
    backup_path = f"{file_path}.{int(time.time())}.bak"
    try:
        with open(file_path, 'r', encoding='utf-8') as original:
            with open(backup_path, 'w', encoding='utf-8') as backup:
                backup.write(original.read())
        logger.info(f"Created backup at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return False

def update_app_code():
    """Update app.py to use users table for passwords."""
    logger.info("Starting to update app.py code")
    
    if not backup_file(APP_PATH):
        logger.error("Backup failed, aborting update")
        return False
    
    try:
        with open(APP_PATH, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 1. Replace temp_passwords table creation
        old_table_creation = r"""        # Create temp_passwords table for storing temporary plaintext passwords
        cursor.execute('''CREATE TABLE IF NOT EXISTS temp_passwords \(
            user_id INTEGER PRIMARY KEY,
            temp_password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verification_hash TEXT
        \)''')"""
        
        new_table_creation = """        # Ensure users table has columns for storing plaintext passwords
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0,
                plain_password TEXT,
                verification_hash TEXT,
                last_password_change TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')"""
        
        content = re.sub(old_table_creation, new_table_creation, content)
        
        # 2. Replace password storage in reset_password function
        content = content.replace(
            """        # Delete any existing temp password for this user first
        cursor.execute('DELETE FROM temp_passwords WHERE user_id = ?', (user_id,))
        
        # Insert new temp password with verification hash
        cursor.execute('''
            INSERT INTO temp_passwords (user_id, temp_password, verification_hash) 
            VALUES (?, ?, ?)
        ''', (user_id, hashed_password, verification_hash))""",
            
            """        # Update the user's plain password and verification hash
        cursor.execute('''
            UPDATE users 
            SET plain_password = ?,
                verification_hash = ?,
                last_password_change = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (hashed_password, verification_hash, user_id))"""
        )
        
        # 3. Replace password storage in change_password function
        content = content.replace(
            """            # Delete any existing temp password for this user first
            cursor.execute('DELETE FROM temp_passwords WHERE user_id = ?', (user_id,))
            
            # Insert new temp password with verification hash
            cursor.execute('''
                INSERT INTO temp_passwords (user_id, temp_password, verification_hash) 
                VALUES (?, ?, ?)
            ''', (user_id, hashed_password, verification_hash))""",
            
            """            # Update the user's plain password and verification hash
            cursor.execute('''
                UPDATE users 
                SET plain_password = ?,
                    verification_hash = ?,
                    last_password_change = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (hashed_password, verification_hash, user_id))"""
        )
        
        # 4. Replace password retrieval in get_user_password function
        content = content.replace(
            """            # Try to get the temporary password from the temp_passwords table
            cursor.execute('SELECT temp_password, verification_hash FROM temp_passwords WHERE user_id = ?', (user_id,))
            temp_password_record = cursor.fetchone()""",
            
            """            # Get the plain password from the users table
            cursor.execute('SELECT plain_password, verification_hash FROM users WHERE id = ?', (user_id,))
            temp_password_record = cursor.fetchone()"""
        )
        
        # 5. Replace password update in get_user_password function (first occurrence)
        content = content.replace(
            """                    # Update the temporary password record
                    cursor.execute('''
                        UPDATE temp_passwords 
                        SET temp_password = ?, verification_hash = ? 
                        WHERE user_id = ?
                    ''', (hashed_password, new_verification_hash, user_id))""",
            
            """                    # Update the user record
                    cursor.execute('''
                        UPDATE users 
                        SET plain_password = ?, verification_hash = ?, last_password_change = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', (hashed_password, new_verification_hash, user_id))"""
        )
        
        # 6. Replace second password update in get_user_password function
        content = content.replace(
            """                        # Update the temporary password record with the new format
                        cursor.execute('''
                            UPDATE temp_passwords 
                            SET temp_password = ?, verification_hash = ? 
                            WHERE user_id = ?
                        ''', (hashed_password, verification_hash, user_id))""",
            
            """                        # Update the user record with the new format
                        cursor.execute('''
                            UPDATE users 
                            SET plain_password = ?, verification_hash = ?, last_password_change = CURRENT_TIMESTAMP 
                            WHERE id = ?
                        ''', (hashed_password, verification_hash, user_id))"""
        )
        
        # 7. Replace final password update in get_user_password function
        content = content.replace(
            """                # Store the hashed password with verification hash
                cursor.execute('DELETE FROM temp_passwords WHERE user_id = ?', (user_id,))
                cursor.execute('''
                    INSERT INTO temp_passwords (user_id, temp_password, verification_hash) 
                    VALUES (?, ?, ?)
                ''', (user_id, hashed_password, verification_hash))""",
            
            """                # Store the hashed password with verification hash
                cursor.execute('''
                    UPDATE users 
                    SET plain_password = ?, verification_hash = ?, last_password_change = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (hashed_password, verification_hash, user_id))"""
        )
        
        # Write the updated content back to app.py
        with open(APP_PATH, 'w', encoding='utf-8') as file:
            file.write(content)
        
        logger.info("Successfully updated app.py code")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update app.py code: {e}")
        return False

if __name__ == "__main__":
    if update_app_code():
        print("Code migration completed successfully!")
        sys.exit(0)
    else:
        print("Code migration failed. Check the logs for details.")
        sys.exit(1)
