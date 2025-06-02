import sqlite3

# Connect to the database
conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

# Check if column exists
cursor.execute("PRAGMA table_info(user_settings)")
columns = [column[1] for column in cursor.fetchall()]

# Add column if it doesn't exist
if 'arbzg_breaks_enabled' not in columns:
    try:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN arbzg_breaks_enabled BOOLEAN DEFAULT 1")
        print("Added arbzg_breaks_enabled column to user_settings table")
    except sqlite3.Error as e:
        print(f"Error adding column: {e}")
    
    # Update existing records to enable ArbZG breaks by default
    try:
        cursor.execute("UPDATE user_settings SET arbzg_breaks_enabled = 1")
        print("Set default value for arbzg_breaks_enabled in existing records")
    except sqlite3.Error as e:
        print(f"Error updating records: {e}")
    
    # Make sure system-wide settings (user_id = 0) exist and include ArbZG setting
    try:
        cursor.execute("SELECT id FROM user_settings WHERE user_id = 0")
        system_settings = cursor.fetchone()
        
        if system_settings:
            # Update existing system settings
            cursor.execute("UPDATE user_settings SET arbzg_breaks_enabled = 1 WHERE user_id = 0")
            print("Updated system-wide settings with ArbZG breaks enabled")
        else:
            # Insert system settings if they don't exist
            cursor.execute('''INSERT INTO user_settings 
                          (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, 
                           exclude_breaks_from_billing, arbzg_breaks_enabled)
                          VALUES (0, 1, 30, 1, 1)''')
            print("Created system-wide settings with ArbZG breaks enabled")
    except sqlite3.Error as e:
        print(f"Error configuring system settings: {e}")
    
    conn.commit()
else:
    print("Column arbzg_breaks_enabled already exists")

conn.close()
print("Migration completed")

