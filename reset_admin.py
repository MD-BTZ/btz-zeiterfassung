import sqlite3
from flask_bcrypt import Bcrypt

# Create bcrypt instance
bcrypt = Bcrypt()
# Create a new hashed password
hashed_password = bcrypt.generate_password_hash("admin").decode('utf-8')

# Connect to the database
conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

# Update the admin user's password
cursor.execute("UPDATE users SET password = ? WHERE username = 'admin'", (hashed_password,))
conn.commit()
conn.close()

print("Admin password has been reset to 'admin'")
