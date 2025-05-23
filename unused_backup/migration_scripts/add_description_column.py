import sqlite3

# Connect to the database
conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

# Check if description column exists in breaks table
cursor.execute("PRAGMA table_info(breaks)")
columns = [column[1] for column in cursor.fetchall()]
print("Current columns in breaks table:", columns)

# Add description column if it doesn't exist
if 'description' not in columns:
    try:
        cursor.execute("ALTER TABLE breaks ADD COLUMN description TEXT")
        print("Added description column to breaks table")
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error adding column: {e}")
else:
    print("Column description already exists in breaks table")

conn.close()
print("Migration completed")
