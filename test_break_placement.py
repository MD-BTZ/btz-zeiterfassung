#!/usr/bin/env python3
# test_break_placement.py
# Comprehensive testing for ArbZG-compliant break placement algorithm

import unittest
import sqlite3
import os
import sys
from datetime import datetime, timedelta
import shutil
import tempfile
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('break_placement_tests.log')
    ]
)
logger = logging.getLogger('break_placement_tests')

# Import the app module - adjust the path if necessary
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app, init_db, try_parse

class TestArbZGBreakPlacement(unittest.TestCase):
    """Test suite for ArbZG-compliant break placement algorithm"""
    
    def setUp(self):
        """Set up test environment with a temporary database"""
        # Create a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp()
        # Override the app's DATABASE path
        app.config['DATABASE'] = self.db_path
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SERVER_NAME'] = 'localhost'
        
        # Initialize database with test data
        with app.app_context():
            init_db()
            self._populate_test_data()
        
        # Create test client
        self.client = app.test_client()
        
        # Create a test context
        self.ctx = app.test_request_context()
        self.ctx.push()
        
        # Login as admin
        with self.client as c:
            with c.session_transaction() as sess:
                sess['username'] = 'admin'
                sess['admin_logged_in'] = True
                sess['user_id'] = 1  # admin user ID
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove the temporary database
        os.close(self.db_fd)
        os.unlink(self.db_path)
        # Remove the context
        self.ctx.pop()
    
    def _populate_test_data(self):
        """Populate the database with test data"""
        db = sqlite3.connect(self.db_path)
        cursor = db.cursor()
        
        # Ensure user_settings has the arbzg_breaks_enabled column
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'arbzg_breaks_enabled' not in columns:
            cursor.execute("ALTER TABLE user_settings ADD COLUMN arbzg_breaks_enabled BOOLEAN DEFAULT 1")
            cursor.execute("UPDATE user_settings SET arbzg_breaks_enabled = 1")
        
        # Set system-wide settings for testing
        cursor.execute('''INSERT OR REPLACE INTO user_settings 
                        (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, 
                        exclude_breaks_from_billing, arbzg_breaks_enabled)
                        VALUES (0, 1, 30, 1, 1)''')
        
        # Create a test user
        cursor.execute("INSERT INTO users (username, password) VALUES ('testuser', 'password')")
        
        db.commit()
        db.close()
    
    def _create_attendance(self, user_id, check_in, check_out=None):
        """Helper to create an attendance record"""
        db = sqlite3.connect(app.config['DATABASE'])
        cursor = db.cursor()
        
        if check_out:
            cursor.execute(
                "INSERT INTO attendance (user_id, check_in, check_out) VALUES (?, ?, ?)",
                (user_id, check_in, check_out)
            )
        else:
            cursor.execute(
                "INSERT INTO attendance (user_id, check_in) VALUES (?, ?)",
                (user_id, check_in)
            )
        
        attendance_id = cursor.lastrowid
        db.commit()
        db.close()
        
        return attendance_id
    
    def _add_manual_break(self, attendance_id, start_time, end_time, description="Manual break"):
        """Helper to add a manual break"""
        db = sqlite3.connect(app.config['DATABASE'])
        cursor = db.cursor()
        
        # Calculate duration
        start_dt = try_parse(start_time)
        end_dt = try_parse(end_time)
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
        
        cursor.execute(
            """INSERT INTO breaks 
               (attendance_id, start_time, end_time, duration_minutes, 
                is_excluded_from_billing, is_auto_detected, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (attendance_id, start_time, end_time, duration_minutes, True, False, description)
        )
        
        db.commit()
        db.close()
    
    def _get_breaks(self, attendance_id):
        """Helper to get all breaks for an attendance record"""
        db = sqlite3.connect(app.config['DATABASE'])
        cursor = db.cursor()
        
        cursor.execute(
            """SELECT id, start_time, end_time, duration_minutes, 
                     is_excluded_from_billing, is_auto_detected, description
               FROM breaks 
               WHERE attendance_id = ?
               ORDER BY start_time""",
            (attendance_id,)
        )
        
        breaks = cursor.fetchall()
        db.close()
        
        return breaks
    
    def _simulate_checkout(self, user_id, attendance_id, checkout_time):
        """Simulate the checkout process"""
        with app.test_request_context(
            '/checkout',
            method='POST',
            data={
                'user_id': user_id,
                'skip_confirmation': 'true'
            }
        ):
            # Mock the current time
            app.checkout_time_override = checkout_time
            
            # Import the checkout function from app.py
            from app import checkout
            response = checkout()
            
            # Reset time override
            app.checkout_time_override = None
            
            return response
    
    def _check_break_placement(self, attendance_id, expected_breaks):
        """Check if breaks match expected configuration"""
        actual_breaks = self._get_breaks(attendance_id)
        
        self.assertEqual(len(actual_breaks), len(expected_breaks),
                         f"Expected {len(expected_breaks)} breaks, got {len(actual_breaks)}")
        
        for i, (actual, expected) in enumerate(zip(actual_breaks, expected_breaks)):
            # Parse times for easier comparison
            actual_start = try_parse(actual[1])
            actual_end = try_parse(actual[2])
            expected_start = try_parse(expected['start_time'])
            expected_end = try_parse(expected['end_time'])
            
            # Compare times with tolerance (within 1 minute)
            self.assertLessEqual(abs((actual_start - expected_start).total_seconds()), 60,
                               f"Break {i+1} start time mismatch: {actual_start} vs {expected_start}")
            self.assertLessEqual(abs((actual_end - expected_end).total_seconds()), 60,
                               f"Break {i+1} end time mismatch: {actual_end} vs {expected_end}")
            
            # Check duration
            self.assertEqual(actual[3], expected['duration'],
                           f"Break {i+1} duration mismatch: {actual[3]} vs {expected['duration']}")
            
            # Check if it's auto-detected
            self.assertEqual(bool(actual[5]), expected['is_auto'],
                           f"Break {i+1} auto-detection mismatch")
            
            # Check description match (partial match is fine)
            if expected.get('description_contains'):
                self.assertIn(expected['description_contains'], actual[6] or "",
                             f"Break {i+1} description mismatch: '{actual[6]}' should contain '{expected['description_contains']}'")
    
    # Test Cases
    
    def test_simple_no_break_needed(self):
        """Test case where no breaks are needed (work < 6 hours)"""
        # Create a 5-hour workday
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T08:00:00"
        check_out = f"{today}T13:00:00"
        
        logger.info("Testing a 5-hour workday (no breaks needed)")
        attendance_id = self._create_attendance(2, check_in, check_out)
        
        # Verify no breaks are added
        breaks = self._get_breaks(attendance_id)
        self.assertEqual(len(breaks), 0, "No breaks should be added for work < 6 hours")
    
    def test_6_hour_day_with_lunch(self):
        """Test a 6.5 hour day with lunch break (should add 30 min break)"""
        # Create a 6.5-hour workday that spans lunch hour
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T09:00:00"
        check_out = f"{today}T15:30:00"
        
        logger.info("Testing a 6.5-hour workday spanning lunch period")
        attendance_id = self._create_attendance(2, check_in)
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Expected: One 30-minute break during lunch period (12:00-12:30)
        expected_breaks = [{
            'start_time': f"{today}T12:00:00",
            'end_time': f"{today}T12:30:00",
            'duration': 30,
            'is_auto': True,
            'description_contains': "Mittagspause"
        }]
        
        self._check_break_placement(attendance_id, expected_breaks)
    
    def test_9_hour_day_with_lunch(self):
        """Test a 10-hour day with lunch break (should add 45 min break)"""
        # Create a 10-hour workday spanning lunch
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T07:00:00"
        check_out = f"{today}T17:00:00"
        
        logger.info("Testing a 10-hour workday spanning lunch period")
        attendance_id = self._create_attendance(2, check_in)
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Expected: One 45-minute break during lunch period (around 12:00-12:45)
        expected_breaks = [{
            'start_time': f"{today}T12:00:00",
            'end_time': f"{today}T12:45:00",
            'duration': 45,
            'is_auto': True,
            'description_contains': "Mittagspause"
        }]
        
        self._check_break_placement(attendance_id, expected_breaks)
    
    def test_day_after_lunch(self):
        """Test a case where work starts after lunch period"""
        # Create an 8-hour workday starting at 15:00 (after lunch)
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T15:00:00"
        check_out = f"{today}T23:00:00"
        
        logger.info("Testing a workday starting after lunch period")
        attendance_id = self._create_attendance(2, check_in)
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Expected: One 30-minute break at the end of the day
        expected_breaks = [{
            'start_time': f"{today}T22:30:00",
            'end_time': f"{today}T23:00:00",
            'duration': 30,
            'is_auto': True,
            'description_contains': "Ende des Arbeitstages"
        }]
        
        self._check_break_placement(attendance_id, expected_breaks)
    
    def test_day_before_lunch(self):
        """Test a case where work ends before lunch period"""
        # Create a 7-hour workday ending at 11:00 (before lunch)
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T04:00:00"
        check_out = f"{today}T11:00:00"
        
        logger.info("Testing a workday ending before lunch period")
        attendance_id = self._create_attendance(2, check_in)
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Expected: One 30-minute break at the end of the day
        expected_breaks = [{
            'start_time': f"{today}T10:30:00",
            'end_time': f"{today}T11:00:00",
            'duration': 30,
            'is_auto': True,
            'description_contains': "Ende des Arbeitstages"
        }]
        
        self._check_break_placement(attendance_id, expected_breaks)
    
    def test_partial_lunch_period(self):
        """Test a case where work period partially overlaps lunch period"""
        # Create a workday that starts during lunch and ends after
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T12:30:00"
        check_out = f"{today}T19:30:00" # 7 hours
        
        logger.info("Testing a workday starting during lunch period")
        attendance_id = self._create_attendance(2, check_in)
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Expected: One 30-minute break at the end of the day
        # This is because there is limited lunch period available (12:30-14:00)
        expected_breaks = [{
            'start_time': f"{today}T19:00:00",
            'end_time': f"{today}T19:30:00",
            'duration': 30,
            'is_auto': True,
            'description_contains': "Ende des Arbeitstages"
        }]
        
        self._check_break_placement(attendance_id, expected_breaks)
    
    def test_existing_breaks_sufficient(self):
        """Test a case where existing manually added breaks are sufficient"""
        # Create a 9-hour workday
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T08:00:00"
        check_out = f"{today}T17:00:00"
        
        logger.info("Testing a workday with existing breaks")
        attendance_id = self._create_attendance(2, check_in)
        
        # Add a manual 45-minute break
        self._add_manual_break(
            attendance_id,
            f"{today}T12:00:00",
            f"{today}T12:45:00",
            "Lunch break"
        )
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Expected: Only the existing manual break, no auto breaks added
        breaks = self._get_breaks(attendance_id)
        self.assertEqual(len(breaks), 1, "No additional breaks should be added")
        self.assertEqual(breaks[0][3], 45, "Manual break should be 45 minutes")
        self.assertEqual(bool(breaks[0][5]), False, "Break should be manual")
    
    def test_existing_breaks_insufficient(self):
        """Test a case where existing manually added breaks are insufficient"""
        # Create a 9-hour workday
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T08:00:00"
        check_out = f"{today}T17:00:00"
        
        logger.info("Testing a workday with insufficient existing breaks")
        attendance_id = self._create_attendance(2, check_in)
        
        # Add a manual 25-minute break (insufficient for 9 hours, need 45)
        self._add_manual_break(
            attendance_id,
            f"{today}T12:00:00",
            f"{today}T12:25:00",
            "Short lunch break"
        )
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Expected: The manual break + an additional auto break of 20 minutes
        breaks = self._get_breaks(attendance_id)
        self.assertEqual(len(breaks), 2, "Should have 2 breaks: manual + auto")
        
        # Calculate total break time
        total_break_minutes = sum(b[3] for b in breaks)
        self.assertEqual(total_break_minutes, 45, "Total break time should be 45 minutes")
        
        # Check that an auto break was added for the remaining time
        auto_breaks = [b for b in breaks if bool(b[5])]
        self.assertEqual(len(auto_breaks), 1, "Should have 1 auto break")
        self.assertEqual(auto_breaks[0][3], 20, "Auto break should be 20 minutes")
    
    def test_arbzg_setting_disabled(self):
        """Test with ArbZG breaks disabled"""
        # Disable ArbZG breaks in settings
        db = sqlite3.connect(app.config['DATABASE'])
        cursor = db.cursor()
        cursor.execute(
            "UPDATE user_settings SET arbzg_breaks_enabled = 0 WHERE user_id = 0"
        )
        db.commit()
        db.close()
        
        # Create a 9-hour workday
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T08:00:00"
        check_out = f"{today}T17:00:00"
        
        logger.info("Testing with ArbZG breaks disabled")
        attendance_id = self._create_attendance(2, check_in)
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Expected: No breaks added since ArbZG is disabled
        breaks = self._get_breaks(attendance_id)
        self.assertEqual(len(breaks), 0, "No breaks should be added when ArbZG is disabled")
        
        # Re-enable ArbZG breaks for subsequent tests
        db = sqlite3.connect(app.config['DATABASE'])
        cursor = db.cursor()
        cursor.execute(
            "UPDATE user_settings SET arbzg_breaks_enabled = 1 WHERE user_id = 0"
        )
        db.commit()
        db.close()
    
    def test_exactly_6_hours(self):
        """Test a case with exactly 6 hours of work (edge case)"""
        # Create a 6-hour workday
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T08:00:00"
        check_out = f"{today}T14:00:00"  # Exactly 6 hours
        
        logger.info("Testing a workday with exactly 6 hours")
        attendance_id = self._create_attendance(2, check_in)
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Expected: No breaks are needed as ArbZG requires breaks for > 6 hours
        breaks = self._get_breaks(attendance_id)
        self.assertEqual(len(breaks), 0, "No breaks should be added for exactly 6 hours")
    
    def test_just_over_6_hours(self):
        """Test a case with just over 6 hours of work (6 hours and 1 minute)"""
        # Create a workday of 6 hours and 1 minute
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T08:00:00"
        check_out = f"{today}T14:01:00"  # 6 hours and 1 minute
        
        logger.info("Testing a workday with 6 hours and 1 minute")
        attendance_id = self._create_attendance(2, check_in)
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Expected: 30-minute break is needed
        expected_breaks = [{
            'start_time': f"{today}T13:31:00",
            'end_time': f"{today}T14:01:00",
            'duration': 30,
            'is_auto': True,
            'description_contains': "ArbZG"
        }]
        
        self._check_break_placement(attendance_id, expected_breaks)
    
    def test_just_over_9_hours(self):
        """Test a case with just over 9 hours (9 hours and 1 minute)"""
        # Create a workday of 9 hours and 1 minute
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T08:00:00"
        check_out = f"{today}T17:01:00"  # 9 hours and 1 minute
        
        logger.info("Testing a workday with 9 hours and 1 minute")
        attendance_id = self._create_attendance(2, check_in)
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Expected: 45-minute break is needed
        expected_breaks = [{
            'start_time': f"{today}T16:16:00",
            'end_time': f"{today}T17:01:00",
            'duration': 45,
            'is_auto': True,
            'description_contains': "ArbZG"
        }]
        
        self._check_break_placement(attendance_id, expected_breaks)

    def test_improved_lunch_period_handling(self):
        """Test that breaks are properly adjusted to fit within the lunch period"""
        # Create a workday that includes a short lunch window
        today = datetime.now().strftime('%Y-%m-%d')
        check_in = f"{today}T09:00:00"
        check_out = f"{today}T16:00:00"  # 7 hours
        
        logger.info("Testing improved lunch period handling")
        attendance_id = self._create_attendance(2, check_in)
        
        # Simulate checkout
        self._simulate_checkout(2, attendance_id, check_out)
        
        # Get the lunch break
        breaks = self._get_breaks(attendance_id)
        self.assertEqual(len(breaks), 1, "Should have 1 break added")
        
        # Extract break time details
        break_start = try_parse(breaks[0][1])
        break_end = try_parse(breaks[0][2])
        break_duration = breaks[0][3]
        
        # Check that the break fits within the lunch period (11:30-14:00)
        lunch_start = datetime.strptime(f"{today}T11:30:00", '%Y-%m-%dT%H:%M:%S')
        lunch_end = datetime.strptime(f"{today}T14:00:00", '%Y-%m-%dT%H:%M:%S')
        
        self.assertGreaterEqual(break_start, lunch_start, 
                               f"Break should not start before lunch period ({break_start} < {lunch_start})")
        self.assertLessEqual(break_end, lunch_end, 
                            f"Break should not end after lunch period ({break_end} > {lunch_end})")
        self.assertEqual(break_duration, 30, "Break duration should be 30 minutes")

if __name__ == '__main__':
    unittest.main()
