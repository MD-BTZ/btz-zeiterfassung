# BTZ Zeiterfassung - Project Cleanup Plan

## 🎯 **Cleanup Goals**
- Remove outdated test files and test results
- Clean up duplicate migration scripts 
- Remove temporary HTML test pages
- Consolidate log files
- Remove unused backup files
- Keep only essential files for production

## 🗂️ **Files to Remove**

### **Test Files & Results (No longer needed)**
```bash
# Test Python scripts
test_menu_selenium.py
test_break_placement.py  
test_dropdown_comprehensive.py
test_complete_flow.py
test_detailed_menu.py

# Test HTML pages
dropdown_test.html
menu_test.html
test_responsive.html
debug_page_source.html
logged_in_page.html

# Test result JSON files
detailed_menu_test_results.json
dropdown_test_results_simple.json
dropdown_menu_test_results.json
menu_structure_analysis.json
final_menu_validation.json
menu_error_analysis.json
menu_test_results.json
```

### **Duplicate Migration Scripts (Keep originals, remove duplicates)**
```bash
# Duplicates in root (originals are in unused_backup/migration_scripts/)
migrate_user_break_preferences.py
migrate_passwords.py
migrate_temp_passwords.py
```

### **Old Log Files**
```bash
break_validation.log
code_migration.log  
fix_auto_breaks.log
migration.log
```

### **Temporary/Debug Files**
```bash
temp_route.py
temp_style_changes.txt
session_cookies.txt
nohup.out
```

### **Legacy Script Files**
```bash
add_arbzg_breaks.py  # Keep only v2 version
add_description_column.py  # One-time migration, completed
fix_auto_breaks_flag.py    # One-time fix, completed
update_password_code.py    # One-time update, completed
```

### **Documentation Files to Keep Updated**
```bash
# Keep and update
README.md
requirements.txt
run_migrations.sh

# Consolidate documentation
CSS_CLEANUP_COMPLETE.md
INDEX_MODERNIZATION_COMPLETE.md  
MODERNIZATION_COMPLETE.md
UNIVERSAL_GLASS_MORPHISM_COMPLETE.md
MENU_FUNCTIONALITY_REPORT.md
```

## 🎯 **Files to Keep (Essential for Production)**

### **Core Application**
- `app.py` - Main Flask application
- `requirements.txt` - Dependencies
- `attendance.db` - Production database

### **Active Migration Scripts**
- `migrate_db.py` - Base database migration
- `fix_settings.py` - Settings configuration
- `migrate_arbzg.py` - ArbZG compliance migration  
- `add_arbzg_breaks_v2.py` - Enhanced break placement
- `check_and_fix_db.py` - Database validation
- `run_migrations.sh` - Migration orchestration

### **Utility Scripts**
- `reset_admin.py` - Admin reset functionality
- `init_db_test.py` - Database initialization testing

### **Essential Test Scripts**
- `test_menu_login.py` - Basic login functionality test
- `test_dropdown_simple.py` - Simple dropdown validation

### **Active Static Files**
- `static/` directory with current CSS/JS
- `templates/` directory with current templates

### **Documentation**
- `docs/` directory with current documentation
- `unused_backup/` directory (keep as archive)

## ⚡ **Cleanup Commands**

### Phase 1: Remove Test Files
```bash
rm test_menu_selenium.py test_break_placement.py test_dropdown_comprehensive.py
rm test_complete_flow.py test_detailed_menu.py
rm dropdown_test.html menu_test.html test_responsive.html
rm debug_page_source.html logged_in_page.html
```

### Phase 2: Remove Test Results
```bash
rm *.json  # Remove all test result JSON files
```

### Phase 3: Remove Duplicate Migrations
```bash
rm migrate_user_break_preferences.py migrate_passwords.py migrate_temp_passwords.py
```

### Phase 4: Remove Old Logs & Temp Files
```bash
rm break_validation.log code_migration.log fix_auto_breaks.log migration.log
rm temp_route.py temp_style_changes.txt session_cookies.txt nohup.out
```

### Phase 5: Remove Completed One-Time Scripts
```bash
rm add_arbzg_breaks.py add_description_column.py
rm fix_auto_breaks_flag.py update_password_code.py
```

### Phase 6: Consolidate Documentation
```bash
# Create single comprehensive documentation file
# Keep unused_backup/ as archive
```

## 📊 **Before/After File Count**
- **Before Cleanup:** ~100+ files
- **After Cleanup:** ~40-50 essential files
- **Reduction:** ~50% file count reduction

## ✅ **Verification Steps**
1. Ensure application runs correctly: `python app.py`
2. Test basic functionality: login, attendance, menus
3. Verify dropdown menus work with our fixes
4. Run remaining essential tests
5. Check database migrations still work

## 🔄 **Rollback Plan**
- All removed files are preserved in `unused_backup/`
- Can restore any file if needed
- Database backups remain intact
- Git history preserves all changes
