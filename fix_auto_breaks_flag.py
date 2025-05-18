#!/usr/bin/env python3
"""
This script fixes records where automatic breaks exist but the has_auto_breaks flag is not set.
"""
import sqlite3
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_auto_breaks.log'),
        logging.StreamHandler()
    ]
)

# Database path
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'attendance.db')

def fix_auto_breaks_flag():
    """Fix attendance records that have auto breaks but flag not set"""
    print("Fixing attendance records with automatic breaks...")
    
    # Connect to database
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Find attendance records with auto-detected breaks
    cursor.execute('''
        SELECT DISTINCT a.id, a.has_auto_breaks, u.username, a.check_in, a.check_out
        FROM attendance a
        JOIN breaks b ON b.attendance_id = a.id
        JOIN users u ON a.user_id = u.id
        WHERE b.is_auto_detected = 1
        AND a.has_auto_breaks = 0
    ''')
    
    records = cursor.fetchall()
    
    print(f"Found {len(records)} records with auto breaks but flag not set.")
    
    # Update each record
    count = 0
    for record in records:
        attendance_id = record['id']
        username = record['username']
        check_in = record['check_in']
        
        print(f"Fixing record {attendance_id} for user {username} (check-in: {check_in[:16]})")
        
        cursor.execute('''
            UPDATE attendance
            SET has_auto_breaks = 1
            WHERE id = ?
        ''', (attendance_id,))
        
        count += 1
    
    conn.commit()
    conn.close()
    
    print(f"Updated {count} attendance records.")

if __name__ == '__main__':
    fix_auto_breaks_flag()
