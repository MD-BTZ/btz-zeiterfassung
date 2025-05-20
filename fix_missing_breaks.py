#!/usr/bin/env python
"""
Script to check all attendance records and add missing ArbZG-compliant breaks
This script adds legally required breaks (ArbZG) to any attendance records 
that are longer than 6 hours and don't already have sufficient breaks
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
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
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
    
    # If standard parsing fails, try using dateutil as a fallback
    try:
        from dateutil import parser
        return parser.parse(date_string)
    except Exception:
        pass
    
    return None

def fix_missing_breaks():
    """Check attendance records and add ArbZG-compliant breaks where needed."""
    print("Starting ArbZG break compliance check and fix...")
    
    # Connect to database
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get exclude_breaks_from_billing setting (system-wide)
    cursor.execute("SELECT exclude_breaks_from_billing FROM user_settings WHERE user_id = 0")
    exclude_breaks_setting = cursor.fetchone()
    exclude_breaks_from_billing = exclude_breaks_setting['exclude_breaks_from_billing'] if exclude_breaks_setting else 1
    
    print(f"Exclude breaks from billing setting: {exclude_breaks_from_billing}")
    
    # Get all completed attendance records
    cursor.execute("""
        SELECT a.id, a.user_id, a.check_in, a.check_out, a.billable_minutes, u.username 
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE a.check_out IS NOT NULL
        ORDER BY a.id DESC
    """)
    
    records = cursor.fetchall()
    print(f"Found {len(records)} attendance records to check")
    
    records_updated = 0
    breaks_added = 0
    
    # Process each record
    for record in records:
        attendance_id = record['id']
        user_id = record['user_id']
        check_in = record['check_in']
        check_out = record['check_out']
        billable_minutes = record['billable_minutes']
        username = record['username']
        
        print(f"\nChecking record {attendance_id} for user {username}")
        
        # Parse datetimes
        check_in_dt = try_parse(check_in)
        check_out_dt = try_parse(check_out)
        
        if not check_in_dt or not check_out_dt:
            print(f"  Skipping record ID {attendance_id}: Invalid datetime format")
            continue
        
        # Make sure both are naive datetimes for calculation
        if check_in_dt.tzinfo:
            check_in_dt = check_in_dt.replace(tzinfo=None)
        if check_out_dt.tzinfo:
            check_out_dt = check_out_dt.replace(tzinfo=None)
        
        # Calculate total work duration in minutes
        total_work_minutes = int((check_out_dt - check_in_dt).total_seconds() / 60)
        print(f"  Total work minutes: {total_work_minutes}")
        
        # Determine if break is required per ArbZG
        required_break_minutes = 0
        if total_work_minutes > 9 * 60:  # > 9 hours: 45 min break
            required_break_minutes = 45
            break_desc = "Gesetzliche Pause (ArbZG §4) für Arbeitszeit über 9 Stunden"
        elif total_work_minutes > 6 * 60:  # > 6 hours: 30 min break
            required_break_minutes = 30
            break_desc = "Gesetzliche Pause (ArbZG §4) für Arbeitszeit über 6 Stunden"
        
        if required_break_minutes == 0:
            print(f"  No break required for record {attendance_id} (work time < 6 hours)")
            continue
        
        print(f"  Required break: {required_break_minutes} minutes")
        
        # Check existing breaks for this record
        cursor.execute("SELECT SUM(duration_minutes) as total FROM breaks WHERE attendance_id = ?", 
                      (attendance_id,))
        existing_breaks = cursor.fetchone()
        existing_break_minutes = existing_breaks['total'] or 0
        print(f"  Existing break minutes: {existing_break_minutes}")
        
        # Calculate missing break minutes
        missing_break_minutes = required_break_minutes - existing_break_minutes
        
        if missing_break_minutes <= 0:
            print(f"  Sufficient breaks already exist for record {attendance_id}")
            continue
        
        print(f"  Adding {missing_break_minutes} minutes of break for record {attendance_id}")
        
        # Try to place break during lunch time or at end of day
        lunch_start = check_in_dt.replace(hour=12, minute=0, second=0)
        lunch_end = check_in_dt.replace(hour=13, minute=0, second=0)
        
        # If lunch time is within the work period
        if check_in_dt <= lunch_end and check_out_dt >= lunch_start:
            break_start = max(check_in_dt, lunch_start)
            break_end = min(check_out_dt, break_start + timedelta(minutes=missing_break_minutes))
            
            # Make sure break doesn't exceed lunch period
            if break_end > lunch_end:
                break_end = lunch_end
        else:
            # Place break at end of workday
            break_end = check_out_dt
            break_start = break_end - timedelta(minutes=missing_break_minutes)
        
        # Format for database
        break_start_str = break_start.strftime('%Y-%m-%d %H:%M:%S')
        break_end_str = break_end.strftime('%Y-%m-%d %H:%M:%S')
        
        # Add the break
        try:
            cursor.execute("""
                INSERT INTO breaks (attendance_id, start_time, end_time, duration_minutes,
                                is_excluded_from_billing, is_auto_detected, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (attendance_id, break_start_str, break_end_str, missing_break_minutes,
                  exclude_breaks_from_billing, 1, break_desc))
            
            # Update billable minutes
            if exclude_breaks_from_billing:
                new_billable_minutes = billable_minutes - missing_break_minutes
                cursor.execute("""
                    UPDATE attendance 
                    SET billable_minutes = ? 
                    WHERE id = ?
                """, (new_billable_minutes, attendance_id))
                print(f"  Updated billable minutes from {billable_minutes} to {new_billable_minutes}")
            
            conn.commit()
            breaks_added += 1
            records_updated += 1
            print(f"  Successfully added break and updated record {attendance_id}")
            
        except sqlite3.Error as e:
            print(f"  Error adding break to record {attendance_id}: {e}")
            conn.rollback()
    
    conn.close()
    print(f"\nSummary: Added {breaks_added} breaks to {records_updated} records")

if __name__ == "__main__":
    fix_missing_breaks()
