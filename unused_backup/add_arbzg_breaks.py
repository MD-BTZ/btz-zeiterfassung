"""
Script to check existing attendance records and retroactively add ArbZG-compliant breaks
to records that don't have sufficient breaks.
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
    
    # If standard parsing fails, try using dateutil as a fallback
    try:
        from dateutil import parser
        return parser.parse(date_string)
    except:
        pass
    
    return None

def add_arbzg_breaks():
    """Check attendance records and add ArbZG-compliant breaks where needed."""
    print("Starting ArbZG break compliance check...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
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
        
        # Get exclude_breaks_from_billing setting
        cursor.execute("SELECT value FROM system_settings WHERE key = 'exclude_breaks_from_billing'")
        exclude_breaks_setting = cursor.fetchone()
        exclude_breaks_from_billing = exclude_breaks_setting[0] == '1' if exclude_breaks_setting else False
        
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
                break_desc = "Gesetzliche Pause (ArbZG §4) für Arbeitszeit über 9 Stunden"
            elif total_work_minutes > 6 * 60:  # More than 6 hours
                required_break_minutes = 30
                break_desc = "Gesetzliche Pause (ArbZG §4) für Arbeitszeit über 6 Stunden"
                
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
            
            # Try to add a break during lunch hour if possible
            lunch_start = check_in_dt.replace(hour=12, minute=0, second=0)
            lunch_end = check_in_dt.replace(hour=13, minute=0, second=0)
            
            # If lunch time is within the work period
            if check_in_dt <= lunch_end and check_out_dt >= lunch_start:
                # Place the break during lunch time
                actual_lunch_start = max(check_in_dt, lunch_start)
                actual_lunch_end = min(check_out_dt, lunch_end)
                
                # If we have enough time during lunch for the break
                lunch_period_minutes = (actual_lunch_end - actual_lunch_start).total_seconds() / 60
                
                if lunch_period_minutes >= missing_break_minutes:
                    # Center the break in the lunch period
                    lunch_midpoint = actual_lunch_start + (actual_lunch_end - actual_lunch_start) / 2
                    break_start = lunch_midpoint - timedelta(minutes=missing_break_minutes/2)
                    break_end = break_start + timedelta(minutes=missing_break_minutes)
                else:
                    # Use the entire available lunch period
                    break_start = actual_lunch_start
                    break_end = actual_lunch_end
                    
                    # If we still need more break time, add it at the end of the day
                    if lunch_period_minutes < missing_break_minutes:
                        remaining_break = missing_break_minutes - lunch_period_minutes
                        
                        # Insert the lunch break
                        break_start_str = break_start.strftime('%Y-%m-%d %H:%M:%S')
                        break_end_str = break_end.strftime('%Y-%m-%d %H:%M:%S')
                        
                        cursor.execute("""
                            INSERT INTO breaks (attendance_id, start_time, end_time, duration_minutes,
                                             is_excluded_from_billing, is_auto_detected, description, break_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (attendance_id, break_start_str, break_end_str, int(lunch_period_minutes),
                              exclude_breaks_from_billing, True, break_desc, "gesetzlich"))
                        
                        # Add a second break at the end
                        break_end = check_out_dt
                        break_start = break_end - timedelta(minutes=remaining_break)
                        break_start_str = break_start.strftime('%Y-%m-%d %H:%M:%S')
                        break_end_str = break_end.strftime('%Y-%m-%d %H:%M:%S')
                        
                        cursor.execute("""
                            INSERT INTO breaks (attendance_id, start_time, end_time, duration_minutes,
                                             is_excluded_from_billing, is_auto_detected, description, break_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (attendance_id, break_start_str, break_end_str, int(remaining_break),
                              exclude_breaks_from_billing, True, break_desc, "gesetzlich"))
                        
                        breaks_added_count += 2
                        continue
            else:
                # Place break in the middle of the work day
                middle_point = check_in_dt + (check_out_dt - check_in_dt) / 2
                break_start = middle_point - timedelta(minutes=missing_break_minutes/2)
                break_end = break_start + timedelta(minutes=missing_break_minutes)
            
            # Ensure break is within work hours
            if break_start < check_in_dt:
                break_start = check_in_dt
                break_end = break_start + timedelta(minutes=missing_break_minutes)
            
            if break_end > check_out_dt:
                break_end = check_out_dt
                break_start = break_end - timedelta(minutes=missing_break_minutes)
                
            # Format for database
            break_start_str = break_start.strftime('%Y-%m-%d %H:%M:%S')
            break_end_str = break_end.strftime('%Y-%m-%d %H:%M:%S')
            
            # Insert the break
            cursor.execute("""
                INSERT INTO breaks (attendance_id, start_time, end_time, duration_minutes,
                                 is_excluded_from_billing, is_auto_detected, description, break_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (attendance_id, break_start_str, break_end_str, missing_break_minutes,
                  exclude_breaks_from_billing, True, break_desc, "gesetzlich"))
                  
            breaks_added_count += 1
            processed_count += 1
            
            # Update every 10 records
            if processed_count % 10 == 0:
                conn.commit()
                print(f"Processed {processed_count} records so far, added {breaks_added_count} breaks")
        
        # Commit any remaining changes
        conn.commit()
        print(f"Finished: processed {processed_count} records, added {breaks_added_count} breaks")
            
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        conn.rollback()
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_arbzg_breaks()
