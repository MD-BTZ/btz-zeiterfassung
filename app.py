from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from markupsafe import Markup
import sqlite3
import os
from datetime import datetime, timedelta
import pytz
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this in production
bcrypt = Bcrypt(app)
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'attendance.db')

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
        # Insert default admin if not exists
        cursor.execute('SELECT * FROM users WHERE username=?', ("admin",))
        if cursor.fetchone() is None:
            hashed_password = bcrypt.generate_password_hash("admin").decode('utf-8')
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', ("admin", hashed_password))
        db.commit()

@app.route('/')
def index():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, username FROM users')
    users = cursor.fetchall()
    return render_template('index.html', users=users)

@app.route('/checkin', methods=['POST'])
def checkin():
    db = get_db()
    cursor = db.cursor()
    user_id = request.form.get('user_id')
    now = get_local_time()
    cursor.execute('INSERT INTO attendance (user_id, check_in) VALUES (?, ?)', (user_id, now))
    
    # Get username for feedback message
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    username = cursor.fetchone()[0]
    
    db.commit()
    flash(f'Successfully checked in {username} at {now.strftime("%H:%M:%S")}', 'success')
    return redirect(url_for('index'))

@app.route('/checkout', methods=['POST'])
def checkout():
    db = get_db()
    cursor = db.cursor()
    user_id = request.form.get('user_id')
    now = get_local_time()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')  # Store as string for database
    
    # Get username for feedback message
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    username = cursor.fetchone()[0]
    
    # First check if there's an active check-in
    cursor.execute('''SELECT id, check_in FROM attendance 
                     WHERE user_id = ? AND check_out IS NULL 
                     ORDER BY check_in DESC LIMIT 1''', (user_id,))
    active_checkin = cursor.fetchone()
    
    if active_checkin:
        # There is an active check-in, update it with checkout time
        checkin_id = active_checkin[0]
        check_in_time = active_checkin[1]
        cursor.execute('UPDATE attendance SET check_out = ? WHERE id = ?', (now_str, checkin_id))
        db.commit()
        
        # Calculate duration for feedback
        try:
            # For safety, ensure we're working with consistent datetime objects
            checkin_dt = try_parse(check_in_time)
            checkout_dt = datetime.now()  # Use current time for consistent calculation
            
            if checkin_dt:
                # Make both naive datetimes
                if hasattr(checkin_dt, 'tzinfo') and checkin_dt.tzinfo is not None:
                    checkin_dt = checkin_dt.replace(tzinfo=None)
                
                # Check if check-in time is reasonable (not in the future)
                if checkin_dt > checkout_dt:
                    flash(f'Successfully checked out {username} at {now.strftime("%H:%M:%S")}', 'success')
                else:
                    # Calculate duration
                    duration = checkout_dt - checkin_dt
                    
                    # Ensure positive duration
                    total_seconds = max(0, int(duration.total_seconds()))
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    flash(f'Successfully checked out {username} at {now.strftime("%H:%M:%S")}. Duration: {duration_str}', 'success')
            else:
                flash(f'Successfully checked out {username} at {now.strftime("%H:%M:%S")}', 'success')
        except Exception as e:
            # Continue without showing duration
            flash(f'Successfully checked out {username} at {now.strftime("%H:%M:%S")}', 'success')
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
            flash(f'No check-in record found for {username} today. Please check in first.', 'error')
        else:
            flash(f'No active check-in found for {username}. Something went wrong.', 'error')
    
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''SELECT attendance.id, users.username, attendance.check_in, attendance.check_out
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
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        if user and bcrypt.check_password_hash(user[2], password):  # user[2] is the password field
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

@app.route('/user_management')
def user_management():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, username FROM users ORDER BY username ASC')
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
def rectify_user_data():
    """Handle user data correction requests (DSGVO/GDPR right to rectification)"""
    user_id = request.form.get('user_id')
    username = request.form.get('username')
    new_password = request.form.get('new_password')
    current_password = request.form.get('current_password')
    
    if not user_id or not username or not current_password:
        flash('Alle erforderlichen Felder müssen ausgefüllt werden.', 'error')
        return redirect(url_for('data_access'))
    
    # Authenticate the user first
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, username, password FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user or not bcrypt.check_password_hash(user[2], current_password):
        flash('Authentifizierung fehlgeschlagen. Bitte überprüfen Sie Ihr aktuelles Passwort.', 'error')
        return redirect(url_for('data_access'))
    
    try:
        # Check if username exists (if it's changed)
        if username != user[1]:
            cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', (username, user_id))
            if cursor.fetchone():
                flash(f"Benutzername '{username}' wird bereits verwendet.", 'error')
                return redirect(url_for('data_access'))
            
            # Update username
            cursor.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
        
        # Update password if provided
        if new_password:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user_id))
        
        db.commit()
        flash('Ihre Daten wurden erfolgreich aktualisiert.', 'success')
        
        # Re-authenticate with new credentials
        if 'admin_logged_in' not in session:
            # Create a hidden form for automatic re-auth after password change
            return f'''
                <html>
                <body onload="document.getElementById('re-auth-form').submit()">
                    <form id="re-auth-form" method="post" action="/request_data_access">
                        <input type="hidden" name="username" value="{username}">
                        <input type="hidden" name="password" value="{new_password if new_password else current_password}">
                    </form>
                    <p>Authentifiziere erneut mit neuen Anmeldedaten...</p>
                </body>
                </html>
            '''
        
        return redirect(url_for('data_access'))
    
    except Exception as e:
        db.rollback()
        flash(f'Fehler bei der Aktualisierung der Daten: {str(e)}', 'error')
        return redirect(url_for('data_access'))

@app.route('/rectify_attendance', methods=['POST'])
def rectify_attendance():
    """Handle attendance record correction (DSGVO/GDPR right to rectification)"""
    record_id = request.form.get('record_id')
    user_id = request.form.get('user_id')
    date = request.form.get('date')
    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')
    current_password = request.form.get('current_password')
    
    if not record_id or not user_id or not date or not check_in or not current_password:
        flash('Alle erforderlichen Felder müssen ausgefüllt werden.', 'error')
        return redirect(url_for('data_access'))
    
    # Authenticate the user first
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT password FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user or not bcrypt.check_password_hash(user[0], current_password):
        flash('Authentifizierung fehlgeschlagen. Bitte überprüfen Sie Ihr aktuelles Passwort.', 'error')
        return redirect(url_for('data_access'))
    
    try:
        # Format the datetime strings
        check_in_datetime = f"{date} {check_in}:00"
        
        if check_out:
            check_out_datetime = f"{date} {check_out}:00"
            cursor.execute('UPDATE attendance SET check_in = ?, check_out = ? WHERE id = ? AND user_id = ?',
                         (check_in_datetime, check_out_datetime, record_id, user_id))
        else:
            cursor.execute('UPDATE attendance SET check_in = ?, check_out = NULL WHERE id = ? AND user_id = ?',
                         (check_in_datetime, record_id, user_id))
        
        db.commit()
        flash('Anwesenheitsaufzeichnung wurde erfolgreich aktualisiert.', 'success')
        
        # Re-authenticate to show updated data
        return f'''
            <html>
            <body onload="document.getElementById('re-auth-form').submit()">
                <form id="re-auth-form" method="post" action="/request_data_access">
                    <input type="hidden" name="username" value="{get_username_by_id(user_id)}">
                    <input type="hidden" name="password" value="{current_password}">
                </form>
                <p>Aktualisiere Daten...</p>
            </body>
            </html>
        '''
    
    except Exception as e:
        db.rollback()
        flash(f'Fehler bei der Aktualisierung der Anwesenheitsaufzeichnung: {str(e)}', 'error')
        return redirect(url_for('data_access'))

@app.route('/data_access', methods=['GET'])
def data_access():
    """Handle data access requests (DSGVO/GDPR right to access)"""
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

@app.route('/user_report/<username>')
def user_report(username):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    date = request.args.get('date')
    week = request.args.get('week')
    month = request.args.get('month')
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
                        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        duration_str = "Invalid times"
                else:
                    duration_str = "Invalid format"
            records_with_durations.append(((username_row, check_in, check_out), duration_str))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        total_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return render_template('user_report.html', username='All Users', records=records_with_durations, total_time=total_time_str, all_users=True)
    # If a user is selected, filter by user and any date/week/month
    cursor.execute('''SELECT id FROM users WHERE username = ?''', (username,))
    user = cursor.fetchone()
    if not user:
        return f"<h2>User '{username}' not found.</h2>"
    user_id = user[0]
    query = 'SELECT check_in, check_out FROM attendance WHERE user_id = ?'
    params = [user_id]
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
    return render_template('user_report.html', username=username, records=records_with_durations, total_time=total_time_str, all_users=False)

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

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
