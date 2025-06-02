#!/usr/bin/env python3
"""
Script to add ArbZG-compliant breaks to existing attendance records with the new intelligent
break placement strategy.

This script replaces the original add_arbzg_breaks.py with improved break placement logic:
1. Tries to place breaks during lunch period (11:30-14:00) if possible
2. Otherwise adds breaks at the end of the work day
3. Uses descriptive labels to differentiate lunch breaks from end-of-day breaks
"""

import sqlite3
import os
from datetime import datetime, timedelta

# Path to the database
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'attendance.db')

def try_parse(date_string):
    """Try to parse a datetime string in various formats."""
    if not date_string:
        return None
    
    formats = [
        # Standard formats
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        # Formats with timezone info
        '%Y-%m-%d %H:%M:%S%z',
        '%Y-%m-%d %H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S.%f%z'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    return None

def add_arbzg_breaks_intelligent():
    """Check attendance records and add intelligently placed ArbZG-compliant breaks where needed."""
    print("Starting enhanced ArbZG break placement...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Check if arbzg_breaks_enabled column exists, add it if not
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'arbzg_breaks_enabled' not in columns:
            print("Adding arbzg_breaks_enabled column to user_settings table...")
            try:
                cursor.execute("ALTER TABLE user_settings ADD COLUMN arbzg_breaks_enabled BOOLEAN DEFAULT 1")
                cursor.execute("UPDATE user_settings SET arbzg_breaks_enabled = 1")
                conn.commit()
                print("Successfully added arbzg_breaks_enabled column")
            except sqlite3.Error as e:
                print(f"Error adding column: {e}")
        
        # Get user settings for break exclusion
        cursor.execute('''SELECT exclude_breaks_from_billing FROM user_settings WHERE user_id = 0''')
        settings = cursor.fetchone()
        exclude_breaks_from_billing = bool(settings[0]) if settings else True
        
        # Get all completed attendance records
        cursor.execute("""
            SELECT a.id, a.check_in, a.check_out, u.username 
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            WHERE a.check_out IS NOT NULL
            ORDER BY a.check_in DESC
        """)
        
        records = cursor.fetchall()
        print(f"Found {len(records)} attendance records to check")
        
        processed_count = 0
        breaks_added_count = 0
        
        # Check each record
        for record in records:
            attendance_id, check_in, check_out, username = record
            
            # Parse datetimes
            check_in_dt = try_parse(check_in)
            check_out_dt = try_parse(check_out)
            
            if not check_in_dt or not check_out_dt:
                print(f"  Skipping record ID {attendance_id}: Invalid datetime format")
                continue
                
            # Make both naive for calculation
            if check_in_dt.tzinfo:
                check_in_dt = check_in_dt.replace(tzinfo=None)
            if check_out_dt.tzinfo:
                check_out_dt = check_out_dt.replace(tzinfo=None)
            
            # Calculate total work duration in minutes
            total_work_minutes = int((check_out_dt - check_in_dt).total_seconds() / 60)
            
            # Define required breaks per ArbZG
            required_break_minutes = 0
            if total_work_minutes > 9 * 60:  # More than 9 hours
                required_break_minutes = 45
            elif total_work_minutes > 6 * 60:  # More than 6 hours
                required_break_minutes = 30
                
            if required_break_minutes == 0:
                processed_count += 1
                continue  # No break required
                
            # Check existing breaks
            cursor.execute("""
                SELECT SUM(duration_minutes) 
                FROM breaks 
                WHERE attendance_id = ?
            """, (attendance_id,))
            
            existing_breaks_row = cursor.fetchone()
            existing_break_minutes = existing_breaks_row[0] if existing_breaks_row and existing_breaks_row[0] is not None else 0
            
            # Calculate missing break minutes
            missing_break_minutes = required_break_minutes - existing_break_minutes
            
            if missing_break_minutes <= 0:
                processed_count += 1
                continue  # Sufficient breaks already exist
                
            print(f"Adding {missing_break_minutes}min break for {username} on {check_in_dt.date()} (ID: {attendance_id})")
            
            # Try to place the break intelligently during lunch time if possible
            lunch_break_added = False
            
            # Define typical lunch period (11:30 to 14:00)
            lunch_start_time = check_in_dt.replace(hour=11, minute=30, second=0)
            lunch_end_time = check_in_dt.replace(hour=14, minute=0, second=0)
            
            # Check if work period spans lunch time
            if check_in_dt <= lunch_end_time and check_out_dt >= lunch_start_time:
                # The work period includes the lunch period
                actual_lunch_start = max(check_in_dt, lunch_start_time)
                actual_lunch_end = min(check_out_dt, lunch_end_time)
                
                # Calculate available lunch period in minutes
                lunch_period_minutes = int((actual_lunch_end - actual_lunch_start).total_seconds() / 60)
                
                if lunch_period_minutes >= missing_break_minutes:
                    # We have enough time in the lunch period to add the break
                    lunch_midpoint = actual_lunch_start + (actual_lunch_end - actual_lunch_start) / 2
                    break_start = lunch_midpoint - timedelta(minutes=missing_break_minutes/2)
                    break_end = break_start + timedelta(minutes=missing_break_minutes)
                    
                    break_start_str = break_start.strftime('%Y-%m-%d %H:%M:%S')
                    break_end_str = break_end.strftime('%Y-%m-%d %H:%M:%S')
                    
                    cursor.execute("""
                        INSERT INTO breaks (
                            attendance_id, start_time, end_time, duration_minutes,
                            is_excluded_from_billing, is_auto_detected, description
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        attendance_id, break_start_str, break_end_str, 
                        missing_break_minutes, exclude_breaks_from_billing, True,
                        "Gesetzliche Mittagspause (ArbZG §4)"
                    ))
                    lunch_break_added = True
            
            # If we couldn't add a lunch break, add the break at the end of the day
            if not lunch_break_added:
                break_end = check_out_dt
                break_start = break_end - timedelta(minutes=missing_break_minutes)
                
                # Ensure break doesn't start before check-in
                if break_start < check_in_dt:
                    break_start = check_in_dt
                
                break_start_str = break_start.strftime('%Y-%m-%d %H:%M:%S')
                break_end_str = break_end.strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute("""
                    INSERT INTO breaks (
                        attendance_id, start_time, end_time, duration_minutes,
                        is_excluded_from_billing, is_auto_detected, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    attendance_id, break_start_str, break_end_str, 
                    missing_break_minutes, exclude_breaks_from_billing, True,
                    "Automatische Pause gem. ArbZG §4"
                ))
            
            # Update attendance record to show that automatic breaks were added
            cursor.execute("UPDATE attendance SET has_auto_breaks = 1 WHERE id = ?", (attendance_id,))
            
            breaks_added_count += 1
            processed_count += 1
            
            # Commit every 10 records
            if processed_count % 10 == 0:
                conn.commit()
                print(f"Processed {processed_count} records so far, added {breaks_added_count} breaks")
        
        conn.commit()
        print(f"Completed: Processed {processed_count} records, added {breaks_added_count} breaks")
        
    except Exception as e:
        print(f"Error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    add_arbzg_breaks_intelligent()
