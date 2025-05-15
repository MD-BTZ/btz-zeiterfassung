# ArbZG-Compliant Break Placement System User Guide

## Overview

This guide explains the ArbZG-compliant break placement system in the time tracking application. The system automatically ensures compliance with the German Arbeitszeitgesetz (ArbZG) §4, which mandates specific break durations for employees based on their work hours.

## Legal Requirements (ArbZG §4)

According to German labor law:

- For work periods **exceeding 6 hours**: employees must take at least **30 minutes** of break
- For work periods **exceeding 9 hours**: employees must take at least **45 minutes** of break

These breaks can be split into multiple shorter breaks but must meet the minimum total duration.

## How the System Works

### 1. Break Requirement Calculation

At checkout, the system:

1. Calculates the total working duration for the day (excluding existing breaks)
2. Determines the required break duration:
   - 0 minutes if working < 6 hours
   - 30 minutes if working between 6-9 hours
   - 45 minutes if working > 9 hours
3. Checks if the employee has already taken sufficient breaks
4. Calculates any additional break time needed to comply with ArbZG

### 2. Intelligent Break Placement

If additional breaks are needed, the system uses a sophisticated algorithm to place them:

#### Lunch Period Prioritization

The system tries to place breaks during the configured lunch period:

1. Identifies if the working period overlaps with the configured lunch period
2. Attempts to place the break centered within the lunch period
3. Ensures the break stays within the lunch period boundaries
4. If the lunch period is too short for the required break, it places as much as possible during lunch

#### End of Day Placement

If the lunch period is unavailable or insufficient:

1. The system places the remaining break at the end of the work day
2. For split breaks, it clearly identifies both parts (lunch and end-of-day)

#### Partial Break Allocation

For longer workdays where the lunch period can only accommodate part of the required break:

1. The system places the maximum possible break within the lunch period
2. Places the remainder at the end of the work day
3. Both breaks are labeled appropriately to distinguish their purposes

### 3. Visual Feedback and Logging

The system provides clear visual feedback:

- **Lunch breaks**: Displayed with orange badges
- **End-of-day breaks**: Displayed with green badges
- **Manual ArbZG breaks**: Displayed with purple badges
- **All automatic breaks**: Include an indicator that they were system-generated

Detailed logs are generated for each break placement decision, helping with troubleshooting and compliance verification.

## User Settings

### Configuring the System

Administrators can configure the system through the Break Settings page:

1. **Enable/Disable ArbZG Compliance**: Toggle the "Automatische Pausen nach Arbeitszeitgesetz (ArbZG)" setting
2. **Configure Lunch Period**:
   - Set the lunch period start time (default: 11:30)
   - Set the lunch period end time (default: 14:00)
   - These times determine when the system will preferentially place breaks

### Individual User Settings

Users can have their own lunch period preferences:

1. The system uses user-specific lunch period settings when available
2. Falls back to system-wide settings when individual preferences aren't set

## Break Consolidation

The system is intelligent about existing breaks:

1. **Manual Breaks**: Any breaks manually added by users count toward the ArbZG requirement
2. **Automatic Breaks**: Breaks automatically detected due to inactivity also count
3. **Multiple Breaks**: The system considers the total duration of all breaks when calculating compliance

## Best Practices

### For Employees

- Take breaks naturally during the day when possible
- Use the manual break entry feature when taking breaks that aren't detected automatically
- Review your attendance records to ensure breaks are correctly recorded

### For Administrators

- Configure the lunch period to match your organization's typical meal times
- Regularly review break compliance reports
- Provide guidance to employees on proper break documentation
- Use the validation tools to verify the system is working correctly

## Troubleshooting

If breaks aren't being placed correctly:

1. Verify the ArbZG compliance feature is enabled
2. Check that the lunch period settings are configured appropriately
3. Look at the system logs for detailed break placement information
4. Ensure the database schema is up-to-date (run migrations if needed)
5. Test with the break_placement_validation.py script

## Technical Details

For technical users and developers, the break placement algorithm follows these steps:

1. **Calculate work duration**: `total_work_duration_minutes = end_time - start_time - existing_breaks`
2. **Determine break requirements**: Based on ArbZG §4 (30 min > 6h, 45 min > 9h)
3. **Calculate additional breaks needed**: `break_to_add_minutes = required_break_minutes - existing_break_minutes`
4. **Determine break placement**:
   - Check if work period intersects lunch period
   - Calculate maximum possible lunch period break
   - Place remaining break time at day end if needed
5. **Insert breaks into database** with appropriate descriptions and metadata

The full implementation can be reviewed in the app.py file.
