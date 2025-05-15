from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify, send_file
from markupsafe import Markup
import sqlite3
import os
import logging
from datetime import datetime, timedelta
import pytz
from flask_bcrypt import Bcrypt
from functools import wraps
import json
import csv
import io
import datetime as dt
from werkzeug.utils import secure_filename
import traceback # Added for more detailed error logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# For PDF export
try:
    import pdfkit
except ImportError:
    pdfkit = None

# Helper function to parse datetime strings
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

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this in production
bcrypt = Bcrypt(app)
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'attendance.db')

# Helper functions for templates
def get_duration(start_time, end_time):
    try:
        start_dt = try_parse(start_time)
        end_dt = try_parse(end_time)
        if start_dt and end_dt:
            duration = end_dt - start_dt
            total_seconds = max(0, int(duration.total_seconds()))
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}"
        return "-"
    except Exception:
        return "-"

def format_minutes(minutes):
    if minutes is None:
        return "-"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

# Add template helpers to Jinja environment
app.jinja_env.globals.update(get_duration=get_duration)
app.jinja_env.globals.update(format_minutes=format_minutes)

# Set the timezone to CEST (Central European Summer Time)
TIMEZONE = 'Europe/Berlin'

def get_local_time():
    """Get the current time in CEST (Central European Summer/Winter Time)"""
    return datetime.now(pytz.timezone(TIMEZONE))

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def check_and_fix_db_schema():
    """Check and fix database schema issues."""
    print("Checking and fixing database schema...")
    
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Check if the arbzg_breaks_enabled column exists in user_settings
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'arbzg_breaks_enabled' not in columns:
            print("Adding arbzg_breaks_enabled column to user_settings...")
            try:
                cursor.execute("ALTER TABLE user_settings ADD COLUMN arbzg_breaks_enabled BOOLEAN DEFAULT 1")
                cursor.execute("UPDATE user_settings SET arbzg_breaks_enabled = 1")
                db.commit()
                print("Added arbzg_breaks_enabled column successfully")
            except sqlite3.Error as e:
                print(f"Error adding column: {e}")
        
        # Add lunch period preference columns
        lunch_period_columns = [
            ('lunch_period_start_hour', 'INTEGER DEFAULT 11'),
            ('lunch_period_start_minute', 'INTEGER DEFAULT 30'),
            ('lunch_period_end_hour', 'INTEGER DEFAULT 14'),
            ('lunch_period_end_minute', 'INTEGER DEFAULT 0')
        ]
        
        for column_name, column_def in lunch_period_columns:
            if column_name not in columns:
                print(f"Adding {column_name} column to user_settings...")
                try:
                    cursor.execute(f"ALTER TABLE user_settings ADD COLUMN {column_name} {column_def}")
                    db.commit()
                    print(f"Added {column_name} column successfully")
                except sqlite3.Error as e:
                    print(f"Error adding column {column_name}: {e}")
        
        # Check if the description column exists in breaks table
        cursor.execute("PRAGMA table_info(breaks)")
        break_columns = [column[1] for column in cursor.fetchall()]
        
        if 'description' not in break_columns:
            print("Adding description column to breaks table...")
            try:
                cursor.execute("ALTER TABLE breaks ADD COLUMN description TEXT")
                db.commit()
                print("Added description column successfully")
            except sqlite3.Error as e:
                print(f"Error adding column: {e}")
        
        print("Database schema check and fix completed")


def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            check_in TIMESTAMP,
            check_out TIMESTAMP,
            has_auto_breaks BOOLEAN DEFAULT 0,
            billable_minutes INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        # Create breaks table for automatic break detection
        cursor.execute('''CREATE TABLE IF NOT EXISTS breaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attendance_id INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_minutes INTEGER,
            is_excluded_from_billing BOOLEAN DEFAULT 0,
            is_auto_detected BOOLEAN DEFAULT 0,
            description TEXT,
            FOREIGN KEY(attendance_id) REFERENCES attendance(id)
        )''')
        # Create user settings table
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            auto_break_detection_enabled BOOLEAN DEFAULT 0,
            auto_break_threshold_minutes INTEGER DEFAULT 30,
            exclude_breaks_from_billing BOOLEAN DEFAULT 0,
            arbzg_breaks_enabled BOOLEAN DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        # Create consent table for GDPR compliance
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_consents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            consent_status TEXT,
            consent_date TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        # Create data deletion log table
        cursor.execute('''CREATE TABLE IF NOT EXISTS data_deletion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            deletion_date TIMESTAMP,
            record_count INTEGER
        )''')
        # Insert default admin if not exists
        cursor.execute('SELECT * FROM users WHERE username=?', ("admin",))
        if cursor.fetchone() is None:
            hashed_password = bcrypt.generate_password_hash("admin").decode('utf-8')
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', ("admin", hashed_password))
        
        # Check if user_settings table has defaults for system-wide settings (user_id = 0)
        cursor.execute('SELECT id FROM user_settings WHERE user_id = 0')
        if cursor.fetchone() is None:
            # Insert default system-wide settings
            cursor.execute('''INSERT INTO user_settings 
                          (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing, arbzg_breaks_enabled)
                          VALUES (0, 1, 30, 1, 1)''')
            print("Inserted default system-wide break settings")
        
        db.commit()
        
        # Run the database schema checker and fixer
        check_and_fix_db_schema()

@app.route('/')
def index():
    # Check if user is logged in
    if not session.get('username'):
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Admin can see all users
    if session.get('admin_logged_in'):
        cursor.execute('SELECT id, username FROM users')
        users = cursor.fetchall()
    else:
        # Regular users can only see themselves
        cursor.execute('SELECT id, username FROM users WHERE id = ?', (session.get('user_id'),))
        users = cursor.fetchall()
    
    return render_template('index.html', users=users)

@app.route('/user_break_preferences')
def user_break_preferences():
    """User-specific break preferences page"""
    if not session.get('logged_in') and not session.get('username'):
        return redirect(url_for('login'))
    
    # Get the current user's ID
    user_id = session.get('user_id')
    
    # Get the user's current preferences
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute("""SELECT 
                        lunch_period_start_hour, lunch_period_start_minute,
                        lunch_period_end_hour, lunch_period_end_minute,
                        prefer_consolidated_breaks, break_timing_strategy,
                        min_break_duration, max_breaks_per_day, preferred_break_spacing
                      FROM user_settings 
                      WHERE user_id = ?""", (user_id,))
        preferences_row = cursor.fetchone()
        
        # Create a preferences dictionary
        preferences = {}
        if preferences_row:
            preferences = {
                'lunch_period_start_hour': preferences_row[0],
                'lunch_period_start_minute': preferences_row[1],
                'lunch_period_end_hour': preferences_row[2],
                'lunch_period_end_minute': preferences_row[3]
            }
            
            # Add the enhanced preferences if they exist
            if len(preferences_row) > 4:
                preferences.update({
                    'prefer_consolidated_breaks': bool(preferences_row[4]),
                    'break_timing_strategy': preferences_row[5] or 'lunch_priority',
                    'min_break_duration': preferences_row[6] or 15,
                    'max_breaks_per_day': preferences_row[7] or 3,
                    'preferred_break_spacing': preferences_row[8] or 120
                })
    except sqlite3.OperationalError as e:
        app.logger.warning(f"Error fetching user break preferences: {e}")
        preferences = {
            'lunch_period_start_hour': 11,
            'lunch_period_start_minute': 30,
            'lunch_period_end_hour': 14,
            'lunch_period_end_minute': 0,
            'prefer_consolidated_breaks': False,
            'break_timing_strategy': 'lunch_priority',
            'min_break_duration': 15,
            'max_breaks_per_day': 3,
            'preferred_break_spacing': 120
        }
    
    message = request.args.get('message')
    message_type = request.args.get('message_type')
    
    return render_template('user_break_preferences.html', 
                          preferences=preferences, 
                          message=message,
                          message_type=message_type)

@app.route('/update_user_break_preferences', methods=['POST'])
def update_user_break_preferences():
    """Handle submission of user break preferences form"""
    if not session.get('username'):
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    
    # Get form data
    lunch_period_start_hour = int(request.form.get('lunch_period_start_hour', 11))
    lunch_period_start_minute = int(request.form.get('lunch_period_start_minute', 30))
    lunch_period_end_hour = int(request.form.get('lunch_period_end_hour', 14))
    lunch_period_end_minute = int(request.form.get('lunch_period_end_minute', 0))
    prefer_consolidated_breaks = request.form.get('prefer_consolidated_breaks', '0') == '1'
    break_timing_strategy = request.form.get('break_timing_strategy', 'lunch_priority')
    min_break_duration = int(request.form.get('min_break_duration', 15))
    max_breaks_per_day = int(request.form.get('max_breaks_per_day', 3))
    preferred_break_spacing = int(request.form.get('preferred_break_spacing', 120))
    
    # Validate inputs
    if not (0 <= lunch_period_start_hour <= 23 and 0 <= lunch_period_start_minute <= 59 and
            0 <= lunch_period_end_hour <= 23 and 0 <= lunch_period_end_minute <= 59):
        return redirect(url_for('user_break_preferences', 
                        message='Ungültige Zeitangaben für den Mittagszeitraum', 
                        message_type='danger'))
    
    # Ensure end time is after start time
    lunch_start_minutes = lunch_period_start_hour * 60 + lunch_period_start_minute
    lunch_end_minutes = lunch_period_end_hour * 60 + lunch_period_end_minute
    
    if lunch_end_minutes <= lunch_start_minutes:
        return redirect(url_for('user_break_preferences', 
                        message='Mittagszeitraum-Endzeit muss nach der Startzeit liegen', 
                        message_type='danger'))
    
    # Validate other fields
    if min_break_duration < 5 or min_break_duration > 60:
        return redirect(url_for('user_break_preferences', 
                        message='Minimale Pausendauer muss zwischen 5 und 60 Minuten liegen', 
                        message_type='danger'))
    
    if max_breaks_per_day < 1 or max_breaks_per_day > 5:
        return redirect(url_for('user_break_preferences', 
                        message='Maximale Pausenanzahl muss zwischen 1 und 5 liegen', 
                        message_type='danger'))
    
    if preferred_break_spacing < 60 or preferred_break_spacing > 240:
        return redirect(url_for('user_break_preferences', 
                        message='Bevorzugter Pausenabstand muss zwischen 60 und 240 Minuten liegen', 
                        message_type='danger'))
    
    # Check if break timing strategy is valid
    valid_strategies = ['lunch_priority', 'distributed', 'end_of_day']
    if break_timing_strategy not in valid_strategies:
        break_timing_strategy = 'lunch_priority'
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Check if user already has preferences
        cursor.execute("SELECT id FROM user_settings WHERE user_id = ?", (user_id,))
        existing_user_settings = cursor.fetchone()
        
        if existing_user_settings:
            # Update existing settings
            try:
                cursor.execute("""UPDATE user_settings SET 
                                lunch_period_start_hour = ?,
                                lunch_period_start_minute = ?,
                                lunch_period_end_hour = ?,
                                lunch_period_end_minute = ?,
                                prefer_consolidated_breaks = ?,
                                break_timing_strategy = ?,
                                min_break_duration = ?,
                                max_breaks_per_day = ?,
                                preferred_break_spacing = ?
                                WHERE user_id = ?""", 
                                (lunch_period_start_hour, lunch_period_start_minute,
                                lunch_period_end_hour, lunch_period_end_minute,
                                prefer_consolidated_breaks, break_timing_strategy,
                                min_break_duration, max_breaks_per_day, preferred_break_spacing,
                                user_id))
            except sqlite3.OperationalError as e:
                # Columns might not exist yet
                app.logger.info(f"Updating only lunch period settings due to schema: {e}")
                cursor.execute("""UPDATE user_settings SET 
                                lunch_period_start_hour = ?,
                                lunch_period_start_minute = ?,
                                lunch_period_end_hour = ?,
                                lunch_period_end_minute = ?
                                WHERE user_id = ?""", 
                                (lunch_period_start_hour, lunch_period_start_minute,
                                lunch_period_end_hour, lunch_period_end_minute,
                                user_id))
        else:
            # Insert new user settings
            try:
                cursor.execute("""INSERT INTO user_settings 
                                (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, 
                                exclude_breaks_from_billing, arbzg_breaks_enabled,
                                lunch_period_start_hour, lunch_period_start_minute,
                                lunch_period_end_hour, lunch_period_end_minute,
                                prefer_consolidated_breaks, break_timing_strategy,
                                min_break_duration, max_breaks_per_day, preferred_break_spacing)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (user_id, True, 30, True, True,
                                lunch_period_start_hour, lunch_period_start_minute,
                                lunch_period_end_hour, lunch_period_end_minute,
                                prefer_consolidated_breaks, break_timing_strategy,
                                min_break_duration, max_breaks_per_day, preferred_break_spacing))
            except sqlite3.OperationalError as e:
                # Columns might not exist yet
                app.logger.info(f"Inserting only basic settings due to schema: {e}")
                cursor.execute("""INSERT INTO user_settings 
                                (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, 
                                exclude_breaks_from_billing, arbzg_breaks_enabled,
                                lunch_period_start_hour, lunch_period_start_minute,
                                lunch_period_end_hour, lunch_period_end_minute)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (user_id, True, 30, True, True,
                                lunch_period_start_hour, lunch_period_start_minute,
                                lunch_period_end_hour, lunch_period_end_minute))
        
        db.commit()
        return redirect(url_for('user_break_preferences', 
                        message='Pauseneinstellungen wurden erfolgreich aktualisiert', 
                        message_type='success'))
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error updating user break preferences: {e}")
        app.logger.error(traceback.format_exc())
        return redirect(url_for('user_break_preferences', 
                        message=f'Fehler beim Aktualisieren der Einstellungen: {str(e)}', 
                        message_type='danger'))

@app.route('/checkin', methods=['POST'])
def checkin():
    db = get_db()
    cursor = db.cursor()
    user_id = request.form.get('user_id')
    now = get_local_time()
    
    # Get username for feedback messages
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    username = cursor.fetchone()[0]
    
    # Check if user has an active check-in (no check-out)
    cursor.execute('''SELECT id FROM attendance 
                      WHERE user_id = ? AND check_out IS NULL 
                      ORDER BY check_in DESC LIMIT 1''', (user_id,))
    active_checkin = cursor.fetchone()
    
    if active_checkin:
        flash(f'{username} ist bereits eingecheckt. Bitte zuerst auschecken.', 'error')
        return redirect(url_for('index'))
    
    # Format the time consistently before storing in the database
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO attendance (user_id, check_in) VALUES (?, ?)', (user_id, now_str))
    
    db.commit()
    flash(f'Erfolgreich eingeloggt: {username} um {now.strftime("%H:%M:%S")}', 'success')
    return redirect(url_for('index'))

@app.route('/checkout', methods=['POST'])
def checkout():
    """
    Handle user checkout and process break time calculations.
    
    This function handles:
    1. Recording checkout time
    2. Calculating total work duration
    3. Processing breaks including ArbZG compliance
       - For work periods > 6 hours: at least 30 minutes break
       - For work periods > 9 hours: at least 45 minutes break
    4. Calculating billable time
    
    If ArbZG compliance is enabled, the system will ensure legally required 
    break times are met by intelligently placing breaks according to user preferences:
    - Different break placement strategies (lunch priority, distributed, end of day)
    - Break consolidation preferences (single longer break vs multiple shorter breaks)
    - Customizable break duration and spacing
    """
    db = get_db()
    cursor = db.cursor()
    user_id = request.form.get('user_id')
    now = get_local_time()
    # Store with consistent format - no timezone info in the database string
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')  # Store as string for database
    
    # Get username for feedback message
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    username = cursor.fetchone()[0]
    
    # Check for confirmation (if required, can be disabled with parameter)
    confirm = request.form.get('confirm', 'false')
    skip_confirmation = request.form.get('skip_confirmation', 'false') == 'true'
    
    # First check for system-wide break settings (user_id = 0)
    cursor.execute('''SELECT auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing 
                    FROM user_settings WHERE user_id = 0''')
    system_settings = cursor.fetchone()
    
    # Set default values
    auto_break_detection = False
    auto_break_threshold = 30
    exclude_breaks = False
    
    # Apply system-wide settings if available
    if system_settings:
        auto_break_detection = bool(system_settings[0])
        auto_break_threshold = int(system_settings[1])
        exclude_breaks = bool(system_settings[2])
    
    # First check if there's an active check-in
    cursor.execute('''SELECT id, check_in FROM attendance 
                     WHERE user_id = ? AND check_out IS NULL 
                     ORDER BY check_in DESC LIMIT 1''', (user_id,))
    active_checkin = cursor.fetchone()
    
    if active_checkin:
        # There is an active check-in, update it with checkout time
        checkin_id = active_checkin[0]
        check_in_time = active_checkin[1]
        
        # Check if confirmation is required for long check-ins
        if confirm != 'true' and not skip_confirmation:
            try:
                checkin_dt = try_parse(check_in_time)
                if checkin_dt:
                    # Calculate hours since check-in
                    duration = now - checkin_dt
                    hours_since_checkin = duration.total_seconds() / 3600
                    
                    # If check-in was more than 10 hours ago, require confirmation
                    if hours_since_checkin > 10:
                        return render_template('checkout_confirm.html', 
                                              user_id=user_id, 
                                              username=username, 
                                              check_in_time=checkin_dt.strftime("%H:%M:%S"), 
                                              hours=int(hours_since_checkin))
            except Exception as e:
                # If there's an error calculating time, proceed with checkout
                print(f"Error while checking confirmation need: {str(e)}")
        
        # Calculate billable time and store checkout
        billable_minutes = 0
        
        try:
            checkin_dt = try_parse(check_in_time) 
            checkout_dt = try_parse(now_str) 
            
            if not (checkin_dt and checkout_dt):
                flash('Fehler beim Parsen der Check-in/Check-out Zeiten.', 'error')
                if 'db' in locals(): # Check if db is defined
                    db.close()
                return redirect(url_for('index'))

            total_work_duration_minutes = int((checkout_dt - checkin_dt).total_seconds() / 60)
            
            # Check if we should use user_settings or system_settings table
            try:
                # Check if the arbzg_breaks_enabled column exists
                cursor.execute("PRAGMA table_info(user_settings)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # Default values if settings not found
                auto_break_detection_enabled = False
                auto_break_threshold = 30
                exclude_breaks_from_billing_applies = False
                arbzg_breaks_enabled = True  # Default to enabled for compatibility
                
                if 'arbzg_breaks_enabled' in columns:
                    # The column exists, use it in the query
                    cursor.execute('''SELECT auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing, arbzg_breaks_enabled
                                  FROM user_settings WHERE user_id = 0''')
                    settings = cursor.fetchone()
                    
                    if settings:
                        auto_break_detection_enabled = bool(settings[0])
                        auto_break_threshold = int(settings[1])
                        exclude_breaks_from_billing_applies = bool(settings[2])
                        arbzg_breaks_enabled = bool(settings[3])
                else:
                    # The column doesn't exist, query without it
                    cursor.execute('''SELECT auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing
                                  FROM user_settings WHERE user_id = 0''')
                    settings = cursor.fetchone()
                    
                    if settings:
                        auto_break_detection_enabled = bool(settings[0])
                        auto_break_threshold = int(settings[1])
                        exclude_breaks_from_billing_applies = bool(settings[2])
                    
                    # Add the column for future use
                    try:
                        cursor.execute("ALTER TABLE user_settings ADD COLUMN arbzg_breaks_enabled BOOLEAN DEFAULT 1")
                        cursor.execute("UPDATE user_settings SET arbzg_breaks_enabled = 1")
                        db.commit()
                        app.logger.info("Added arbzg_breaks_enabled column to user_settings table")
                    except sqlite3.Error as e:
                        app.logger.warning(f"Error adding column: {e}")
            except Exception:
                # Try system_settings table as fallback
                cursor.execute("SELECT value FROM system_settings WHERE key = 'auto_break_detection'")
                auto_break_setting = cursor.fetchone()
                auto_break_detection_enabled = auto_break_setting[0] == '1' if auto_break_setting else False
    
                cursor.execute("SELECT value FROM system_settings WHERE key = 'exclude_breaks_from_billing'")
                exclude_breaks_setting = cursor.fetchone()
                exclude_breaks_from_billing_applies = exclude_breaks_setting[0] == '1' if exclude_breaks_setting else False
            except Exception as e:
                app.logger.error(f"Error fetching break settings: {e}")
                # Fallback to defaults if there's any error
                auto_break_detection_enabled = False
                exclude_breaks_from_billing_applies = False

            has_auto_breaks_flag = False # Initialize flag
            
            # Automatic break management according to labor laws (ArbZG)
            if auto_break_detection_enabled and total_work_duration_minutes > 0 and arbzg_breaks_enabled: 
                app.logger.info(f"Processing ArbZG break requirements for user {username}, attendance_id {checkin_id}")
                app.logger.info(f"Total work duration: {total_work_duration_minutes} minutes ({total_work_duration_minutes/60:.2f} hours)")
                
                # Calculate statutory break requirements based on German labor law
                # ArbZG § 4 mandates breaks as follows:
                # - For work periods > 6 hours: at least 30 minutes break
                # - For work periods > 9 hours: at least 45 minutes break
                statutory_break_due_minutes = 0
                if total_work_duration_minutes > 9 * 60:  # More than 9 hours
                    statutory_break_due_minutes = 45
                    app.logger.info(f"Work period > 9 hours: 45 minutes break required")
                elif total_work_duration_minutes > 6 * 60:  # More than 6 hours
                    statutory_break_due_minutes = 30
                    app.logger.info(f"Work period > 6 hours: 30 minutes break required")
                else:
                    app.logger.info(f"Work period <= 6 hours: No statutory break required")

                if statutory_break_due_minutes > 0:
                    cursor.execute("SELECT id, start_time, end_time, duration_minutes, description FROM breaks WHERE attendance_id = ?", (checkin_id,))
                    existing_breaks = cursor.fetchall()
                    
                    if existing_breaks:
                        app.logger.info(f"Found {len(existing_breaks)} existing breaks:")
                        existing_break_minutes_taken = 0
                        for i, break_record in enumerate(existing_breaks):
                            br_id, br_start, br_end, br_duration, br_desc = break_record
                            app.logger.info(f"  Break {i+1}: {br_start} to {br_end}, {br_duration} min, description: {br_desc or 'none'}")
                            existing_break_minutes_taken += br_duration
                        app.logger.info(f"Total existing break time: {existing_break_minutes_taken} minutes")
                    else:
                        app.logger.info("No existing breaks found")
                        existing_break_minutes_taken = 0
                    
                    break_to_add_minutes = statutory_break_due_minutes - existing_break_minutes_taken
                    app.logger.info(f"Additional break minutes needed: {break_to_add_minutes} min")
                    
                    if break_to_add_minutes > 0:
                        # Get user's preferences for breaks
                        user_break_preferences = {
                            'lunch_period_start_hour': 11,
                            'lunch_period_start_minute': 30,
                            'lunch_period_end_hour': 14,
                            'lunch_period_end_minute': 0,
                            'prefer_consolidated_breaks': False,
                            'break_timing_strategy': 'lunch_priority',
                            'min_break_duration': 15,
                            'max_breaks_per_day': 3,
                            'preferred_break_spacing': 120
                        }
                        
                        # Try to fetch user-specific break preferences
                        try:
                            cursor.execute("""SELECT 
                                lunch_period_start_hour, lunch_period_start_minute,
                                lunch_period_end_hour, lunch_period_end_minute,
                                prefer_consolidated_breaks, break_timing_strategy,
                                min_break_duration, max_breaks_per_day, preferred_break_spacing
                                FROM user_settings WHERE user_id = ?""", (user_id,))
                            preferences_row = cursor.fetchone()
                            
                            if preferences_row:
                                # Update with user preferences if available
                                user_break_preferences['lunch_period_start_hour'] = preferences_row[0] or user_break_preferences['lunch_period_start_hour']
                                user_break_preferences['lunch_period_start_minute'] = preferences_row[1] or user_break_preferences['lunch_period_start_minute']
                                user_break_preferences['lunch_period_end_hour'] = preferences_row[2] or user_break_preferences['lunch_period_end_hour']
                                user_break_preferences['lunch_period_end_minute'] = preferences_row[3] or user_break_preferences['lunch_period_end_minute']
                                
                                # Check if enhanced preferences exist
                                if len(preferences_row) > 4:
                                    user_break_preferences['prefer_consolidated_breaks'] = bool(preferences_row[4])
                                    user_break_preferences['break_timing_strategy'] = preferences_row[5] or user_break_preferences['break_timing_strategy']
                                    user_break_preferences['min_break_duration'] = preferences_row[6] or user_break_preferences['min_break_duration']
                                    user_break_preferences['max_breaks_per_day'] = preferences_row[7] or user_break_preferences['max_breaks_per_day']
                                    user_break_preferences['preferred_break_spacing'] = preferences_row[8] or user_break_preferences['preferred_break_spacing']
                                
                                app.logger.info(f"Using user-specific break preferences: {user_break_preferences}")
                        except sqlite3.OperationalError as e:
                            app.logger.warning(f"Error fetching user break preferences: {e}. Using defaults.")
                        
                        # Define lunch period based on preferences
                        lunch_start_hour = user_break_preferences['lunch_period_start_hour']
                        lunch_start_minute = user_break_preferences['lunch_period_start_minute']
                        lunch_end_hour = user_break_preferences['lunch_period_end_hour']
                        lunch_end_minute = user_break_preferences['lunch_period_end_minute']
                        
                        # Get other preferences
                        prefer_consolidated = user_break_preferences['prefer_consolidated_breaks']
                        break_timing_strategy = user_break_preferences['break_timing_strategy']
                        min_break_duration = user_break_preferences['min_break_duration']
                        max_breaks = user_break_preferences['max_breaks_per_day']
                        preferred_break_spacing = user_break_preferences['preferred_break_spacing']
                        
                        # Log the break strategy being used
                        app.logger.info(f"Break timing strategy: {break_timing_strategy}")
                        
                        # Determine how to distribute breaks
                        breaks_to_add = []
                        
                        # Define lunch period
                        lunch_start_time = checkin_dt.replace(hour=lunch_start_hour, minute=lunch_start_minute, second=0)
                        lunch_end_time = checkin_dt.replace(hour=lunch_end_hour, minute=lunch_end_minute, second=0)
                        
                        # Calculate available lunch period
                        lunch_period_available = checkin_dt <= lunch_end_time and checkout_dt >= lunch_start_time
                        
                        # Choose break placement based on strategy
                        if break_timing_strategy == 'end_of_day':
                            # End of day strategy - always place breaks at the end
                            # Not affected by break consolidation preference
                            app.logger.info(f"Using end_of_day strategy for break placement")
                            
                            auto_break_end_dt = checkout_dt
                            auto_break_start_dt = checkout_dt - timedelta(minutes=break_to_add_minutes)
                            
                            # Ensure break doesn't start before check-in
                            if auto_break_start_dt < checkin_dt:
                                auto_break_start_dt = checkin_dt
                                actual_break_minutes = int((auto_break_end_dt - auto_break_start_dt).total_seconds() / 60)
                                if actual_break_minutes < break_to_add_minutes:
                                    break_to_add_minutes = actual_break_minutes
                                    app.logger.warning(f"Break adjusted to {break_to_add_minutes} min due to work period constraints")
                            
                            if break_to_add_minutes > 0:
                                breaks_to_add.append({
                                    'start': auto_break_start_dt,
                                    'end': auto_break_end_dt,
                                    'minutes': break_to_add_minutes,
                                    'description': "ArbZG §4 Pflichtpause (Ende des Arbeitstages)"
                                })
                        
                        elif break_timing_strategy == 'distributed':
                            # Distributed strategy - evenly distribute breaks throughout the day
                            app.logger.info(f"Using distributed strategy for break placement")
                            
                            # Work period boundaries
                            work_start = checkin_dt
                            work_end = checkout_dt
                            work_duration_minutes = total_work_duration_minutes
                            
                            if prefer_consolidated:
                                # Prefer one break if possible (still using distributed strategy for placement)
                                app.logger.info("Consolidating breaks as per user preference")
                                
                                # Place single break in the middle of the work day
                                ideal_break_time = work_start + (work_end - work_start) / 2
                                
                                auto_break_start_dt = ideal_break_time - timedelta(minutes=break_to_add_minutes/2)
                                auto_break_end_dt = auto_break_start_dt + timedelta(minutes=break_to_add_minutes)
                                
                                # Ensure break times are within work period
                                if auto_break_start_dt < work_start:
                                    auto_break_start_dt = work_start
                                    auto_break_end_dt = auto_break_start_dt + timedelta(minutes=break_to_add_minutes)
                                
                                if auto_break_end_dt > work_end:
                                    auto_break_end_dt = work_end
                                    auto_break_start_dt = auto_break_end_dt - timedelta(minutes=break_to_add_minutes)
                                    if auto_break_start_dt < work_start:
                                        auto_break_start_dt = work_start
                                        # This will make the break shorter than required
                                        actual_break_minutes = int((auto_break_end_dt - auto_break_start_dt).total_seconds() / 60)
                                        if actual_break_minutes < break_to_add_minutes:
                                            break_to_add_minutes = actual_break_minutes
                                            app.logger.warning(f"Break adjusted to {break_to_add_minutes} min due to work period constraints")
                                
                                if break_to_add_minutes > 0:
                                    breaks_to_add.append({
                                        'start': auto_break_start_dt,
                                        'end': auto_break_end_dt,
                                        'minutes': break_to_add_minutes,
                                        'description': "ArbZG §4 Pflichtpause (Mitte des Arbeitstages)"
                                    })
                            else:
                                # Use multiple breaks with max_breaks limit and min_break_duration
                                app.logger.info(f"Using multiple breaks (up to {max_breaks})")
                                
                                # Calculate how many breaks to add
                                num_breaks = min(max_breaks, max(1, break_to_add_minutes // min_break_duration))
                                if num_breaks == 0:
                                    num_breaks = 1  # Ensure at least one break
                                
                                # Calculate break duration for each break
                                break_duration = break_to_add_minutes // num_breaks
                                if break_duration < min_break_duration:
                                    # If individual breaks would be too short, reduce number of breaks
                                    num_breaks = max(1, break_to_add_minutes // min_break_duration)
                                    break_duration = break_to_add_minutes // num_breaks
                                
                                app.logger.info(f"Distributing {break_to_add_minutes} min into {num_breaks} breaks of ~{break_duration} min each")
                                
                                # Calculate total usable work period for break placement
                                usable_period_minutes = work_duration_minutes - (break_duration * num_breaks)
                                
                                # Ensure we have a valid period
                                if usable_period_minutes <= 0:
                                    # Not enough time to distribute breaks - fall back to end of day
                                    app.logger.warning("Insufficient time for distributed breaks, falling back to end-of-day")
                                    auto_break_end_dt = checkout_dt
                                    auto_break_start_dt = checkout_dt - timedelta(minutes=break_to_add_minutes)
                                    
                                    breaks_to_add.append({
                                        'start': auto_break_start_dt,
                                        'end': auto_break_end_dt,
                                        'minutes': break_to_add_minutes,
                                        'description': "ArbZG §4 Pflichtpause (Ende des Arbeitstages)"
                                    })
                                else:
                                    # Calculate intervals between breaks
                                    interval_minutes = usable_period_minutes // (num_breaks + 1)
                                    
                                    # Distribute breaks
                                    for i in range(num_breaks):
                                        # Calculate position for this break
                                        position_minutes = interval_minutes * (i + 1) + (break_duration * i)
                                        break_start = work_start + timedelta(minutes=position_minutes)
                                        break_end = break_start + timedelta(minutes=break_duration)
                                        
                                        # Ensure the break doesn't go beyond the work period
                                        if break_end > work_end:
                                            break_end = work_end
                                            break_start = break_end - timedelta(minutes=break_duration)
                                            if break_start < work_start:
                                                break_start = work_start
                                                actual_break_minutes = int((break_end - break_start).total_seconds() / 60)
                                                if actual_break_minutes < break_duration:
                                                    break_duration = actual_break_minutes
                                        
                                        if break_duration > 0:
                                            breaks_to_add.append({
                                                'start': break_start,
                                                'end': break_end,
                                                'minutes': break_duration,
                                                'description': f"ArbZG §4 Pflichtpause ({i+1}/{num_breaks})"
                                            })
                        
                        else:  # Default: lunch_priority strategy
                            app.logger.info(f"Using lunch_priority strategy for break placement")
                            
                            lunch_break_added = False
                            
                            # Check if work period spans lunch time
                            if lunch_period_available:
                                # The work period includes the lunch period
                                actual_lunch_start = max(checkin_dt, lunch_start_time)
                                actual_lunch_end = min(checkout_dt, lunch_end_time)
                                
                                # Calculate available lunch period in minutes
                                lunch_period_minutes = int((actual_lunch_end - actual_lunch_start).total_seconds() / 60)
                                
                                if lunch_period_minutes >= break_to_add_minutes:
                                    # We have enough time in the lunch period to add the break
                                    lunch_midpoint = actual_lunch_start + (actual_lunch_end - actual_lunch_start) / 2
                                    auto_break_start_dt = lunch_midpoint - timedelta(minutes=break_to_add_minutes/2)
                                    auto_break_end_dt = auto_break_start_dt + timedelta(minutes=break_to_add_minutes)
                                    
                                    # Ensure break times remain within the actual lunch period
                                    if auto_break_start_dt < actual_lunch_start:
                                        auto_break_start_dt = actual_lunch_start
                                        auto_break_end_dt = auto_break_start_dt + timedelta(minutes=break_to_add_minutes)
                                    
                                    if auto_break_end_dt > actual_lunch_end:
                                        auto_break_end_dt = actual_lunch_end
                                        auto_break_start_dt = auto_break_end_dt - timedelta(minutes=break_to_add_minutes)
                                        # Final check to ensure we're not going before lunch start
                                        if auto_break_start_dt < actual_lunch_start:
                                            auto_break_start_dt = actual_lunch_start
                                            actual_break_minutes = int((auto_break_end_dt - auto_break_start_dt).total_seconds() / 60)
                                            if actual_break_minutes < break_to_add_minutes:
                                                app.logger.warning(f"Lunch period too short: Required {break_to_add_minutes} minutes, but only {actual_break_minutes} available.")
                                                
                                                # If we prefer consolidated breaks, place the remaining at the end of the day
                                                if prefer_consolidated:
                                                    remainder_minutes = break_to_add_minutes - actual_break_minutes
                                                    if remainder_minutes > 0:
                                                        app.logger.info(f"Adding remaining {remainder_minutes} min at end of day")
                                                        end_day_break_end_dt = checkout_dt
                                                        end_day_break_start_dt = checkout_dt - timedelta(minutes=remainder_minutes)
                                                        
                                                        breaks_to_add.append({
                                                            'start': end_day_break_start_dt,
                                                            'end': end_day_break_end_dt,
                                                            'minutes': remainder_minutes,
                                                            'description': "ArbZG §4 Pflichtpause (Zusätzlich zum Ende des Arbeitstages)"
                                                        })
                                                
                                                # Adjust the lunch break to what's available
                                                break_to_add_minutes = actual_break_minutes
                                    
                                    if break_to_add_minutes > 0:
                                        breaks_to_add.append({
                                            'start': auto_break_start_dt,
                                            'end': auto_break_end_dt,
                                            'minutes': break_to_add_minutes,
                                            'description': "Gesetzliche Mittagspause (ArbZG §4) - Intelligent platziert"
                                        })
                                        lunch_break_added = True
                            
                            # If we couldn't add a lunch break (or not all of the required break), add at the end of the day
                            if not lunch_break_added:
                                app.logger.info(f"No lunch break possible, adding {break_to_add_minutes} min break at end of day")
                                
                                auto_break_end_dt = checkout_dt
                                auto_break_start_dt = checkout_dt - timedelta(minutes=break_to_add_minutes)

                                # Ensure auto break start is not before check-in time
                                if auto_break_start_dt < checkin_dt:
                                    app.logger.warning(f"Break would start before check-in time. Adjusting to check-in time: {checkin_dt}")
                                    auto_break_start_dt = checkin_dt
                                    actual_break_minutes = int((auto_break_end_dt - auto_break_start_dt).total_seconds() / 60)
                                    if actual_break_minutes < break_to_add_minutes:
                                        app.logger.warning(f"Cannot add full {break_to_add_minutes} min break - workday too short. Adding {actual_break_minutes} min instead.")
                                        break_to_add_minutes = actual_break_minutes
                                
                                if break_to_add_minutes > 0:
                                    breaks_to_add.append({
                                        'start': auto_break_start_dt,
                                        'end': auto_break_end_dt,
                                        'minutes': break_to_add_minutes,
                                        'description': "ArbZG §4 Pflichtpause (Ende des Arbeitstages)"
                                    })
                        
                        # Now add all calculated breaks to the database
                        for break_entry in breaks_to_add:
                            auto_break_start_str = break_entry['start'].strftime('%Y-%m-%d %H:%M:%S')
                            auto_break_end_str = break_entry['end'].strftime('%Y-%m-%d %H:%M:%S')
                            break_minutes = break_entry['minutes']
                            break_description = break_entry['description']
                            
                            app.logger.info(f"Adding break: {auto_break_start_str} to {auto_break_end_str} ({break_minutes} min) - {break_description}")
                            
                            # Ensure the break slot is valid (start < end) and at least 1 minute long before inserting
                            if break_entry['start'] < break_entry['end'] and break_minutes > 0:
                                cursor.execute("""INSERT INTO breaks 
                                              (attendance_id, start_time, end_time, duration_minutes, is_excluded_from_billing, is_auto_detected, description)
                                              VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                           (checkin_id, auto_break_start_str, auto_break_end_str, break_minutes, 
                                            exclude_breaks_from_billing_applies, True, break_description))
                                has_auto_breaks_flag = True
                            else:
                                app.logger.warning(f"Skipped inserting auto-break for attendance_id {checkin_id} due to invalid time slot.")

            # Recalculate total_excluded_break_minutes (includes any newly added auto-breaks if they are set to be excluded)
            cursor.execute("""
                SELECT SUM(duration_minutes) FROM breaks 
                WHERE attendance_id = ? AND is_excluded_from_billing = 1
            """, (checkin_id,))
            total_excluded_break_minutes_row = cursor.fetchone()
            total_excluded_break_minutes = total_excluded_break_minutes_row[0] if total_excluded_break_minutes_row and total_excluded_break_minutes_row[0] is not None else 0
            
            billable_minutes = total_work_duration_minutes - total_excluded_break_minutes
            if billable_minutes < 0: # Billable time cannot be negative
                billable_minutes = 0

            # Update attendance record with checkout time, calculated billable minutes, and auto_break flag
            cursor.execute('''UPDATE attendance SET check_out = ?, billable_minutes = ?, has_auto_breaks = ?
                              WHERE id = ?''', (now_str, billable_minutes, has_auto_breaks_flag, checkin_id))
            db.commit()
            
            username = session.get('username', 'Benutzer') # Get username from session, with a default
            # Update flash message to include total work duration, total breaks, and billable time
            flash_message = f'Erfolgreich ausgeloggt: {username} um {now.strftime("%H:%M:%S")}. '
            flash_message += f'Gesamtarbeitszeit: {format_minutes(total_work_duration_minutes)}. '
            
            # Get total break duration (both excluded and included) for the flash message
            cursor.execute("SELECT SUM(duration_minutes) FROM breaks WHERE attendance_id = ?", (checkin_id,))
            total_breaks_for_flash_row = cursor.fetchone()
            total_breaks_for_flash = total_breaks_for_flash_row[0] if total_breaks_for_flash_row and total_breaks_for_flash_row[0] is not None else 0
            
            flash_message += f'Pausen gesamt: {format_minutes(total_breaks_for_flash)}. '
            flash_message += f'Verrechenbare Zeit: {format_minutes(billable_minutes)}.'
            if has_auto_breaks_flag:
                flash_message += ' (Automatische Pausen wurden hinzugefügt.)'
            flash(flash_message, 'success')

        except Exception as e:
            if 'db' in locals(): # Check if db was initialized
                db.rollback()
            app.logger.error(f"Error during checkout for user {session.get('user_id','<unknown>')}, checkin_id {checkin_id if 'checkin_id' in locals() else '<unknown>'}: {e}") # checkin_id might not be defined if error is early
            app.logger.error(traceback.format_exc()) # Ensure traceback is imported
            flash(f'Ein Fehler ist beim Auschecken aufgetreten. Bitte versuchen Sie es erneut oder kontaktieren Sie den Support.', 'error') # Generic error for user
        finally:
            if 'db' in locals(): 
                db.close()
    else:
        # Check if there was any check-in today
        today = datetime.now().strftime('%Y-%m-%d')  # Using naive datetime for date comparison
        cursor.execute('''SELECT check_in, check_out FROM attendance 
                         WHERE user_id = ? AND date(check_in) = ? 
                         ORDER BY check_in DESC LIMIT 1''', (user_id, today))
        recent = cursor.fetchone()
        
        if recent and recent[1]:  # Already has checkout
            flash(f'{username} has already checked out today at {recent[1][11:19]}. Please check in first.', 'error')
        elif not recent:  # No check-in today at all
            flash(f'Kein Check-in für {username} heute gefunden. Bitte zuerst einchecken.', 'error')
        else:
            flash(f'Kein aktiver Check-in für {username} gefunden. Etwas ist schiefgelaufen.', 'error')
    
    return redirect(url_for('index'))

@app.route('/break_settings')
def break_settings():
    """
    Handle the break settings page (admin only).
    
    This route displays and handles system-wide break settings including:
    - Automatic break detection
    - Break threshold time
    - Whether breaks are excluded from billing
    
    The system supports both user_settings and system_settings tables for
    backward compatibility after database schema migrations.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
    
    # Check if user is an admin
    if not session.get('admin_logged_in'):
        flash('Nur Administratoren können auf die Pauseneinstellungen zugreifen', 'error')
        return redirect(url_for('index'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Get global (system-wide) settings
    user_settings = {
        'auto_break_detection': False,
        'auto_break_threshold': 30,
        'exclude_breaks': False,
        'arbzg_breaks_enabled': True  # Default to enabled for compatibility
    }
    
    try:
        # First try to get settings from user_settings table
        try:
            cursor.execute('''SELECT auto_break_detection_enabled, auto_break_threshold_minutes, 
                            exclude_breaks_from_billing, arbzg_breaks_enabled,
                            lunch_period_start_hour, lunch_period_start_minute,
                            lunch_period_end_hour, lunch_period_end_minute 
                            FROM user_settings WHERE user_id = 0''')
            settings = cursor.fetchone()
            
            if settings:
                user_settings = {
                    'auto_break_detection': settings[0],
                    'auto_break_threshold': settings[1],
                    'exclude_breaks': settings[2],
                    'arbzg_breaks_enabled': settings[3] if len(settings) > 3 else True
                }
                
                # Add lunch period settings if available
                if len(settings) > 7:
                    user_settings.update({
                        'lunch_period_start_hour': settings[4],
                        'lunch_period_start_minute': settings[5],
                        'lunch_period_end_hour': settings[6],
                        'lunch_period_end_minute': settings[7]
                    })
        except sqlite3.OperationalError:
            # The arbzg_breaks_enabled column might not exist yet, try without it
            cursor.execute('''SELECT auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing
                            FROM user_settings WHERE user_id = 0''')
            settings = cursor.fetchone()
            
            if settings:
                user_settings = {
                    'auto_break_detection': settings[0],
                    'auto_break_threshold': settings[1],
                    'exclude_breaks': settings[2],
                    'arbzg_breaks_enabled': True  # Default to enabled
                }
                
                # Add the missing column
                try:
                    cursor.execute("ALTER TABLE user_settings ADD COLUMN arbzg_breaks_enabled BOOLEAN DEFAULT 1")
                    cursor.execute("UPDATE user_settings SET arbzg_breaks_enabled = 1")
                    db.commit()
                    print("Added arbzg_breaks_enabled column to user_settings table")
                except sqlite3.Error as e:
                    print(f"Error adding column: {e}")
        else:
            # If not found, try to get from system_settings table
            try:
                # Get auto_break_detection setting
                cursor.execute("SELECT value FROM system_settings WHERE key = 'auto_break_detection'")
                auto_break_detection = cursor.fetchone()
                if auto_break_detection:
                    user_settings['auto_break_detection'] = auto_break_detection[0] == '1'
                
                # Get threshold setting (not directly available in system_settings)
                cursor.execute("SELECT value FROM system_settings WHERE key = 'statutory_break_6h_work_threshold'")
                threshold = cursor.fetchone()
                if threshold:
                    # Convert to minutes, use a reasonable value
                    user_settings['auto_break_threshold'] = int(int(threshold[0]) / 60)
                
                # Get exclude_breaks setting
                cursor.execute("SELECT value FROM system_settings WHERE key = 'exclude_breaks_from_billing'")
                exclude_breaks = cursor.fetchone()
                if exclude_breaks:
                    user_settings['exclude_breaks'] = exclude_breaks[0] == '1'
                
                # If found in system_settings, migrate to user_settings for future use
                cursor.execute('''INSERT OR REPLACE INTO user_settings 
                               (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing)
                               VALUES (?, ?, ?, ?)''', 
                               (0, user_settings['auto_break_detection'], 
                                user_settings['auto_break_threshold'], 
                                user_settings['exclude_breaks']))
                db.commit()
                
            except sqlite3.Error as e:
                app.logger.error(f"Error accessing system_settings: {e}")
    except Exception as e:
        app.logger.error(f"Error accessing break settings: {e}")
        # We'll use the default values initialized above
    
    # Get recent break history for all users
    cursor.execute('''
        SELECT b.id, b.start_time, b.end_time, b.duration_minutes, 
               b.is_excluded_from_billing, b.is_auto_detected, 
               u.username, b.description
        FROM breaks b
        JOIN attendance a ON b.attendance_id = a.id
        JOIN users u ON a.user_id = u.id
        ORDER BY b.start_time DESC
        LIMIT 30
    ''')
    break_history = cursor.fetchall()
    
    return render_template('break_settings.html', settings=user_settings, breaks=break_history)

@app.route('/update_user_settings', methods=['POST'])
def update_user_settings():
    """
    Handle the submission of break settings form.
    
    This route processes the form submission from the break settings page
    and updates either the user_settings or system_settings table based on
    what's available in the database.
    
    Settings include:
    - auto_break_detection: Whether breaks should be automatically detected
    - auto_break_threshold: Inactivity time threshold for auto breaks
    - exclude_breaks: Whether breaks should be excluded from billable time
    - arbzg_breaks_enabled: Whether to enforce ArbZG-compliant breaks
    """
    if not session.get('username'):
        return redirect(url_for('login'))
    
    auto_break_detection = request.form.get('auto_break_detection', '0') == '1'
    auto_break_threshold = int(request.form.get('auto_break_threshold', '30'))
    exclude_breaks = request.form.get('exclude_breaks', '0') == '1'
    arbzg_breaks_enabled = request.form.get('arbzg_breaks_enabled', '0') == '1'
    
    # Get lunch period settings
    lunch_period_start_hour = int(request.form.get('lunch_period_start_hour', '11'))
    lunch_period_start_minute = int(request.form.get('lunch_period_start_minute', '30'))
    lunch_period_end_hour = int(request.form.get('lunch_period_end_hour', '14'))
    lunch_period_end_minute = int(request.form.get('lunch_period_end_minute', '0'))
    
    # Validate lunch period times
    if not (0 <= lunch_period_start_hour <= 23 and 0 <= lunch_period_start_minute <= 59 and
            0 <= lunch_period_end_hour <= 23 and 0 <= lunch_period_end_minute <= 59):
        flash('Ungültige Zeitangaben für den Mittagszeitraum. Werte wurden auf Standard zurückgesetzt.', 'error')
        lunch_period_start_hour = 11
        lunch_period_start_minute = 30
        lunch_period_end_hour = 14
        lunch_period_end_minute = 0
    
    # Ensure end time is after start time
    lunch_start_minutes = lunch_period_start_hour * 60 + lunch_period_start_minute
    lunch_end_minutes = lunch_period_end_hour * 60 + lunch_period_end_minute
    
    if lunch_end_minutes <= lunch_start_minutes:
        flash('Mittagszeitraum-Endzeit muss nach der Startzeit liegen. Werte wurden auf Standard zurückgesetzt.', 'error')
        lunch_period_start_hour = 11
        lunch_period_start_minute = 30
        lunch_period_end_hour = 14
        lunch_period_end_minute = 0
    
    db = get_db()
    cursor = db.cursor()
    
    # If admin is updating - use system-wide settings (user_id = 0)
    if session.get('admin_logged_in'):
        user_id = 0  # Special ID for system-wide settings
        flash('Systemweite Pauseneinstellungen wurden aktualisiert', 'success')
    else:
        user_id = session.get('user_id')
    
    try:
        # First check if user_settings table exists and has entries
        cursor.execute('SELECT id FROM user_settings WHERE user_id = ?', (user_id,))
        settings = cursor.fetchone()
        
        if settings:
            # Update existing settings in user_settings
            cursor.execute('''UPDATE user_settings 
                            SET auto_break_detection_enabled = ?, 
                                auto_break_threshold_minutes = ?, 
                                exclude_breaks_from_billing = ?,
                                arbzg_breaks_enabled = ?,
                                lunch_period_start_hour = ?,
                                lunch_period_start_minute = ?,
                                lunch_period_end_hour = ?,
                                lunch_period_end_minute = ?
                            WHERE user_id = ?''', 
                            (auto_break_detection, auto_break_threshold, exclude_breaks, arbzg_breaks_enabled,
                             lunch_period_start_hour, lunch_period_start_minute, lunch_period_end_hour, lunch_period_end_minute,
                             user_id))
        else:
                        # Create new settings in user_settings
            try:
                cursor.execute('''INSERT INTO user_settings 
                          (user_id, auto_break_detection_enabled, auto_break_threshold_minutes, 
                           exclude_breaks_from_billing, arbzg_breaks_enabled,
                           lunch_period_start_hour, lunch_period_start_minute,
                           lunch_period_end_hour, lunch_period_end_minute)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                          (user_id, auto_break_detection, auto_break_threshold, exclude_breaks, arbzg_breaks_enabled,
                           lunch_period_start_hour, lunch_period_start_minute, lunch_period_end_hour, lunch_period_end_minute))
            except sqlite3.Error:
                # If user_settings table doesn't exist, try to use system_settings table
                try:
                    # Update system_settings (key-value store)
                    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", 
                                ('auto_break_detection', '1' if auto_break_detection else '0'))
                    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", 
                                ('exclude_breaks_from_billing', '1' if exclude_breaks else '0'))
                    app.logger.info("Updated settings in system_settings table")
                except sqlite3.Error as e:
                    app.logger.error(f"Error updating settings: {e}")
                    flash('Fehler beim Aktualisieren der Einstellungen.', 'error')
                    return redirect(url_for('break_settings'))
    except Exception as e:
        app.logger.error(f"Error updating user settings: {e}")
        flash('Fehler beim Aktualisieren der Einstellungen.', 'error')
        return redirect(url_for('break_settings'))
    
    db.commit()
    flash('Pauseneinstellungen wurden aktualisiert', 'success')
    
    # Determine where to redirect based on referrer
    referrer = request.referrer
    if referrer and 'break_settings' in referrer:
        return redirect(url_for('break_settings'))
    else:
        return redirect(url_for('index'))

@app.route('/add_break', methods=['POST'])
def add_break():
    """
    Handle adding a manual break to an attendance record.
    
    This route processes form submissions to add break periods to existing
    attendance records. Breaks can be:
    - Marked as excluded from billing or included in billable time
    - Automatically detected or manually added
    - Tracked with precise start and end times
    - Categorized by type (regular, lunch, ArbZG) with descriptions
    
    Short breaks (≤ 5 minutes) are not excluded from billing by default.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
    
    attendance_id = request.form.get('attendance_id')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    is_excluded = request.form.get('is_excluded', '0') == '1'
    is_auto = request.form.get('is_auto', '0') == '1'
    break_type = request.form.get('break_type', 'regular')
    description = request.form.get('description', '')
    
    # Generate description based on break type if not provided
    if not description:
        if break_type == 'lunch':
            description = "Mittagspause (manuell eingetragen)"
        elif break_type == 'arbzg':
            description = "ArbZG Pflichtpause (manuell eingetragen)"
    
    # Calculate duration in minutes
    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    duration = int((end_dt - start_dt).total_seconds() / 60)
    
    # Short auto-breaks (≤ 5 minutes) should not be excluded from billing
    if is_auto and duration <= 5:
        is_excluded = False
    
    db = get_db()
    cursor = db.cursor()
    
    # Check if the description column exists
    cursor.execute("PRAGMA table_info(breaks)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'description' in columns:
        cursor.execute('''INSERT INTO breaks 
                       (attendance_id, start_time, end_time, duration_minutes, 
                       is_excluded_from_billing, is_auto_detected, description)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                       (attendance_id, start_time, end_time, duration, 
                       is_excluded, is_auto, description))
    else:
        # Fallback if description column doesn't exist
        cursor.execute('''INSERT INTO breaks 
                       (attendance_id, start_time, end_time, duration_minutes, 
                       is_excluded_from_billing, is_auto_detected)
                       VALUES (?, ?, ?, ?, ?, ?)''', 
                       (attendance_id, start_time, end_time, duration, 
                       is_excluded, is_auto))
    db.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {'success': True, 'message': 'Pause wurde hinzugefügt'}
    
    flash('Pause wurde hinzugefügt', 'success')
    return redirect(url_for('index'))

@app.route('/get_user_settings')
def get_user_settings():
    if not session.get('username'):
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # First check if the arbzg_breaks_enabled column exists
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'arbzg_breaks_enabled' in columns:
            # Column exists, use it in the query
            cursor.execute('''SELECT auto_break_detection_enabled, auto_break_threshold_minutes, 
                            exclude_breaks_from_billing, arbzg_breaks_enabled,
                            lunch_period_start_hour, lunch_period_start_minute,
                            lunch_period_end_hour, lunch_period_end_minute
                            FROM user_settings WHERE user_id = 0''')
            settings = cursor.fetchone()
            
            if settings:
                result = {
                    'auto_break_detection': settings[0],
                    'auto_break_threshold': settings[1],
                    'exclude_breaks': settings[2],
                    'arbzg_breaks_enabled': settings[3]
                }
                
                # Add lunch period settings if they exist
                if len(settings) > 4:
                    result.update({
                        'lunch_period_start_hour': settings[4],
                        'lunch_period_start_minute': settings[5],
                        'lunch_period_end_hour': settings[6],
                        'lunch_period_end_minute': settings[7]
                    })
                
                return result
        else:
            # Column doesn't exist, run the migration and use defaults for now
            try:
                cursor.execute("ALTER TABLE user_settings ADD COLUMN arbzg_breaks_enabled BOOLEAN DEFAULT 1")
                cursor.execute("UPDATE user_settings SET arbzg_breaks_enabled = 1")
                db.commit()
                print("Added arbzg_breaks_enabled column to user_settings table")
            except sqlite3.Error as e:
                print(f"Error adding column: {e}")
                
            # Query without the new column
            cursor.execute('''SELECT auto_break_detection_enabled, auto_break_threshold_minutes, exclude_breaks_from_billing
                            FROM user_settings WHERE user_id = 0''')
            settings = cursor.fetchone()
            
            if settings:
                return {
                    'auto_break_detection': settings[0],
                    'auto_break_threshold': settings[1],
                    'exclude_breaks': settings[2],
                    'arbzg_breaks_enabled': True  # Default to enabled
                }
    except Exception as e:
        print(f"Error in get_user_settings: {e}")
    
    # Return defaults if no settings exist or if there was an error
    return {
        'auto_break_detection': False,
        'auto_break_threshold': 30,
        'exclude_breaks': False,
        'arbzg_breaks_enabled': True
    }

@app.route('/get_breaks/<int:attendance_id>')
def get_breaks(attendance_id):
    if not session.get('username'):
        return jsonify({'error': 'Not authorized'}), 401
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''SELECT id, start_time, end_time, duration_minutes, 
                    is_excluded_from_billing, is_auto_detected, description
                    FROM breaks WHERE attendance_id = ? ORDER BY start_time''', (attendance_id,))
    break_records = cursor.fetchall()
    
    breaks = []
    for record in break_records:
        # Determine break type based on description
        break_type = 'regular'
        if record[6]:
            if 'Mittagspause' in record[6]:
                break_type = 'lunch'
            elif 'ArbZG' in record[6]:
                break_type = 'arbzg'
        
        breaks.append({
            'id': record[0],
            'start_time': record[1],
            'end_time': record[2],
            'duration': record[3],
            'is_excluded': bool(record[4]),
            'is_auto': bool(record[5]),
            'description': record[6] if len(record) > 6 and record[6] else None,
            'break_type': break_type
        })
    
    return jsonify({'breaks': breaks})
    
@app.route('/get_today_attendance/<int:user_id>')
def get_today_attendance(user_id):
    if not session.get('username'):
        return jsonify({'error': 'Not authorized'}), 401
    
    # Verify the user is requesting their own attendance or is admin
    if session.get('user_id') != user_id and not session.get('admin_logged_in'):
        return jsonify({'error': 'Not authorized to access this user\'s attendance'}), 403
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''SELECT id, check_in, check_out 
                    FROM attendance 
                    WHERE user_id = ? AND date(check_in) = ? 
                    ORDER BY check_in DESC LIMIT 1''', (user_id, today))
    attendance = cursor.fetchone()
    
    if attendance:
        return jsonify({
            'attendance': {
                'id': attendance[0],
                'check_in': attendance[1],
                'check_out': attendance[2]
            }
        })
    
    return jsonify({'attendance': None})

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''SELECT attendance.id, users.username, attendance.check_in, attendance.check_out, 
                      attendance.has_auto_breaks, attendance.billable_minutes
                      FROM attendance
                      JOIN users ON attendance.user_id = users.id
                      ORDER BY attendance.check_in DESC''')
    records = cursor.fetchall()
    return render_template('admin.html', records=records)

@app.route('/add_user', methods=['POST'])
def add_user():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    username = request.form['username']
    password = request.form['password']
    db = get_db()
    cursor = db.cursor()
    error = None
    user_id = None
    try:
        # Hash the password before storing
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        db.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        error = f"Benutzername '{username}' existiert bereits."
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {
            'success': error is None,
            'message': error or f"User '{username}' added successfully.",
            'user_id': user_id,
            'username': username
        }
    cursor.execute('SELECT id, username FROM users ORDER BY username ASC')
    users = cursor.fetchall()
    return render_template('user_management.html', users=users, error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Clear any existing flash messages that might be from a previous session
    session.pop('_flashes', None)
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        if user and bcrypt.check_password_hash(user[2], password):  # user[2] is the password field
            # Clear previous session data completely to avoid any issues
            session.clear()
            
            # Store user info in session
            session['admin_logged_in'] = (username == 'admin')
            session['username'] = username
            session['user_id'] = user[0]
            
            # Set a flash message for successful login
            flash('Sie wurden erfolgreich angemeldet.', 'success')
            
            # Redirect admins to admin panel, regular users to homepage
            if username == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Clear all session data
    session.clear()
    
    # Add flash message about successful logout
    flash('Sie wurden erfolgreich abgemeldet.', 'success')
    
    # Return to login page
    return redirect(url_for('login'))

@app.route('/user_management')
def user_management():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    
    # Fetch users along with their most recent consent status
    cursor.execute('''
        SELECT u.id, u.username, 
               COALESCE(
                   (SELECT c.consent_status 
                    FROM user_consents c 
                    WHERE c.user_id = u.id 
                    ORDER BY c.consent_date DESC 
                    LIMIT 1), 
                   'Nicht angegeben'
               ) as consent_status
        FROM users u
        ORDER BY u.username ASC
    ''')
    users = cursor.fetchall()
    return render_template('user_management.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not session.get('admin_logged_in'):
        return {'success': False, 'message': 'Not authorized'}, 403
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    return {'success': True, 'message': 'User deleted successfully'}

@app.route('/reset_password/<int:user_id>', methods=['POST'])
def reset_password(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    new_password = request.form['new_password']
    db = get_db()
    cursor = db.cursor()
    
    # Hash the new password
    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    
    # Update the user's password
    cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user_id))
    db.commit()
    
    # Get username for feedback message
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    username = user[0] if user else "Unknown"
    
    flash(f"Password for {username} has been reset successfully", "success")
    return redirect(url_for('user_management'))

@app.route('/rectify_data', methods=['POST'])
def rectify_data():
    """Process data rectification request with authentication"""
    user_id = request.form.get('user_id')
    username = request.form.get('username')
    new_password = request.form.get('new_password')
    current_password = request.form.get('current_password')
    
    if not user_id or not username or not current_password:
        flash('Alle erforderlichen Felder müssen ausgefüllt werden.', 'error')
        return redirect(url_for('data_access'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Verify user exists
    cursor.execute('SELECT id, password FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        flash('Benutzer nicht gefunden.', 'error')
        return redirect(url_for('data_access'))
    
    # Verify current password
    if not bcrypt.check_password_hash(user[1], current_password):
        flash('Das aktuelle Passwort ist nicht korrekt.', 'error')
        return redirect(url_for('data_access'))
    
    try:
        # Update username
        cursor.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
        
        # Update password if provided
        if new_password:
            pw_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
            cursor.execute('UPDATE users SET password = ? WHERE id = ?', (pw_hash, user_id))
        
        # Add to consent log that user updated their data
        consent_timestamp = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO user_consents (user_id, consent_status, consent_date)
            VALUES (?, ?, ?)
        ''', (user_id, "Daten aktualisiert", consent_timestamp))
        
        db.commit()
        flash('Ihre Daten wurden erfolgreich aktualisiert.', 'success')
        
        # Update session with new username if the logged-in user is updating their own data
        if 'user_id' in session and int(session['user_id']) == int(user_id):
            session['username'] = username
        
    except Exception as e:
        db.rollback()
        flash(f'Fehler bei der Aktualisierung der Daten: {str(e)}', 'error')
    
    return redirect(url_for('data_access'))

@app.route('/rectify_attendance', methods=['POST'])
def rectify_attendance():
    """Process attendance record rectification request"""
    record_id = request.form.get('record_id')
    user_id = request.form.get('user_id')
    date = request.form.get('date')  # Format: YYYY-MM-DD
    check_in = request.form.get('check_in')  # Format: HH:MM:SS
    check_out = request.form.get('check_out')  # Format: HH:MM:SS
    current_password = request.form.get('current_password')
    
    if not record_id or not user_id or not date or not check_in or not current_password:
        flash('Alle erforderlichen Felder müssen ausgefüllt werden.', 'error')
        return redirect(url_for('data_access'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Verify user exists and password is correct
    cursor.execute('SELECT password FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user or not bcrypt.check_password_hash(user[0], current_password):
        flash('Authentifizierung fehlgeschlagen.', 'error')
        return redirect(url_for('data_access'))
    
    try:
        # Format datetime strings
        check_in_datetime = f"{date}T{check_in}:00"  # Format: YYYY-MM-DDTHH:MM:SS
        
        if check_out:
            check_out_datetime = f"{date}T{check_out}:00"  # Format: YYYY-MM-DDTHH:MM:SS
            cursor.execute('''
                UPDATE attendance SET check_in = ?, check_out = ?
                WHERE id = ? AND user_id = ?
            ''', (check_in_datetime, check_out_datetime, record_id, user_id))
        else:
            cursor.execute('''
                UPDATE attendance SET check_in = ?, check_out = NULL
                WHERE id = ? AND user_id = ?
            ''', (check_in_datetime, record_id, user_id))
        
        db.commit()
        flash('Anwesenheitsaufzeichnung erfolgreich aktualisiert.', 'success')
        
    except Exception as e:
        db.rollback()
        flash(f'Fehler bei der Aktualisierung der Anwesenheitsaufzeichnung: {str(e)}', 'error')
    
    # Re-authenticate to see updated data
    return redirect(url_for('data_access'))

@app.route('/data_access', methods=['GET'])
def data_access():
    """Handle data access requests (DSGVO/GDPR right to access)"""
    # Check if user is already logged in
    username = session.get('username')
    if username:
        # Get user data without requiring re-authentication
        db = get_db()
        cursor = db.cursor()
        
        # Fetch user details
        cursor.execute('SELECT id, username FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if user:
            user_id = user[0]
            
            # Get attendance records and other user data (similar to request_data_access)
            cursor.execute('''
                SELECT id, check_in, check_out FROM attendance 
                WHERE user_id = ? 
                ORDER BY check_in DESC
            ''', (user_id,))
            
            attendance_records = cursor.fetchall()
            records = []
            total_seconds = 0
            
            # Process attendance records
            for rec in attendance_records:
                record_id = rec[0]
                check_in = rec[1]
                check_out = rec[2]
                
                # Format date and time for display
                check_in_date = None
                check_in_time = None
                check_out_time = None
                duration = None
                
                if check_in:
                    dt_in = try_parse(check_in)
                    if dt_in:
                        check_in_date = dt_in.strftime('%d.%m.%Y')
                        check_in_time = dt_in.strftime('%H:%M:%S')
                
                if check_out:
                    dt_out = try_parse(check_out)
                    if dt_out and 'dt_in' in locals() and dt_in:
                        check_out_time = dt_out.strftime('%H:%M:%S')
                        
                        # Make both naive for calculation
                        if hasattr(dt_in, 'tzinfo') and dt_in.tzinfo is not None:
                            dt_in = dt_in.replace(tzinfo=None)
                        if hasattr(dt_out, 'tzinfo') and dt_out.tzinfo is not None:
                            dt_out = dt_out.replace(tzinfo=None)
                        
                        diff = (dt_out - dt_in).total_seconds()
                        if diff > 0:
                            total_seconds += int(diff)
                            hours = int(diff) // 3600
                            minutes = (int(diff) % 3600) // 60
                            seconds = int(diff) % 60
                            duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                
                records.append({
                    'id': record_id,
                    'date': check_in_date,
                    'check_in': check_in_time,
                    'check_out': check_out_time,
                    'duration': duration
                })
                
            # Calculate total time
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            total_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Get consent information
            cursor.execute('''
                SELECT consent_status, consent_date FROM user_consents 
                WHERE user_id = ? 
                ORDER BY consent_date DESC LIMIT 1
            ''', (user_id,))
            
            consent = cursor.fetchone()
            consent_status = consent[0] if consent else 'Not provided'
            consent_date = consent[1] if consent else None
            
            user_data = {
                'username': username,
                'user_id': user_id,
                'total_time': total_time,
                'records': records,
                'consent_status': consent_status,
                'consent_date': consent_date
            }
            
            # Store temporary password in session for data export
            session['temp_password'] = 'authenticated_via_session'
            
            return render_template('data_access.html', user_data=user_data, password_placeholder='authenticated_via_session')
    
    # If not logged in, show the form
    return render_template('data_access.html', user_data=None)

@app.route('/request_data_access', methods=['POST'])
def request_data_access():
    """Process data access request with authentication"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('Benutzername und Passwort werden benötigt.', 'error')
        return redirect(url_for('data_access'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Verify user credentials
    cursor.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    if not user or not bcrypt.check_password_hash(user[2], password):
        flash('Ungültiger Benutzername oder Passwort.', 'error')
        return redirect(url_for('data_access'))
    
    user_id = user[0]
    username = user[1]
    
    # Get user's attendance records
    cursor.execute('''
        SELECT id, check_in, check_out FROM attendance 
        WHERE user_id = ? 
        ORDER BY check_in DESC
    ''', (user_id,))
    
    attendance_records = cursor.fetchall()
    records = []
    total_seconds = 0
    
    # Process attendance records
    for rec in attendance_records:
        record_id = rec[0]
        check_in = rec[1]
        check_out = rec[2]
        
        # Format date and time for display
        check_in_date = None
        check_in_time = None
        check_out_time = None
        duration = None
        
        if check_in:
            dt_in = try_parse(check_in)
            if dt_in:
                check_in_date = dt_in.strftime('%d.%m.%Y')
                check_in_time = dt_in.strftime('%H:%M:%S')
        
        if check_out:
            dt_out = try_parse(check_out)
            if dt_out and dt_in:
                check_out_time = dt_out.strftime('%H:%M:%S')
                
                # Make both naive for calculation
                if hasattr(dt_in, 'tzinfo') and dt_in.tzinfo is not None:
                    dt_in = dt_in.replace(tzinfo=None)
                if hasattr(dt_out, 'tzinfo') and dt_out.tzinfo is not None:
                    dt_out = dt_out.replace(tzinfo=None)
                
                diff = (dt_out - dt_in).total_seconds()
                if diff > 0:
                    total_seconds += int(diff)
                    hours = int(diff) // 3600
                    minutes = (int(diff) % 3600) // 60
                    seconds = int(diff) % 60
                    duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        records.append({
            'id': record_id,
            'date': check_in_date or '(Kein Datum)',
            'check_in': check_in_time or '(Kein Check-in)',
            'check_out': check_out_time or '(Kein Check-out)',
            'duration': duration or '(Nicht berechnet)'
        })
    
    # Calculate total duration
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    total_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # Get consent status
    cursor.execute('SELECT consent_status, consent_date FROM user_consents WHERE user_id = ? ORDER BY consent_date DESC LIMIT 1', (user_id,))
    consent = cursor.fetchone()
    consent_status = consent[0] if consent else "Nicht angegeben"
    consent_date = consent[1] if consent and len(consent) > 1 else None
    
    # Prepare user data object
    user_data = {
        'user_id': user_id,
        'username': username,
        'records': records,
        'total_duration': total_duration,
        'consent_status': consent_status,
        'consent_date': consent_date
    }
    
    # Store password in session for data export
    password_placeholder = '*' * len(password)
    session['temp_password'] = password
    
    return render_template('data_access.html', user_data=user_data, password_placeholder=password_placeholder)

@app.route('/export_data', methods=['POST'])
def export_data():
    """Export user data in various formats (CSV, PDF, JSON)"""
    username = request.form.get('username')
    export_format = request.form.get('format', 'csv')
    password = session.get('temp_password')  # Get stored password from session
    
    # Check if the user is logged in via session
    session_username = session.get('username')
    is_authenticated_by_session = False
    
    # If username matches the logged-in user's name, they're already authenticated
    if session_username and username == session_username:
        is_authenticated_by_session = True
    
    # If not authenticated by session, we need password
    if not is_authenticated_by_session and (not username or not password):
        flash('Benutzername und Passwort werden benötigt.', 'error')
        return redirect(url_for('data_access'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Verify user credentials
    cursor.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    # Skip password check if authenticated via session
    if not user or (not is_authenticated_by_session and not bcrypt.check_password_hash(user[2], password)):
        flash('Ungültiger Benutzername oder Passwort.', 'error')
        return redirect(url_for('data_access'))
    
    user_id = user[0]
    username = user[1]
    
    # Get user's attendance records
    cursor.execute('''
        SELECT id, check_in, check_out FROM attendance 
        WHERE user_id = ? 
        ORDER BY check_in DESC
    ''', (user_id,))
    
    attendance_records = cursor.fetchall()
    records = []
    total_seconds = 0
    
    # Process attendance records
    for rec in attendance_records:
        record_id = rec[0]
        check_in = rec[1]
        check_out = rec[2]
        
        # Format date and time for display
        check_in_date = None
        check_in_time = None
        check_out_time = None
        duration = None
        
        if check_in:
            dt_in = try_parse(check_in)
            if dt_in:
                check_in_date = dt_in.strftime('%d.%m.%Y')
                check_in_time = dt_in.strftime('%H:%M:%S')
        
        if check_out:
            dt_out = try_parse(check_out)
            if dt_out and dt_in:
                check_out_time = dt_out.strftime('%H:%M:%S')
                
                # Make both naive for calculation
                if hasattr(dt_in, 'tzinfo') and dt_in.tzinfo is not None:
                    dt_in = dt_in.replace(tzinfo=None)
                if hasattr(dt_out, 'tzinfo') and dt_out.tzinfo is not None:
                    dt_out = dt_out.replace(tzinfo=None)
                
                diff = (dt_out - dt_in).total_seconds()
                if diff > 0:
                    total_seconds += int(diff)
                    hours = int(diff) // 3600
                    minutes = (int(diff) % 3600) // 60
                    seconds = int(diff) % 60
                    duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        records.append({
            'id': record_id,
            'date': check_in_date or '(Kein Datum)',
            'check_in': check_in_time or '(Kein Check-in)',
            'check_out': check_out_time or '(Kein Check-out)',
            'duration': duration or '(Nicht berechnet)'
        })
    
    # Calculate total duration
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    total_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # Get consent status
    cursor.execute('SELECT consent_status, consent_date FROM user_consents WHERE user_id = ? ORDER BY consent_date DESC LIMIT 1', (user_id,))
    consent = cursor.fetchone()
    consent_status = consent[0] if consent else "Nicht angegeben"
    consent_date = consent[1] if consent and len(consent) > 1 else None
    
    # Prepare user data object
    user_data = {
        'user_id': user_id,
        'username': username,
        'records': records,
        'total_duration': total_duration,
        'consent_status': consent_status,
        'consent_date': consent_date
    }
    
    # Export according to requested format
    if export_format == 'csv':
        return export_as_csv(user_data)
    elif export_format == 'pdf':
        return export_as_pdf(user_data)
    elif export_format == 'json':
        return export_as_json(user_data)
    else:
        flash('Ungültiges Exportformat.', 'error')
        return redirect(url_for('data_access'))

def export_as_csv(user_data):
    """Export user data as CSV file"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Benutzername', user_data['username']])
    writer.writerow(['Benutzer-ID', user_data['user_id']])
    writer.writerow(['Einwilligungsstatus', user_data['consent_status']])
    if user_data['consent_date']:
        writer.writerow(['Letzte Aktualisierung der Einwilligung', user_data['consent_date']])
    writer.writerow([])  # Empty row as separator
    
    # Write attendance records header
    writer.writerow(['Datum', 'Check-In', 'Check-Out', 'Dauer'])
    
    # Write attendance records
    for record in user_data['records']:
        writer.writerow([
            record['date'],
            record['check_in'],
            record['check_out'],
            record['duration']
        ])
    
    # Write total duration
    writer.writerow([])
    writer.writerow(['Gesamtzeit', user_data['total_duration']])
    
    # Create response
    output.seek(0)
    filename = f"zeiterfassung_export_{user_data['username']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

def export_as_pdf(user_data):
    """Export user data as PDF file"""
    if pdfkit is None:
        flash('PDF-Export ist nicht verfügbar. Bitte installieren Sie wkhtmltopdf und pdfkit.', 'error')
        return redirect(url_for('data_access'))
    
    # Render HTML template with user data
    export_date = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    current_year = datetime.now().year
    rendered_html = render_template(
        'full_data_export.html', 
        user_data=user_data, 
        export_date=export_date,
        current_year=current_year
    )
    
    # Convert HTML to PDF
    pdf_options = {
        'encoding': 'UTF-8',
        'page-size': 'A4',
        'margin-top': '1cm',
        'margin-right': '1cm',
        'margin-bottom': '1cm',
        'margin-left': '1cm',
    }
    pdf = pdfkit.from_string(rendered_html, False, options=pdf_options)
    
    # Create response
    filename = f"zeiterfassung_export_{user_data['username']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    
    return send_file(
        io.BytesIO(pdf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

def export_as_json(user_data):
    """Export user data as JSON file"""
    # Create a clean copy of the user data for export
    export_data = {
        'user': {
            'username': user_data['username'],
            'user_id': user_data['user_id'],
            'consent_status': user_data['consent_status'],
        },
        'attendance_records': user_data['records'],
        'total_duration': user_data['total_duration'],
        'export_timestamp': datetime.now().isoformat()
    }
    
    if user_data['consent_date']:
        export_data['user']['consent_date'] = user_data['consent_date']
    
    # Create response
    filename = f"zeiterfassung_export_{user_data['username']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    
    return send_file(
        io.BytesIO(json.dumps(export_data, indent=2, ensure_ascii=False).encode('utf-8')),
        mimetype='application/json',
        as_attachment=True,
        download_name=filename
    )

@app.route('/privacy_policy')
def privacy_policy():
    """Display the privacy policy"""
    return render_template('privacy_policy.html')

def get_username_by_id(user_id):
    """Helper function to get username by ID"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    return user[0] if user else ""

def try_parse(dt_str):
    """Try to parse a datetime string using multiple formats, with improved error handling."""
    if not dt_str:
        return None
    
    # Add more formats that might be in your database
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S.%f',
        # Try with timezone info
        '%Y-%m-%d %H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%d %H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S.%f%z'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    
    # If we can't parse it with standard formats, try a more flexible approach
    try:
        # Try to use Python's own ISO format parser as a fallback
        parsed_date = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return parsed_date
    except Exception:
        # Log the problematic datetime string to help debugging
        print(f"Failed to parse datetime: '{dt_str}'")
        return None

@app.route('/user_report/<username>', methods=['GET', 'POST'])
def user_report(username):
    # Get filter parameters from both GET and POST requests
    date = request.args.get('date') or request.form.get('date', '')
    week = request.args.get('week') or request.form.get('week', '')
    month = request.args.get('month') or request.form.get('month', '')
    entire_period_str = request.args.get('entire_period') or request.form.get('entire_period', '0')
    entire_period = entire_period_str == '1'
    
    # Connect to database
    db = get_db()
    cursor = db.cursor()
    
    # Admin check
    is_admin = session.get('admin_logged_in', False)
    current_user = session.get('username')
    
    # Authorization logic
    # 1. Admin can access any report
    # 2. Regular user can only access their own report with password
    # 3. Regular user who is logged in can access their own report without password
    
    # Non-admin trying to access reports (either needs to be the same user or provide password)
    if not is_admin:
        # Accessing another user's report or 'all' users
        if current_user != username or username == 'all':
            if request.method == 'POST':
                # Check password authentication
                password = request.form.get('password')
                
                # Only allow username == current_user or admin can see 'all'
                if username != current_user and username != 'all':
                    flash('Sie können nur Ihre eigenen Berichte einsehen.', 'error')
                    return redirect(url_for('index'))
                    
                if username == 'all':
                    flash('Nur Administratoren können Berichte für alle Benutzer einsehen.', 'error')
                    return redirect(url_for('index'))
                
                # Verify credentials for the user
                cursor.execute('SELECT id, password FROM users WHERE username = ?', (current_user,))
                user_record = cursor.fetchone()
                
                if not user_record or not bcrypt.check_password_hash(user_record[1], password):
                    flash('Ungültiges Passwort für Berichtszugriff.', 'error')
                    return redirect(url_for('index'))
            else:
                # GET request - show auth form for other users' reports
                if username == 'all':
                    flash('Nur Administratoren können Berichte für alle Benutzer einsehen.', 'error')
                    return redirect(url_for('index'))
                else:
                    # Redirect to own report page if trying to access someone else's report
                    if username != current_user:
                        flash('Sie können nur Ihre eigenen Berichte einsehen.', 'error')
                        return redirect(url_for('user_report', username=current_user))
                    
                    # Show password form for own report
                    return render_template('report_auth.html', username=username, 
                                         date=date, week=week, month=month, entire_period=entire_period_str)
    
    # Handle form parameters from POST requests
    if request.method == 'POST':
        form_date = request.form.get('date')
        form_week = request.form.get('week')
        form_month = request.form.get('month')
        
        if form_date and not date:
            date = form_date
        if form_week and not week:
            week = form_week
        if form_month and not month:
            month = form_month
    # If 'all' is selected, show all users for the filter
    if username == 'all' or not username:
        query = '''SELECT users.username, attendance.check_in, attendance.check_out FROM attendance JOIN users ON attendance.user_id = users.id WHERE 1=1'''
        params = []
        if week:
            y, w = week.split('-W')
            week_start = datetime.strptime(f'{y}-W{w}-1', "%G-W%V-%u")
            week_end = week_start + timedelta(days=6)
            query += ' AND date(check_in) >= ? AND date(check_in) <= ?'
            params.extend([week_start.date(), week_end.date()])
        if month:
            y, m = month.split('-')
            month_start = datetime(int(y), int(m), 1)
            if int(m) == 12:
                month_end = datetime(int(y)+1, 1, 1) - timedelta(days=1)
            else:
                month_end = datetime(int(y), int(m)+1, 1) - timedelta(days=1)
            query += ' AND date(check_in) >= ? AND date(check_in) <= ?'
            params.extend([month_start.date(), month_end.date()])
        if date:
            query += ' AND date(check_in) = ?'
            params.append(date)
        query += ' ORDER BY users.username ASC, check_in DESC'
        cursor.execute(query, params)
        records = cursor.fetchall()
        total_seconds = 0
        records_with_durations = []
        for rec in records:
            username_row, check_in, check_out = rec
            if not check_in and not check_out:
                duration_str = "No check-in/out"
            elif check_in and not check_out:
                duration_str = "Not checked out"
            elif not check_in and check_out:
                duration_str = "No check-in time"
            else:
                dt_in = try_parse(check_in) if check_in else None
                dt_out = try_parse(check_out) if check_out else None
                if dt_in and dt_out:
                    # Ensure both datetimes are naive before subtraction
                    if hasattr(dt_in, 'tzinfo') and dt_in.tzinfo is not None:
                        dt_in = dt_in.replace(tzinfo=None)
                    if hasattr(dt_out, 'tzinfo') and dt_out.tzinfo is not None:
                        dt_out = dt_out.replace(tzinfo=None)
                    
                    diff = (dt_out - dt_in).total_seconds()
                    if diff > 0:
                        total_seconds += int(diff)
                        hours = int(diff) // 3600
                        minutes = (int(diff) % 3600) // 60
                        seconds = int(diff) % 60
                        duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Calculate total duration
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        total_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return render_template('user_report.html', 
                              username='All Users', 
                              records=records_with_durations, 
                              total_time=total_time_str, 
                              all_users=True,
                              entire_period=entire_period)
    # If a user is selected, filter by user and any date/week/month
    cursor.execute('''SELECT id FROM users WHERE username = ?''', (username,))
    user = cursor.fetchone()
    if not user:
        return f"<h2>User '{username}' not found.</h2>"
    user_id = user[0]
    query = 'SELECT check_in, check_out FROM attendance WHERE user_id = ?'
    params = [user_id]
    
    # Skip date/week/month filters if entire_period is selected
    if not entire_period:
        if week:
            y, w = week.split('-W')
            week_start = datetime.strptime(f'{y}-W{w}-1', "%G-W%V-%u")
            week_end = week_start + timedelta(days=6)
            query += ' AND date(check_in) >= ? AND date(check_in) <= ?'
            params.extend([week_start.date(), week_end.date()])
        if month:
            y, m = month.split('-')
            month_start = datetime(int(y), int(m), 1)
            if int(m) == 12:
                month_end = datetime(int(y)+1, 1, 1) - timedelta(days=1)
            else:
                month_end = datetime(int(y), int(m)+1, 1) - timedelta(days=1)
            query += ' AND date(check_in) >= ? AND date(check_in) <= ?'
            params.extend([month_start.date(), month_end.date()])
        if date:
            query += ' AND date(check_in) = ?'
            params.append(date)
    query += ' ORDER BY check_in DESC'
    cursor.execute(query, params)
    records = cursor.fetchall()
    total_seconds = 0
    durations = []
    for rec in records:
        check_in, check_out = rec
        if not check_in and not check_out:
            duration_str = "No check-in/out"
        elif check_in and not check_out:
            duration_str = "Not checked out"
        elif not check_in and check_out:
            duration_str = "No check-in time"
        else:
            dt_in = try_parse(check_in) if check_in else None
            dt_out = try_parse(check_out) if check_out else None
            if dt_in and dt_out:
                # Ensure both datetimes are naive before subtraction
                if hasattr(dt_in, 'tzinfo') and dt_in.tzinfo is not None:
                    dt_in = dt_in.replace(tzinfo=None)
                if hasattr(dt_out, 'tzinfo') and dt_out.tzinfo is not None:
                    dt_out = dt_out.replace(tzinfo=None)
                
                diff = (dt_out - dt_in).total_seconds()
                if diff > 0:
                    total_seconds += int(diff)
                    hours = int(diff) // 3600
                    minutes = (int(diff) % 3600) // 60
                    seconds = int(diff) % 60
                    duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = "Invalid times"
            else:
                duration_str = "Invalid format"
        durations.append(duration_str)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    total_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    records_with_durations = list(zip(records, durations))
    
    # Pass the entire_period flag to the template
    return render_template('user_report.html', 
                          username=username, 
                          records=records_with_durations, 
                          total_time=total_time_str, 
                          all_users=False,
                          entire_period=entire_period)

@app.route('/update_consent', methods=['POST'])
def update_consent():
    """Update user consent status (DSGVO/GDPR compliance)"""
    if not session.get('admin_logged_in'):
        return {'success': False, 'message': 'Not authorized'}, 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    consent_status = data.get('consent_status')
    
    if not user_id or not consent_status:
        return {'success': False, 'message': 'Missing required parameters'}
    
    db = get_db()
    cursor = db.cursor()
    now = get_local_time()
    
    try:
        cursor.execute(
            'INSERT INTO user_consents (user_id, consent_status, consent_date) VALUES (?, ?, ?)',
            (user_id, consent_status, now)
        )
        db.commit()
        return {'success': True, 'message': 'Einwilligungsstatus erfolgreich aktualisiert'}
    except Exception as e:
        db.rollback()
        return {'success': False, 'message': f'Fehler bei der Aktualisierung: {str(e)}'}

@app.route('/log_consent', methods=['POST'])
def log_consent():
    """Log user consent for DSGVO compliance"""
    try:
        data = request.json
        user_id = data.get('user_id')
        consent_type = data.get('consent_type', 'unknown')
        
        if not user_id:
            return jsonify({'status': 'error', 'message': 'User ID is required'}), 400
        
        # Verify user exists
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        
        if not cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Log consent
        consent_timestamp = datetime.now().isoformat()
        consent_status = f"Cookie-Einwilligung: {consent_type}"
        
        cursor.execute('''
            INSERT INTO user_consents (user_id, consent_status, consent_date)
            VALUES (?, ?, ?)
        ''', (user_id, consent_status, consent_timestamp))
        
        db.commit()
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/manual_attendance', methods=['GET'])
def manual_attendance():
    """Display form for manually adding attendance records"""
    # Check if user is logged in
    if not session.get('username'):
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Admin can see all users
    if session.get('admin_logged_in'):
        cursor.execute('SELECT id, username FROM users ORDER BY username')
        users = cursor.fetchall()
    else:
        # Regular users can only see themselves
        cursor.execute('SELECT id, username FROM users WHERE id = ?', (session.get('user_id'),))
        users = cursor.fetchall()
    
    return render_template('manual_attendance.html', users=users)

@app.route('/add_manual_attendance', methods=['POST'])
def add_manual_attendance():
    """Process manual attendance record submission"""
    if not session.get('username'):
        return redirect(url_for('login'))
    
    user_id = request.form.get('user_id')
    date = request.form.get('date')  # Format: YYYY-MM-DD
    check_in = request.form.get('check_in')  # Format: HH:MM
    check_out = request.form.get('check_out')  # Format: HH:MM (optional)
    current_password = request.form.get('current_password')
    
    # Validate required fields
    if not user_id or not date or not check_in or not current_password:
        flash('Alle erforderlichen Felder müssen ausgefüllt werden.', 'error')
        return redirect(url_for('manual_attendance'))
    
    # Ensure user has permission to add this record
    current_user_id = session.get('user_id')
    is_admin = session.get('admin_logged_in', False)
    
    if not is_admin and int(user_id) != current_user_id:
        flash('Sie können nur Aufzeichnungen für sich selbst hinzufügen.', 'error')
        return redirect(url_for('manual_attendance'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Verify user exists and password is correct
    cursor.execute('SELECT password FROM users WHERE id = ?', (current_user_id,))
    user = cursor.fetchone()
    
    if not user or not bcrypt.check_password_hash(user[0], current_password):
        flash('Authentifizierung fehlgeschlagen.', 'error')
        return redirect(url_for('manual_attendance'))
    
    try:
        # Get username for feedback message
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        username = cursor.fetchone()[0]
        
        # Format datetime strings
        check_in_datetime = f"{date}T{check_in}:00"  # Format: YYYY-MM-DDTHH:MM:SS
        
        # Check if the date is in the future
        now = get_local_time()
        check_in_dt = datetime.strptime(check_in_datetime, '%Y-%m-%dT%H:%M:%S')
        
        # Make check_in_dt timezone aware for comparison with now
        check_in_dt_tz = pytz.timezone(TIMEZONE).localize(check_in_dt)
        
        if check_in_dt_tz > now:
            flash('Anwesenheitsaufzeichnungen können nicht für die Zukunft erstellt werden.', 'error')
            return redirect(url_for('manual_attendance'))
        
        # Check for conflicting records on the same day
        check_date = datetime.strptime(date, '%Y-%m-%d').date()
        cursor.execute('''
            SELECT id, check_in, check_out FROM attendance 
            WHERE user_id = ? AND date(check_in) = ?
            ORDER BY check_in
        ''', (user_id, check_date))
        existing_records = cursor.fetchall()
        
        # If check_out is provided, validate and format it
        check_out_datetime = None
        if check_out:
            check_out_datetime = f"{date}T{check_out}:00"  # Format: YYYY-MM-DDTHH:MM:SS
            check_out_dt = datetime.strptime(check_out_datetime, '%Y-%m-%dT%H:%M:%S')
            
            # Ensure check_out is after check_in
            if check_out_dt <= check_in_dt:
                flash('Die Check-Out Zeit muss nach der Check-In Zeit liegen.', 'error')
                return redirect(url_for('manual_attendance'))
            
            # Make check_out_dt timezone aware for comparison with now
            check_out_dt_tz = pytz.timezone(TIMEZONE).localize(check_out_dt)
            
            # Ensure check_out is not in the future
            if check_out_dt_tz > now:
                flash('Anwesenheitsaufzeichnungen können nicht für die Zukunft erstellt werden.', 'error')
                return redirect(url_for('manual_attendance'))
                
            # Calculate billable minutes
            billable_minutes = int((check_out_dt - check_in_dt).total_seconds() / 60)
        
        # Check for time conflicts with existing records
        for record in existing_records:
            record_id = record[0]
            record_in = datetime.strptime(record[1], '%Y-%m-%dT%H:%M:%S') if record[1] else None
            record_out = datetime.strptime(record[2], '%Y-%m-%dT%H:%M:%S') if record[2] else None
            
            # All datetimes are kept as naive for comparisons among themselves
            # This works because they are all in the same timezone
            
            # Check for overlap
            if record_in and record_out:  # Complete record with in and out
                if (check_in_dt >= record_in and check_in_dt <= record_out) or \
                   (check_out_datetime and check_out_dt >= record_in and check_out_dt <= record_out) or \
                   (check_in_dt <= record_in and (check_out_datetime and check_out_dt >= record_out)):
                    flash(f'Zeitkonflikt mit existierendem Eintrag vom {record_in.strftime("%d.%m.%Y %H:%M")} bis {record_out.strftime("%H:%M")}', 'error')
                    return redirect(url_for('manual_attendance'))
            elif record_in and not record_out:  # Only check-in, no check-out
                if check_in_dt >= record_in or (check_out_datetime and check_out_dt >= record_in):
                    flash(f'Zeitkonflikt mit existierendem Eintrag vom {record_in.strftime("%d.%m.%Y %H:%M")} (ohne Check-Out)', 'error')
                    return redirect(url_for('manual_attendance'))
        
        # Insert the new record
        if check_out_datetime:
            cursor.execute('''
                INSERT INTO attendance (user_id, check_in, check_out, billable_minutes)
                VALUES (?, ?, ?, ?)
            ''', (user_id, check_in_datetime, check_out_datetime, billable_minutes))
        else:
            cursor.execute('''
                INSERT INTO attendance (user_id, check_in)
                VALUES (?, ?)
            ''', (user_id, check_in_datetime))
        
        db.commit()
        
        # Success message
        if check_out:
            flash(f'Anwesenheitsaufzeichnung für {username} von {check_in} bis {check_out} am {date} erfolgreich hinzugefügt.', 'success')
        else:
            flash(f'Check-In für {username} um {check_in} am {date} erfolgreich hinzugefügt.', 'success')
        
        return redirect(url_for('manual_attendance'))
        
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error adding manual attendance: {str(e)}")
        flash(f'Fehler beim Hinzufügen der Anwesenheitsaufzeichnung: {str(e)}', 'error')
        return redirect(url_for('manual_attendance'))

@app.route('/request_data_deletion', methods=['POST'])
def request_data_deletion():
    """Process data deletion request with authentication"""
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_deletion = request.form.get('confirm_deletion')
    
    if not username or not password:
        flash('Benutzername und Passwort werden benötigt.', 'error')
        return redirect(url_for('data_access'))
    
    if not confirm_deletion:
        flash('Bitte bestätigen Sie die Datenlöschung.', 'error')
        return redirect(url_for('data_access'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Verify user credentials
    cursor.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    if not user or not bcrypt.check_password_hash(user[2], password):
        flash('Ungültiger Benutzername oder Passwort.', 'error')
        return redirect(url_for('data_access'))
    
    user_id = user[0]
    
    try:
        # Begin transaction
        db.execute('BEGIN TRANSACTION')
        
        # First, export the data for record-keeping
        cursor.execute('''
            SELECT id, check_in, check_out FROM attendance 
            WHERE user_id = ? 
            ORDER BY check_in DESC
        ''', (user_id,))
        
        attendance_records = cursor.fetchall()
        
        # Store deletion log with anonymized data
        deletion_timestamp = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO data_deletion_log (user_id, deletion_date, record_count)
            VALUES (?, ?, ?)
        ''', (user_id, deletion_timestamp, len(attendance_records)))
        
        # Delete user consent records
        cursor.execute('DELETE FROM user_consents WHERE user_id = ?', (user_id,))
        
        # Delete attendance records
        cursor.execute('DELETE FROM attendance WHERE user_id = ?', (user_id,))
        
        # Finally, delete the user
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        # Commit transaction
        db.commit()
        
        # Clear any session data
        session.clear()
        
        flash('Ihre Daten wurden erfolgreich gelöscht. Wir bedauern, dass Sie uns verlassen.', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        # Rollback in case of error
        db.rollback()
        flash(f'Fehler bei der Datenlöschung: {str(e)}', 'error')
        return redirect(url_for('data_access'))

if __name__ == '__main__':
    print("Initializing BTZ-Zeiterfassung application...")
    init_db()
    print("Database initialization complete")
    print("Starting web server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
