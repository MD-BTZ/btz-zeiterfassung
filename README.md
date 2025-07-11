Copyright © 2025 Michal Kopecki - BTZ Zeiterfassung

Alle Rechte vorbehalten. Unerlaubte Nutzung, Vervielfältigung oder Verbreitung ist untersagt.

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

## Project Structure
- `app.py` - Main application file
- `templates/` - HTML templates
- `static/` - CSS, JS, and other static files
- `docs/` - Documentation files
- `run_migrations.sh` - Script to run database migrations
- `run.sh` - Script to start the application

For details about the project cleanup and file organization, see `docs/cleanup_documentation.md`.

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

### Break Management System

The application includes a comprehensive break management system that handles both automatic and manual breaks.

#### Break Settings (Admin Only)
Administrators can configure system-wide break preferences through the "Pauseneinstellungen" page:

1. **Automatische Pausenerkennung aktivieren**: Enable/disable automatic break detection
2. **Pausen automatisch erkennen**: Set inactivity threshold (minutes) - configurable from 10 to 120 minutes
3. **Pausen von Abrechnung ausschließen**: Choose whether breaks should be excluded from billable hours
4. **Automatische Pausen nach Arbeitszeitgesetz (ArbZG)**: Enable/disable automatic breaks according to German labor law

#### Automatic Break Detection
The system can automatically detect periods of inactivity and mark them as breaks based on the configured threshold.

#### ArbZG-Compliant Breaks
When the ArbZG feature is enabled, the system automatically ensures compliance with German labor law (Arbeitszeitgesetz):

- For work periods > 6 hours: 30 minutes of break are required
- For work periods > 9 hours: 45 minutes of break are required

If a user has not taken sufficient breaks, the system automatically adds the required break time at checkout. The system intelligently places these breaks:

1. **Lunch Period Placement**: If the work day spans the typical lunch period (11:30-14:00), the system will try to place the break during this time
2. **End of Day Placement**: If the lunch period can't be used, breaks are added at the end of the work day
3. **Break Consolidation**: The system keeps track of all breaks (manual and automatic) to ensure the total break time meets legal requirements
4. **Visual Differentiation**: The UI distinguishes between lunch breaks (orange badges) and end-of-day breaks (green badges) with different styling

##### Intelligent Break Placement Algorithm
The intelligent break placement works as follows:

1. Calculate the total work duration and determine required break time (30 or 45 minutes)
2. Check if existing breaks already satisfy the requirement
3. If additional breaks are needed:
   - Check if the work period spans the lunch period (11:30-14:00)
   - If yes and there's enough time in that period, place the break centered in the lunch period
   - If not, place the break at the end of the work day

ArbZG break compliance is a separate feature from the general automatic break detection and can be enabled/disabled independently using the Break Settings page.

#### Break Tracking
All breaks are tracked with the following information:
- Start and end times
- Duration in minutes
- Whether the break was auto-detected or manually added
- Whether the break is excluded from billable hours

#### Manual Break Entry
Users and administrators can add breaks manually:
1. Breaks can be added to any attendance record
2. Enter start time, end time, break type, and description
3. Select break type (Regular, Mittagspause, or ArbZG Pflichtpause)
4. Set billing options (abrechenbar/nicht abrechenbar)
5. System validates to prevent overlapping breaks
6. Different break types are visually distinguished in reports and history

### Manual Attendance Entry
Users can manually add attendance records for past dates:
1. Navigate to "Zeiterfassung hinzufügen" in the menu
2. Select the date and enter check-in/check-out times
3. Confirm with password
4. System validates to prevent time conflicts with existing records

## Notes
- The database (`attendance.db`) is created automatically.
- Default admin user must be created manually in the database for first login.
