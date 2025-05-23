# Project Cleanup Documentation

## Overview
This document records the cleanup process performed on the BTZ Zeiterfassung project to remove redundant and unused files.

## Date
Cleanup performed on: May 23, 2025

## Files Moved to Backup

### Backup Files
- `app.py.1747896547.bak` - Old backup of the main application file
- `templates/user_management.html.bak` - Backup of user management template
- `templates/user_management.html.bak2` - Additional backup of user management template
- `templates/user_management.html.old` - Old version of user management template
- `attendance_backup_1747896474.db` - Database backup
- `attendance_backup_1747896511.db` - Additional database backup
- `templates/break_settings.html.new`
- `templates/user_management.html.new-fixed`
- `templates/user_report.html.new`

### Consolidated CSS Files
The following CSS files were consolidated into `layout-fixes.css`:
- `static/content-fix.css` - Content padding adjustments
- `static/icon-fix.css` - Font Awesome icon fixes
- `static/page-layout-fix.css` - Layout fixes for page structure
- `static/menu-fix.css` - Additional menu fixes
- `static/menu-position-fix.css` - Empty file kept for compatibility

### Unused/Empty CSS & JS Files
- `static/menu-dropdown.js` - Empty file
- `static/menu-dropdown.css` - Placeholder file with comments only
- `static/mobile-dropdown.css` - Empty file

### One-Time Migration Scripts
These scripts were used for one-time database migrations and are no longer needed in the primary codebase:
- `migrate_user_break_preferences.py` - Added enhanced user break preferences
- `migrate_passwords.py` - Migrated passwords to users table
- `migrate_temp_passwords.py` - Added verification hash to temp_passwords table
- `add_description_column.py` - Added description column to breaks table
- `fix_auto_breaks_flag.py` - Fixed records with automatic breaks
- `update_password_code.py` - Updated password handling in app.py
- `fix_missing_breaks.py` 
- `cleanup_tables.py`
- `break_placement_validation.py`
- `add_arbzg_breaks.py` - Original version replaced by v2

### Miscellaneous Files
- `temp_route.py` - Contains a route that should be integrated into app.py
- `test_run.sh` - Test script not needed in production
- `nohup.out` - Output log from nohup command

### Log Files
The following log files were backed up:
- `break_validation.log`
- `code_migration.log` 
- `fix_auto_breaks.log`
- `migration.log`

## Migration Script Updates
Updated `run_migrations.sh` to only use the enhanced version of ArbZG breaks placement (v2) instead of running both versions sequentially.

## Current Active Scripts
The following scripts remain active in the project:
- `app.py` - Main application file
- `migrate_db.py` - Base migration script
- `fix_settings.py` - Settings fix script
- `migrate_arbzg.py` - ArbZG migration script
- `add_arbzg_breaks_v2.py` - Enhanced ArbZG breaks script
- `check_and_fix_db.py` - Database schema checker and fixer
- `reset_admin.py` - Admin reset utility

## CSS Consolidation (COMPLETED)

### Phase 1: Initial Consolidation ✅
Created `layout-fixes.css` which combines all the layout and UI fixes from separate files to improve maintainability and reduce HTTP requests.

### Phase 2: Complete Unification ✅
**Date:** May 23, 2025

Created unified `static/app.css` (733 lines) containing:
- CSS variables for colors, spacing, typography
- Base styles and typography rules
- Layout components and navigation styling
- Form and button styling
- Table and break management styles
- Modal and alert components
- Responsive design breakpoints
- Print styles

**Template Updates:**
- Updated `templates/head_includes.html` to use only unified `app.css`
- Removed legacy CSS references from all template files
- Preserved external dependencies (Font Awesome, jQuery UI)

**Legacy Files Moved to Backup:**
- `static/*.css` files (15 files) → `unused_backup/css_legacy_files/static/`
- `static/css/*.css` files (12 files) → `unused_backup/css_legacy_files/static_css/`

**Benefits:**
- Single stylesheet for entire application
- Reduced HTTP requests from 15+ to 1 CSS file
- Improved maintainability and consistency
- Easier theming and style updates
- Better performance and caching

**Testing:**
- Application tested and verified working with unified CSS
- All pages render correctly with consistent styling
- Responsive design maintained across all breakpoints
