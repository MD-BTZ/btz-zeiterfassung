# Attendance Web Application

## Requirements
- Python 3
- pip

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Migrate the database:
   ```bash
   python migrate_db.py
   ```
3. Run the app:
   ```bash
   python app.py
   ```
4. Open your browser and go to `http://localhost:5000`

## Features
- Check-in and check-out tracking
- Automatic break detection
- Manual break entry
- Manual attendance record creation for past dates
- Exclusion of breaks from billable hours
- User management
- Reporting features

## Break Detection System
The application now includes an automatic break detection system that:
- Detects long periods of inactivity
- Suggests breaks based on configurable thresholds
- Allows excluding break time from billable hours
- Supports manual entry of breaks

### Break Settings (Admin Only)
Administrators can configure system-wide break preferences:
1. Enable/disable automatic break detection
2. Set inactivity threshold (minutes)
3. Choose whether to exclude breaks from billable hours for all users

### Manual Attendance Entry
Users can manually add attendance records for past dates:
1. Navigate to "Zeiterfassung hinzufügen" in the menu
2. Select the date and enter check-in/check-out times
3. Confirm with password
4. System validates to prevent time conflicts with existing records

## Notes
- The database (`attendance.db`) is created automatically.
- Default admin user must be created manually in the database for first login.
