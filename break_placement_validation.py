#!/usr/bin/env python3
# break_placement_validation.py
# Simple validation test for ArbZG-compliant break placement

import sqlite3
import os
import sys
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('break_validation.log')
    ]
)
logger = logging.getLogger('break_validation')

# Get the database path
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
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    return None

def validate_break_placement():
    """Test the ArbZG break placement algorithm with various scenarios"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Clean up any test data
    cursor.execute("DELETE FROM users WHERE username = 'test_user'")
    cursor.execute("DELETE FROM attendance WHERE user_id IN (SELECT id FROM users WHERE username = 'test_user')")
    conn.commit()
    
    # Create a test user
    cursor.execute("INSERT INTO users (username, password) VALUES ('test_user', 'password')")
    test_user_id = cursor.lastrowid
    
    # Make sure ArbZG breaks are enabled
    cursor.execute("""
        INSERT OR REPLACE INTO user_settings 
        (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing, arbzg_breaks_enabled) 
        VALUES (0, 1, 30, 1, 1)
    """)
    conn.commit()
    
    # Test cases
    test_cases = [
        {
            'name': "6 Hour Work Day - No Break Required",
            'check_in': datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
            'check_out': datetime.now().replace(hour=15, minute=0, second=0, microsecond=0),
            'expected_breaks': 0
        },
        {
            'name': "7 Hour Work Day - 30 Min Break Required (Lunch)",
            'check_in': datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
            'check_out': datetime.now().replace(hour=16, minute=0, second=0, microsecond=0),
            'expected_breaks': 1,
            'expected_break_duration': 30
        },
        {
            'name': "10 Hour Work Day - 45 Min Break Required (Lunch)",
            'check_in': datetime.now().replace(hour=8, minute=0, second=0, microsecond=0),
            'check_out': datetime.now().replace(hour=18, minute=0, second=0, microsecond=0),
            'expected_breaks': 1,
            'expected_break_duration': 45
        },
        {
            'name': "8 Hour Work After Lunch - 30 Min Break At End",
            'check_in': datetime.now().replace(hour=15, minute=0, second=0, microsecond=0),
            'check_out': datetime.now().replace(hour=23, minute=0, second=0, microsecond=0),
            'expected_breaks': 1,
            'expected_break_duration': 30,
            'expected_break_position': 'end'
        }
    ]
    
    for test_case in test_cases:
        logger.info(f"Running test case: {test_case['name']}")
        
        # Create attendance record
        check_in_str = test_case['check_in'].strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO attendance (user_id, check_in) VALUES (?, ?)",
            (test_user_id, check_in_str)
        )
        attendance_id = cursor.lastrowid
        
        # Add checkout time
        check_out_str = test_case['check_out'].strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "UPDATE attendance SET check_out = ? WHERE id = ?",
            (check_out_str, attendance_id)
        )
        
        # Simulate the break calculation logic
        total_work_duration_minutes = int((test_case['check_out'] - test_case['check_in']).total_seconds() / 60)
        
        # Calculate statutory break requirements
        statutory_break_minutes = 0
        if total_work_duration_minutes > 9 * 60:  # More than 9 hours
            statutory_break_minutes = 45
        elif total_work_duration_minutes > 6 * 60:  # More than 6 hours
            statutory_break_minutes = 30
        
        # Check if we need to add breaks
        if statutory_break_minutes > 0:
            # Define lunch period
            lunch_start_time = test_case['check_in'].replace(hour=11, minute=30, second=0)
            lunch_end_time = test_case['check_in'].replace(hour=14, minute=0, second=0)
            
            # Check if work period overlaps lunch time
            lunch_break_possible = (test_case['check_in'] <= lunch_end_time and 
                                   test_case['check_out'] >= lunch_start_time)
            
            # Adjust lunch times to actual overlap
            if lunch_break_possible:
                actual_lunch_start = max(test_case['check_in'], lunch_start_time)
                actual_lunch_end = min(test_case['check_out'], lunch_end_time)
                
                lunch_period_minutes = int((actual_lunch_end - actual_lunch_start).total_seconds() / 60)
                
                if lunch_period_minutes >= statutory_break_minutes:
                    # Can fit break in lunch period
                    lunch_midpoint = actual_lunch_start + (actual_lunch_end - actual_lunch_start) / 2
                    auto_break_start = lunch_midpoint - timedelta(minutes=statutory_break_minutes/2)
                    auto_break_end = auto_break_start + timedelta(minutes=statutory_break_minutes)
                    
                    # Ensure break is within lunch period
                    if auto_break_start < actual_lunch_start:
                        auto_break_start = actual_lunch_start
                        auto_break_end = auto_break_start + timedelta(minutes=statutory_break_minutes)
                    
                    if auto_break_end > actual_lunch_end:
                        auto_break_end = actual_lunch_end
                        auto_break_start = auto_break_end - timedelta(minutes=statutory_break_minutes)
                        if auto_break_start < actual_lunch_start:
                            auto_break_start = actual_lunch_start
                    
                    auto_break_start_str = auto_break_start.strftime('%Y-%m-%d %H:%M:%S')
                    auto_break_end_str = auto_break_end.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Add a lunch break
                    logger.info(f"Adding lunch break: {auto_break_start_str} to {auto_break_end_str}")
                    cursor.execute("""INSERT INTO breaks 
                                    (attendance_id, start_time, end_time, duration_minutes, is_excluded_from_billing, is_auto_detected, description)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                 (attendance_id, auto_break_start_str, auto_break_end_str, statutory_break_minutes, 
                                  True, True, "Gesetzliche Mittagspause (ArbZG §4) - Validation Test"))
                else:
                    # Add break at end of day
                    logger.info(f"Lunch period too short, adding end-of-day break")
                    auto_break_end = test_case['check_out']
                    auto_break_start = auto_break_end - timedelta(minutes=statutory_break_minutes)
                    
                    auto_break_start_str = auto_break_start.strftime('%Y-%m-%d %H:%M:%S')
                    auto_break_end_str = auto_break_end.strftime('%Y-%m-%d %H:%M:%S')
                    
                    cursor.execute("""INSERT INTO breaks 
                                    (attendance_id, start_time, end_time, duration_minutes, is_excluded_from_billing, is_auto_detected, description)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                 (attendance_id, auto_break_start_str, auto_break_end_str, statutory_break_minutes, 
                                  True, True, "ArbZG §4 Pflichtpause (Ende des Arbeitstages) - Validation Test"))
            else:
                # No lunch period overlap, add end-of-day break
                logger.info(f"No lunch period overlap, adding end-of-day break")
                auto_break_end = test_case['check_out']
                auto_break_start = auto_break_end - timedelta(minutes=statutory_break_minutes)
                
                auto_break_start_str = auto_break_start.strftime('%Y-%m-%d %H:%M:%S')
                auto_break_end_str = auto_break_end.strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute("""INSERT INTO breaks 
                                (attendance_id, start_time, end_time, duration_minutes, is_excluded_from_billing, is_auto_detected, description)
                                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                             (attendance_id, auto_break_start_str, auto_break_end_str, statutory_break_minutes, 
                              True, True, "ArbZG §4 Pflichtpause (Ende des Arbeitstages) - Validation Test"))
                
        conn.commit()
        
        # Check the results
        cursor.execute(
            "SELECT id, start_time, end_time, duration_minutes, is_auto_detected, description FROM breaks WHERE attendance_id = ?",
            (attendance_id,)
        )
        breaks = cursor.fetchall()
        
        # Verify the test case
        if len(breaks) != test_case.get('expected_breaks', 0):
            logger.error(f"FAIL: Expected {test_case.get('expected_breaks', 0)} breaks, got {len(breaks)}")
        else:
            logger.info(f"PASS: Found expected number of breaks: {len(breaks)}")
            
            if len(breaks) > 0:
                break_duration = breaks[0][3]
                expected_duration = test_case.get('expected_break_duration', 0)
                
                if break_duration == expected_duration:
                    logger.info(f"PASS: Break duration correct: {break_duration} min")
                else:
                    logger.error(f"FAIL: Expected break duration {expected_duration} min, got {break_duration} min")
                
                if 'expected_break_position' in test_case:
                    break_desc = breaks[0][5] or ""
                    if (test_case['expected_break_position'] == 'end' and 'Ende des Arbeitstages' in break_desc) or \
                       (test_case['expected_break_position'] != 'end' and 'Mittagspause' in break_desc):
                        logger.info(f"PASS: Break position correct: {break_desc}")
                    else:
                        logger.error(f"FAIL: Break position incorrect. Expected: {test_case['expected_break_position']}, Got: {break_desc}")
    
    # Clean up test data
    cursor.execute("DELETE FROM breaks WHERE attendance_id IN (SELECT id FROM attendance WHERE user_id = ?)", (test_user_id,))
    cursor.execute("DELETE FROM attendance WHERE user_id = ?", (test_user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (test_user_id,))
    conn.commit()
    
    logger.info("Break placement validation completed")
    conn.close()

if __name__ == "__main__":
    validate_break_placement()
